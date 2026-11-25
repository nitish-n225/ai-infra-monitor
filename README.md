# Enterprise Autonomous AI Infrastructure Monitoring System
> **College Mini-Project | Research Paper Implementation**  
> **Current Status**: `Stage 4 Completed (Conversational AI Infrastructure Assistant)`

---

## 📌 Project Overview & Research Context

Modern enterprise digital architectures rely on distributed cloud servers, Kubernetes containers, caching clusters, and relational databases. When operational disruptions strike, traditional keyword searches (such as `grep` or SQL `LIKE '%error%'`) fail because different microservices express equivalent failures with distinct terminology (e.g., `"FATAL: remaining connection slots reserved"` vs `"database down"`).

This project implements an **Enterprise Autonomous AI Infrastructure Monitoring System** based on our research paper:
- **Stage 1 (Completed)**: Multi-format log ingestion, structured normalization (Bracketed, ISO, Syslog, JSON), operational telemetry, and an interactive Streamlit observability dashboard.
- **Stage 2 (Completed)**: Critical event detection across **6 incident categories**, fault tree **Root Cause Analysis (RCA)**, explainable **Infrastructure Health Index (0-100%)**, predictive **Failure Risk Assessment**, and **Autonomous Self-Healing Playbooks** with safety constraints.
- **Stage 3 (Completed)**: High-dimensional semantic vectorization using **Sentence Transformers** (`all-MiniLM-L6-v2`) and **FAISS** vector indexing for sub-second natural language log retrieval.
- **Stage 4 (Completed)**: Context-aware **Conversational AI Infrastructure Assistant** grounded in active log evidence, telemetry, and advisory recovery actions with deterministic offline fallback and optional cloud LLM support.
- **Stage 5 (Upcoming)**: End-to-End Enterprise Hardening, CI/CD Pipeline & Final Project Packaging.

---

## 🤖 Stage 4: Conversational AI Infrastructure Assistant

### 1. Assistant Architecture (`src/assistant_engine.py`)
The Assistant engine provides natural-language dialogue grounded strictly in the active dataset's operational reality:
- **Dual-Engine Architecture**:
  1. **Deterministic Evidence-Based Engine (Default / Local Offline)**:
     - Operates 100% locally with zero internet dependency and zero API costs.
     - Performs rule-based intent parsing, fault-tree correlation from Stage 2 RCA, telemetry lookup, health penalty tracing, and FAISS vector search retrieval.
     - Never hallucinates: if evidence is not present in the ingested logs, it explicitly responds with `"Insufficient evidence in active logs"`.
  2. **Optional Cloud LLM Provider (OpenAI-Compatible)**:
     - Activated seamlessly when the `OPENAI_API_KEY` environment variable is defined.
     - Injects ground-truth operational telemetry and extracted log evidence into system instructions with temperature 0.1.
     - If the cloud service times out, rate limits, or fails, it **automatically falls back** to the deterministic evidence engine without crashing.
- **Ground-Truth Log Evidence Citing**:
  - Every answer includes an expandable evidence tray citing exact log lines, source line numbers (`Line 14`), timestamps, service tags (`[db-postgres]`), and severity levels (`[CRITICAL]`).
  - Distinguishes verified **Observed Facts** (recorded in logs) from **Inferred Explanations** (derived from fault trees).

### 2. Example Questions Supported
Engineers and operators can query the assistant naturally:
- *"What are the most critical incidents?"*
- *"Why is the database failing?"*
- *"Which services are affected?"*
- *"Find logs related to memory exhaustion."*
- *"What factors increased the infrastructure risk score?"*
- *"How was the health score calculated?"*
- *"What recovery steps are recommended?"*
- *"Show the evidence supporting this suspected root cause."*

### 3. Safety Enforcement & Advisory Limitations
- **Execution Safety Gate**: Automated execution of remediation actions against live infrastructure is strictly disabled (`SAFETY_POLICY_DISCLAIMER`).
- **Advisory Simulation Only**: All recovery playbooks are displayed with prerequisites, step-by-step verification commands, and dry-run commands.
- Calling `InfrastructureAIAssistant.execute_recovery_action()` raises a strict `RuntimeError` blocking execution.

### 4. Model-Provider Configuration (Optional Cloud LLM)
To use a cloud language model instead of the default offline engine, set your environment variables without committing secrets to source control:

```powershell
# Set your API key in your Windows terminal session (do NOT commit to code):
$env:OPENAI_API_KEY="your-api-key-here"

# Optional: Configure model or custom endpoint (defaults to gpt-4o-mini):
$env:OPENAI_MODEL="gpt-4o-mini"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
```

If no environment variables are set, the dashboard automatically uses the local **Deterministic Evidence-Based Engine** and displays `[Provider: Deterministic Evidence-Based Engine (Offline, No API Key Required)]`.

---

## 📂 Project Structure (Stage 4)

