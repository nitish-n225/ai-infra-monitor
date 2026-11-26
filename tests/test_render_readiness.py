"""
Render Deployment Readiness & Persistence Tests:
- Validates render.yaml & .python-version
- Verifies PostgreSQL URL normalization & SQL placeholder translation
- Verifies FAISS index rebuild from persisted database events after ephemeral disk wipe
- Verifies BACKEND_URL resolution & CORS origin configuration
"""
import os
import sys
import tempfile
from pathlib import Path

import yaml

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))


def test_render_yaml_and_runtime():
    ry_path = ROOT_DIR / "render.yaml"
    assert ry_path.exists()
    data = yaml.safe_load(ry_path.read_text(encoding="utf-8"))
    assert "services" in data and "databases" in data
    svc = data["services"][0]
    assert svc["startCommand"] == "uvicorn backend.server:app --host 0.0.0.0 --port $PORT"
    assert svc["healthCheckPath"] == "/health"
    assert (ROOT_DIR / ".python-version").read_text(encoding="utf-8").strip() == "3.11.11"
    assert (ROOT_DIR / ".gitignore").exists()
    print("[PASS] render.yaml, .python-version, and .gitignore validated.")


def test_postgres_url_and_sql_translation():
    from backend.database import get_database_url, _translate_sql

    old_val = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = "postgres://user:pass@host:5432/db"
        assert get_database_url() == "postgresql://user:pass@host:5432/db"
        assert _translate_sql("SELECT * FROM devices WHERE device_id = ?", True) == "SELECT * FROM devices WHERE device_id = %s"
        assert _translate_sql("SELECT * FROM devices WHERE device_id = ?", False) == "SELECT * FROM devices WHERE device_id = ?"
    finally:
        if old_val is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old_val
    print("[PASS] PostgreSQL URL normalization and SQL placeholder translation verified.")


def test_faiss_rebuild_after_ephemeral_disk_wipe():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        old_db = os.environ.get("MONITOR_DB_PATH")
        old_pg = os.environ.pop("DATABASE_URL", None)
        old_lm = os.environ.get("LOW_MEMORY_MODE")
        os.environ["MONITOR_DB_PATH"] = str(tmp_path / "rebuild_test.db")
        os.environ["LOW_MEMORY_MODE"] = "true"
        try:
            from backend.database import init_monitoring_db, upsert_device_registration, insert_events_deduplicated
            from backend.ai_pipeline import PersistentLiveVectorStore

            init_monitoring_db()
            upsert_device_registration(
                {"device_id": "dev-rebuild", "hostname": "WIN-REBUILD"},
                token_hash="hash",
                config={},
            )
            insert_events_deduplicated([{
                "event_uid": "uid-rebuild-1",
                "device_id": "dev-rebuild",
                "hostname": "WIN-REBUILD",
                "timestamp": "2026-11-25T21:00:00Z",
                "source_type": "WINDOWS_EVENT_LOG",
                "channel": "System",
                "event_id": 7031,
                "record_number": 10,
                "level": "CRITICAL",
                "service": "Service Control Manager",
                "message": "PostgreSQL database connection slots exhausted",
                "raw_line": "2026-11-25T21:00:00Z [CRITICAL] [db] connection slots exhausted",
                "is_critical": 1,
                "rca_category": "DATABASE_FAILURE",
                "similar_incidents": [],
            }])

            # Simulate fresh ephemeral disk with empty FAISS directory
            faiss_dir = tmp_path / "ephemeral_faiss"
            vs = PersistentLiveVectorStore(index_dir=faiss_dir)
            assert vs.get_stats()["total_vectors"] == 0

            rebuilt = vs.rebuild_from_db_if_empty()
            assert rebuilt == 1
            assert vs.get_stats()["total_vectors"] == 1
            res = vs.search("database connection slots", top_k=1, min_similarity=0.1)
            assert res["total_matches"] == 1
        finally:
            if old_db is None:
                os.environ.pop("MONITOR_DB_PATH", None)
            else:
                os.environ["MONITOR_DB_PATH"] = old_db
            if old_pg is not None:
                os.environ["DATABASE_URL"] = old_pg
            if old_lm is None:
                os.environ.pop("LOW_MEMORY_MODE", None)
            else:
                os.environ["LOW_MEMORY_MODE"] = old_lm
    print("[PASS] FAISS index rebuild from persisted database verified.")


def test_backend_url_env_and_cors():
    from src.realtime_client import get_backend_url, is_remote_backend_configured
    from backend.server import _parse_cors_origins

    old_b = os.environ.get("BACKEND_URL")
    old_c = os.environ.get("CORS_ALLOWED_ORIGINS")
    try:
        os.environ["BACKEND_URL"] = "https://ai-monitor-backend.onrender.com/"
        assert get_backend_url() == "https://ai-monitor-backend.onrender.com"
        assert is_remote_backend_configured() is True

        os.environ["CORS_ALLOWED_ORIGINS"] = "https://my-dash.streamlit.app, http://localhost:8501"
        assert _parse_cors_origins() == ["https://my-dash.streamlit.app", "http://localhost:8501"]
    finally:
        if old_b is None:
            os.environ.pop("BACKEND_URL", None)
        else:
            os.environ["BACKEND_URL"] = old_b
        if old_c is None:
            os.environ.pop("CORS_ALLOWED_ORIGINS", None)
        else:
            os.environ["CORS_ALLOWED_ORIGINS"] = old_c
    print("[PASS] BACKEND_URL resolution and CORS origin parsing verified.")


if __name__ == "__main__":
    print("=" * 65)
    print("Running Render Deployment Readiness Tests")
    print("=" * 65)
    test_render_yaml_and_runtime()
    test_postgres_url_and_sql_translation()
    test_faiss_rebuild_after_ephemeral_disk_wipe()
    test_backend_url_env_and_cors()
    print("=" * 65)
    print("[SUCCESS] All Render deployment readiness checks passed!")
    print("=" * 65)

