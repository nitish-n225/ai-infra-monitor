"""
Enterprise Autonomous AI Infrastructure Monitoring System.
Main Streamlit Application Entrypoint - Authenticated Real-Time Fleet & Offline Log Analysis.
"""
import os
import sys

# Limit BLAS/OpenMP thread buffers to prevent OpenBLAS memory allocation failures on constrained Windows hosts
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import streamlit as st
import pandas as pd

from config import PROJECT_TITLE, PROJECT_SUBTITLE, VERSION, EMBEDDING_MODEL_NAME, SEVERITY_COLORS
from src.parser import InfrastructureLogParser
from src.telemetry import TelemetryAnalyzer
from src.rca_engine import RootCauseAnalysisEngine
from src.predictive_failure import PredictiveFailureDetector
from src.health_score import InfrastructureHealthScorer
from src.vector_store import FaissVectorStore, SIMILARITY_DISCLAIMER
from src.assistant_engine import InfrastructureAIAssistant
from src.realtime_client import BackendAPIClient, get_realtime_bridge, get_backend_url
from src.ui.components import apply_custom_styles
from src.ui.live_views import (
    render_fleet_admin_tab,
    render_live_fleet_fragment,
    render_live_incidents_fragment,
)
from src.ui.views import (
    render_assistant_tab,
    render_overview_tab,
    render_rca_tab,
    render_roadmap_tab,
    render_semantic_search_tab,
    render_upload_tab,
)

