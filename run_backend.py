"""
Startup script for the Central FastAPI Monitoring Backend.
"""
import os
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uvicorn


def main():
    host = os.environ.get("MONITOR_BACKEND_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT") or os.environ.get("MONITOR_BACKEND_PORT") or "8000")

    from backend.database import init_monitoring_db
    from backend.auth import get_or_init_admin_key, ensure_default_admin_user, ensure_default_enrollment_token

    init_monitoring_db()
    admin_key = get_or_init_admin_key()
    ensure_default_admin_user()
    env_tok = ensure_default_enrollment_token()

    print("=" * 72)
    print(" Enterprise Autonomous AI Infrastructure Monitoring - Central Backend")
    print("=" * 72)
    print(f" Listen Address : http://{host}:{port}")
    print(f" API Docs       : http://127.0.0.1:{port}/docs")
    print(f" WebSocket Live : ws://127.0.0.1:{port}/ws/live")
    print(f" SSE Stream     : http://127.0.0.1:{port}/api/v1/stream")
    print(f" Dashboard Login: username='admin' (password=MONITOR_ADMIN_PASSWORD or Admin Key)")
    print(f" Admin API Key  : {admin_key}")
    if env_tok:
        print(" Enrollment Tok : Loaded from MONITOR_ENROLLMENT_TOKEN env var")
    else:
        print(" Enrollment Tok : Generate in Dashboard -> Fleet Management (or POST /api/v1/enrollment-tokens)")
    print("=" * 72)

    uvicorn.run("backend.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