```text
log detection system/
├── app.py                      # Main Streamlit Dashboard (Overview, RCA, FAISS Search, AI Assistant, Upload, Roadmap)
├── config.py                   # Global project settings, metadata, and stage definitions
├── requirements.txt            # Project dependencies (Streamlit, Pandas, Sentence-Transformers, FAISS)
├── README.md                   # Complete documentation and execution guide
│
├── src/                        # Modular Source Package
│   ├── __init__.py             # Package root
│   ├── parser.py               # Robust parser for Bracketed, ISO, Syslog, & JSON logs
│   ├── telemetry.py            # Summary stats, severity counts, and service breakdown
│   ├── rca_engine.py           # [Stage 2] 6-category failure detection & evidence extraction
│   ├── predictive_failure.py   # [Stage 2] Operational failure risk assessment & factor weights
│   ├── health_score.py         # [Stage 2] Explainable Infrastructure Health Score (0-100%)
│   ├── self_healing.py         # [Stage 2] Safe self-healing playbooks & dry-run simulation
│   ├── embedding_engine.py     # [Stage 3] SentenceTransformer ('all-MiniLM-L6-v2') vectorizer
│   ├── vector_store.py         # [Stage 3] FAISS IndexFlatIP store & semantic similarity search
│   ├── assistant_engine.py     # [Stage 4] Grounded Conversational AI Assistant & safety gate
│   ├── sample_data.py          # Loader for built-in enterprise benchmark datasets
│   └── ui/                     # UI Presentation Subpackage
│       ├── __init__.py
│       ├── components.py       # Custom dark CSS, KPI metric cards, and stage badges
│       └── views.py            # Overview, RCA/Health, Semantic Search, Assistant, Ingestion, Roadmap views
│
├── sample_logs/                # Benchmark Test Log Traces
│   ├── production_incident.log # Cascading outage trace (Redis OOM -> DB pool exhaustion -> Pod restart)
│   └── normal_operations.log   # Healthy baseline cluster operations trace
│
└── tests/                      # Automated Unit & Integration Test Suite
    ├── test_stage1.py          # Tests for parser, telemetry, and sample data
    ├── test_stage2.py          # Tests for RCA categories, health boundaries, risk, and healing
    ├── test_stage3.py          # Tests for embeddings, FAISS indexing, metadata mapping & real-model search
    └── test_stage4.py          # Tests for AI assistant dialogue, evidence mapping, safety gate & provider fallback
```

---

## 🚀 How to Run Locally on Windows

### Step 1: Open Terminal in Project Directory
```powershell
cd "c:\Users\NITISH I D\Downloads\log detection system"
```

### Step 2: Install Dependencies (One-time Setup)
```powershell
pip install -r requirements.txt
```

### Step 3: Launch the Streamlit Application
```powershell
streamlit run app.py
```
*Streamlit will automatically open in your browser at `http://localhost:8501`.*

---

## 🧪 Running Automated Unit & Integration Tests

All test suites can be executed independently from the project root:

```powershell
# Run Stage 1 Tests (Parser & Telemetry)
python tests/test_stage1.py

# Run Stage 2 Tests (RCA, Risk, Health, Self-Healing)
python tests/test_stage2.py

# Run Stage 3 Tests (Embeddings, FAISS Index, Metadata Mapping & Real-Model Integration)
python tests/test_stage3.py

# Run Stage 4 Tests (AI Assistant Grounding, Safety Gate, Provider Fallback & Evidence)
python tests/test_stage4.py
```

### Stage 4 Test Suite Verification Output
```text
=================================================================
Running Stage 4 Test Suite: Conversational AI Assistant
=================================================================
[PASS] Questions about incidents and affected services verified.
[PASS] Evidence citations and source-line mapping verified.
[PASS] Health score breakdown and failure risk explanation verified.
[PASS] Recovery recommendations and strict safety execution gate verified.
[PASS] Unknown query and insufficient evidence handling verified (no hallucination).
[PASS] Empty logs and malformed input handling verified.
[PASS] Dataset switching and session history reset verified.
[PASS] Cloud provider error handling and deterministic fallback verified.
=================================================================
[SUCCESS] All Stage 4 unit & integration tests passed successfully!
=================================================================
```

---

## ⚠️ Known Limitations & Operational Considerations

1. **Local Disk Space Headroom**:
   - Machine learning models (PyTorch and Hugging Face sentence transformers) use memory-mapped allocations and virtual memory paging. Ensure at least ~1 GB of free disk space on the primary OS drive for smooth paging and temporary cache storage.
2. **Safety by Design**:
   - The AI Assistant will never execute commands against host operating systems, Kubernetes clusters, or databases. All remediation playbooks are purely advisory simulations.
3. **Session-Bound Conversation History**:
   - Chat history is maintained in active Streamlit session memory. When a new log dataset is uploaded or selected, the assistant automatically resets the session to prevent cross-dataset context pollution.
