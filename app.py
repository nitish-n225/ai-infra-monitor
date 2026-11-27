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
from src.embedding_engine import LogEmbeddingEngine
from src.health_score import InfrastructureHealthScorer
from src.ml_log_anomaly import LogAnomalyScorer
from src.parser import InfrastructureLogParser
from src.predictive_failure import PredictiveFailureDetector
from src.rca_engine import RootCauseAnalysisEngine
from src.realtime_client import (
    BackendAPIClient,
    get_backend_url,
    get_realtime_bridge,
    is_remote_backend_configured,
)
from src.sample_data import load_sample_log
from src.telemetry import TelemetryAnalyzer
from src.ui.components import (
    apply_custom_styles,
    esc,
    render_3d_ai_neural_core,
    render_3d_vector_constellation,
    render_assistant_faq_grid,
    render_hero_header,
    render_luxury_login_header,
    render_luxury_login_showcase,
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
ml_analysis = LogAnomalyScorer.score_parsed_logs(parsed_df)

vector_store = st.session_state["vector_store"]
if st.session_state.get("vector_store_indexed_file") != active_filename:
    vector_store.reset()
if not parsed_df.empty and vector_store.get_stats().get("total_vectors", 0) == 0:
    try:
        embs, recs, mode_used = LogEmbeddingEngine.embed_logs_with_fallback(parsed_df)
        if embs.size > 0:
            vector_store.build_index(embs, recs, embedding_mode=mode_used)
            st.session_state["vector_store_indexed_file"] = active_filename
    except Exception:
        pass

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
        "WORKSPACE",
        options=[
            "Overview",
            "Live Monitoring",
            "Log Intelligence",
            "AI Diagnostics",
            "Predictive Health",
            "Recovery Center",
            "Reports & Assistant",
        ],
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

# Top Command Header (hidden only on the dedicated login screen)
if not (data_mode == "Live Monitoring" and backend_health and not jwt_token):
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


def _render_live_semantic_search_panel():
    """Renders authenticated live fleet semantic search against Central Backend."""
    st.markdown("#### 🔎 Live Fleet Semantic Search")
    col_q, col_btn, col_k = st.columns([4.2, 1.1, 1.1], vertical_alignment="bottom")
    default_live_q = st.session_state.get("live_faiss_q", "")
    live_q = col_q.text_input(
        "🔍 Natural Language Search",
        value=default_live_q,
        placeholder="🔍 Search live logs by meaning (e.g. service terminated unexpectedly, disk space low)...",
        key="live_faiss_q_input",
    )
    col_btn.button("🔍 Search", use_container_width=True, type="primary", key="live_faiss_search_btn")
    live_k = col_k.number_input("Results", min_value=1, max_value=20, value=5, step=1, key="live_faiss_k")
    if live_q.strip():
        clean_live_q = live_q.strip()
        st.session_state["live_faiss_q"] = clean_live_q
        try:
            res = api_client.semantic_search(clean_live_q, top_k=int(live_k))
            if not res.get("results"):
                st.info("No matching historical events exceeded the semantic relevance threshold.")
            else:
                render_3d_vector_constellation(clean_live_q, res["results"])
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
                            <div style="font-family:'JetBrains Mono', monospace; font-size:0.84rem; color:#0f172a; margin-top:0.3rem;">
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


def _render_live_assistant_panel():
    """Renders authenticated live fleet AI assistant panel."""
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

    quick_live_prompt = render_assistant_faq_grid("live_ai")

    for msg in st.session_state["live_assistant_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("evidence"):
                with st.expander(f"📑 Evidence ({len(msg['evidence'])})", expanded=False):
                    for ev in msg["evidence"]:
                        st.code(f"[{ev.get('timestamp')}] [{ev.get('service')}] [{ev.get('level')}] {ev.get('message')}")

    chat_in = st.chat_input("Ask about live incidents, root causes, or recovery...", key="live_ai_input")
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


if data_mode == "Overview":
    if not active_content:
        st.info("Upload a log file or load a sample trace in **Log Intelligence → 📥 Upload Logs & Kaggle** to analyze traces.")
    render_overview_tab(telemetry_data, parsed_df, health_data, risk_data, ml_analysis=ml_analysis, active_filename=active_filename)

elif data_mode == "Live Monitoring":
    if not backend_health:
        if is_remote_backend_configured():
            st.info(
                f"Central backend (`{backend_url}`) is waking from sleep or temporarily unreachable. "
                "Click **🔄 Wake Backend Now** below (Render free tier cold starts typically take 20–40 seconds), "
                "or select **Overview** / **Log Intelligence** in the sidebar."
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
        st.markdown("<div style='height:0.65rem;'></div>", unsafe_allow_html=True)
        col_pad_l, col_portal, col_showcase, col_pad_r = st.columns([0.05, 1.32, 0.90, 0.05], gap="large")
        with col_portal:
            render_luxury_login_header()
            with st.form("operator_login_form"):
                u_in = st.text_input("Username", value="admin")
                p_in = st.text_input("Password", type="password", placeholder="MONITOR_ADMIN_PASSWORD or Admin Key")
                login_btn = st.form_submit_button("🔓 Sign In", use_container_width=True, type="primary")
        with col_showcase:
            render_luxury_login_showcase(height=360)
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
        tab_live, tab_admin = st.tabs(["📡 Fleet Overview", "⚙️ Fleet Admin"])
        with tab_live:
            render_live_fleet_fragment(api_client)
        with tab_admin:
            render_fleet_admin_tab(api_client)

elif data_mode == "Log Intelligence":
    if jwt_token and backend_health:
        tab_search, tab_upload, tab_live_search = st.tabs([
            "🔎 Semantic Search",
            "📥 Upload Logs & Kaggle",
            "📡 Live Fleet Search",
        ])
        with tab_search:
            render_semantic_search_tab(vector_store, parsed_df)
        with tab_upload:
            render_upload_tab(InfrastructureLogParser)
        with tab_live_search:
            _render_live_semantic_search_panel()
    else:
        tab_search, tab_upload = st.tabs(["🔎 Semantic Search", "📥 Upload Logs & Kaggle"])
        with tab_search:
            render_semantic_search_tab(vector_store, parsed_df)
        with tab_upload:
            render_upload_tab(InfrastructureLogParser)

elif data_mode == "AI Diagnostics":
    if jwt_token and backend_health:
        tab_rca_local, tab_rca_live = st.tabs(["🔍 Log Incidents, RCA & Kaggle ML", "🚨 Live Fleet Incidents & RCA"])
        with tab_rca_local:
            render_rca_tab(rca_results, risk_data, health_data, parsed_df, ml_analysis=ml_analysis)
        with tab_rca_live:
            render_live_incidents_fragment(api_client)
    else:
        render_rca_tab(rca_results, risk_data, health_data, parsed_df, ml_analysis=ml_analysis)

elif data_mode == "Predictive Health":
    from src.ui.components import render_3d_gauge_pair, render_metric_card
    st.markdown("#### 📈 Predictive Health & Failure Risk Modeling")
    h_score = float(health_data.get("health_score", 100.0))
    r_score = float(risk_data.get("risk_score", 0.0))
    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card("Health Index", f"{h_score}%", f"Condition: {health_data.get('condition', 'Stable')}", health_data.get("color", "#10b981"))
    with c2:
        render_metric_card("Failure Risk Score", f"{r_score}/100", f"Level: {risk_data.get('risk_level', 'LOW')}", "#ef4444" if r_score >= 70 else ("#f59e0b" if r_score >= 30 else "#10b981"))
    with c3:
        ml_peak = float(ml_analysis.get("max_anomaly_prob", 0.0)) if ml_analysis else 0.0
        render_metric_card("Kaggle ML Peak Risk", f"{ml_peak:.1f}%", f"Flagged: {ml_analysis.get('flagged_events', 0) if ml_analysis else 0} events", "#22d3ee")

    render_3d_gauge_pair(
        h_score,
        f"{health_data.get('condition', 'Stable')} ({h_score}%)",
        r_score,
        f"{risk_data.get('risk_level', 'LOW')} ({r_score}/100)",
    )
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("**Health Score Deduction Breakdown**")
        st.caption(health_data.get("explanation", ""))
        if health_data.get("deductions_breakdown"):
            st.dataframe(pd.DataFrame(health_data["deductions_breakdown"]), use_container_width=True, hide_index=True)
        else:
            st.success("Zero stability deductions.")
    with col_p2:
        st.markdown("**Predictive Risk Factor Weights**")
        st.caption(risk_data.get("risk_indicator", ""))
        if risk_data.get("contributing_factors"):
            st.dataframe(pd.DataFrame(risk_data["contributing_factors"]), use_container_width=True, hide_index=True)

    if jwt_token and backend_health:
        st.markdown("---")
        st.markdown("#### 💻 Live Host Telemetry Trend Forecasts")
        try:
            devs = api_client.get_devices()
            if not devs:
                st.info("No live agents enrolled yet.")
            for d in devs:
                fc = api_client.get_device_forecast(d["device_id"])
                if fc.get("warnings"):
                    for w in fc["warnings"]:
                        st.warning(f"**{d['hostname']}**: {w}")
                else:
                    st.caption(
                        f"**{d['hostname']}** ({fc.get('samples', 0)} samples): "
                        f"CPU `{fc.get('cpu_slope_per_sample', 0.0):+.2f}%` • "
                        f"RAM `{fc.get('ram_slope_per_sample', 0.0):+.2f}%` • "
                        f"Disk `{fc.get('disk_slope_per_sample', 0.0):+.2f}%`"
                    )
        except Exception as e:
            st.caption(f"Live forecast unavailable: {e}")

elif data_mode == "Recovery Center":
    from src.self_healing import SAFETY_POLICY_DISCLAIMER, SelfHealingEngine
    st.markdown("#### 🛠️ Recovery Center & Self-Healing Playbooks")
    st.caption(f"🛡️ {SAFETY_POLICY_DISCLAIMER}")
    incidents = rca_results.get("incidents", [])
    recommendations = SelfHealingEngine.generate_recommendations(incidents)
    if not recommendations:
        st.info("No active incidents requiring remediation in the loaded log trace.")
    else:
        for r in recommendations:
            st.markdown(
                f"""
                <div class="metric-card" style="margin-bottom:0.75rem; border-left:4px solid #22d3ee;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem;">
                        <strong style="color:#0f172a;">🔧 [{esc(r['action_id'])}] {esc(r['title'])}</strong>
                        <span style="font-size:0.75rem; color:#0284c7; font-weight:700;">Target: {esc(r['target_service'])}</span>
                    </div>
                    <div style="font-size:0.84rem; color:#334155; margin-bottom:0.3rem;"><strong>Reason:</strong> {esc(r['reason'])}</div>
                    <div style="font-size:0.78rem; color:#475569;"><strong>Prerequisites:</strong> {esc(r['prerequisites'])}</div>
                    <div style="font-size:0.78rem; color:#475569;"><strong>Verification:</strong> {esc(r['verification_steps'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"🧪 Simulate Dry-Run ({r['action_id']})", key=f"rec_sim_{r['action_id']}"):
                sim_result = SelfHealingEngine.simulate_action(r["action_id"])
                st.success(f"**{sim_result['message']}** (`{sim_result['simulation_mode']}`)")

    if jwt_token and backend_health:
        st.markdown("---")
        render_live_incidents_fragment(api_client)

elif data_mode == "Reports & Assistant":
    if jwt_token and backend_health:
        tab_ai_off, tab_ai_live, tab_rep = st.tabs([
            "🤖 Log AI Assistant",
            "📡 Live Fleet AI Assistant",
            "📄 Model & System Reports",
        ])
        with tab_ai_off:
            render_assistant_tab(assistant_engine, parsed_df, rca_results, health_data, risk_data, vector_store, active_filename)
        with tab_ai_live:
            _render_live_assistant_panel()
        with tab_rep:
            st.markdown("#### 📄 Export & Training Reports")
            if not parsed_df.empty:
                st.download_button(
                    "💾 Export Parsed Logs (CSV)",
                    data=parsed_df.to_csv(index=False).encode("utf-8"),
                    file_name=f"parsed_{active_filename}.csv",
                    mime="text/csv",
                )
            rep_path = Path("MODEL_TRAINING_REPORT.md")
            if rep_path.exists():
                rep_txt = rep_path.read_text(encoding="utf-8")
                st.download_button("📘 Download MODEL_TRAINING_REPORT.md", data=rep_txt.encode("utf-8"), file_name="MODEL_TRAINING_REPORT.md", mime="text/markdown")
                with st.expander("📖 Preview Kaggle Model Training Report", expanded=False):
                    st.markdown(rep_txt)
    else:
        tab_ai_off, tab_rep = st.tabs(["🤖 Log AI Assistant", "📄 Model & System Reports"])
        with tab_ai_off:
            render_assistant_tab(assistant_engine, parsed_df, rca_results, health_data, risk_data, vector_store, active_filename)
        with tab_rep:
            st.markdown("#### 📄 Export & Training Reports")
            if not parsed_df.empty:
                st.download_button(
                    "💾 Export Parsed Logs (CSV)",
                    data=parsed_df.to_csv(index=False).encode("utf-8"),
                    file_name=f"parsed_{active_filename}.csv",
                    mime="text/csv",
                )
            rep_path = Path("MODEL_TRAINING_REPORT.md")
            if rep_path.exists():
                rep_txt = rep_path.read_text(encoding="utf-8")
                st.download_button("📘 Download MODEL_TRAINING_REPORT.md", data=rep_txt.encode("utf-8"), file_name="MODEL_TRAINING_REPORT.md", mime="text/markdown")
                with st.expander("📖 Preview Kaggle Model Training Report", expanded=False):
                    st.markdown(rep_txt)
