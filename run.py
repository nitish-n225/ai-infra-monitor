import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import uvicorn

def main():
    print("=" * 65)
    print(" [SEC] AegisLog: Intelligent Log Anomaly & Threat Detection System")
    print("       College Mini-Project | Powered by FastAPI, ML & WebSockets")
    print("=" * 65)
    print("\n[+] Initializing SQLite Threat Database...")
    from storage.database import init_db
    init_db()

    print("[+] Loading/Training Isolation Forest Anomaly Detection Model...")
    from detection.ml_detector import MLAnomalyDetector
    detector = MLAnomalyDetector()
    print("    -> ML Model Loaded & Calibrated Successfully.")

    print("\n[+] Starting FastAPI Application Server on http://127.0.0.1:8000")
    print("    -> Open your browser to: http://127.0.0.1:8000")
    print("    -> Interactive API Docs:  http://127.0.0.1:8000/docs")
    print("=" * 65)
    print("Press CTRL+C at any time to stop the server.\n")

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    main()
