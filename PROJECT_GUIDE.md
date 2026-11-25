# AegisLog: Intelligent Log Anomaly & Cyber Threat Detection System
> **College Mini-Project Documentation, Viva Guide & Execution Manual**
> **Domain**: Cybersecurity & Machine Learning (SIEM Systems)

---

## 1. Project Overview & Synopsis (For Project Report)

Modern web servers and cloud services generate massive volumes of event logs every second. Manual log inspection is impossible, while traditional Security Information and Event Management (SIEM) tools struggle with high false-positive rates and fail to catch zero-day attacks.

**AegisLog** is an end-to-end, real-time log analysis and threat detection system designed with a **Hybrid Detection Architecture**:
1. **Deterministic Rule Engine**: High-speed signature pattern matching for known OWASP cyber attacks (SQL Injection, Cross-Site Scripting, Directory Traversal, Sensitive Configuration Probing) and stateful sliding-window rate limiters for Brute-Force and DoS floods.
2. **Machine Learning Anomaly Engine**: Employs an **Unsupervised Isolation Forest** algorithm to detect statistical outliers, unusual payload entropies, and anomalous data sizes without requiring pre-labeled attack datasets.
3. **Interactive Security Command Center**: A modern, dark-mode, glassmorphic web dashboard providing live log streaming via WebSockets, real-time KPI metrics, dynamic Chart.js visualizations, and an **Instant Attack Simulator** for live demonstration.

---

## 2. System Architecture & Workflow

```
[ Raw Logs / Simulated Attack Streams ]
                   │
                   ▼
       [ Ingestion & Preprocessing ]
       (Extracts IP, Endpoint, Status, Method, Size)
                   │
                   ▼
      [ Hybrid Detection Engine ]
      ├── Layer 1: Rule-Based Signatures (Regex & Window Counters)
      │     └── Flags SQLi, XSS, Path Traversal, Brute-Force, DoS
      │
      └── Layer 2: Scikit-Learn Isolation Forest (Unsupervised ML)
            └── Flags Outlier Endpoints, Payload Sizes & Anomalous Methods
                   │
                   ▼
         [ SQLite Database Storage ]
         (Indexed tables for logs, alerts, and incident resolutions)
                   │
                   ▼
      [ FastAPI Backend + WebSocket Manager ]
      (Streams events to connected dashboards in real time)
                   │
                   ▼
    [ AegisLog Web Dashboard (HTML5 / Vanilla CSS / Chart.js) ]
    - Live Traffic Velocity & Threat Doughnut Charts
    - Instant Attack Simulator Buttons (For Evaluation Viva)
    - Searchable & Filterable Live Log Stream
```

---

## 3. Detected Threat Vectors

| Threat Vector | Detection Method | Severity | Example Pattern |
|---|---|---|---|
| **SQL Injection (SQLi)** | Signature Regex | `CRITICAL` | `UNION SELECT`, `' OR 1=1 --`, `DROP TABLE` |
| **Cross-Site Scripting (XSS)** | Signature Regex | `HIGH` | `<script>`, `javascript:alert()`, `onerror=` |
| **Path Traversal** | Signature Regex | `HIGH` | `../../../../etc/passwd`, `win.ini` |
| **Reconnaissance** | Signature Regex | `MEDIUM` | Probing `/.env`, `/.git`, `/wp-config.php` |
| **Brute Force Auth** | Stateful Sliding Window | `CRITICAL` | &ge; 5 failed `POST /login` (HTTP 401) in 60s |
| **DDoS / Traffic Flood** | Stateful Sliding Window | `CRITICAL` | &ge; 25 rapid requests in 10s from same IP |
| **Behavioral Outlier** | Isolation Forest ML | `MEDIUM` / `HIGH` | Unusual query entropy or response byte anomalies |

---

## 4. How to Run the Project (Step-by-Step)

### Step 1: Open Terminal in the Project Folder
Open PowerShell or Command Prompt in:
```bash
c:\Users\NITISH I D\Downloads\log detection system
```

### Step 2: Install Required Libraries (One-time setup)
```bash
pip install -r requirements.txt
```

### Step 3: Launch the Application
```bash
python run.py
```

### Step 4: Access the Security Dashboard
Open your web browser (Chrome, Edge, or Firefox) and navigate to:
```
http://127.0.0.1:8000
```
- You will see the live WebSocket connection indicator turn green (`LIVE MONITORING`).
- Background web traffic will automatically stream into the log table.
- Click any button in the **Interactive Attack Simulator** bar to immediately trigger attacks and watch them get flagged!

---

## 5. College Viva Questions & Model Answers

### Q1: Why did you choose a Hybrid architecture instead of only Machine Learning?
> **Answer**: Pure Machine Learning models suffer from false positives and can be slow for known signatures. Rule-based engines provide $O(1)$ instantaneous deterministic detection for well-known attacks like SQL Injection and Brute-Force. However, rule engines cannot detect zero-day attacks or stealthy behavioral shifts. Combining both gives us maximum speed and precision for known attacks, plus AI-driven adaptability for unknown anomalies.

### Q2: Why Isolation Forest instead of Supervised algorithms like Random Forest or SVM?
> **Answer**: In cybersecurity, real-world attack logs represent less than 0.1% of all traffic (heavy class imbalance), and zero-day attacks do not have historical labels. Supervised models fail on unseen attack vectors. Isolation Forest is an unsupervised algorithm specifically built on the principle that anomalies are "few and different", meaning they isolate near the root of tree partitions with much shorter average path lengths.

### Q3: How does the system handle real-time streaming without lagging the UI?
> **Answer**: The backend is built with FastAPI's asynchronous event loop (`asyncio`) and WebSockets. When a log is processed, it is broadcast to connected clients in non-blocking fashion. On the frontend, a circular buffer (capped at 60 items) and Chart.js animations maintain smooth 60fps rendering without memory bloat.

### Q4: How is state maintained for Brute-Force and DDoS attacks?
> **Answer**: The `RulesEngine` maintains in-memory sliding windows using Python `collections.deque` keyed by client IP. As new requests arrive, timestamps older than the evaluation window (e.g., 60 seconds) are pruned in $O(1)$ time, allowing instant threshold validation.

---

## 6. Project Directory Layout

```
log detection system/
├── run.py                 # One-click startup script
├── requirements.txt       # Dependencies
├── PROJECT_GUIDE.md       # Complete Viva and Report Guide
├── api/
│   └── main.py            # FastAPI REST & WebSocket Server
├── detection/
│   ├── rules_engine.py    # Signatures & Sliding Window Rate Limiting
│   ├── ml_detector.py     # Isolation Forest Anomaly Detection
│   └── pipeline.py        # Master Security Pipeline
├── ingestion/
│   ├── log_parser.py      # Apache/Nginx & JSON Log Normalizer
│   └── log_generator.py   # Synthetic Normal & Attack Traffic Generator
├── storage/
│   └── database.py        # SQLite Database Schema & Queries
├── web/
│   ├── index.html         # Cybersecurity Command Center UI
│   ├── styles.css         # Dark glassmorphic design system
│   └── app.js             # WebSocket Client & Dynamic Visualizations
└── tests/
    └── test_pipeline.py   # Unit test verification suite
```
