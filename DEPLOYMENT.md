# Deployment & Operations Guide
**Enterprise Autonomous AI Infrastructure Monitoring System (Real-Time Multi-Device Platform)**

---

## 1. System Components
1. **Central FastAPI Backend (`backend/server.py`, `run_backend.py`)**
   - Receives live logs, telemetry, and heartbeats from enrolled Windows 10/11 computers.
   - Persists devices, tokens, telemetry snapshots, deduplicated events, and AI incidents in SQLite (`data/monitoring_system.db`, WAL mode) and historical log vectors in FAISS (`data/faiss_live/`).
   - Broadcasts real-time updates over WebSocket (`/ws/live`) and SSE (`/api/v1/stream`).
   - Runs a background heartbeat watchdog marking stale devices `OFFLINE` automatically.
2. **Real-Time Streamlit Admin Dashboard (`app.py`)**
   - Displays fleet status, connected/offline devices, CPU/RAM/Disk/Network charts, real-time logs, RCA incidents, FAISS similarity search, Conversational AI Assistant, and device enrollment/revocation controls.
3. **Windows Background Monitoring Agent (`agent/`)**
   - Runs on Windows 10 and Windows 11 endpoints with explicit user consent.
   - Collects real Windows Event Viewer logs (`System`, `Application`, optional `Security`), real OS metrics (`psutil` + `pywin32`), and configured application log files.

---

## 2. Environment Variables
Copy `.env.example` to `.env` or set variables in your shell:

| Variable | Default | Description |
|---|---|---|
| `MONITOR_BACKEND_HOST` | `0.0.0.0` | FastAPI bind address |
| `MONITOR_BACKEND_PORT` | `8000` | FastAPI port |
| `MONITOR_ADMIN_KEY` | Auto-generated in `data/.admin_key` | Required `X-Admin-Key` for API automation |
| `MONITOR_ADMIN_USER` | `admin` | Operator login username for Streamlit Dashboard |
| `MONITOR_ADMIN_PASSWORD` | Defaults to `MONITOR_ADMIN_KEY` | Operator login password (PBKDF2 hashed in DB) |
| `MONITOR_JWT_SECRET` | Auto-generated in `data/.jwt_secret` | HMAC-SHA256 signing secret for operator JWT sessions |
| `MONITOR_ENROLLMENT_TOKEN` | *(empty)* | Optional bootstrap enrollment token |
| `MONITOR_DB_PATH` | `data/monitoring_system.db` | SQLite database file path |
| `MONITOR_FAISS_DIR` | `data/faiss_live` | Persistent FAISS index directory |
| `DEVICE_OFFLINE_SECONDS` | `30` | Seconds without heartbeat/telemetry before a device becomes `OFFLINE` |
| `EVENT_RETENTION_DAYS` | `30` | Automatic event retention pruning window |
| `TELEMETRY_RETENTION_DAYS` | `14` | Automatic telemetry retention pruning window |
| `ALERT_WEBHOOK_URL` | *(empty)* | Optional Slack/Teams/JSON webhook URL for critical & offline alerts |
| `MONITOR_BACKEND_URL` | `http://127.0.0.1:8000` | Backend URL used by the Streamlit dashboard (or remote agent override) |
| `OPENAI_API_KEY` | *(empty)* | Optional OpenAI-compatible key for cloud LLM enhancement in AI Assistant |

---

## 3. Startup Instructions (Central Server)

### Step 1: Install Dependencies
```powershell
cd "C:\Users\NITISH I D\Downloads\log detection system"
pip install -r requirements.txt
```

### Step 2: Start the Central FastAPI Backend
```powershell
python run_backend.py
```
- The startup banner prints the **Admin API Key** (also stored in `data/.admin_key`), API docs URL (`/docs`), WebSocket URL (`/ws/live`), and SSE URL (`/api/v1/stream`).

### Step 3: Start the Real-Time Streamlit Admin Dashboard
In a second terminal:
```powershell
cd "C:\Users\NITISH I D\Downloads\log detection system"
streamlit run app.py
```

---

## 4. Connecting Other People's Windows Laptops & PCs

### Important Network Requirement
- **Do NOT use `localhost` or `127.0.0.1`** as the `BackendUrl` on remote computers.
- For **LAN / College / Office Wi-Fi**: Find your central server's LAN IP (e.g. `ipconfig` -> `192.168.1.50`), allow TCP port `8000` in Windows Defender Firewall, and use `http://192.168.1.50:8000`.
- For **Internet / Multi-Network Deployment**: Host the FastAPI backend behind a TLS reverse proxy (Nginx / Caddy / Cloudflare Tunnel / AWS ALB / Azure App Service) at `https://monitor.yourdomain.com`.

### Step A: Generate an Enrollment Token
1. Open the Streamlit Dashboard -> **🔧 Fleet Enrollment & Device Admin**.
2. Enter a label (e.g. `Engineering-Laptops`), max devices, and your server's reachable URL.
3. Click **🔑 Generate Enrollment Token** and copy the token.

### Step B: Package & Install on Target Windows 10/11 PC
1. Build the portable bundle on the server:
   ```powershell
   python installer/package_agent.py
   ```
   This creates `dist/windows-monitoring-agent.zip`.
2. Copy and extract `windows-monitoring-agent.zip` on the user's Windows 10/11 computer.
3. Run the interactive installer in PowerShell:
   ```powershell
   .\installer\install_agent.ps1 -BackendUrl "https://monitor.yourdomain.com" -EnrollmentToken "enroll_..."
   ```
   - The installer displays the data-collection disclosure and asks the user to type `YES` to grant explicit consent.
   - It creates `%LOCALAPPDATA%\EnterpriseAIMonitorAgent`, installs `psutil`, `pywin32`, and `requests`, registers a Windows Scheduled Task (`EnterpriseAIMonitorAgent`) to auto-start at logon, and starts the agent immediately.

### Step C: Manual Agent CLI Startup (Alternative)
```powershell
python -m agent.main --backend-url "https://monitor.yourdomain.com" --enrollment-token "enroll_..." --accept-consent
```
Optional flags:
- `--include-security` (collects selected Security Event IDs when running elevated)
- `--once` (runs a single collection & upload cycle and exits)

---

## 5. Production Deployment Hardening Checklist
1. **TLS / HTTPS**: Terminate HTTPS in front of FastAPI (`wss://` for WebSockets, `https://` for agent REST ingestion).
2. **Firewall**: Expose only the reverse proxy port (`443` or `8000`) to agent subnets; restrict Streamlit admin dashboard (`8501`) behind VPN, SSO, or internal firewall.
3. **Admin Key**: Set a strong `MONITOR_ADMIN_KEY` environment variable in production.
4. **Windows Service / Installer Packaging Plan**:
   - Current phase provides a PowerShell Scheduled Task installer (`installer/install_agent.ps1`) + portable ZIP packager (`installer/package_agent.py`).
   - For enterprise MSI distribution, wrap `agent/main.py` using `PyInstaller --onedir` and NSSM (`nssm install EnterpriseAIMonitorAgent`) or WiX Toolset MSI with the same consent dialog and `agent_config.json` bootstrap parameters.
5. **Security Event Log Access**: Reading Windows `Security` channel requires running the agent with Administrator / `SeSecurityPrivilege`. Without elevation, the agent gracefully logs a permission warning and continues monitoring `System`, `Application`, hardware metrics, services, and application log files.

