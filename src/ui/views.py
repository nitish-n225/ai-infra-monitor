"""
Views and Layout Modules for Enterprise Autonomous AI Infrastructure Monitoring System.
Stage 2: Critical Event Detection, RCA, Health Scoring, and Self-Healing Recommendations.
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any, List
from config import STAGES, SEVERITY_COLORS
from src.ui.components import render_metric_card
from src.sample_data import load_sample_log
from src.self_healing import SelfHealingEngine, SAFETY_POLICY_DISCLAIMER

def render_overview_tab(telemetry: Dict[str, Any], df: pd.DataFrame, health_data: Dict[str, Any] = None, risk_data: Dict[str, Any] = None):
    """Renders the Infrastructure Overview and Health Telemetry tab."""
    st.markdown("### 🖥️ Enterprise Infrastructure Telemetry & Operational Health")
    st.caption("Real-time telemetry aggregated from ingested infrastructure service logs.")

    # Top KPI Metrics Row (Enhanced with Stage 2 Health & Failure Risk)
    col1, col2, col3, col4 = st.columns(4)

    total_logs = telemetry.get("total_logs", 0)
    crit_count = telemetry.get("critical_count", 0) + telemetry.get("error_count", 0)
    services_count = telemetry.get("unique_services_count", 0)

    # Health & Risk Data Defaults
    health_score = health_data.get("health_score", 100.0) if health_data else 100.0
    health_cond = health_data.get("condition", "Stable") if health_data else "Stable"
    health_color = health_data.get("color", "#10b981") if health_data else "#10b981"

    risk_score = risk_data.get("risk_score", 0.0) if risk_data else 0.0
    risk_level = risk_data.get("risk_level", "LOW") if risk_data else "LOW"
    risk_color = "#ef4444" if risk_score >= 70 else ("#f59e0b" if risk_score >= 30 else "#10b981")

    with col1:
        render_metric_card("Infrastructure Health Index", f"{health_score}%", f"Condition: {health_cond}", health_color)
    with col2:
        render_metric_card("Predictive Failure Risk", f"{risk_score}/100", f"Risk Level: {risk_level}", risk_color)
    with col3:
        render_metric_card("Critical & Error Incidents", f"{crit_count}", f"Across {total_logs:,} total logs", "#ef4444" if crit_count > 0 else "#10b981")
    with col4:
        render_metric_card("Monitored Services", f"{services_count}", "Active infrastructure components", "#a855f7")

    st.markdown("---")

    # Infrastructure Services Health Topology Cards
    st.markdown("#### 🌐 Monitored Service Components")
    if not df.empty and telemetry.get("service_counts"):
        service_cols = st.columns(min(len(telemetry["services"]), 4) or 1)
        for idx, (svc_name, count) in enumerate(telemetry["service_counts"].items()):
            col_target = service_cols[idx % len(service_cols)]
            with col_target:
                # Check if this service had errors
                svc_errors = df[(df["service"] == svc_name) & (df["level"].isin(["CRITICAL", "FATAL", "ERROR"]))].shape[0]
                status_color = "#ef4444" if svc_errors > 0 else "#10b981"
                status_text = f"⚠️ {svc_errors} Errors" if svc_errors > 0 else "🟢 Healthy"
                
                st.markdown(
                    f"""
                    <div class="metric-card" style="margin-bottom: 0.75rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="color: #f8fafc; font-size: 0.9rem;">{svc_name}</strong>
                            <span style="font-size: 0.75rem; color: {status_color}; font-weight: 700;">{status_text}</span>
                        </div>
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.35rem;">
                            {count} event logs recorded
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.info("No service telemetry available yet. Upload a log file in the Log Ingestion tab to view service components.")

    st.markdown("---")

    # Visual Charts Row
    st.markdown("#### 📊 Event Severity & Distribution")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("**Log Level Distribution**")
        if not df.empty and telemetry.get("level_counts"):
            level_series = pd.Series(telemetry["level_counts"])
            st.bar_chart(level_series, use_container_width=True)
        else:
            st.caption("Awaiting log ingestion.")

    with col_chart2:
        st.markdown("**Activity by Service Component**")
        if not df.empty and telemetry.get("service_counts"):
            svc_series = pd.Series(telemetry["service_counts"])
            st.bar_chart(svc_series, use_container_width=True)
        else:
            st.caption("Awaiting log ingestion.")

    # Critical Events Banner Feed
    if crit_count > 0 and telemetry.get("critical_events"):
        st.markdown("---")
        st.markdown("#### 🚨 Ingested Critical & Error Log Events")
        for ev in telemetry["critical_events"]:
            sev = ev.get("level", "ERROR")
            color = SEVERITY_COLORS.get(sev, "#ef4444")
            st.markdown(
                f"""
                <div class="critical-banner">
                    <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.25rem;">
                        <span><strong style="color: {color};">[{sev}]</strong> Service: <code>{ev.get('service', 'unknown')}</code></span>
                        <span>{ev.get('timestamp', '')}</span>
                    </div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #f8fafc;">
                        {ev.get('message', '')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

def render_rca_tab(rca_results: Dict[str, Any], risk_data: Dict[str, Any], health_data: Dict[str, Any], df: pd.DataFrame):
    """Renders the Stage 2 Incident Analysis, Root Cause Analysis, and Health Scoring tab."""
    st.markdown("### 🔍 Root Cause Analysis (RCA), Health Score & Risk Assessment")
    st.caption("Automated failure classification across 6 incident categories, risk trajectories, and safe recovery playbooks.")

    # Section 1: Health Score & Failure Risk Summary
    st.markdown("#### 1. Infrastructure Health & Failure Risk Profile")
    col_h1, col_h2 = st.columns(2)

    with col_h1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="metric-label">INFRASTRUCTURE HEALTH SCORE</span>
                    <span style="font-size: 0.85rem; font-weight: 700; color: {health_data['color']};">
                        Condition: {health_data['condition']}
                    </span>
                </div>
                <div class="metric-value" style="color: {health_data['color']}; margin: 0.35rem 0;">
                    {health_data['health_score']}%
                </div>
                <div class="metric-desc" style="color: #cbd5e1;">
                    {health_data['explanation']}
                </div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #94a3b8; margin-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 0.35rem;">
                    Formula: {health_data['formula_summary']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.expander("📐 View Health Score Deduction Breakdown", expanded=False):
            if health_data.get("deductions_breakdown"):
                for d in health_data["deductions_breakdown"]:
                    st.markdown(f"- **{d['reason']}**: `- {d['deduction']} pts` ({d['detail']})")
            else:
                st.write("Zero penalty deductions. Full 100.0% operational health.")

    with col_h2:
        risk_score = risk_data.get("risk_score", 0.0)
        risk_color = "#ef4444" if risk_score >= 70 else ("#f59e0b" if risk_score >= 30 else "#10b981")
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="metric-label">PREDICTIVE FAILURE RISK INDEX</span>
                    <span style="font-size: 0.85rem; font-weight: 700; color: {risk_color};">
                        Risk Level: {risk_data['risk_level']}
                    </span>
                </div>
                <div class="metric-value" style="color: {risk_color}; margin: 0.35rem 0;">
                    {risk_score}/100
                </div>
                <div class="metric-desc" style="color: #cbd5e1;">
                    {risk_data['risk_indicator']}
                </div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.5rem; font-style: italic; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 0.35rem;">
                    ⚠️ {risk_data['disclaimer']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.expander("📊 View Risk Factor Breakdown & Weights", expanded=False):
            if risk_data.get("contributing_factors"):
                factor_df = pd.DataFrame([
                    {
                        "Factor": f["factor"],
                        "Score Contribution": f"{f['score']} / {f['max_weight']} pts",
                        "Observed Metric": f["metric"],
                        "Impact": f["impact"]
                    }
                    for f in risk_data["contributing_factors"]
                ])
                st.dataframe(factor_df, use_container_width=True, hide_index=True)
            else:
                st.write(risk_data.get("summary", "No factors computed."))

    st.markdown("---")

    # Section 2: Detected Incidents & Root Cause Analysis
    st.markdown("#### 2. Detected Critical Incidents & Root Cause Analysis")
    incidents = rca_results.get("incidents", [])

    if not incidents:
        st.success("🟢 All Services Healthy: No failure signatures detected in the active log trace.")
    else:
        st.warning(f"⚠️ Identified **{len(incidents)} critical operational failure category/categories**.")

        for idx, inc in enumerate(incidents, start=1):
            sev_color = "#ef4444" if inc["severity"] == "CRITICAL" else "#f59e0b"
            with st.expander(f"Incident #{idx}: [{inc['severity']}] {inc['title']} ({inc['evidence_count']} Evidence Lines)", expanded=True):
                col_i1, col_i2 = st.columns([1.5, 1])

                with col_i1:
                    st.markdown(f"**Likely Root Cause (Inferred)**:")
                    st.markdown(f"> {inc['likely_root_cause']}")
                    st.markdown(f"**Rule-Match Explanation**: {inc['explanation']}")

                with col_i2:
                    st.markdown(f"**Severity**: `<span style='color:{sev_color}; font-weight:700;'>{inc['severity']}</span>`", unsafe_allow_html=True)
                    st.markdown(f"**Detection Confidence**: `{inc['confidence_label']}`")
                    st.markdown(f"**Category Identifier**: `{inc['category']}`")

                st.markdown("##### 🔍 Supporting Log Evidence (Direct from Original Trace):")
                evidence_rows = []
                for ev in inc["detected_evidence"]:
                    evidence_rows.append({
                        "Line": ev.get("line_no", "-"),
                        "Timestamp": ev.get("timestamp", "-"),
                        "Service": ev.get("service", "-"),
                        "Level": ev.get("level", "-"),
                        "Matched Message": ev.get("message", "-")
                    })
                st.dataframe(pd.DataFrame(evidence_rows), use_container_width=True, hide_index=True)

                st.markdown("##### 🛠️ Recommended Next Steps:")
                for step in inc["recommended_next_steps"]:
                    st.markdown(f"- {step}")

    st.markdown("---")

    # Section 3: Autonomous Self-Healing Recommendations & Safe Simulation
    st.markdown("#### 3. Autonomous Self-Healing Recommendations & Recovery Playbooks")
    st.caption(f"🛡️ {SAFETY_POLICY_DISCLAIMER}")

    recommendations = SelfHealingEngine.generate_recommendations(incidents)

    if not recommendations:
        st.info("No active incidents requiring remediation playbooks.")
    else:
        for r in recommendations:
            with st.container():
                st.markdown(
                    f"""
                    <div class="metric-card" style="margin-bottom: 0.85rem; border-left: 4px solid #38bdf8;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                            <span style="font-weight: 700; color: #f8fafc; font-size: 0.95rem;">
                                🔧 [{r['action_id']}] {r['title']}
                            </span>
                            <span style="font-size: 0.75rem; color: #38bdf8; font-weight: 700;">
                                Target: {r['target_service']}
                            </span>
                        </div>
                        <div style="font-size: 0.85rem; color: #cbd5e1; margin-bottom: 0.4rem;">
                            <strong>Reason:</strong> {r['reason']}
                        </div>
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.25rem;">
                            <strong>Prerequisites:</strong> {r['prerequisites']}
                        </div>
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.5rem;">
                            <strong>Verification Steps:</strong> {r['verification_steps']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Simulated Dry-Run Execution Button (Guarantees zero live commands)
                btn_key = f"sim_btn_{r['action_id']}"
                if st.button(f"🧪 Simulate Dry-Run Remediation ({r['action_id']})", key=btn_key):
                    sim_result = SelfHealingEngine.simulate_action(r["action_id"])
                    st.success(
                        f"**{sim_result['message']}**\n\n"
                        f"*Mode*: `{sim_result['simulation_mode']}` • *Safety Assurance*: {sim_result['safety_guarantee']}"
                    )

def render_upload_tab(parser_cls):
    """Renders the Log Ingestion and Upload tab."""
    st.markdown("### 📥 Infrastructure Log Ingestion")
    st.caption("Upload raw system, Kubernetes, cloud, or application logs (.log, .txt, .csv, .json).")

    # Sample Log Quick-Load Section
    with st.expander("⚡ Instant Testing: Load Built-in Enterprise Sample Logs", expanded=True):
        st.markdown("If you don't have a log file on hand, load realistic enterprise benchmark logs with one click:")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("🔥 Load Production Incident Log (Cascading Outage)", use_container_width=True):
                sample_text = load_sample_log("production_incident.log")
                if sample_text:
                    st.session_state["raw_log_content"] = sample_text
                    st.session_state["active_file_name"] = "production_incident.log"
                    st.success("Loaded 'production_incident.log' successfully!")
                    st.rerun()
        with col_s2:
            if st.button("🟢 Load Normal Operations Log (Healthy Cluster)", use_container_width=True):
                sample_text = load_sample_log("normal_operations.log")
                if sample_text:
                    st.session_state["raw_log_content"] = sample_text
                    st.session_state["active_file_name"] = "normal_operations.log"
                    st.success("Loaded 'normal_operations.log' successfully!")
                    st.rerun()

    # File Uploader
    uploaded_file = st.file_uploader(
        "Upload Infrastructure Log File",
        type=["log", "txt", "csv", "json"],
        help="Upload standard enterprise logs (Syslog, K8s, Docker, Nginx, or microservice logs)"
    )

    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode("utf-8", errors="replace")
            st.session_state["raw_log_content"] = content
            st.session_state["active_file_name"] = uploaded_file.name
            st.success(f"File '{uploaded_file.name}' uploaded successfully ({len(content.splitlines())} lines).")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # Active Log Data Processing
    active_content = st.session_state.get("raw_log_content", "")
    active_filename = st.session_state.get("active_file_name", "None")

    if active_content:
        st.markdown("---")
        st.markdown(f"#### 📄 Active Dataset: ` {active_filename} `")
        
        # Parse into DataFrame
        df = parser_cls.parse_text(active_content)
        st.session_state["parsed_df"] = df

        # Quick filters
        st.markdown("##### 🔍 Filter & Explore Parsed Logs")
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        
        with col_f1:
            search_query = st.text_input("Search in message text or service", placeholder="e.g. timeout, memory, postgres...")
        with col_f2:
            all_levels = sorted(df["level"].unique().tolist())
            selected_levels = st.multiselect("Severity Level", options=all_levels, default=all_levels)
        with col_f3:
            all_services = sorted(df["service"].unique().tolist())
            selected_services = st.multiselect("Service Name", options=all_services, default=all_services)

        # Apply filtering
        filtered_df = df.copy()
        if selected_levels:
            filtered_df = filtered_df[filtered_df["level"].isin(selected_levels)]
        if selected_services:
            filtered_df = filtered_df[filtered_df["service"].isin(selected_services)]
        if search_query:
            query_lower = search_query.lower()
            filtered_df = filtered_df[
                filtered_df["message"].str.lower().str.contains(query_lower, na=False) |
                filtered_df["service"].str.lower().str.contains(query_lower, na=False)
            ]

        # Display Parsed Table
        st.caption(f"Showing {len(filtered_df)} of {len(df)} total parsed log lines.")
        st.dataframe(
            filtered_df[["line_no", "timestamp", "level", "service", "message"]],
            use_container_width=True,
            height=360
        )

        # Download button
        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="💾 Download Filtered Logs as CSV",
            data=csv_data,
            file_name=f"parsed_{active_filename}.csv",
            mime="text/csv"
        )

        # Raw log viewer
        with st.expander("👁️ Inspect Raw Unparsed Log Text"):
            st.text_area("Raw Text", active_content, height=220, disabled=True)
    else:
        st.info("No active log dataset loaded. Upload a file above or click one of the instant testing buttons to begin.")

def render_roadmap_tab():
    """Renders the Research Project Roadmap & Architecture tab."""
    st.markdown("### 🗺️ System Architecture & Implementation Roadmap")
    st.caption("College Mini-Project Research Implementation: Enterprise Autonomous AI Infrastructure Monitoring System")

    st.markdown(
        """
        > **Academic Alignment (IEEE Paper Specification)**:
        > This project directly implements the 10-step algorithm and 11 core functional modules specified in your research paper.
        """
    )

    for stage_key, info in STAGES.items():
        is_complete = info["status"] == "COMPLETED"
        icon = "✅" if is_complete else "⏳"
        badge_style = "color: #10b981; font-weight: 700;" if is_complete else "color: #f59e0b; font-weight: 700;"

        st.markdown(
            f"""
            <div class="metric-card" style="margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                    <span style="font-size: 1.05rem; font-weight: 700; color: #f8fafc;">{icon} {stage_key}: {info['title']}</span>
                    <span style="{badge_style}">[{info['status']}]</span>
                </div>
                <div style="font-size: 0.75rem; color: #38bdf8; font-weight: 600; margin-bottom: 0.4rem;">
                    Paper Mapping: {info.get('paper_steps', '')}
                </div>
                <div style="font-size: 0.85rem; color: #94a3b8; line-height: 1.4;">
                    {info['description']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("#### 🔬 Research Paper Architecture & 11 Core Modules (Table 1)")
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown(
            """
            * **Log Upload Module**: Multi-format log ingestion (`.log`, `.txt`, `.csv`, `.json`).
            * **Log Processing Module**: Cleaning, symbol normalization & structured parsing.
            * **Semantic Embedding Module**: SentenceTransformer (`all-MiniLM-L6-v2`) embeddings.
            * **FAISS Intelligence Engine**: Scalable high-dimensional vector similarity indexing.
            * **Critical Event Detection**: Error, fail, crash, timeout keyword & pattern filtering.
            * **Root Cause Analysis (RCA)**: Pinpoints 6 failure causes (DB, CPU, Memory, Storage, Auth, Network).
            """
        )
    with col_m2:
        st.markdown(
            """
            * **Predictive Failure Detection**: Instability probability based on anomaly frequency.
            * **Autonomous Self-Healing Engine**: Proactive recovery suggestions (restarts, scale-out, cache flush).
            * **Infrastructure Health Scoring Module**: Health Index percentage (Stable, Warning, Critical).
            * **Conversational AI Assistant**: Natural language operational assistant for engineers.
            * **Monitoring Dashboard**: Interactive Streamlit observability frontend.
            """
        )

def render_semantic_search_tab(vector_store, df: pd.DataFrame):
    """Renders the Stage 3 Semantic Log Search and FAISS Similarity Retrieval tab."""
    from src.embedding_engine import LogEmbeddingEngine
    from src.vector_store import SIMILARITY_DISCLAIMER

    st.markdown("### 🔎 Semantic Log Vectorization & FAISS Similarity Search")
    st.caption("Dense vector representation using SentenceTransformer 'all-MiniLM-L6-v2' (384 dimensions) and sub-second similarity retrieval via FAISS.")

    stats = vector_store.get_stats()
    total_indexed = stats.get("total_vectors", 0)

    # Section 1: Vector Index Status & Controls
    col_idx1, col_idx2 = st.columns([2, 1])

    with col_idx1:
        if total_indexed > 0:
            st.success(f"🟢 **FAISS CPU Vector Index Active**: `{total_indexed}` log records indexed (384-dimensional dense vectors).")
        else:
            st.warning("⚪ **FAISS Vector Index Empty**: Active logs have not been vectorized yet.")

    with col_idx2:
        btn_label = "⚡ Index Active Logs in FAISS" if total_indexed == 0 else "🔄 Re-Index Active Dataset"
        if st.button(btn_label, use_container_width=True, type="primary" if total_indexed == 0 else "secondary"):
            if df.empty:
                st.error("No active logs to index. Upload or load a log file first.")
            else:
                with st.spinner("Generating 384-dim dense embeddings with SentenceTransformer ('all-MiniLM-L6-v2')..."):
                    try:
                        embeddings, records = LogEmbeddingEngine.embed_logs(df)
                        vector_store.build_index(embeddings, records)
                        st.session_state["vector_store_indexed_file"] = st.session_state.get("active_file_name", "unknown")
                        st.success(f"Successfully generated and indexed {len(records)} log vectors into FAISS!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to generate embeddings: {e}")

    st.markdown("---")

    # Section 2: Semantic Search Query Interface
    st.markdown("#### 💬 Natural Language Infrastructure Query")
    st.markdown("Search infrastructure logs using plain everyday English—the model retrieves contextually similar events even when exact keywords don't match:")

    # Quick Preset Query Buttons
    st.markdown("<small style='color:#94a3b8;'>Quick Query Presets (Click to Search):</small>", unsafe_allow_html=True)
    col_q1, col_q2, col_q3, col_q4, col_q5 = st.columns(5)
    
    preset_query = None
    with col_q1:
        if st.button("💥 DB Pool Depleted", use_container_width=True):
            preset_query = "database connection failure and slots"
    with col_q2:
        if st.button("🧠 Out of Memory", use_container_width=True):
            preset_query = "out of memory container crash OOM"
    with col_q3:
        if st.button("🌐 Network Latency", use_container_width=True):
            preset_query = "upstream gateway timeout and latency"
    with col_q4:
        if st.button("⚡ CPU Saturation", use_container_width=True):
            preset_query = "high CPU utilization compute load"
    with col_q5:
        if st.button("🔒 Auth Failure", use_container_width=True):
            preset_query = "token verification timeout unauthorized"

    # Search Bar & Top-K Slider
    col_s1, col_s2 = st.columns([3, 1])

    with col_s1:
        default_query_text = preset_query or st.session_state.get("last_semantic_query", "database connection pool exhausted")
        user_query = st.text_input(
            "Natural Language Query",
            value=default_query_text,
            placeholder="e.g. database pool exhausted, high memory pressure, circuit breaker..."
        )
    with col_s2:
        top_k = st.slider("Max Results (Top-K)", min_value=1, max_value=20, value=5, key="semantic_top_k_slider")

    # Execute Search
    if total_indexed == 0:
        st.info("👆 Please click **'⚡ Index Active Logs in FAISS'** above to generate vector embeddings before searching.")
    elif user_query:
        st.session_state["last_semantic_query"] = user_query
        search_res = vector_store.search(user_query, top_k=top_k)

        st.markdown(f"##### 🎯 Search Results for: *'{user_query}'*")
        st.caption(f"Retrieved **{search_res['total_matches']}** most contextually relevant log records.")

        if not search_res["results"]:
            st.info("No matching log vectors found.")
        else:
            for item in search_res["results"]:
                rank = item["rank"]
                score_pct = item["similarity_pct"]
                raw_score = item["similarity_score"]
                sev = item.get("level", "INFO")
                sev_color = SEVERITY_COLORS.get(sev, "#94a3b8")
                score_color = "#10b981" if score_pct >= 70 else ("#38bdf8" if score_pct >= 50 else "#94a3b8")

                st.markdown(
                    f"""
                    <div class="metric-card" style="margin-bottom: 0.75rem; border-left: 4px solid {score_color};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                            <span>
                                <strong style="color: #f8fafc; font-size: 0.95rem;">#{rank}</strong> &nbsp;
                                <span style="font-size: 0.75rem; color: #94a3b8;">Line {item['line_no']}</span> &nbsp;
                                <code style="color: #38bdf8;">[{item['service']}]</code> &nbsp;
                                <strong style="color: {sev_color};">[{sev}]</strong>
                            </span>
                            <span style="font-size: 0.8rem; font-weight: 700; color: {score_color};">
                                {score_pct}% Match <small style="color: #64748b;">(Cosine: {raw_score})</small>
                            </span>
                        </div>
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #f8fafc; margin-bottom: 0.25rem;">
                            {item['message']}
                        </div>
                        <div style="font-size: 0.7rem; color: #64748b;">
                            Timestamp: {item['timestamp']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.caption(f"ℹ️ {SIMILARITY_DISCLAIMER}")

    st.markdown("---")

    # Section 3: Educational Comparison Card
    st.markdown("#### 🔬 Research Insight: Semantic Vector Search vs Root Cause Analysis")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown(
            """
            **Stage 3: FAISS Semantic Vector Search**
            - Converts unstructured log strings into 384-dimensional continuous dense embeddings using a transformer model (`all-MiniLM-L6-v2`).
            - Computes geometric cosine similarity to discover synonymously phrased logs.
            - *Scope*: Information retrieval & contextual log exploration.
            """
        )
    with col_c2:
        st.markdown(
            """
            **Stage 2: Root Cause Analysis (RCA)**
            - Classifies systemic operational failures into 6 fault tree categories (DB, CPU, Memory, Storage, Auth, Network).
            - Distinguishes observed symptoms from inferred root causes and assesses failure risk.
            - *Scope*: Diagnostic reasoning & incident remediation.
            """
        )

def render_assistant_tab(assistant, df: pd.DataFrame, rca_results: Dict[str, Any], health_data: Dict[str, Any], risk_data: Dict[str, Any], vector_store, active_filename: str):
    """
    Renders Stage 4 Conversational AI Infrastructure Assistant tab.
    Provides natural-language dialogue grounded strictly in active logs, RCA findings,
    health calculation breakdown, predictive failure risk, and advisory self-healing playbooks.
    """
    st.markdown("### 🤖 Conversational AI Infrastructure Assistant")
    st.caption("Interactive natural language copilot grounded in operational log telemetry, RCA fault trees, and FAISS vector intelligence.")

    # Provider and Dataset Context Header
    col_p1, col_p2, col_p3 = st.columns([2, 1.5, 1])
    with col_p1:
        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.6); padding: 0.6rem 0.85rem; border-radius: 8px; border: 1px solid #334155;">
                <span style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Active AI Provider</span><br>
                <strong style="color: #38bdf8; font-size: 0.85rem;">{assistant.provider.provider_name}</strong>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_p2:
        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.6); padding: 0.6rem 0.85rem; border-radius: 8px; border: 1px solid #334155;">
                <span style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Grounding Context</span><br>
                <strong style="color: #f8fafc; font-size: 0.85rem;">`{active_filename}`</strong>
                <span style="font-size: 0.75rem; color: #10b981;"> ({len(df)} logs)</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_p3:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            assistant.reset_session(active_filename)
            st.session_state["assistant_chat_history"] = []
            st.rerun()

    st.markdown("---")

    # Safety Notice Banner
    st.info("🛡️ **Safety Policy**: All remediation guidance and recovery actions are strictly advisory dry-run simulations. Execution on live infrastructure is disabled.")

    # Initialize Session Chat History
    if "assistant_chat_history" not in st.session_state:
        st.session_state["assistant_chat_history"] = []

    # Quick Inquiry Preset Prompts
    st.markdown("##### 💡 Suggested Questions (Click to Ask)")
    col_q1, col_q2, col_q3 = st.columns(3)
    col_q4, col_q5, col_q6 = st.columns(3)

    submitted_prompt = None

    with col_q1:
        if st.button("💥 Why is the database failing?", use_container_width=True):
            submitted_prompt = "Why is the database failing?"
    with col_q2:
        if st.button("🚨 What are the critical incidents?", use_container_width=True):
            submitted_prompt = "What are the most critical incidents?"
    with col_q3:
        if st.button("🌐 Which services are affected?", use_container_width=True):
            submitted_prompt = "Which services are affected?"
    with col_q4:
        if st.button("🩺 How was health score calculated?", use_container_width=True):
            submitted_prompt = "How was the health score calculated?"
    with col_q5:
        if st.button("⚡ What factors increased risk score?", use_container_width=True):
            submitted_prompt = "What factors increased the infrastructure risk score?"
    with col_q6:
        if st.button("🛠️ What recovery steps are recommended?", use_container_width=True):
            submitted_prompt = "What recovery steps are recommended?"

    st.markdown("---")

    # Render Conversation Thread
    chat_container = st.container()

    with chat_container:
        if not st.session_state["assistant_chat_history"]:
            st.markdown(
                """
                <div style="text-align: center; padding: 2rem 1rem; color: #64748b;">
                    <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">💬</div>
                    <strong style="color: #cbd5e1; font-size: 1rem;">Infrastructure Assistant Ready</strong><br>
                    Ask any question about root causes, failure risk, affected services, or recommended remediation steps.<br>
                    <small style="color: #475569;">All answers are 100% grounded in your active logs and verified by source line numbers.</small>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            for msg in st.session_state["assistant_chat_history"]:
                role = msg.get("role", "user")
                if role == "user":
                    with st.chat_message("user"):
                        st.markdown(f"**{msg.get('content')}**")
                else:
                    with st.chat_message("assistant"):
                        # Provider badge
                        p_name = msg.get("provider", "Deterministic Engine")
                        conf = msg.get("confidence", "HIGH")
                        conf_color = "#10b981" if conf == "HIGH" else ("#f59e0b" if conf == "MEDIUM" else "#ef4444")

                        st.markdown(
                            f"""
                            <div style="margin-bottom: 0.5rem;">
                                <span style="font-size: 0.7rem; color: #38bdf8; background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.25); padding: 2px 6px; border-radius: 4px;">
                                    {p_name}
                                </span> &nbsp;
                                <span style="font-size: 0.7rem; color: {conf_color}; background: rgba(15,23,42,0.6); border: 1px solid {conf_color}; padding: 2px 6px; border-radius: 4px;">
                                    Confidence: {conf}
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        st.markdown(msg.get("content", ""))

                        # Supporting Evidence Expander
                        evidence = msg.get("evidence", [])
                        if evidence:
                            with st.expander(f"📑 Ground-Truth Log Evidence ({len(evidence)} events)", expanded=False):
                                for ev in evidence:
                                    line_no = ev.get("line_no", 0)
                                    ts = ev.get("timestamp", "N/A")
                                    svc = ev.get("service", "unknown")
                                    lvl = ev.get("level", "INFO")
                                    msg_text = ev.get("message", "")
                                    sev_color = SEVERITY_COLORS.get(lvl, "#94a3b8")

                                    st.markdown(
                                        f"""
                                        <div style="background: rgba(15,23,42,0.8); border: 1px solid #334155; border-left: 3px solid {sev_color}; padding: 0.5rem; border-radius: 4px; margin-bottom: 0.4rem;">
                                            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; margin-bottom: 0.2rem;">
                                                <span><strong>Line {line_no}</strong> &bull; <code>[{svc}]</code> &bull; <strong style="color: {sev_color};">[{lvl}]</strong></span>
                                                <span style="color: #64748b;">{ts}</span>
                                            </div>
                                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #f8fafc;">
                                                {msg_text}
                                            </div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )

    # Chat Input Box
    chat_prompt = st.chat_input("Ask a question about infrastructure incidents, root causes, health score, or recovery...")
    active_prompt = submitted_prompt or chat_prompt

    if active_prompt:
        # Append user message
        st.session_state["assistant_chat_history"].append({
            "role": "user",
            "content": active_prompt
        })

        # Process query with Assistant Engine
        with st.spinner("Analyzing operational telemetry and logs..."):
            res = assistant.ask(
                query=active_prompt,
                df=df,
                rca_results=rca_results,
                health_data=health_data,
                risk_data=risk_data,
                vector_store=vector_store,
                dataset_id=active_filename
            )

        # Append assistant response
        st.session_state["assistant_chat_history"].append({
            "role": "assistant",
            "content": res["answer"],
            "provider": res["provider"],
            "confidence": res["confidence"],
            "evidence": res["evidence"],
            "intent": res["intent"]
        })

        st.rerun()


