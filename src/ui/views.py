"""
Clean Static / Uploaded Log Analyzer Views for Enterprise AI Infrastructure Monitor.
"""
from typing import Any, Dict
import pandas as pd
import streamlit as st

from config import SEVERITY_COLORS
from src.sample_data import load_sample_log
from src.self_healing import SAFETY_POLICY_DISCLAIMER, SelfHealingEngine
from src.ui.components import (
    esc,
    render_3d_ai_neural_core,
    render_3d_gauge_pair,
    render_3d_rca_fault_graph,
    render_3d_topology_scene,
    render_3d_vector_constellation,
    render_metric_card,
)


def render_overview_tab(
    telemetry: Dict[str, Any],
    df: pd.DataFrame,
    health_data: Dict[str, Any] = None,
    risk_data: Dict[str, Any] = None,
):
    """Renders the static log telemetry and operational health overview."""
    col1, col2, col3, col4 = st.columns(4)
    total_logs = telemetry.get("total_logs", 0)
    crit_count = telemetry.get("critical_count", 0) + telemetry.get("error_count", 0)
    services_count = telemetry.get("unique_services_count", 0)

    health_score = health_data.get("health_score", 100.0) if health_data else 100.0
    health_cond = health_data.get("condition", "Stable") if health_data else "Stable"
    health_color = health_data.get("color", "#10b981") if health_data else "#10b981"

    risk_score = risk_data.get("risk_score", 0.0) if risk_data else 0.0
    risk_level = risk_data.get("risk_level", "LOW") if risk_data else "LOW"
    risk_color = "#ef4444" if risk_score >= 70 else ("#f59e0b" if risk_score >= 30 else "#10b981")

    with col1:
        render_metric_card("Health Index", f"{health_score}%", f"Condition: {health_cond}", health_color, accent=health_color)
    with col2:
        render_metric_card("Failure Risk", f"{risk_score}/100", f"Risk Level: {risk_level}", risk_color, accent=risk_color)
    with col3:
        render_metric_card(
            "Critical & Errors",
            f"{crit_count}",
            f"Out of {total_logs:,} logs",
            "#ef4444" if crit_count > 0 else "#10b981",
            accent="#ef4444" if crit_count > 0 else "#10b981",
        )
    with col4:
        render_metric_card("Services", f"{services_count}", "Active components", "#22d3ee", accent="#22d3ee")

    if not df.empty:
        st.markdown("")
        render_3d_gauge_pair(health_score, health_cond, risk_score, risk_level)

    st.markdown("---")
    st.markdown("#### 🌐 3D Infrastructure Service Topology")
    if not df.empty and telemetry.get("service_counts"):
        svc_3d_nodes = []
        for svc_name, count in telemetry["service_counts"].items():
            svc_crit = df[(df["service"] == svc_name) & (df["level"].isin(["CRITICAL", "FATAL"]))].shape[0]
            svc_err = df[(df["service"] == svc_name) & (df["level"] == "ERROR")].shape[0]
            svc_warn = df[(df["service"] == svc_name) & (df["level"].isin(["WARN", "WARNING"]))].shape[0]
            state = "critical" if svc_crit > 0 else ("warning" if (svc_err > 0 or svc_warn > 0) else "healthy")
            svc_3d_nodes.append({
                "label": svc_name,
                "state": state,
                "size": min(22, 11 + int(count)),
                "detail": f"Events: {int(count)}<br>Critical: {int(svc_crit)} | Errors: {int(svc_err)} | Warns: {int(svc_warn)}",
            })
        render_3d_topology_scene(
            nodes=svc_3d_nodes,
            center_label="Cluster Core",
            center_sub="RCA Fault Graph",
            title="Interactive 3D Service Dependency & Fault Topology",
            height=350,
        )

        service_cols = st.columns(min(len(telemetry["services"]), 4) or 1)
        for idx, (svc_name, count) in enumerate(telemetry["service_counts"].items()):
            with service_cols[idx % len(service_cols)]:
                svc_errors = df[(df["service"] == svc_name) & (df["level"].isin(["CRITICAL", "FATAL", "ERROR"]))].shape[0]
                status_color = "#ef4444" if svc_errors > 0 else "#10b981"
                status_text = f"⚠️ {svc_errors} Errors" if svc_errors > 0 else "● Healthy"
                st.markdown(
                    f"""
                    <div class="metric-card" style="margin-bottom:0.75rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong style="color:#f1f5f9; font-size:0.9rem;">{esc(svc_name)}</strong>
                            <span style="font-size:0.74rem; color:{status_color}; font-weight:700;">{esc(status_text)}</span>
                        </div>
                        <div style="font-size:0.74rem; color:#94a3b8; margin-top:0.35rem;">{esc(count)} log events</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("Upload a log file or load a sample dataset in **📥 Upload Logs** to inspect telemetry.")

    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.markdown("**Log Severity Distribution**")
        if not df.empty and telemetry.get("level_counts"):
            st.bar_chart(pd.Series(telemetry["level_counts"]), use_container_width=True)
        else:
            st.caption("Awaiting log dataset.")
    with col_chart2:
        st.markdown("**Events by Service**")
        if not df.empty and telemetry.get("service_counts"):
            st.bar_chart(pd.Series(telemetry["service_counts"]), use_container_width=True)
        else:
            st.caption("Awaiting log dataset.")

    if crit_count > 0 and telemetry.get("critical_events"):
        st.markdown("---")
        st.markdown("#### 🚨 Critical & Error Events")
        for ev in telemetry["critical_events"]:
            sev = ev.get("level", "ERROR")
            color = SEVERITY_COLORS.get(sev, "#ef4444")
            st.markdown(
                f"""
                <div class="critical-banner">
                    <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#94a3b8; margin-bottom:0.25rem;">
                        <span><strong style="color:{color};">[{esc(sev)}]</strong> <code>{esc(ev.get('service', 'unknown'))}</code></span>
                        <span>{esc(ev.get('timestamp', ''))}</span>
                    </div>
                    <div style="font-family:'JetBrains Mono', monospace; font-size:0.84rem; color:#f1f5f9;">
                        {esc(ev.get('message', ''))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_rca_tab(rca_results: Dict[str, Any], risk_data: Dict[str, Any], health_data: Dict[str, Any], df: pd.DataFrame):
    """Renders 3D Health/Risk gauges, 3D RCA Fault Graph, Root Cause Analysis, and Playbooks."""
    risk_score = risk_data.get("risk_score", 0.0)
    render_3d_gauge_pair(
        health_data["health_score"],
        f"{health_data['condition']} ({health_data['health_score']}%)",
        risk_score,
        f"{risk_data['risk_level']} ({risk_score}/100)",
    )

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        with st.expander("📐 Score Deduction Breakdown", expanded=False):
            st.caption(health_data["explanation"])
            if health_data.get("deductions_breakdown"):
                for d in health_data["deductions_breakdown"]:
                    st.markdown(f"- **{d['reason']}**: `- {d['deduction']} pts` ({d['detail']})")
            else:
                st.write("Zero deductions — 100.0% healthy.")

    with col_h2:
        with st.expander("📊 Risk Factor Weights", expanded=False):
            st.caption(risk_data["risk_indicator"])
            if risk_data.get("contributing_factors"):
                factor_df = pd.DataFrame([
                    {
                        "Factor": f["factor"],
                        "Contribution": f"{f['score']} / {f['max_weight']} pts",
                        "Observed": f["metric"],
                        "Impact": f["impact"],
                    }
                    for f in risk_data["contributing_factors"]
                ])
                st.dataframe(factor_df, use_container_width=True, hide_index=True)
            else:
                st.write(risk_data.get("summary", "No factors computed."))

    st.markdown("---")
    st.markdown("#### 🔍 3D Root Cause Analysis & Incidents")
    incidents = rca_results.get("incidents", [])
    if not incidents:
        st.success("🟢 No failure signatures detected in the active dataset.")
    else:
        render_3d_rca_fault_graph(incidents, live_mode=False, height=340)
        for idx, inc in enumerate(incidents, start=1):
            sev_color = "#ef4444" if inc["severity"] == "CRITICAL" else "#f59e0b"
            with st.expander(f"#{idx} [{inc['severity']}] {inc['title']} ({inc['evidence_count']} log lines)", expanded=True):
                col_i1, col_i2 = st.columns([1.6, 1])
                with col_i1:
                    st.markdown("**Likely Root Cause**")
                    st.markdown(f"> {inc['likely_root_cause']}")
                    st.caption(inc["explanation"])
                with col_i2:
                    st.markdown(f"**Severity**: <span style='color:{sev_color}; font-weight:700;'>{esc(inc['severity'])}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Confidence**: `{inc['confidence_label']}`")
                    st.markdown(f"**Category**: `{inc['category']}`")

                evidence_rows = [
                    {
                        "Line": ev.get("line_no", "-"),
                        "Timestamp": ev.get("timestamp", "-"),
                        "Service": ev.get("service", "-"),
                        "Level": ev.get("level", "-"),
                        "Message": ev.get("message", "-"),
                    }
                    for ev in inc["detected_evidence"]
                ]
                st.dataframe(pd.DataFrame(evidence_rows), use_container_width=True, hide_index=True)

                st.markdown("**Recommended Next Steps**")
                for step in inc["recommended_next_steps"]:
                    st.markdown(f"- {step}")

    st.markdown("---")
    st.markdown("#### 🛠️ Recovery Playbooks (Advisory)")
    st.caption(f"🛡️ {SAFETY_POLICY_DISCLAIMER}")
    recommendations = SelfHealingEngine.generate_recommendations(incidents)
    if not recommendations:
        st.info("No active incidents requiring remediation.")
    else:
        for r in recommendations:
            st.markdown(
                f"""
                <div class="metric-card" style="margin-bottom:0.75rem; border-left:4px solid #22d3ee;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem;">
                        <strong style="color:#f1f5f9;">🔧 [{esc(r['action_id'])}] {esc(r['title'])}</strong>
                        <span style="font-size:0.75rem; color:#22d3ee; font-weight:700;">Target: {esc(r['target_service'])}</span>
                    </div>
                    <div style="font-size:0.84rem; color:#cbd5e1; margin-bottom:0.3rem;"><strong>Reason:</strong> {esc(r['reason'])}</div>
                    <div style="font-size:0.78rem; color:#94a3b8;"><strong>Prerequisites:</strong> {esc(r['prerequisites'])}</div>
                    <div style="font-size:0.78rem; color:#94a3b8;"><strong>Verification:</strong> {esc(r['verification_steps'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"🧪 Simulate Dry-Run ({r['action_id']})", key=f"sim_btn_{r['action_id']}"):
                sim_result = SelfHealingEngine.simulate_action(r["action_id"])
                st.success(f"**{sim_result['message']}** (`{sim_result['simulation_mode']}`)")


def render_semantic_search_tab(vector_store, df: pd.DataFrame):
    """Renders clean Semantic Vector Search with automatic lightweight fallback."""
    from src.embedding_engine import LogEmbeddingEngine
    from src.vector_store import SIMILARITY_DISCLAIMER

    stats = vector_store.get_stats()
    total_indexed = stats.get("total_vectors", 0)

    col_idx1, col_idx2 = st.columns([2.3, 1])
    with col_idx1:
        if total_indexed > 0:
            st.success(f"🟢 Vector Index Active: `{total_indexed}` log events indexed.")
        else:
            st.info("⚪ Vector Index Empty — index active logs to run semantic search.")

    with col_idx2:
        btn_label = "⚡ Index Active Logs" if total_indexed == 0 else "🔄 Re-Index Logs"
        if st.button(btn_label, use_container_width=True, type="primary" if total_indexed == 0 else "secondary"):
            if df.empty:
                st.error("Load or upload a log dataset first.")
            else:
                with st.spinner("Generating 384-dim log vectors..."):
                    try:
                        embeddings, records, mode_used = LogEmbeddingEngine.embed_logs_with_fallback(df)
                        vector_store.build_index(embeddings, records)
                        st.session_state["vector_store_indexed_file"] = st.session_state.get("active_file_name", "unknown")
                        st.session_state["vector_store_mode"] = mode_used
                        st.rerun()
                    except Exception as e:
                        st.error(f"Vector indexing failed: {e}")

    st.markdown("---")
    col_q1, col_q2, col_q3, col_q4, col_q5 = st.columns(5)
    preset_query = None
    if col_q1.button("💥 DB Pool", use_container_width=True):
        preset_query = "database connection failure and slots"
    if col_q2.button("🧠 Out of Memory", use_container_width=True):
        preset_query = "out of memory container crash OOM"
    if col_q3.button("🌐 Gateway Timeout", use_container_width=True):
        preset_query = "upstream gateway timeout and latency"
    if col_q4.button("⚡ CPU Saturation", use_container_width=True):
        preset_query = "high CPU utilization compute load"
    if col_q5.button("🔒 Auth Failure", use_container_width=True):
        preset_query = "token verification timeout unauthorized"

    col_s1, col_s2 = st.columns([3, 1])
    default_query_text = preset_query or st.session_state.get("last_semantic_query", "database connection pool exhausted")
    user_query = col_s1.text_input(
        "Semantic Query",
        value=default_query_text,
        placeholder="e.g. database pool exhausted, high memory pressure...",
    )
    top_k = col_s2.slider("Top-K", min_value=1, max_value=20, value=5, key="semantic_top_k_slider")

    if total_indexed > 0 and user_query:
        st.session_state["last_semantic_query"] = user_query
        search_res = vector_store.search(user_query, top_k=top_k)
        st.caption(f"Matched **{search_res['total_matches']}** log events for `'{user_query}'`.")
        if search_res["results"]:
            render_3d_vector_constellation(user_query, search_res["results"])
        for item in search_res["results"]:
            sev = item.get("level", "INFO")
            sev_color = SEVERITY_COLORS.get(sev, "#94a3b8")
            score_pct = item["similarity_pct"]
            score_color = "#10b981" if score_pct >= 70 else ("#22d3ee" if score_pct >= 50 else "#94a3b8")
            st.markdown(
                f"""
                <div class="metric-card" style="margin-bottom:0.7rem; border-left:4px solid {score_color};">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.3rem;">
                        <span>
                            <strong>#{esc(item['rank'])}</strong> &bull;
                            <span style="font-size:0.75rem; color:#94a3b8;">Line {esc(item['line_no'])}</span> &bull;
                            <code style="color:#22d3ee;">[{esc(item['service'])}]</code> &bull;
                            <strong style="color:{sev_color};">[{esc(sev)}]</strong>
                        </span>
                        <span style="font-size:0.8rem; font-weight:700; color:{score_color};">{esc(score_pct)}% Match</span>
                    </div>
                    <div style="font-family:'JetBrains Mono', monospace; font-size:0.84rem; color:#f1f5f9;">{esc(item['message'])}</div>
                    <div style="font-size:0.72rem; color:#64748b; margin-top:0.2rem;">{esc(item['timestamp'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.caption(f"ℹ️ {SIMILARITY_DISCLAIMER}")


def render_upload_tab(parser_cls):
    """Renders log upload and built-in sample log loader."""
    with st.expander("⚡ Load Sample Infrastructure Trace", expanded=True):
        col_s1, col_s2 = st.columns(2)
        if col_s1.button("🔥 Production Incident Trace", use_container_width=True):
            sample_text = load_sample_log("production_incident.log")
            if sample_text:
                st.session_state["raw_log_content"] = sample_text
                st.session_state["active_file_name"] = "production_incident.log"
                st.rerun()
        if col_s2.button("🟢 Healthy Operations Trace", use_container_width=True):
            sample_text = load_sample_log("normal_operations.log")
            if sample_text:
                st.session_state["raw_log_content"] = sample_text
                st.session_state["active_file_name"] = "normal_operations.log"
                st.rerun()

    uploaded_file = st.file_uploader("Upload Log File (.log, .txt, .csv, .json)", type=["log", "txt", "csv", "json"])
    if uploaded_file is not None:
        upload_sig = f"{uploaded_file.name}:{uploaded_file.size}"
        if st.session_state.get("last_uploaded_sig") != upload_sig:
            try:
                content = uploaded_file.read().decode("utf-8", errors="replace")
                st.session_state["last_uploaded_sig"] = upload_sig
                st.session_state["raw_log_content"] = content
                st.session_state["active_file_name"] = uploaded_file.name
                st.rerun()
            except Exception as e:
                st.error(f"Error reading file: {e}")

    active_content = st.session_state.get("raw_log_content", "")
    active_filename = st.session_state.get("active_file_name", "None")
    if active_content:
        st.markdown("---")
        st.markdown(f"#### 📄 Active Dataset: `{active_filename}`")
        df = parser_cls.parse_text(active_content)
        st.session_state["parsed_df"] = df

        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        search_query = col_f1.text_input("Search logs", placeholder="e.g. timeout, memory, postgres...")
        all_levels = sorted(df["level"].unique().tolist())
        selected_levels = col_f2.multiselect("Level", options=all_levels, default=all_levels)
        all_services = sorted(df["service"].unique().tolist())
        selected_services = col_f3.multiselect("Service", options=all_services, default=all_services)

        filtered_df = df.copy()
        if selected_levels:
            filtered_df = filtered_df[filtered_df["level"].isin(selected_levels)]
        if selected_services:
            filtered_df = filtered_df[filtered_df["service"].isin(selected_services)]
        if search_query:
            q = search_query.lower()
            filtered_df = filtered_df[
                filtered_df["message"].str.lower().str.contains(q, na=False)
                | filtered_df["service"].str.lower().str.contains(q, na=False)
            ]

        st.caption(f"Showing {len(filtered_df)} of {len(df)} log lines.")
        st.dataframe(filtered_df[["line_no", "timestamp", "level", "service", "message"]], use_container_width=True, height=340, hide_index=True)
        st.download_button(
            "💾 Export Filtered CSV",
            data=filtered_df.to_csv(index=False).encode("utf-8"),
            file_name=f"parsed_{active_filename}.csv",
            mime="text/csv",
        )


def render_assistant_tab(
    assistant,
    df: pd.DataFrame,
    rca_results: Dict[str, Any],
    health_data: Dict[str, Any],
    risk_data: Dict[str, Any],
    vector_store,
    active_filename: str,
):
    """Renders clean grounded AI Assistant tab."""
    col_p1, col_p2 = st.columns([4, 1])
    col_p1.caption(f"Context: `{active_filename}` ({len(df)} logs) • Engine: `{assistant.provider.provider_name}` • Advisory only")
    if col_p2.button("🗑️ Clear Chat", use_container_width=True):
        assistant.reset_session(active_filename)
        st.session_state["assistant_chat_history"] = []
        st.rerun()

    if "assistant_chat_history" not in st.session_state:
        st.session_state["assistant_chat_history"] = []

    last_ai_msg = next(
        (m for m in reversed(st.session_state["assistant_chat_history"]) if m.get("role") == "assistant"),
        None,
    )
    render_3d_ai_neural_core(
        context_label=f"{active_filename} ({len(df)} logs)",
        intent_label=(last_ai_msg or {}).get("intent", "READY"),
        confidence_label=(last_ai_msg or {}).get("confidence", "GROUNDED"),
        evidence_items=(last_ai_msg or {}).get("evidence", []),
        height=310,
    )

    col_q1, col_q2, col_q3 = st.columns(3)
    submitted_prompt = None
    if col_q1.button("🚨 Critical incidents?", use_container_width=True):
        submitted_prompt = "What are the most critical incidents?"
    if col_q2.button("💥 Why is DB failing?", use_container_width=True):
        submitted_prompt = "Why is the database failing?"
    if col_q3.button("🛠️ Recovery steps?", use_container_width=True):
        submitted_prompt = "What recovery steps are recommended?"

    st.markdown("---")
    for msg in st.session_state["assistant_chat_history"]:
        role = msg.get("role", "user")
        with st.chat_message(role):
            st.markdown(msg.get("content", ""))
            evidence = msg.get("evidence", [])
            if role == "assistant" and evidence:
                with st.expander(f"📑 Evidence ({len(evidence)} log lines)", expanded=False):
                    for ev in evidence:
                        st.code(f"[Line {ev.get('line_no', 0)}] [{ev.get('timestamp', 'N/A')}] [{ev.get('service', 'unknown')}] [{ev.get('level', 'INFO')}] {ev.get('message', '')}")

    chat_prompt = st.chat_input("Ask about incidents, root causes, health score, or recovery...")
    active_prompt = submitted_prompt or chat_prompt
    if active_prompt:
        st.session_state["assistant_chat_history"].append({"role": "user", "content": active_prompt})
        with st.spinner("Analyzing logs..."):
            res = assistant.ask(
                query=active_prompt,
                df=df,
                rca_results=rca_results,
                health_data=health_data,
                risk_data=risk_data,
                vector_store=vector_store,
                dataset_id=active_filename,
            )
        st.session_state["assistant_chat_history"].append({
            "role": "assistant",
            "content": res["answer"],
            "provider": res["provider"],
            "confidence": res["confidence"],
            "evidence": res["evidence"],
            "intent": res["intent"],
        })
        st.rerun()
