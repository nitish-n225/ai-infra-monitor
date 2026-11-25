"""
Real End-to-End Live System Test on Windows:
1. Starts real FastAPI backend subprocess with JWT & Admin Key auth
2. Starts real Streamlit dashboard subprocess
3. Connects authenticated WebSocket client to /ws/live?token=...
4. Starts real Windows Monitoring Agent subprocess (SQLite WAL state, real Event Viewer, real multi-drive metrics, app log tailing)
5. Confirms device registration, heartbeat, real Windows logs, real CPU/RAM/disk_volumes, WebSocket push, RCA incidents
6. Stops the monitoring agent and confirms device transitions automatically to OFFLINE!
"""
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

import requests
import websockets

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_http_ok(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise TimeoutError(f"Service did not become ready at {url} within {timeout}s")


async def _collect_ws_events(ws_url: str, collected: list, stop_flag: asyncio.Event):
    async with websockets.connect(ws_url, open_timeout=5) as ws:
        while not stop_flag.is_set():
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                collected.append(json.loads(raw))
            except asyncio.TimeoutError:
                continue
            except Exception:
                break


def run_e2e_live_test():
    backend_port = _free_port()
    dashboard_port = _free_port()
    backend_url = f"http://127.0.0.1:{backend_port}"
    dashboard_url = f"http://127.0.0.1:{dashboard_port}"
    admin_key = "e2e-live-admin-key"
    admin_pw = "E2eStrongPass!2026"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        env = os.environ.copy()
        env["OPENBLAS_NUM_THREADS"] = "1"
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["MONITOR_BACKEND_HOST"] = "127.0.0.1"
        env["MONITOR_BACKEND_PORT"] = str(backend_port)
        env["MONITOR_BACKEND_URL"] = backend_url
        env["MONITOR_DB_PATH"] = str(tmp_path / "e2e_monitor.db")
        env["MONITOR_FAISS_DIR"] = str(tmp_path / "e2e_faiss")
        env["MONITOR_ADMIN_KEY"] = admin_key
        env["MONITOR_ADMIN_USER"] = "admin"
        env["MONITOR_ADMIN_PASSWORD"] = admin_pw
        env["MONITOR_JWT_SECRET"] = "e2e-jwt-secret-key-at-least-32-chars"
        env["DEVICE_OFFLINE_SECONDS"] = "6"

        app_log_file = tmp_path / "live_service.log"
        app_log_file.write_text("2026-11-25 20:00:01 [INFO] [order-api] Service boot complete\n", encoding="utf-8")

        agent_cfg_path = tmp_path / "agent_config.json"
        agent_state_path = tmp_path / "agent_state.db"

        backend_proc = None
        dash_proc = None
        agent_proc = None

        try:
            print(f"[E2E] 1. Starting FastAPI backend on {backend_url} ...")
            backend_proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "backend.server:app", "--host", "127.0.0.1", "--port", str(backend_port)],
                cwd=str(ROOT_DIR),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
            _wait_http_ok(f"{backend_url}/health", timeout=30.0)
            print("[E2E]    Backend healthy.")

            print(f"[E2E] 2. Starting Streamlit dashboard on {dashboard_url} ...")
            dash_proc = subprocess.Popen(
                [
                    sys.executable, "-m", "streamlit", "run", "app.py",
                    "--server.port", str(dashboard_port),
                    "--server.address", "127.0.0.1",
                    "--server.headless", "true",
                    "--browser.gatherUsageStats", "false",
                ],
                cwd=str(ROOT_DIR),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
            _wait_http_ok(f"{dashboard_url}/_stcore/health", timeout=60.0)
            print("[E2E]    Streamlit dashboard healthy.")

            # Authenticate as operator via JWT login
            login_resp = requests.post(
                f"{backend_url}/api/v1/auth/login",
                json={"username": "admin", "password": admin_pw},
                timeout=5,
            )
            login_resp.raise_for_status()
            jwt_token = login_resp.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {jwt_token}"}
            ws_url = f"ws://127.0.0.1:{backend_port}/ws/live?token={quote(jwt_token)}"

            tok_resp = requests.post(
                f"{backend_url}/api/v1/enrollment-tokens",
                headers=auth_headers,
                json={"label": "E2E Live Test", "client_org": "EnterpriseProd", "max_uses": 5, "expires_hours": 1},
                timeout=5,
            )
            tok_resp.raise_for_status()
            enroll_token = tok_resp.json()["token"]

            agent_cfg_path.write_text(
                json.dumps({
                    "backend_url": backend_url,
                    "enrollment_token": enroll_token,
                    "client_org": "EnterpriseProd",
                    "device_id": "e2e-real-windows-laptop",
                    "consent_accepted": True,
                    "heartbeat_interval_sec": 2,
                    "telemetry_interval_sec": 2,
                    "log_poll_interval_sec": 2,
                    "event_channels": ["System", "Application"],
                    "include_security_events": False,
                    "watched_log_paths": [str(app_log_file)],
                    "initial_event_lookback": 10,
                }),
                encoding="utf-8",
            )

            async def run_live_checks():
                ws_events = []
                stop_flag = asyncio.Event()
                ws_task = asyncio.create_task(_collect_ws_events(ws_url, ws_events, stop_flag))

                print("[E2E] 3. Starting real Windows monitoring agent...")
                nonlocal agent_proc
                agent_proc = subprocess.Popen(
                    [
                        sys.executable, "-m", "agent.main",
                        "--config", str(agent_cfg_path),
                        "--state", str(agent_state_path),
                    ],
                    cwd=str(ROOT_DIR),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.STDOUT,
                )

                deadline = time.time() + 30.0
                registered_dev = None
                while time.time() < deadline:
                    devs = requests.get(f"{backend_url}/api/v1/devices", headers=auth_headers, timeout=10).json()
                    if devs and devs[0].get("latest_telemetry"):
                        registered_dev = devs[0]
                        break
                    await asyncio.sleep(1.0)

                assert registered_dev is not None, "Agent did not register and send telemetry in time"
                assert registered_dev["status"] == "ONLINE"
                assert registered_dev["client_org"] == "EnterpriseProd"
                tel = registered_dev["latest_telemetry"]
                assert 0.0 <= tel["cpu_percent"] <= 100.0
                assert 0.0 < tel["ram_percent"] <= 100.0
                assert len(tel.get("disk_volumes", [])) >= 1
                print(f"[E2E] 4-8. Confirmed org=EnterpriseProd registration, heartbeat, CPU={tel['cpu_percent']}%, RAM={tel['ram_percent']}%, Volumes={len(tel['disk_volumes'])}")

                with open(app_log_file, "a", encoding="utf-8") as f:
                    f.write("2026-11-25 20:00:10 [CRITICAL] [db-postgres] FATAL: remaining connection slots reserved for superuser\n")

                ev_deadline = time.time() + 20.0
                events = []
                incidents = []
                while time.time() < ev_deadline:
                    events = requests.get(f"{backend_url}/api/v1/events", headers=auth_headers, params={"device_id": "e2e-real-windows-laptop"}, timeout=10).json()
                    incidents = requests.get(f"{backend_url}/api/v1/incidents", headers=auth_headers, params={"device_id": "e2e-real-windows-laptop"}, timeout=10).json()
                    win_evts = [e for e in events if e["source_type"] == "WINDOWS_EVENT_LOG"]
                    if win_evts and incidents:
                        break
                    await asyncio.sleep(1.0)

                win_evts = [e for e in events if e["source_type"] == "WINDOWS_EVENT_LOG"]
                assert len(win_evts) > 0, "Expected real Windows Event Viewer logs ingested"
                assert len(incidents) > 0, "Expected AI incident generated from real log evidence"

                ws_types = {m.get("type") for m in ws_events}
                assert "INIT" in ws_types
                assert "NEW_TELEMETRY" in ws_types or "NEW_LOGS" in ws_types
                print(f"[E2E] 9-10. Confirmed {len(win_evts)} Windows Event logs, {len(incidents)} RCA incident(s), and authenticated WebSocket types {ws_types}")

                print("[E2E] 11. Stopping monitoring agent to verify offline detection...")
                agent_proc.terminate()
                agent_proc.wait(timeout=10)
                agent_proc = None

                off_deadline = time.time() + 18.0
                final_status = "ONLINE"
                while time.time() < off_deadline:
                    dev_now = requests.get(f"{backend_url}/api/v1/devices/e2e-real-windows-laptop", headers=auth_headers, timeout=10).json()
                    final_status = dev_now["status"]
                    if final_status == "OFFLINE":
                        break
                    await asyncio.sleep(1.0)

                assert final_status == "OFFLINE", f"Expected device OFFLINE after stopping agent, got {final_status}"
                print("[E2E] 12. Confirmed device transitioned to OFFLINE automatically!")

                stop_flag.set()
                await ws_task

            asyncio.run(run_live_checks())

        finally:
            for proc in (agent_proc, dash_proc, backend_proc):
                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except Exception:
                        proc.kill()


if __name__ == "__main__":
    print("=" * 65)
    print("Running Live End-to-End Windows Monitoring Verification")
    print("=" * 65)
    run_e2e_live_test()
    print("=" * 65)
    print("[SUCCESS] All Live End-to-End verification steps passed!")
    print("=" * 65)
