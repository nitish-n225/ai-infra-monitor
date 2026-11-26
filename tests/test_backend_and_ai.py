"""
Automated Integration Tests for Central FastAPI Backend:
- Operator JWT Authentication & API Key Enforcement (401 on unauth)
- Multi-Tenant Client Org Scoping
- Hardware Telemetry Trend Forecasting
- Live AI RCA, FAISS, Assistant, Audit Logs, Alert Webhooks, Retention Pruning & Revocation
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("LOW_MEMORY_MODE", "true")

TMP_DIR = tempfile.TemporaryDirectory()
os.environ["MONITOR_DB_PATH"] = str(Path(TMP_DIR.name) / "test_monitor.db")
os.environ["MONITOR_FAISS_DIR"] = str(Path(TMP_DIR.name) / "test_faiss")
os.environ["MONITOR_ADMIN_KEY"] = "test-admin-secret-key"
os.environ["MONITOR_ADMIN_USER"] = "admin"
os.environ["MONITOR_ADMIN_PASSWORD"] = "StrongTestPass!2026"
os.environ["MONITOR_JWT_SECRET"] = "test-jwt-signing-secret-key-at-least-32-bytes"

from fastapi.testclient import TestClient
from backend.server import app, live_vector_store
from backend.database import init_monitoring_db, mark_stale_devices_offline, prune_old_records


def run_backend_tests():
    init_monitoring_db()
    live_vector_store.reset()

    with TestClient(app) as client:
        # 0. Root & health endpoints must return 200
        r_root = client.get("/")
        assert r_root.status_code == 200 and r_root.json()["status"] == "online"
        assert client.get("/health").status_code == 200

        # 1. Unauthenticated requests to protected endpoints must fail with 401
        assert client.get("/api/v1/devices").status_code == 401
        assert client.get("/api/v1/events").status_code == 401
        assert client.post("/api/v1/enrollment-tokens", json={"label": "Unauth"}).status_code == 401

        # 2. Operator JWT Login
        assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401
        r_login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "StrongTestPass!2026"})
        assert r_login.status_code == 200
        jwt_token = r_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {jwt_token}"}

        # 3. Empty state check (0 devices)
        r_devs = client.get("/api/v1/devices", headers=admin_headers)
        assert r_devs.status_code == 200 and r_devs.json() == []

        # 4. Issue org-scoped enrollment token
        r_tok = client.post(
            "/api/v1/enrollment-tokens",
            headers=admin_headers,
            json={"label": "Acme Laptops", "client_org": "AcmeCorp", "max_uses": 5, "expires_hours": 24},
        )
        assert r_tok.status_code == 200
        enrollment_token = r_tok.json()["token"]

        # 5. Consent enforcement
        assert client.post(
            "/api/v1/devices/register",
            json={"device_id": "win-pc-001", "hostname": "LAB-PC-01", "enrollment_token": enrollment_token, "consent_confirmed": False},
        ).status_code == 400

        # 6. Valid registration inherits client_org from enrollment token
        r_reg = client.post(
            "/api/v1/devices/register",
            json={
                "device_id": "win-pc-001",
                "hostname": "ACME-LAPTOP-01",
                "os_name": "Windows",
                "os_version": "10.0.22631",
                "architecture": "AMD64",
                "ip_address": "192.168.1.44",
                "enrollment_token": enrollment_token,
                "consent_confirmed": True,
            },
        )
        assert r_reg.status_code == 200
        assert r_reg.json()["device"]["client_org"] == "AcmeCorp"
        dev_token = r_reg.json()["device_token"]
        dev_headers = {"Authorization": f"Bearer {dev_token}", "X-Device-ID": "win-pc-001"}

        # 7. Org filter check
        assert len(client.get("/api/v1/devices", headers=admin_headers, params={"client_org": "AcmeCorp"}).json()) == 1
        assert len(client.get("/api/v1/devices", headers=admin_headers, params={"client_org": "OtherOrg"}).json()) == 0

        # 8. Send rising RAM telemetry snapshots to verify Hardware Trend Forecasting
        for idx, ram_val in enumerate([74.0, 77.0, 80.5, 84.0]):
            r_tel = client.post(
                "/api/v1/ingest/telemetry",
                headers=dev_headers,
                json={
                    "timestamp": f"2026-11-25T15:00:0{idx}Z",
                    "cpu_percent": 45.0,
                    "cpu_cores": 8,
                    "ram_percent": ram_val,
                    "ram_used_gb": 12.0,
                    "ram_total_gb": 16.0,
                    "disk_percent": 55.0,
                    "disk_used_gb": 220.0,
                    "disk_total_gb": 400.0,
                    "disk_volumes": [{"mount": "C:\\", "fstype": "NTFS", "percent": 55.0, "used_gb": 220.0, "total_gb": 400.0}],
                    "net_bytes_sent": 100000,
                    "net_bytes_recv": 250000,
                    "net_sent_kbps": 12.4,
                    "net_recv_kbps": 45.8,
                    "process_count": 140,
                    "top_processes": [{"pid": 1234, "name": "python.exe", "cpu_percent": 15.0, "memory_percent": 4.2}],
                    "services": [{"name": "W32Time", "display_name": "Windows Time", "status": "running", "start_type": "automatic"}],
                    "uptime_seconds": 1200 + idx * 10,
                },
            )
            assert r_tel.status_code == 200

        r_fc = client.get("/api/v1/devices/win-pc-001/forecast", headers=admin_headers)
        assert r_fc.status_code == 200
        assert r_fc.json()["ram_slope_per_sample"] > 2.0
        assert len(r_fc.json()["warnings"]) >= 1

        # 9. Log ingestion + dedup + RCA + FAISS + Assistant
        events_payload = [
            {
                "event_uid": "evt-unique-001",
                "timestamp": "2026-11-25T15:00:10Z",
                "source_type": "WINDOWS_EVENT_LOG",
                "channel": "System",
                "event_id": 7031,
                "record_number": 501,
                "level": "ERROR",
                "service": "Service Control Manager",
                "message": "The PostgreSQL service terminated unexpectedly. Connection pool exhausted.",
                "raw_line": "2026-11-25T15:00:10Z [ERROR] [db-postgres] FATAL: remaining connection slots reserved",
            },
            {
                "event_uid": "evt-unique-002",
                "timestamp": "2026-11-25T15:00:11Z",
                "source_type": "WINDOWS_EVENT_LOG",
                "channel": "Application",
                "event_id": 1000,
                "record_number": 502,
                "level": "CRITICAL",
                "service": "cache-redis-01",
                "message": "Out of memory: OOMKilled exit code 137",
                "raw_line": "2026-11-25T15:00:11Z [CRITICAL] [cache-redis-01] OOMKilled exit code 137",
            },
        ]
        assert client.post("/api/v1/ingest/logs", headers=dev_headers, json={"events": events_payload}).json()["inserted"] == 2
        assert client.post("/api/v1/ingest/logs", headers=dev_headers, json={"events": events_payload}).json()["duplicates_skipped"] == 2

        assert client.post("/api/v1/search/semantic", headers=admin_headers, json={"query": "database connection slots", "top_k": 3}).json()["total_matches"] >= 1
        assert len(client.post("/api/v1/assistant/query", headers=admin_headers, json={"query": "What are the most critical incidents?", "device_id": "win-pc-001"}).json()["evidence"]) >= 1

        # 10. Alert webhook settings & mocked HTTP dispatch test
        r_aset = client.put(
            "/api/v1/alerts/settings",
            headers=admin_headers,
            json={"webhook_url": "https://hooks.example.test/webhook", "notify_on_critical_incident": True, "notify_on_device_offline": True, "cooldown_seconds": 60},
        )
        assert r_aset.status_code == 200
        with patch("backend.alerts_dispatcher.requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            r_atest = client.post("/api/v1/alerts/test", headers=admin_headers)
            assert r_atest.status_code == 200
            assert r_atest.json()["sent"] is True

        # 11. Audit log verification
        audits = client.get("/api/v1/audit-logs", headers=admin_headers).json()
        actions = {a["action"] for a in audits}
        assert "LOGIN_SUCCESS" in actions
        assert "TOKEN_CREATED" in actions
        assert "DEVICE_REGISTERED" in actions

        # 12. Revocation & Retention pruning
        assert client.post("/api/v1/devices/win-pc-001/revoke", headers=admin_headers, json={"reason": "Audit"}).json()["status"] == "REVOKED"
        assert client.post("/api/v1/devices/win-pc-001/heartbeat", headers=dev_headers, json={}).status_code == 403
        mark_stale_devices_offline(timeout_seconds=0)
        prune_res = prune_old_records(event_retention_days=30, telemetry_retention_days=14)
        assert "deleted_events" in prune_res
        print("[PASS] All Auth, Org Isolation, Trend Forecast, Alerts, Audit Log, FAISS & Revocation tests passed!")


if __name__ == "__main__":
    print("=" * 65)
    print("Running Industry-Grade Backend & AI Integration Tests")
    print("=" * 65)
    run_backend_tests()
    TMP_DIR.cleanup()
    print("=" * 65)
    print("[SUCCESS] Backend & Live AI integration tests passed!")
    print("=" * 65)
