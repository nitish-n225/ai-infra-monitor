"""
Automated Tests for Windows Monitoring Agent Collectors, SQLite Queue, Multi-Drive Metrics & Windows Service.
"""
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.config import AgentConfig, generate_stable_device_id
from agent.state_store import AgentStateStore
from agent.metrics_collector import SystemMetricsCollector
from agent.win_event_collector import WindowsEventLogCollector
from agent.file_log_collector import ApplicationLogCollector
import agent.win_service as win_service


def test_real_system_metrics_and_multidrive():
    collector = SystemMetricsCollector()
    m = collector.collect()
    assert 0.0 <= m["cpu_percent"] <= 100.0
    assert m["cpu_cores"] >= 1
    assert 0.0 < m["ram_percent"] <= 100.0
    assert m["ram_total_gb"] > 0
    assert m["disk_total_gb"] > 0
    assert isinstance(m["disk_volumes"], list) and len(m["disk_volumes"]) >= 1
    assert m["process_count"] > 5
    assert len(m["top_processes"]) > 0
    assert m["uptime_seconds"] > 0
    print(f"[PASS] Real OS metrics + {len(m['disk_volumes'])} disk volume(s): CPU={m['cpu_percent']}%, RAM={m['ram_percent']}%, Procs={m['process_count']}")


def test_sqlite_state_and_offline_queue():
    with tempfile.TemporaryDirectory() as tmp:
        state = AgentStateStore(Path(tmp) / "agent_state.db")
        state.set_credentials("dev-1", "tok-secret")
        assert state.get_credentials() == ("dev-1", "tok-secret")

        state.enqueue_events([{"event_uid": "e1", "msg": "a"}, {"event_uid": "e2", "msg": "b"}])
        assert state.pending_count() == 2
        popped = state.pop_pending_events(batch_size=1)
        assert len(popped) == 1 and popped[0]["event_uid"] == "e1"
        assert state.pending_count() == 1
        print("[PASS] SQLite WAL state store and offline retry queue verified.")


def test_real_windows_event_log_collector_and_bookmarks():
    with tempfile.TemporaryDirectory() as tmp:
        state = AgentStateStore(Path(tmp) / "state.db")
        collector = WindowsEventLogCollector(
            device_id="test-win-device",
            state_store=state,
            channels=["System", "Application"],
            include_security=False,
            initial_lookback=5,
        )
        first_batch = collector.collect_new_events(max_per_channel=20)
        assert len(first_batch) > 0, "Expected real Windows System/Application events"
        first_uids = {e["event_uid"] for e in first_batch}
        second_batch = collector.collect_new_events(max_per_channel=20)
        second_uids = {e["event_uid"] for e in second_batch}
        assert first_uids.isdisjoint(second_uids), "Bookmarks must prevent duplicate Windows events"
        print(f"[PASS] Real Windows Event Viewer logs collected ({len(first_batch)} events) with SQLite bookmark deduplication.")


def test_application_log_incremental_and_rotation():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        log_file = tmp_path / "app.log"
        state = AgentStateStore(tmp_path / "state.db")
        collector = ApplicationLogCollector("test-dev", state, [str(log_file)])

        log_file.write_text(
            "2026-11-25 10:00:00 [INFO] [worker] Started cleanly\n"
            "2026-11-25 10:00:01 [ERROR] [db-client] FATAL: connection pool exhausted\n",
            encoding="utf-8",
        )
        batch1 = collector.collect_new_lines()
        assert len(batch1) == 2
        assert collector.collect_new_lines() == []

        with open(log_file, "a", encoding="utf-8") as f:
            f.write("2026-11-25 10:00:05 [CRITICAL] [cache] Out of memory\n")
        batch2 = collector.collect_new_lines()
        assert len(batch2) == 1

        log_file.write_text("2026-11-25 10:01:00 [INFO] [worker] Log rotated\n", encoding="utf-8")
        batch3 = collector.collect_new_lines()
        assert len(batch3) == 1 and "Log rotated" in batch3[0]["message"]
        print("[PASS] Application log incremental tailing, rotation detection, and dedup verified.")


def test_config_and_win_service_module():
    dev_id = generate_stable_device_id()
    assert len(dev_id) >= 32
    assert win_service.HAS_WIN32_SERVICE is True
    assert hasattr(win_service, "EnterpriseAIMonitorService")
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "agent_config.json"
        cfg = AgentConfig(backend_url="https://monitor.example.com", client_org="AcmeCorp", enrollment_token="enroll_abc", consent_accepted=True)
        cfg.save(cfg_path)
        loaded = AgentConfig.load(cfg_path)
        assert loaded.client_org == "AcmeCorp"
    print("[PASS] Agent config, org tagging, and pywin32 Windows Service module verified.")


if __name__ == "__main__":
    print("=" * 65)
    print("Running Industry-Grade Windows Agent Collector Tests")
    print("=" * 65)
    test_real_system_metrics_and_multidrive()
    test_sqlite_state_and_offline_queue()
    test_real_windows_event_log_collector_and_bookmarks()
    test_application_log_incremental_and_rotation()
    test_config_and_win_service_module()
    print("=" * 65)
    print("[SUCCESS] All Agent Collector tests passed!")
    print("=" * 65)