st.set_page_config(
    page_title="AI Infrastructure Monitor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_styles()

# Initialize Session State
if "operator_jwt" not in st.session_state:
    st.session_state["operator_jwt"] = ""
if "operator_user" not in st.session_state:
    st.session_state["operator_user"] = ""

if "raw_log_content" not in st.session_state:
    st.session_state["raw_log_content"] = ""
    st.session_state["active_file_name"] = "None (Upload or Load Log)"

if "vector_store" not in st.session_state:
    st.session_state["vector_store"] = FaissVectorStore()

if "assistant_engine" not in st.session_state:
    st.session_state["assistant_engine"] = InfrastructureAIAssistant()

jwt_token = st.session_state.get("operator_jwt", "")
api_client = BackendAPIClient(bearer_token=jwt_token)
backend_health = api_client.health()

if jwt_token:
    get_realtime_bridge(token=jwt_token)

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

# Sidebar Navigation & System Telemetry
with st.sidebar:
    st.markdown("### 🛡️ Enterprise AI Monitor")
    st.caption(f"{PROJECT_SUBTITLE} • `{VERSION}`")
    st.markdown("---")

    data_mode = st.radio(
        "📡 Monitoring Mode",
        options=["Live Windows Fleet (Real-Time)", "Log File Analysis (Offline/Upload)"],
        index=0,
        help="Switch between real-time multi-device Windows agents and static uploaded log analysis.",
    )

    st.markdown("---")
    st.markdown("#### 🔌 Central Backend Status")
    if backend_health:
        st.success(f"🟢 Connected (`{api_client.base_url}`)")
        if jwt_token:
            st.caption(f"Signed in as: `{st.session_state.get('operator_user', 'admin')}`")
            if st.button("🚪 Sign Out", use_container_width=True):
                st.session_state["operator_jwt"] = ""
                st.session_state["operator_user"] = ""
                st.rerun()
            try:
                fleet_sum = api_client.get_summary()
                st.write(f"**Registered Devices**: `{fleet_sum['total_devices']}`")
                st.write(f"**Online / Offline**: `{fleet_sum['online_devices']}` / `{fleet_sum['offline_devices']}`")
                st.write(f"**Open Incidents**: `{fleet_sum['open_incidents']}`")
                st.write(f"**Live FAISS Vectors**: `{fleet_sum.get('faiss_vectors', 0)}`")
            except Exception:
                pass
    else:
        st.error(f"🔴 Offline (`{api_client.base_url}`)")
        st.caption("Run `python run_backend.py` to start the central backend.")

    st.markdown("---")
    st.markdown("#### ⚙️ AI Engine & Environment")
    st.caption(f"Assistant: `{assistant_engine.provider.provider_name}`")
    st.caption(f"Embeddings: `{EMBEDDING_MODEL_NAME}` • FAISS: `CPU`")
    st.caption(f"Python: `{sys.version.split()[0]}` • OS: `Windows`")

# Top Header
st.title(PROJECT_TITLE)
st.markdown(
    """
    **Real-Time Windows Fleet Telemetry, Live AI Root Cause Analysis, FAISS Semantic Intelligence & Conversational Copilot**
    """
)

if data_mode == "Live Windows Fleet (Real-Time)":
    if not backend_health:
        st.error(
            f"🔴 **Central Backend Offline** (`{get_backend_url()}`). "
            "Start the backend server with `python run_backend.py`."
        )
    elif not jwt_token:
        st.markdown("### 🔐 Operator Sign-In Required")
        st.caption("Authenticate against the Central Monitoring Backend to access live client telemetry, logs, and fleet admin controls.")
        with st.form("operator_login_form"):
            u_in = st.text_input("Username", value="admin")
            p_in = st.text_input("Password (or Admin API Key)", type="password")
            login_btn = st.form_submit_button("🔓 Sign In")
        if login_btn:
            try:
                auth_res = api_client.login(u_in.strip(), p_in)
                st.session_state["operator_jwt"] = auth_res["access_token"]
                st.session_state["operator_user"] = auth_res["username"]
                get_realtime_bridge(token=auth_res["access_token"])
                st.success("Authenticated successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Authentication failed: {e}")
        st.info(
            "Default operator username is `admin`. Password is `MONITOR_ADMIN_PASSWORD` "
            "(or the Admin API Key printed at backend startup / stored in `data/.admin_key`)."
        )
    else:
        tab_live, tab_incidents, tab_search, tab_assistant, tab_admin, tab_roadmap = st.tabs([
            "📡 Live Fleet Monitor",
            "🚨 Live Incidents & RCA",
            "🔎 Semantic Search (Live FAISS)",
            "🤖 AI Assistant (Live)",
            "🔧 Fleet Enrollment & Device Admin",
            "🗺️ Architecture & Roadmap",
        ])

        with tab_live:
            render_live_fleet_fragment(api_client)

        with tab_incidents:
            render_live_incidents_fragment(api_client)

        with tab_search:
            st.markdown("### 🔎 Live Fleet Semantic Search (Persistent FAISS)")
            st.caption("Searches real ingested Windows & application logs vectorized with `all-MiniLM-L6-v2` across all enrolled computers.")
            col_q, col_k = st.columns([3, 1])
            live_q = col_q.text_input("Semantic Query", placeholder="e.g. service terminated unexpectedly, disk space low, logon failure...", key="live_faiss_q")
            live_k = col_k.slider("Top-K", 1, 20, 5, key="live_faiss_k")
            if live_q:
                try:
                    res = api_client.semantic_search(live_q, top_k=live_k)
                    if not res.get("results"):
                        st.info("No matching historical events indexed in FAISS yet.")
                    else:
                        for item in res["results"]:
                            sev = item.get("level", "INFO")
                            sev_color = SEVERITY_COLORS.get(sev, "#94a3b8")
                            st.markdown(
                                f"""
                                <div class="metric-card" style="margin-bottom:0.75rem; border-left:4px solid {sev_color};">
                                    <div style="display:flex; justify-content:space-between; font-size:0.82rem;">
                                        <span><strong>#{item['rank']}</strong> &bull; <code>{item.get('hostname', 'host')}</code> &bull; <code>[{item['service']}]</code> &bull; <strong style="color:{sev_color};">[{sev}]</strong></span>
                                        <span style="color:#10b981; font-weight:700;">{item['similarity_pct']}% Match</span>
                                    </div>
                                    <div style="font-family:'JetBrains Mono', monospace; font-size:0.85rem; color:#f8fafc; margin-top:0.3rem;">
                                        {item['message']}
                                    </div>
                                    <div style="font-size:0.72rem; color:#64748b; margin-top:0.2rem;">
                                        Timestamp: {item['timestamp']} &bull; Channel: {item.get('channel', '')}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        st.caption(f"ℹ️ {SIMILARITY_DISCLAIMER}")
                except Exception as e:
                    st.error(f"Semantic search failed: {e}")

        with tab_assistant:
            st.markdown("### 🤖 Conversational AI Infrastructure Assistant (Live Fleet Grounded)")
            st.caption("Queries real persisted logs, incidents, health scores, and risk trajectories from enrolled Windows machines.")
            if "live_assistant_history" not in st.session_state:
                st.session_state["live_assistant_history"] = []
            for msg in st.session_state["live_assistant_history"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg.get("evidence"):
                        with st.expander(f"📑 Evidence ({len(msg['evidence'])})", expanded=False):
                            for ev in msg["evidence"]:
                                st.code(f"[{ev.get('timestamp')}] [{ev.get('service')}] [{ev.get('level')}] {ev.get('message')}")
            prompt = st.chat_input("Ask about live incidents, root causes, health score, or recovery recommendations...", key="live_ai_input")
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

        with tab_roadmap:
            render_roadmap_tab()

else:
    if not active_content:
        st.info("Upload a log file or load a benchmark sample in the **📥 Log Ingestion & Upload** tab to analyze static files.")
    tab_overview, tab_rca, tab_search, tab_assistant, tab_upload, tab_roadmap = st.tabs([
        "🖥️ Infrastructure Overview",
        "🔍 Incidents & RCA (Stage 2)",
        "🔎 Semantic Search (FAISS)",
        "🤖 AI Assistant (Stage 4)",
        "📥 Log Ingestion & Upload",
        "🗺️ Research Roadmap",
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

    with tab_roadmap:
        render_roadmap_tab()

st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #64748b; font-size: 0.8rem; padding: 1rem;">
        Enterprise Autonomous AI Infrastructure Monitoring System • Real-Time Windows Agents, FastAPI, FAISS & Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
