"""
Enterprise Autonomous AI Infrastructure Monitoring System.
Main Streamlit Dashboard — Real-Time Multi-Device Fleet & Log Analysis.
"""
import os
from pathlib import Path
import streamlit as st
import pandas as pd

# Guard BLAS/OpenMP threads before numerical/FAISS imports
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
if Path("/mount/src").exists():
    os.environ.setdefault("LOW_MEMORY_MODE", "true")

from config import PROJECT_SUBTITLE, PROJECT_TITLE, SEVERITY_COLORS, VERSION
from src.assistant_engine import InfrastructureAIAssistant
from src.health_score import InfrastructureHealthScorer
from src.parser import InfrastructureLogParser
from src.predictive_failure import PredictiveFailureDetector
from src.rca_engine import RootCauseAnalysisEngine
from src.realtime_client import (
    BackendAPIClient,
    get_backend_url,
    get_realtime_bridge,
    is_remote_backend_configured,
)
from src.telemetry import TelemetryAnalyzer
from src.ui.components import (
    apply_custom_styles,
    esc,
    render_3d_ai_neural_core,
    render_3d_vector_constellation,
    render_hero_header,
)
from src.ui.live_views import (
    render_fleet_admin_tab,
    render_live_fleet_fragment,
    render_live_incidents_fragment,
)
from src.ui.views import (
    render_assistant_tab,
    render_overview_tab,
    render_rca_tab,
    render_semantic_search_tab,
    render_upload_tab,
)
from src.vector_store import FaissVectorStore, SIMILARITY_DISCLAIMER

