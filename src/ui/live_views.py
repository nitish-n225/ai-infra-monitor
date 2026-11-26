"""
Real-Time Multi-Device Windows Fleet Views for Enterprise AI Infrastructure Monitor.
"""
import json
import pandas as pd
import streamlit as st

from src.realtime_client import BackendAPIClient, get_realtime_bridge
from src.ui.components import (
    esc,
    render_3d_gauge_pair,
    render_3d_topology_scene,
    render_metric_card,
    resource_bar_html,
)


def _status_badge(status: str) -> str:
    colors = {
        "ONLINE": ("#10b981", "rgba(16, 185, 129, 0.14)"),
        "OFFLINE": ("#f59e0b", "rgba(245, 158, 11, 0.14)"),
        "REVOKED": ("#ef4444", "rgba(239, 68, 68, 0.14)"),
    }
    fg, bg = colors.get(status, ("#94a3b8", "rgba(148, 163, 184, 0.14)"))
    return (
        f"<span class='status-pill' style='color:{fg}; background:{bg}; border:1px solid {fg}66;'>"
        f"{esc(status)}</span>"
    )


@st.fragment(run_every=5)
def render_live_fleet_fragment(api_client: BackendAPIClient):
    """Auto-refreshing real-time fleet overview, host telemetry, trend forecast, and log stream."""
    bridge = get_realtime_bridge(
        token=api_client.bearer_token or api_client.admin_key,
        backend_url=api_client.base_url,
    )
    bridge_status = bridge.get_status()
    health_info = api_client.health(timeout=10.0)

    if health_info is None:
        st.warning(
            f"Backend at `{api_client.base_url}` did not respond in time. "
            "If hosted on Render free tier, it may be waking from sleep."
        )
        if st.button("🔄 Retry Connection", key="retry_live_frag"):
            st.rerun()
        return

    transport = bridge_status["transport"]
    stream_color = "#10b981" if bridge_status["connected"] else "#f59e0b"
    col_strip, col_btn = st.columns([6, 1])
    with col_strip:
        st.markdown(
            f"""
            <div class="stream-strip">
                <span>
                    <strong style="color:{stream_color};">● {esc(transport)}</strong>
                    &nbsp;&bull;&nbsp;
                    <span style="color:#94a3b8;">Vectors: <code>{esc(health_info.get('faiss_vectors', 0))}</code></span>
                    &nbsp;&bull;&nbsp;
                    <span style="color:#94a3b8;">Timeout: <code>{esc(health_info.get('offline_timeout_seconds', 30))}s</code></span>
                </span>
                <span style="color:#64748b;">
                    Seq <code>#{esc(bridge_status['last_seq'])}</code> &bull; Auto-refresh 5s
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("🔄 Refresh", use_container_width=True, key="manual_refresh_fleet"):
            st.rerun()

    try:
        all_summary = api_client.get_summary()
        orgs = ["ALL"] + [o for o in all_summary.get("client_orgs", []) if o]
        selected_org = st.selectbox("Organization Scope", orgs, key="live_org_scope")
        summary = api_client.get_summary(client_org=selected_org)
        devices = api_client.get_devices(client_org=selected_org)
    except Exception as e:
        st.error(f"Error querying central backend: {e}")
        return

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        render_metric_card("Devices", summary["total_devices"], "Enrolled hosts", "#22d3ee", accent="#22d3ee")
    with c2:
        render_metric_card("Online", summary["online_devices"], "Active heartbeats", "#10b981", accent="#10b981")
    with c3:
        render_metric_card(
            "Offline",
            summary["offline_devices"],
            f"Revoked: {summary['revoked_devices']}",
            "#f59e0b" if summary["offline_devices"] > 0 else "#94a3b8",
            accent="#f59e0b" if summary["offline_devices"] > 0 else "#334155",
        )
    with c4:
        render_metric_card(
            "Open Incidents",
            summary["open_incidents"],
            f"{summary['critical_events']} critical events",
            "#ef4444" if summary["open_incidents"] > 0 else "#10b981",
            accent="#ef4444" if summary["open_incidents"] > 0 else "#10b981",
        )
    with c5:
        h_score = summary["fleet_health_score"]
        h_color = "#10b981" if h_score >= 80 else ("#f59e0b" if h_score >= 50 else "#ef4444")
        render_metric_card("Fleet Health", f"{h_score}%", "Avg host score", h_color, accent=h_color)
    with c6:
        r_score = summary["fleet_risk_score"]
        r_color = "#ef4444" if r_score >= 55 else ("#f59e0b" if r_score >= 30 else "#10b981")
        render_metric_card("Peak Risk", f"{r_score}/100", "Failure risk index", r_color, accent=r_color)

    st.markdown("---")

    if not devices:
        st.info(
            "No Windows agents enrolled yet. Open **⚙️ Fleet Admin → 🔑 Enroll Device** to generate a setup command."
        )
        return

    render_3d_gauge_pair(
        summary["fleet_health_score"],
        "Healthy" if summary["fleet_health_score"] >= 80 else ("Degraded" if summary["fleet_health_score"] >= 50 else "Critical"),
        summary["fleet_risk_score"],
        "High Risk" if summary["fleet_risk_score"] >= 55 else ("Moderate" if summary["fleet_risk_score"] >= 30 else "Low Risk"),
    )

    fleet_3d_nodes = []
    for d in devices:
        tel = d.get("latest_telemetry") or {}
        st_name = d.get("status", "OFFLINE")
        h_val = float(d.get("health_score", 100))
        node_state = "critical" if (st_name == "REVOKED" or h_val < 50) else ("warning" if (st_name == "OFFLINE" or h_val < 80) else "healthy")
        cpu_str = f"{tel['cpu_percent']:.1f}%" if "cpu_percent" in tel else "N/A"
        ram_str = f"{tel['ram_percent']:.1f}%" if "ram_percent" in tel else "N/A"
        disk_str = f"{tel['disk_percent']:.1f}%" if "disk_percent" in tel else "N/A"
        fleet_3d_nodes.append({
            "label": d.get("hostname", "host"),
            "state": node_state,
            "size": 16 if st_name == "ONLINE" else 13,
            "detail": (
                f"Status: {esc(st_name)} &bull; Org: {esc(d.get('client_org', 'Default'))}<br>"
                f"CPU: {esc(cpu_str)} | RAM: {esc(ram_str)} | Disk: {esc(disk_str)}<br>"
                f"Health: {esc(h_val)}% | IP: {esc(d.get('ip_address') or 'N/A')}"
            ),
        })
    render_3d_topology_scene(
        nodes=fleet_3d_nodes,
        center_label="AI Control Plane",
        center_sub="Live Fleet Hub",
        title="Live 3D Fleet Topology & Telemetry Streams",
        height=340,
    )

    st.markdown("#### 💻 Monitored Endpoints")
    device_cols = st.columns(min(len(devices), 3))
    for idx, dev in enumerate(devices):
        tel = dev.get("latest_telemetry") or {}
        cpu_val = tel.get("cpu_percent")
        ram_val = tel.get("ram_percent")
        disk_val = tel.get("disk_percent")
        net_rx = f"{tel.get('net_recv_kbps', 0):.1f}" if tel else "0.0"
        net_tx = f"{tel.get('net_sent_kbps', 0):.1f}" if tel else "0.0"
        badge = _status_badge(dev["status"])
        health_v = dev.get("health_score", 100)
        risk_v = dev.get("risk_score", 0)
        h_col = "#10b981" if health_v >= 80 else ("#f59e0b" if health_v >= 50 else "#ef4444")

        with device_cols[idx % len(device_cols)]:
            st.markdown(
                f"""
                <div class="metric-card" style="margin-bottom:0.85rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                        <strong style="color:#f1f5f9; font-size:0.98rem;">🖥️ {esc(dev['hostname'])}</strong>
                        {badge}
                    </div>
                    <div style="font-size:0.74rem; color:#94a3b8; margin-bottom:0.55rem;">
                        Org <code>{esc(dev.get('client_org', 'Default'))}</code> &bull;
                        IP <code>{esc(dev.get('ip_address') or 'N/A')}</code> &bull;
                        v{esc(dev.get('agent_version', '2.0.0'))}<br>
                        Last seen <code>{esc(dev.get('last_seen', 'N/A'))}</code>
                    </div>
                    {resource_bar_html("CPU", cpu_val)}
                    {resource_bar_html("RAM", ram_val)}
                    {resource_bar_html("Disk", disk_val)}
                    <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#94a3b8; margin-top:0.6rem; border-top:1px solid rgba(148,163,184,0.12); padding-top:0.45rem;">
                        <span>Net ↓{net_rx} / ↑{net_tx} KB/s</span>
                        <span>Health <strong style="color:{h_col};">{esc(health_v)}%</strong> &bull; Risk <strong>{esc(risk_v)}</strong></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    device_options = {"ALL": "All Registered Devices"}
    for d in devices:
        device_options[d["device_id"]] = f"{d['hostname']} [{d.get('client_org', 'Default')}] ({d['status']})"

    col_sel1, col_sel2, col_sel3 = st.columns([2, 1, 1])
    with col_sel1:
        selected_key = st.selectbox(
            "Host Scope",
            options=list(device_options.keys()),
            format_func=lambda k: device_options[k],
            key="live_device_filter",
        )
    with col_sel2:
        level_filter = st.selectbox("Severity", ["ALL", "CRITICAL", "FATAL", "ERROR", "WARN", "INFO"], key="live_level_filter")
    with col_sel3:
        channel_filter = st.selectbox("Channel", ["ALL", "System", "Application", "Security"], key="live_channel_filter")

    target_device_id = None if selected_key == "ALL" else selected_key
    telemetry_device_id = target_device_id or devices[0]["device_id"]
    target_device = next((d for d in devices if d["device_id"] == telemetry_device_id), devices[0])

    st.markdown(f"#### 📈 Live Telemetry — `{target_device['hostname']}`")
    tel_history = api_client.get_telemetry_history(telemetry_device_id, limit=60)
    if tel_history:
        tel_df = pd.DataFrame(tel_history)
        tel_df["time_label"] = pd.to_datetime(tel_df["timestamp"], errors="coerce").dt.strftime("%H:%M:%S").fillna(tel_df["timestamp"])
        chart_df = tel_df.set_index("time_label")

        ch1, ch2 = st.columns(2)
        with ch1:
            st.caption("CPU, RAM & Disk Utilization (%)")
            st.line_chart(chart_df[["cpu_percent", "ram_percent", "disk_percent"]], use_container_width=True)
        with ch2:
            st.caption("Network Throughput (KB/s)")
            st.line_chart(chart_df[["net_recv_kbps", "net_sent_kbps"]], use_container_width=True)

        try:
            forecast = api_client.get_device_forecast(telemetry_device_id)
            if forecast.get("warnings"):
                for w in forecast["warnings"]:
                    st.warning(f"📉 **Trend Forecast**: {w}")
            elif forecast.get("status") == "ANALYZED":
                st.caption(
                    f"Trend ({forecast['samples']} samples): "
                    f"CPU `{forecast['cpu_slope_per_sample']:+.2f}%` • "
                    f"RAM `{forecast['ram_slope_per_sample']:+.2f}%` • "
                    f"Disk `{forecast['disk_slope_per_sample']:+.2f}%`"
                )
        except Exception:
            pass

        latest_t = tel_history[-1]
        v_col, p_col, s_col = st.columns(3)
        with v_col:
            with st.expander("💾 Disk Volumes", expanded=False):
                vols = latest_t.get("disk_volumes", [])
                if vols:
                    st.dataframe(pd.DataFrame(vols), use_container_width=True, hide_index=True)
                else:
                    st.caption(
                        f"System Drive: {latest_t.get('disk_used_gb', 0)}/{latest_t.get('disk_total_gb', 0)} GB "
                        f"({latest_t.get('disk_percent', 0)}%)"
                    )
        with p_col:
            with st.expander(f"⚙️ Top Processes ({latest_t.get('process_count', 0)} total)", expanded=False):
                procs = latest_t.get("top_processes", [])
                if procs:
                    st.dataframe(pd.DataFrame(procs), use_container_width=True, hide_index=True)
                else:
                    st.caption("No process snapshot recorded yet.")
        with s_col:
            with st.expander("🧩 Windows Services", expanded=False):
                svcs = latest_t.get("services", [])
                if svcs:
                    st.dataframe(pd.DataFrame(svcs), use_container_width=True, hide_index=True)
                else:
                    st.caption("No service snapshot recorded yet.")
    else:
        st.info(f"Awaiting first telemetry snapshot from `{target_device['hostname']}`.")

    st.markdown("---")
    st.markdown("#### 📜 Live Event Stream")
    search_txt = st.text_input("Filter live logs", placeholder="Search message, service, EventID, or hostname...", key="live_log_search")
    events = api_client.get_events(
        device_id=target_device_id,
        client_org=selected_org,
        level=level_filter,
        channel=channel_filter,
        search=search_txt or None,
        limit=100,
    )
    if events:
        ev_df = pd.DataFrame([
            {
                "Timestamp": e.get("timestamp"),
                "Host": e.get("hostname"),
                "Channel": e.get("channel"),
                "Level": e.get("level"),
                "Service": e.get("service"),
                "EventID": e.get("event_id") if e.get("event_id") is not None else "-",
                "RCA": e.get("rca_category") or "-",
                "Message": e.get("message"),
            }
            for e in events
        ])
        st.dataframe(ev_df, use_container_width=True, hide_index=True, height=340)
        st.download_button(
            "💾 Export Filtered Logs (CSV)",
            data=ev_df.to_csv(index=False).encode("utf-8"),
            file_name="live_infrastructure_logs.csv",
            mime="text/csv",
            key="dl_live_logs_csv",
        )
    else:
        st.info("No log events match the selected filters.")


@st.fragment(run_every=6)
def render_live_incidents_fragment(api_client: BackendAPIClient):
    """Auto-refreshing AI Incident, RCA, Predictive Risk, Historical Matches, and Recovery view."""
    if api_client.health(timeout=10.0) is None:
        st.warning(f"Central Backend unreachable (`{api_client.base_url}`).")
        return

    devices = api_client.get_devices()
    if not devices:
        st.info("No devices connected yet.")
        return

    dev_map = {"ALL": "All Devices"} | {d["device_id"]: f"{d['hostname']} ({d['status']})" for d in devices}
    c1, c2 = st.columns([2, 1])
    with c1:
        sel_dev = st.selectbox("Device Scope", list(dev_map.keys()), format_func=lambda k: dev_map[k], key="inc_dev_filter")
    with c2:
        sel_status = st.selectbox("Status", ["ALL", "OPEN", "ACKNOWLEDGED", "RESOLVED"], key="inc_status_filter")

    incidents = api_client.get_incidents(
        device_id=None if sel_dev == "ALL" else sel_dev,
        status=None if sel_status == "ALL" else sel_status,
    )

    if not incidents:
        st.success("🟢 All monitored endpoints healthy — no matching incidents.")
        return

    col_hdr, col_exp = st.columns([3, 1])
    col_hdr.markdown(f"**{len(incidents)}** incident(s) detected:")
    col_exp.download_button(
        "📥 Export Incidents (JSON)",
        data=json.dumps(incidents, indent=2, default=str).encode("utf-8"),
        file_name="incidents_report.json",
        mime="application/json",
        key="dl_incidents_json",
    )

    for inc in incidents:
        sev = inc.get("severity", "HIGH")
        with st.expander(
            f"[{inc['status']}] [{sev}] {inc['hostname']} — {inc['title']} ({inc['confidence_pct']}% confidence)",
            expanded=(inc["status"] == "OPEN"),
        ):
            st.markdown("**Confirmed Evidence**")
            st.code(inc.get("confirmed_evidence") or "No evidence captured.", language="text")

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Likely Root Cause**")
                st.info(inc.get("possible_root_cause") or "Under investigation.")
            with col_b:
                st.markdown("**Predicted Risk Trajectory**")
                st.warning(inc.get("predicted_risk_note") or "No risk trajectory note.")

            sim_hist = inc.get("similar_history") or []
            if sim_hist:
                st.markdown("**Similar Historical Events**")
                for h in sim_hist:
                    st.caption(
                        f"• `{h.get('similarity_pct', 0)}% Match` [{h.get('hostname', 'host')}] "
                        f"[{h.get('level', 'INFO')}] `{h.get('service', '')}`: {h.get('message', '')}"
                    )

            recs = inc.get("recommendations") or []
            if recs:
                st.markdown("**Recommended Recovery Actions (Advisory)**")
                for r in recs:
                    st.markdown(f"- **[{r.get('action_id')}] {r.get('title')}** — {r.get('reason')} *(Verify: {r.get('verification_steps')})*")

            b1, b2, _ = st.columns([1, 1, 4])
            with b1:
                if inc["status"] == "OPEN" and st.button("Acknowledge", key=f"ack_{inc['id']}"):
                    try:
                        api_client.update_incident_status(inc["id"], "ACKNOWLEDGED")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")
            with b2:
                if inc["status"] != "RESOLVED" and st.button("Mark Resolved", key=f"res_{inc['id']}"):
                    try:
                        api_client.update_incident_status(inc["id"], "RESOLVED")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")


def render_fleet_admin_tab(api_client: BackendAPIClient):
    """Streamlined Fleet Admin organized into focused sub-tabs."""
    if api_client.health(timeout=10.0) is None:
        st.error(f"Central Backend is unreachable at `{api_client.base_url}`.")
        return

    sub_enroll, sub_devices, sub_alerts, sub_audit = st.tabs([
        "🔑 Enroll Device",
        "🖥️ Devices & Config",
        "🔔 Alert Webhooks",
        "🛡️ Audit Log",
    ])

    with sub_enroll:
        st.markdown("#### Onboard a Windows 10/11 Endpoint")
        st.caption("Each agent requires a valid enrollment token, reachable backend HTTPS/LAN URL, and explicit endpoint consent.")
        with st.form("create_token_form"):
            c1, c2, c3, c4 = st.columns([2, 1.5, 1, 1])
            tok_label = c1.text_input("Token Label", value="Workstations")
            client_org = c2.text_input("Organization", value="Default")
            max_uses = c3.number_input("Max Devices", min_value=1, max_value=500, value=10)
            exp_hrs = c4.number_input("Expires (hrs)", min_value=1, max_value=8760, value=168)
            default_public_url = api_client.base_url if api_client.base_url.startswith("https://") else "https://your-service.onrender.com"
            public_url = st.text_input("Reachable Backend URL", value=default_public_url)
            submitted = st.form_submit_button("🔑 Generate Enrollment Token")

        if submitted:
            try:
                res = api_client.create_enrollment_token(tok_label, client_org, int(max_uses), int(exp_hrs))
                raw_tok = res["token"]
                st.success("Token created (copy now — shown once):")
                st.code(raw_tok, language="text")
                st.markdown("**PowerShell Setup Command**")
                st.code(
                    f'.\\installer\\install_agent.ps1 -BackendUrl "{public_url}" -EnrollmentToken "{raw_tok}" -ClientOrg "{client_org}"',
                    language="powershell",
                )
            except Exception as e:
                st.error(f"Failed to generate token: {e}")

        try:
            tokens = api_client.list_enrollment_tokens()
            if tokens:
                with st.expander("📋 Issued Enrollment Tokens", expanded=False):
                    st.dataframe(pd.DataFrame(tokens), use_container_width=True, hide_index=True)
        except Exception:
            pass

    with sub_devices:
        st.markdown("#### Endpoint Configuration & Access Control")
        devices = api_client.get_devices()
        if not devices:
            st.info("No devices enrolled yet.")
        else:
            dev_map = {d["device_id"]: f"{d['hostname']} [{d.get('client_org', 'Default')}] [{d['status']}]" for d in devices}
            chosen_id = st.selectbox("Select Endpoint", list(dev_map.keys()), format_func=lambda k: dev_map[k], key="admin_dev_sel")
            chosen_dev = next(d for d in devices if d["device_id"] == chosen_id)
            cfg = chosen_dev.get("config", {})

            col_cfg, col_rev = st.columns([2, 1])
            with col_cfg:
                with st.form(f"cfg_form_{chosen_id}"):
                    s1, s2, s3 = st.columns(3)
                    hb_sec = s1.number_input("Heartbeat (s)", 3, 300, int(cfg.get("heartbeat_interval_sec", 10)))
                    tel_sec = s2.number_input("Telemetry (s)", 3, 300, int(cfg.get("telemetry_interval_sec", 10)))
                    log_sec = s3.number_input("Log Poll (s)", 2, 300, int(cfg.get("log_poll_interval_sec", 5)))

                    t1, t2, t3 = st.columns(3)
                    cpu_th = t1.number_input("CPU Alert %", 10.0, 100.0, float(cfg.get("cpu_alert_threshold", 90.0)))
                    ram_th = t2.number_input("RAM Alert %", 10.0, 100.0, float(cfg.get("ram_alert_threshold", 90.0)))
                    disk_th = t3.number_input("Disk Alert %", 10.0, 100.0, float(cfg.get("disk_alert_threshold", 90.0)))

                    inc_sec = st.checkbox("Collect Security Event Log IDs (requires Admin/Service)", value=bool(cfg.get("include_security_events", False)))
                    watched_txt = st.text_area(
                        "Watched Application Log Paths (one per line)",
                        value="\n".join(cfg.get("watched_log_paths", [])),
                        height=85,
                    )
                    save_cfg = st.form_submit_button("💾 Save & Push Config")

                if save_cfg:
                    new_cfg = {
                        "heartbeat_interval_sec": int(hb_sec),
                        "telemetry_interval_sec": int(tel_sec),
                        "log_poll_interval_sec": int(log_sec),
                        "event_channels": ["System", "Application"] + (["Security"] if inc_sec else []),
                        "include_security_events": bool(inc_sec),
                        "watched_log_paths": [p.strip() for p in watched_txt.splitlines() if p.strip()],
                        "cpu_alert_threshold": float(cpu_th),
                        "ram_alert_threshold": float(ram_th),
                        "disk_alert_threshold": float(disk_th),
                    }
                    try:
                        api_client.update_device_config(chosen_id, new_cfg)
                        st.success("Configuration saved and queued for next agent heartbeat.")
                    except Exception as e:
                        st.error(f"Failed updating config: {e}")

            with col_rev:
                st.markdown("**Access Control**")
                st.write(f"Status: `{chosen_dev['status']}`")
                revoke_reason = st.text_input("Revocation Reason", value="Decommissioned / Unauthorized", key=f"rev_reason_{chosen_id}")
                if chosen_dev["status"] != "REVOKED":
                    if st.button("🚫 Revoke Device", type="primary", key=f"rev_btn_{chosen_id}"):
                        try:
                            api_client.revoke_device(chosen_id, revoke_reason)
                            st.warning(f"Device `{chosen_dev['hostname']}` revoked.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to revoke device: {e}")
                else:
                    st.error(f"Revoked at {chosen_dev.get('revoked_at')}: {chosen_dev.get('revocation_reason')}")

    with sub_alerts:
        st.markdown("#### Webhook Alert Notifications")
        try:
            alert_cfg = api_client.get_alert_settings()
        except Exception:
            alert_cfg = {"webhook_url": "", "notify_on_critical_incident": True, "notify_on_device_offline": True, "cooldown_seconds": 300}

        with st.form("alert_settings_form"):
            wh_url = st.text_input("Webhook URL (Slack / Teams / JSON)", value=alert_cfg.get("webhook_url", ""), placeholder="https://hooks.slack.com/services/...")
            a1, a2, a3 = st.columns(3)
            on_crit = a1.checkbox("Critical/High Incidents", value=bool(alert_cfg.get("notify_on_critical_incident", True)))
            on_off = a2.checkbox("Device Offline", value=bool(alert_cfg.get("notify_on_device_offline", True)))
            cooldown = a3.number_input("Cooldown (sec)", 30, 86400, int(alert_cfg.get("cooldown_seconds", 300)))
            col_btn1, col_btn2 = st.columns(2)
            save_alerts = col_btn1.form_submit_button("💾 Save Settings")
            test_alerts = col_btn2.form_submit_button("📣 Send Test Alert")

        if save_alerts:
            try:
                api_client.update_alert_settings({
                    "webhook_url": wh_url.strip(),
                    "notify_on_critical_incident": on_crit,
                    "notify_on_device_offline": on_off,
                    "cooldown_seconds": int(cooldown),
                })
                st.success("Alert webhook settings saved.")
            except Exception as e:
                st.error(f"Failed saving alert settings: {e}")
        if test_alerts:
            try:
                res = api_client.test_alert_webhook()
                if res.get("sent"):
                    st.success(f"Test webhook delivered (HTTP {res.get('status_code')}).")
                else:
                    st.warning(f"Webhook not delivered: {res}")
            except Exception as e:
                st.error(f"Webhook test error: {e}")

    with sub_audit:
        st.markdown("#### Security & Operations Audit Log")
        try:
            audit_rows = api_client.get_audit_logs(limit=50)
            if audit_rows:
                st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True, height=320)
            else:
                st.caption("No audit events recorded yet.")
        except Exception as e:
            st.error(f"Could not fetch audit log: {e}")
