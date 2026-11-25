"""
Main Entrypoint for the Windows Background Monitoring Agent.
Features:
- Explicit consent validation
- Rotating file logging for production diagnostics
- Exponential backoff with jitter on backend outage
- Durable SQLite WAL offline event buffering
"""
import argparse
import logging
from logging.handlers import RotatingFileHandler
import random
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agent.client import DeviceRevokedError, MonitoringBackendClient
from agent.config import AgentConfig, DEFAULT_CONFIG_PATH, DEFAULT_STATE_PATH
from agent.file_log_collector import ApplicationLogCollector
from agent.metrics_collector import SystemMetricsCollector
from agent.state_store import AgentStateStore
from agent.win_event_collector import WindowsEventLogCollector

logger = logging.getLogger("agent.main")

CONSENT_NOTICE = """
================================================================================
 ENTERPRISE AUTONOMOUS AI INFRASTRUCTURE MONITORING AGENT - CONSENT NOTICE
================================================================================
 This agent collects ONLY operational infrastructure telemetry and logs:
   1. Windows Event Viewer logs (System, Application, and optional Security)
   2. System hardware & service metrics (CPU, RAM, Disk, Network IO, Services)
   3. Explicitly configured application log file paths

 It does NOT collect personal files, passwords, keystrokes, or browser history.
================================================================================
"""