st.set_page_config(
    page_title="AI Infrastructure Monitor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_styles()


@st.cache_data(ttl=5, show_spinner=False)
def _cached_backend_health(base_url: str, timeout: float = 10.0):
    return BackendAPIClient(base_url=base_url).health(timeout=timeout)


# Initialize session state
if "operator_jwt" not in st.session_state:
    st.session_state["operator_jwt"] = ""
if "operator_user" not in st.session_state:
    st.session_state["operator_user"] = ""
if "raw_log_content" not in st.session_state:
    st.session_state["raw_log_content"] = ""
    st.session_state["active_file_name"] = "None"
if "vector_store" not in st.session_state:
    st.session_state["vector_store"] = FaissVectorStore()
if "assistant_engine" not in st.session_state:
    st.session_state["assistant_engine"] = InfrastructureAIAssistant()
if "live_assistant_history" not in st.session_state:
    st.session_state["live_assistant_history"] = []

jwt_token = st.session_state.get("operator_jwt", "")
backend_url = get_backend_url()
api_client = BackendAPIClient(base_url=backend_url, bearer_token=jwt_token)
backend_health = _cached_backend_health(backend_url)

if jwt_token and backend_health:
    get_realtime_bridge(token=jwt_token, backend_url=backend_url)

active_content = st.session_state.get("raw_log_content", "")
active_filename = st.session_state.get("active_file_name", "None")

if active_content:
    parsed_df = InfrastructureLogParser.parse_text(active_content)
else:
    parsed_df = pd.DataFrame(columns=["line_no", "timestamp", "level", "service", "message", "raw_line"])

telemetry_data = TelemetryAnalyzer.compute_summary(parsed_df)
health_data = InfrastructureHealthScorer.calculate_health(parsed_df)
rca_results = RootCauseAnalysisEngine.analyze_logs(parsed_df)
risk_data = PredictiveFailureDetector.assess_risk(parsed_df, rca_results)

vector_store = st.session_state["vector_store"]
if st.session_state.get("vector_store_indexed_file") != active_filename:
    vector_store.reset()

assistant_engine = st.session_state["assistant_engine"]
if st.session_state.get("last_active_file") != active_filename:
    assistant_engine.reset_session(active_filename)
    st.session_state["assistant_chat_history"] = []
    st.session_state["last_active_file"] = active_filename

# Clean Sidebar
with st.sidebar:
    st.markdown(f"### 🛡️ AI Monitor")
    st.caption(f"{PROJECT_SUBTITLE} • `v{VERSION}`")
    st.markdown("---")

    data_mode = st.radio(
        "Workspace",
        options=["Live Fleet", "Log Analyzer"],
        index=0,
    )

    st.markdown("---")
    st.markdown("#### Central Backend")
    if backend_health:
        st.success(f"🟢 Connected")
        st.caption(f"`{backend_url}`")
        if jwt_token:
            st.caption(f"Operator: `{st.session_state.get('operator_user', 'admin')}`")
            try:
                fleet_sum = api_client.get_summary()
                m1, m2 = st.columns(2)
                m1.metric("Online", f"{fleet_sum['online_devices']}/{fleet_sum['total_devices']}")
                m2.metric("Incidents", fleet_sum["open_incidents"])
            except Exception:
                pass
            if st.button("🚪 Sign Out", use_container_width=True):
                st.session_state["operator_jwt"] = ""
                st.session_state["operator_user"] = ""
                st.rerun()
    else:
        st.warning("🟡 Sleeping / Offline")
        st.caption(f"`{backend_url}`")
        if st.button("🔄 Wake / Retry Backend", use_container_width=True):
            _cached_backend_health.clear()
            with st.spinner("Waking backend (up to 30s)..."):
                woke = api_client.health(timeout=30.0)
            if woke:
                st.rerun()
            else:
                st.error("Still unreachable. Verify backend service or BACKEND_URL secret.")

# Top Command Header
header_status = (
    f"Backend Online • {backend_health.get('database', 'db').upper()}"
    if backend_health
    else "Backend Waking / Offline"
)
render_hero_header(
    PROJECT_TITLE,
    "Real-Time Windows Fleet Telemetry, Root Cause Analysis & Semantic Log Intelligence",
    header_status,
    bool(backend_health),
)

if data_mode == "Live Fleet":
    if not backend_health:
        if is_remote_backend_configured():
            st.info(
                f"Central backend (`{backend_url}`) is waking from sleep or temporarily unreachable. "
                "Click **🔄 Wake Backend Now** below (Render free tier cold starts typically take 20–40 seconds), "
                "or switch to **Log Analyzer** in the sidebar."
            )
        else:
            st.info(
                f"Local backend (`{backend_url}`) is not running. Start it with `python run_backend.py`, "
                "or configure `BACKEND_URL` in Streamlit Secrets."
            )
        if st.button("🔄 Wake Backend Now", type="primary"):
            _cached_backend_health.clear()
            with st.spinner("Contacting central backend..."):
                woke = api_client.health(timeout=35.0)
            if woke:
                st.rerun()
            else:
                st.error(f"Could not reach `{backend_url}`.")
    elif not jwt_token:
        _, col_login, _ = st.columns([1, 1.35, 1])
        with col_login:
            st.markdown("### 🔐 Operator Sign-In")
            st.caption("Authenticate to access real-time fleet telemetry, incidents, and endpoint controls.")
            with st.form("operator_login_form"):
                u_in = st.text_input("Username", value="admin")
                p_in = st.text_input("Password", type="password", placeholder="MONITOR_ADMIN_PASSWORD or Admin Key")
                login_btn = st.form_submit_button("🔓 Sign In", use_container_width=True, type="primary")
            if login_btn:
                with st.spinner("Signing in..."):
                    try:
                        auth_res = api_client.login(u_in.strip(), p_in)
                        st.session_state["operator_jwt"] = auth_res["access_token"]
                        st.session_state["operator_user"] = auth_res["username"]
                        get_realtime_bridge(token=auth_res["access_token"], backend_url=backend_url)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Authentication failed: {e}")
    else:
        tab_live, tab_incidents, tab_search, tab_assistant, tab_admin = st.tabs([
            "📡 Fleet Overview",
            "🚨 Incidents & RCA",
            "🔎 Semantic Search",
            "🤖 AI Assistant",
            "⚙️ Fleet Admin",
        ])

        with tab_live:
            render_live_fleet_fragment(api_client)

        with tab_incidents:
            render_live_incidents_fragment(api_client)

        with tab_search:
            st.markdown("#### 🔎 Live Fleet Semantic Search")
            col_p1, col_p2, col_p3, col_p4 = st.columns(4)
            preset_q = None
            if col_p1.button("💥 DB Connection Issues", use_container_width=True, key="live_pre_db"):
                preset_q = "database connection pool exhausted"
            if col_p2.button("🧠 Memory Exhaustion", use_container_width=True, key="live_pre_mem"):
                preset_q = "out of memory virtual memory low"
            if col_p3.button("⚠️ Service Crashes", use_container_width=True, key="live_pre_svc"):
                preset_q = "service terminated unexpectedly"
            if col_p4.button("🔒 Logon Failures", use_container_width=True, key="live_pre_auth"):
                preset_q = "failed logon authentication unauthorized"

            col_q, col_k = st.columns([3, 1])
            default_live_q = preset_q or st.session_state.get("live_faiss_q", "")
            live_q = col_q.text_input(
                "Natural Language Query",
                value=default_live_q,
                placeholder="e.g. service terminated unexpectedly, disk space low...",
                key="live_faiss_q_input",
            )
            live_k = col_k.slider("Top-K", 1, 20, 5, key="live_faiss_k")
            if live_q:
                st.session_state["live_faiss_q"] = live_q
                try:
                    res = api_client.semantic_search(live_q, top_k=live_k)
                    if not res.get("results"):
                        st.info("No matching historical events indexed yet.")
                    else:
                        render_3d_vector_constellation(live_q, res["results"])
                        for item in res["results"]:
                            sev = item.get("level", "INFO")
                            sev_color = SEVERITY_COLORS.get(sev, "#94a3b8")
                            st.markdown(
                                f"""
                                <div class="metric-card" style="margin-bottom:0.7rem; border-left:4px solid {sev_color};">
                                    <div style="display:flex; justify-content:space-between; font-size:0.82rem;">
                                        <span>
                                            <strong>#{esc(item['rank'])}</strong> &bull;
                                            <code>{esc(item.get('hostname', 'host'))}</code> &bull;
                                            <code>[{esc(item['service'])}]</code> &bull;
                                            <strong style="color:{sev_color};">[{esc(sev)}]</strong>
                                        </span>
                                        <span style="color:#10b981; font-weight:700;">{esc(item['similarity_pct'])}% Match</span>
                                    </div>
                                    <div style="font-family:'JetBrains Mono', monospace; font-size:0.84rem; color:#f1f5f9; margin-top:0.3rem;">
                                        {esc(item['message'])}
                                    </div>
                                    <div style="font-size:0.72rem; color:#64748b; margin-top:0.2rem;">
                                        {esc(item['timestamp'])} &bull; {esc(item.get('channel', ''))}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        st.caption(f"ℹ️ {SIMILARITY_DISCLAIMER}")
                except Exception as e:
                    st.error(f"Semantic search failed: {e}")

        with tab_assistant:
            col_ah1, col_ah2 = st.columns([4, 1])
            col_ah1.markdown("#### 🤖 Fleet AI Assistant")
            if col_ah2.button("🗑️ Clear Chat", use_container_width=True, key="clear_live_ai"):
                st.session_state["live_assistant_history"] = []
                st.rerun()

            last_live_ai = next(
                (m for m in reversed(st.session_state["live_assistant_history"]) if m.get("role") == "assistant"),
                None,
            )
            render_3d_ai_neural_core(
                context_label="Live Fleet Telemetry",
                intent_label="LIVE_FLEET_QUERY" if last_live_ai else "READY",
                confidence_label="GROUNDED" if (last_live_ai and last_live_ai.get("evidence")) else "STANDBY",
                evidence_items=(last_live_ai or {}).get("evidence", []),
                signals=[
                    {"label": "Live Agents", "detail": "Real-time Windows telemetry & Event Viewer"},
                    {"label": "PostgreSQL DB", "detail": "Persisted deduplicated events & snapshots"},
                    {"label": "Live FAISS", "detail": "384-dim real-time historical similarity index"},
                    {"label": "RCA Watchdog", "detail": "Live fault-tree & trend risk engine"},
                ],
                height=310,
            )

            pq1, pq2, pq3 = st.columns(3)
            quick_live_prompt = None
            if pq1.button("🚨 Critical incidents?", use_container_width=True, key="live_ai_q1"):
                quick_live_prompt = "What are the most critical incidents?"
            if pq2.button("🩺 Fleet health & risks?", use_container_width=True, key="live_ai_q2"):
                quick_live_prompt = "How is the fleet health score and failure risk?"
            if pq3.button("🛠️ Recovery steps?", use_container_width=True, key="live_ai_q3"):
                quick_live_prompt = "What recovery steps are recommended?"

            for msg in st.session_state["live_assistant_history"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg.get("evidence"):
                        with st.expander(f"📑 Evidence ({len(msg['evidence'])})", expanded=False):
                            for ev in msg["evidence"]:
                                st.code(f"[{ev.get('timestamp')}] [{ev.get('service')}] [{ev.get('level')}] {ev.get('message')}")

            chat_in = st.chat_input("Ask about live incidents, root causes, health score, or recovery...", key="live_ai_input")
            prompt = quick_live_prompt or chat_in
            if prompt:
                st.session_state["live_assistant_history"].append({"role": "user", "content": prompt})
                with st.spinner("Querying live AI engine..."):
                    try:
                        ans = api_client.ask_assistant(prompt)
                        st.session_state["live_assistant_history"].append({
                            "role": "assistant",
                            "content": ans.get("answer", ""),
                            "evidence": ans.get("evidence", []),
                        })
                    except Exception as e:
                        st.session_state["live_assistant_history"].append({
                            "role": "assistant",
                            "content": f"Error querying backend assistant: {e}",
                        })
                st.rerun()

        with tab_admin:
            render_fleet_admin_tab(api_client)

else:
    if not active_content:
        st.info("Upload a log file or load a sample trace in **📥 Upload Logs** to start analyzing.")
    tab_overview, tab_rca, tab_search, tab_assistant, tab_upload = st.tabs([
        "📊 Overview",
        "🔍 Incidents & RCA",
        "🔎 Semantic Search",
        "🤖 AI Assistant",
        "📥 Upload Logs",
    ])

    with tab_overview:
        render_overview_tab(telemetry_data, parsed_df, health_data, risk_data)

    with tab_rca:
        render_rca_tab(rca_results, risk_data, health_data, parsed_df)

    with tab_search:
        render_semantic_search_tab(vector_store, parsed_df)

    with tab_assistant:
        render_assistant_tab(assistant_engine, parsed_df, rca_results, health_data, risk_data, vector_store, active_filename)

    with tab_upload:
        render_upload_tab(InfrastructureLogParser)