def setup_logging(log_file_path: Optional[str] = None) -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file_path:
        lp = Path(log_file_path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(str(lp), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


class WindowsMonitoringAgent:
    def __init__(self, config: AgentConfig, state_path: Path = DEFAULT_STATE_PATH):
        self.config = config
        self.state_store = AgentStateStore(state_path)
        self.client = MonitoringBackendClient(config, self.state_store)
        self.metrics_collector = SystemMetricsCollector()
        self.event_collector = WindowsEventLogCollector(
            device_id=config.device_id,
            state_store=self.state_store,
            channels=config.event_channels,
            include_security=config.include_security_events,
            allowed_security_event_ids=config.security_event_ids,
            initial_lookback=config.initial_event_lookback,
        )
        self.file_collector = ApplicationLogCollector(
            device_id=config.device_id,
            state_store=self.state_store,
            log_paths=config.watched_log_paths,
        )
        self._running = True

    def stop(self) -> None:
        self._running = False

    def _apply_remote_config(self, remote_cfg: Dict[str, Any]) -> None:
        if not remote_cfg:
            return
        self.config.heartbeat_interval_sec = int(remote_cfg.get("heartbeat_interval_sec", self.config.heartbeat_interval_sec))
        self.config.telemetry_interval_sec = int(remote_cfg.get("telemetry_interval_sec", self.config.telemetry_interval_sec))
        self.config.log_poll_interval_sec = int(remote_cfg.get("log_poll_interval_sec", self.config.log_poll_interval_sec))
        if "event_channels" in remote_cfg:
            self.event_collector.channels = list(remote_cfg["event_channels"])
        if "include_security_events" in remote_cfg:
            self.event_collector.include_security = bool(remote_cfg["include_security_events"])
            if self.event_collector.include_security and "Security" not in self.event_collector.channels:
                self.event_collector.channels.append("Security")
        if "watched_log_paths" in remote_cfg:
            self.file_collector.update_paths(list(remote_cfg["watched_log_paths"]))

    def run_cycle(self, force_all: bool = False) -> Dict[str, Any]:
        remote_cfg = self.client.ensure_enrolled()
        self._apply_remote_config(remote_cfg)

        metrics = self.metrics_collector.collect()
        self.client.send_heartbeat(uptime_seconds=metrics["uptime_seconds"])
        tel_res = self.client.send_telemetry(metrics)

        pending = self.state_store.pop_pending_events(batch_size=200)
        win_events = self.event_collector.collect_new_events(max_per_channel=100)
        app_events = self.file_collector.collect_new_lines(max_lines_per_file=200)
        all_events = pending + win_events + app_events

        logs_res = {"inserted": 0}
        if all_events:
            for i in range(0, len(all_events), 200):
                batch = all_events[i : i + 200]
                try:
                    res = self.client.send_logs(batch)
                    logs_res["inserted"] += int(res.get("inserted", 0))
                except DeviceRevokedError:
                    raise
                except Exception as e:
                    logger.warning("Failed sending log batch (%d events), queuing offline: %s", len(batch), e)
                    self.state_store.enqueue_events(all_events[i:])
                    break

        return {
            "telemetry": tel_res,
            "windows_events_collected": len(win_events),
            "app_events_collected": len(app_events),
            "logs_inserted": logs_res["inserted"],
        }

    def run_forever(self) -> None:
        logger.info("Starting Windows Monitoring Agent v2.0 (device_id=%s, backend=%s)", self.config.device_id, self.config.backend_url)

        backoff = 2.0
        while self._running:
            try:
                remote_cfg = self.client.ensure_enrolled()
                self._apply_remote_config(remote_cfg)
                break
            except DeviceRevokedError as e:
                logger.error("Device has been REVOKED by administrator. Stopping agent: %s", e)
                return
            except Exception as e:
                sleep_s = min(60.0, backoff) + random.uniform(0.0, 1.5)
                logger.warning("Enrollment attempt failed (%s). Retrying in %.1fs...", e, sleep_s)
                time.sleep(sleep_s)
                backoff = min(60.0, backoff * 1.8)

        last_hb = 0.0
        last_tel = 0.0
        last_logs = 0.0
        consecutive_failures = 0

        while self._running:
            now = time.monotonic()
            try:
                if now - last_tel >= self.config.telemetry_interval_sec:
                    metrics = self.metrics_collector.collect()
                    self.client.send_telemetry(metrics)
                    last_tel = now
                    if now - last_hb >= self.config.heartbeat_interval_sec:
                        remote_cfg = self.client.send_heartbeat(uptime_seconds=metrics["uptime_seconds"])
                        self._apply_remote_config(remote_cfg or {})
                        last_hb = now
                    consecutive_failures = 0
                elif now - last_hb >= self.config.heartbeat_interval_sec:
                    remote_cfg = self.client.send_heartbeat(uptime_seconds=0.0)
                    self._apply_remote_config(remote_cfg or {})
                    last_hb = now
                    consecutive_failures = 0

                if now - last_logs >= self.config.log_poll_interval_sec:
                    pending = self.state_store.pop_pending_events(batch_size=200)
                    win_events = self.event_collector.collect_new_events(max_per_channel=100)
                    app_events = self.file_collector.collect_new_lines(max_lines_per_file=200)
                    all_events = pending + win_events + app_events
                    if all_events:
                        for i in range(0, len(all_events), 200):
                            batch = all_events[i : i + 200]
                            try:
                                res = self.client.send_logs(batch)
                                logger.info(
                                    "Sent %d log events (inserted=%s, dedup_skipped=%s)",
                                    len(batch),
                                    res.get("inserted"),
                                    res.get("duplicates_skipped"),
                                )
                            except DeviceRevokedError:
                                raise
                            except Exception as e:
                                logger.warning("Backend unreachable, buffered %d events in SQLite offline queue: %s", len(all_events[i:]), e)
                                self.state_store.enqueue_events(all_events[i:])
                                break
                    last_logs = now

            except DeviceRevokedError as e:
                logger.error("Device REVOKED by administrator. Stopping monitoring agent immediately: %s", e)
                break
            except Exception as e:
                consecutive_failures += 1
                backoff_wait = min(30.0, (1.5 ** min(consecutive_failures, 6))) + random.uniform(0.0, 1.0)
                logger.warning("Agent loop transient error (%s). Backing off %.1fs...", e, backoff_wait)
                time.sleep(backoff_wait)
                continue

            time.sleep(1.0)


def main():
    parser = argparse.ArgumentParser(description="Windows Infrastructure Monitoring Agent")
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG_PATH), help="Path to agent_config.json")
    parser.add_argument("--state", type=str, default=str(DEFAULT_STATE_PATH), help="Path to agent_state.db")
    parser.add_argument("--backend-url", type=str, default=None, help="Central backend URL")
    parser.add_argument("--enrollment-token", type=str, default=None, help="Enrollment token issued by Admin Dashboard")
    parser.add_argument("--client-org", type=str, default=None, help="Client organization / tenant label")
    parser.add_argument("--accept-consent", action="store_true", help="Confirm explicit user consent for infrastructure monitoring")
    parser.add_argument("--include-security", action="store_true", help="Attempt to read selected Security Event Log IDs (requires privileges)")
    parser.add_argument("--once", action="store_true", help="Run one collection/upload cycle and exit")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    cfg = AgentConfig.load(cfg_path)
    if args.backend_url:
        cfg.backend_url = args.backend_url.rstrip("/")
    if args.enrollment_token:
        cfg.enrollment_token = args.enrollment_token.strip()
    if args.client_org:
        cfg.client_org = args.client_org.strip()
    if args.accept_consent:
        cfg.consent_accepted = True
    if args.include_security:
        cfg.include_security_events = True

    setup_logging(cfg.agent_log_path or str(cfg_path.parent / "agent.log"))

    if not cfg.backend_url:
        logger.error("Missing backend_url. Provide --backend-url or set MONITOR_BACKEND_URL / agent_config.json.")
        sys.exit(2)

    if not cfg.consent_accepted:
        print(CONSENT_NOTICE)
        logger.error("Explicit user consent is required. Re-run with --accept-consent or set consent_accepted=true in config.")
        sys.exit(3)

    if args.backend_url or args.enrollment_token or args.accept_consent or args.client_org:
        cfg.save(cfg_path)

    agent = WindowsMonitoringAgent(cfg, state_path=Path(args.state))

    def _handle_sig(signum, frame):
        logger.info("Shutdown signal received (%s). Stopping agent...", signum)
        agent.stop()

    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)

    if args.once:
        summary = agent.run_cycle(force_all=True)
        logger.info("Single cycle complete: %s", summary)
    else:
        agent.run_forever()


if __name__ == "__main__":
    main()
