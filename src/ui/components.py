"""
3D Glassmorphic UI Design System & Interactive 3D Canvas Components for
Enterprise Autonomous AI Infrastructure Monitoring System.
"""
import html
import json
from typing import Any, Dict, List, Optional
import streamlit as st
import streamlit.components.v1 as components


def esc(value: Any) -> str:
    """Escapes untrusted text safely before embedding in HTML fragments."""
    return html.escape("" if value is None else str(value), quote=True)


def apply_custom_styles() -> None:
    """Applies a 3D glassmorphic, depth-layered dark AIOps design system."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {
            --bg-root: #050814;
            --bg-surface: rgba(15, 23, 42, 0.72);
            --bg-surface-strong: rgba(9, 14, 28, 0.92);
            --border-subtle: rgba(148, 163, 184, 0.16);
            --border-accent: rgba(34, 211, 238, 0.48);
            --text-primary: #f8fafc;
            --text-muted: #94a3b8;
            --accent-cyan: #22d3ee;
            --accent-indigo: #818cf8;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #ef4444;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* Clean Streamlit chrome */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        [data-testid="stDecoration"] { display: none; }
        .stDeployButton { display: none; }

        /* 3D Perspective Cyber-Grid Backdrop */
        .stApp {
            background-color: var(--bg-root);
            background-image:
                radial-gradient(ellipse 70% 45% at 15% 0%, rgba(34, 211, 238, 0.14), transparent 60%),
                radial-gradient(ellipse 55% 40% at 88% 5%, rgba(129, 140, 248, 0.13), transparent 58%),
                radial-gradient(ellipse 50% 45% at 50% 100%, rgba(16, 185, 129, 0.08), transparent 65%),
                linear-gradient(rgba(34, 211, 238, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(34, 211, 238, 0.03) 1px, transparent 1px);
            background-size: 100% 100%, 100% 100%, 100% 100%, 44px 44px, 44px 44px;
        }

        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2.5rem;
            max-width: 1440px;
            perspective: 1400px;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(10, 16, 32, 0.96) 0%, rgba(5, 8, 20, 0.98) 100%);
            border-right: 1px solid rgba(34, 211, 238, 0.14);
            box-shadow: 8px 0 32px rgba(0, 0, 0, 0.45);
        }

        /* 3D Glassmorphic Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.8), rgba(9, 14, 28, 0.9));
            padding: 0.42rem;
            border-radius: 14px;
            border: 1px solid var(--border-subtle);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.08),
                0 10px 28px -8px rgba(0, 0, 0, 0.55);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 0.48rem 1rem;
            font-weight: 600;
            font-size: 0.86rem;
            color: var(--text-muted);
            border: 1px solid transparent;
            transition: all 0.2s cubic-bezier(0.22, 1, 0.36, 1);
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: #f1f5f9;
            background: rgba(255, 255, 255, 0.04);
            transform: translateY(-1px);
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(34, 211, 238, 0.22), rgba(129, 140, 248, 0.18)) !important;
            color: #e0f2fe !important;
            border: 1px solid rgba(34, 211, 238, 0.42) !important;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.2),
                0 6px 18px rgba(34, 211, 238, 0.22) !important;
        }
        .stTabs [data-baseweb="tab-highlight"] {
            display: none;
        }

        /* 3D Tactile Buttons */
        .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
            border-radius: 10px;
            font-weight: 600;
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: linear-gradient(180deg, rgba(30, 41, 59, 0.85), rgba(15, 23, 42, 0.95));
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.12),
                0 6px 16px -4px rgba(0, 0, 0, 0.5);
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
            border-color: var(--border-accent);
            transform: translateY(-2px);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.2),
                0 10px 24px -4px rgba(34, 211, 238, 0.28);
        }
        .stButton > button:active {
            transform: translateY(0px);
        }

        /* 3D Hero Command Header */
        .hero-header {
            position: relative;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            background: linear-gradient(135deg, rgba(17, 24, 39, 0.92), rgba(9, 14, 28, 0.96));
            border: 1px solid rgba(34, 211, 238, 0.25);
            border-radius: 16px;
            padding: 1.15rem 1.45rem;
            margin-bottom: 1.15rem;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.14),
                0 20px 44px -14px rgba(0, 0, 0, 0.65),
                0 0 36px -12px rgba(34, 211, 238, 0.22);
            transform-style: preserve-3d;
        }
        .hero-title {
            font-size: 1.38rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(90deg, #f8fafc 0%, #67e8f9 65%, #a5b4fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
        }
        .hero-subtitle {
            font-size: 0.84rem;
            color: var(--text-muted);
            margin-top: 0.22rem;
        }

        /* 3D Glassmorphic Metric & Host Cards */
        .metric-card {
            background: linear-gradient(155deg, rgba(22, 32, 54, 0.82), rgba(8, 13, 26, 0.94));
            border: 1px solid var(--border-subtle);
            border-radius: 14px;
            padding: 1rem 1.15rem;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.12),
                inset 0 -1px 0 rgba(0, 0, 0, 0.35),
                0 16px 34px -12px rgba(0, 0, 0, 0.65);
            transform-style: preserve-3d;
            transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1), border-color 0.22s ease, box-shadow 0.22s ease;
        }
        .metric-card:hover {
            transform: translateY(-5px) rotateX(2.5deg) rotateY(-1deg);
            border-color: var(--border-accent);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.2),
                0 22px 42px -12px rgba(0, 0, 0, 0.78),
                0 0 24px -6px rgba(34, 211, 238, 0.26);
        }
        .metric-label {
            font-size: 0.69rem;
            font-weight: 700;
            color: var(--text-muted);
            letter-spacing: 0.07em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }
        .metric-value {
            font-size: 1.75rem;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-primary);
            line-height: 1.15;
            text-shadow: 0 2px 14px rgba(0, 0, 0, 0.55);
        }
        .metric-desc {
            font-size: 0.74rem;
            color: #64748b;
            margin-top: 0.28rem;
        }

        /* Live Stream Strip */
        .stream-strip {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 0.6rem;
            background: linear-gradient(90deg, rgba(15, 23, 42, 0.88), rgba(17, 24, 39, 0.75));
            border: 1px solid rgba(34, 211, 238, 0.2);
            border-radius: 12px;
            padding: 0.6rem 1rem;
            margin-bottom: 1rem;
            font-size: 0.8rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 8px 20px rgba(0, 0, 0, 0.35);
        }

        /* 3D Beveled Resource Progress Bar */
        .res-row { margin-top: 0.38rem; }
        .res-head {
            display: flex;
            justify-content: space-between;
            font-size: 0.74rem;
            color: #cbd5e1;
            margin-bottom: 0.16rem;
        }
        .res-track {
            width: 100%;
            height: 7px;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid rgba(148, 163, 184, 0.15);
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.65);
            overflow: hidden;
        }
        .res-fill {
            height: 100%;
            border-radius: 999px;
            box-shadow: 0 0 10px currentColor;
            transition: width 0.3s ease;
        }

        /* Status Pills */
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.24rem 0.72rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.15), 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        /* Critical Banner */
        .critical-banner {
            background: linear-gradient(90deg, rgba(239, 68, 68, 0.16), rgba(15, 23, 42, 0.7));
            border: 1px solid rgba(239, 68, 68, 0.28);
            border-left: 4px solid #ef4444;
            border-radius: 12px;
            padding: 0.85rem 1.05rem;
            margin-bottom: 0.75rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 10px 24px -8px rgba(239, 68, 68, 0.25);
        }

        /* Expanders & DataFrames */
        [data-testid="stExpander"] {
            background: rgba(12, 18, 34, 0.75);
            border: 1px solid var(--border-subtle) !important;
            border-radius: 12px !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 10px 24px -10px rgba(0, 0, 0, 0.55);
        }

        /* Stage Badges (compatibility) */
        .stage-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.2rem 0.65rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .stage-active {
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .stage-upcoming {
            background: rgba(148, 163, 184, 0.1);
            color: #94a3b8;
            border: 1px solid rgba(148, 163, 184, 0.2);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero_header(title: str, subtitle: str, status_label: str, status_ok: bool) -> None:
    """Renders the 3D glassmorphic command-center header with a live connection badge."""
    pill_fg = "#10b981" if status_ok else "#f59e0b"
    pill_bg = "rgba(16, 185, 129, 0.15)" if status_ok else "rgba(245, 158, 11, 0.15)"
    st.markdown(
        f"""
        <div class="hero-header">
            <div>
                <div class="hero-title">🛡️ {esc(title)}</div>
                <div class="hero-subtitle">{esc(subtitle)}</div>
            </div>
            <div>
                <span class="status-pill" style="color:{pill_fg}; background:{pill_bg}; border:1px solid {pill_fg}66;">
                    <span>●</span> {esc(status_label)}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(
    label: str,
    value: Any,
    subtext: str = "",
    color: str = "#f8fafc",
    accent: Optional[str] = None,
) -> None:
    """Renders a 3D glassmorphic KPI metric card."""
    border_style = f"border-top: 2px solid {accent};" if accent else ""
    st.markdown(
        f"""
        <div class="metric-card" style="{border_style}">
            <div class="metric-label">{esc(label)}</div>
            <div class="metric-value" style="color: {esc(color)};">{esc(value)}</div>
            <div class="metric-desc">{esc(subtext)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_3d_gauge_pair(
    health_score: float,
    health_label: str,
    risk_score: float,
    risk_label: str,
) -> None:
    """Renders side-by-side 3D luminous SVG radial gauges for Health & Failure Risk."""
    h_clamped = max(0.0, min(100.0, float(health_score)))
    r_clamped = max(0.0, min(100.0, float(risk_score)))
    h_color = "#10b981" if h_clamped >= 80 else ("#f59e0b" if h_clamped >= 50 else "#ef4444")
    r_color = "#ef4444" if r_clamped >= 70 else ("#f59e0b" if r_clamped >= 30 else "#10b981")
    circ = 2 * 3.14159 * 42
    h_off = circ * (1.0 - h_clamped / 100.0)
    r_off = circ * (1.0 - r_clamped / 100.0)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div class="metric-card" style="display:flex; align-items:center; gap:1.15rem; border-top:2px solid {h_color};">
                <svg width="104" height="104" viewBox="0 0 104 104" style="filter: drop-shadow(0 0 10px {h_color}55); flex-shrink:0;">
                    <circle cx="52" cy="52" r="42" fill="rgba(15,23,42,0.75)" stroke="rgba(148,163,184,0.16)" stroke-width="8"/>
                    <circle cx="52" cy="52" r="42" fill="none" stroke="{h_color}" stroke-width="8" stroke-linecap="round"
                            stroke-dasharray="{circ:.2f}" stroke-dashoffset="{h_off:.2f}"
                            transform="rotate(-90 52 52)"/>
                    <text x="52" y="57" text-anchor="middle" fill="#f8fafc" font-family="JetBrains Mono, monospace" font-size="16" font-weight="800">{h_clamped:.0f}%</text>
                </svg>
                <div>
                    <div class="metric-label">3D HEALTH CORE</div>
                    <div class="metric-value" style="font-size:1.35rem; color:{h_color};">{esc(health_label)}</div>
                    <div class="metric-desc">Live operational stability score</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-card" style="display:flex; align-items:center; gap:1.15rem; border-top:2px solid {r_color};">
                <svg width="104" height="104" viewBox="0 0 104 104" style="filter: drop-shadow(0 0 10px {r_color}55); flex-shrink:0;">
                    <circle cx="52" cy="52" r="42" fill="rgba(15,23,42,0.75)" stroke="rgba(148,163,184,0.16)" stroke-width="8"/>
                    <circle cx="52" cy="52" r="42" fill="none" stroke="{r_color}" stroke-width="8" stroke-linecap="round"
                            stroke-dasharray="{circ:.2f}" stroke-dashoffset="{r_off:.2f}"
                            transform="rotate(-90 52 52)"/>
                    <text x="52" y="57" text-anchor="middle" fill="#f8fafc" font-family="JetBrains Mono, monospace" font-size="16" font-weight="800">{r_clamped:.0f}</text>
                </svg>
                <div>
                    <div class="metric-label">FAILURE RISK INDEX</div>
                    <div class="metric-value" style="font-size:1.35rem; color:{r_color};">{esc(risk_label)}</div>
                    <div class="metric-desc">Heuristic cascading risk out of 100</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def resource_bar_html(label: str, value_pct: Optional[float]) -> str:
    """Returns compact HTML for a 3D beveled color-coded CPU/RAM/Disk bar."""
    if value_pct is None:
        return (
            f"<div class='res-row'><div class='res-head'><span>{esc(label)}</span>"
            f"<span style='color:#64748b;'>N/A</span></div>"
            f"<div class='res-track'><div class='res-fill' style='width:0%;'></div></div></div>"
        )
    clamped = max(0.0, min(100.0, float(value_pct)))
    bar_color = "#ef4444" if clamped >= 85 else ("#f59e0b" if clamped >= 70 else "#22d3ee")
    return (
        f"<div class='res-row'><div class='res-head'><span>{esc(label)}</span>"
        f"<strong style='color:{bar_color};'>{clamped:.1f}%</strong></div>"
        f"<div class='res-track'><div class='res-fill' style='width:{clamped:.1f}%; color:{bar_color}; background:linear-gradient(90deg, {bar_color}bb, {bar_color});'></div></div></div>"
    )


def render_3d_topology_scene(
    nodes: List[Dict[str, Any]],
    center_label: str = "AI Core Hub",
    center_sub: str = "FastAPI + FAISS + RCA",
    title: str = "Interactive 3D Infrastructure Topology",
    height: int = 380,
) -> None:
    """
    Renders a self-contained, zero-CDN 60fps interactive 3D topology scene.
    Supports mouse-drag 3D orbit (yaw/pitch), scroll zoom, animated data packets,
    pulsing fault halos, and live hover inspection tooltips.
    """
    payload_json = json.dumps({
        "nodes": nodes[:24],
        "center_label": center_label,
        "center_sub": center_sub,
        "title": title,
    }, default=str)

    html_doc = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{
        background: radial-gradient(circle at 50% 45%, #0e1a35 0%, #050814 78%);
        font-family: Inter, system-ui, -apple-system, sans-serif;
        color: #f8fafc;
        overflow: hidden;
        user-select: none;
      }}
      .wrap {{
        position: relative;
        width: 100%;
        height: {height}px;
        border-radius: 14px;
        border: 1px solid rgba(34, 211, 238, 0.25);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 16px 36px rgba(0,0,0,0.6);
        overflow: hidden;
      }}
      canvas {{ display: block; width: 100%; height: 100%; cursor: grab; }}
      canvas:active {{ cursor: grabbing; }}
      .hud-top {{
        position: absolute; top: 12px; left: 14px; right: 14px;
        display: flex; justify-content: space-between; align-items: center;
        pointer-events: none;
      }}
      .hud-badge {{
        background: rgba(9, 14, 28, 0.78);
        border: 1px solid rgba(34, 211, 238, 0.3);
        backdrop-filter: blur(8px);
        padding: 6px 12px; border-radius: 999px;
        font-size: 12px; font-weight: 700; color: #e0f2fe;
        letter-spacing: 0.02em;
      }}
      .hud-controls {{
        display: flex; gap: 8px; pointer-events: auto;
      }}
      .hud-btn {{
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(148, 163, 184, 0.28);
        color: #cbd5e1; border-radius: 8px; padding: 5px 10px;
        font-size: 11px; font-weight: 600; cursor: pointer;
      }}
      .hud-btn:hover {{ border-color: #22d3ee; color: #fff; }}
      .legend {{
        position: absolute; bottom: 10px; left: 14px;
        display: flex; gap: 14px; align-items: center;
        background: rgba(9, 14, 28, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.16);
        padding: 5px 11px; border-radius: 10px;
        font-size: 11px; color: #94a3b8; pointer-events: none;
      }}
      .dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px; }}
      .tooltip {{
        position: absolute; display: none; pointer-events: none;
        background: rgba(8, 13, 26, 0.94);
        border: 1px solid rgba(34, 211, 238, 0.48);
        border-radius: 10px; padding: 9px 12px;
        font-size: 11.5px; line-height: 1.45; color: #f1f5f9;
        box-shadow: 0 12px 28px rgba(0,0,0,0.7);
        max-width: 240px; z-index: 10;
      }}
    </style>
    </head>
    <body>
      <div class="wrap" id="wrap">
        <canvas id="scene"></canvas>
        <div class="hud-top">
          <div class="hud-badge">🌐 {esc(title)}</div>
          <div class="hud-controls">
            <button class="hud-btn" id="toggleOrbit">⏸ Pause Orbit</button>
            <button class="hud-btn" id="resetCam">⟲ Reset 3D</button>
          </div>
        </div>
        <div class="legend">
          <span><span class="dot" style="background:#10b981;"></span>Healthy / Online</span>
          <span><span class="dot" style="background:#f59e0b;"></span>Warning / Offline</span>
          <span><span class="dot" style="background:#ef4444;"></span>Critical Fault</span>
          <span style="color:#64748b;">Drag to rotate &bull; Scroll to zoom</span>
        </div>
        <div class="tooltip" id="tip"></div>
      </div>
      <script>
        const DATA = {payload_json};
        const canvas = document.getElementById("scene");
        const ctx = canvas.getContext("2d");
        const wrap = document.getElementById("wrap");
        const tip = document.getElementById("tip");
        let W = 800, H = {height}, dpr = window.devicePixelRatio || 1;

        function resize() {{
          W = wrap.clientWidth || 800;
          H = wrap.clientHeight || {height};
          canvas.width = W * dpr;
          canvas.height = H * dpr;
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }}
        resize();
        window.addEventListener("resize", resize);

        let yaw = 0.45, pitch = 0.34, zoom = 1.0, autoOrbit = true;
        let dragging = false, lastX = 0, lastY = 0, mouseX = -999, mouseY = -999;

        canvas.addEventListener("mousedown", e => {{ dragging = true; lastX = e.clientX; lastY = e.clientY; }});
        window.addEventListener("mouseup", () => {{ dragging = false; }});
        window.addEventListener("mousemove", e => {{
          const rect = canvas.getBoundingClientRect();
          mouseX = e.clientX - rect.left;
          mouseY = e.clientY - rect.top;
          if (dragging) {{
            yaw += (e.clientX - lastX) * 0.008;
            pitch = Math.max(-1.15, Math.min(1.15, pitch + (e.clientY - lastY) * 0.008));
            lastX = e.clientX; lastY = e.clientY;
          }}
        }});
        canvas.addEventListener("wheel", e => {{
          e.preventDefault();
          zoom = Math.max(0.55, Math.min(1.85, zoom - e.deltaY * 0.0008));
        }}, {{ passive: false }});

        document.getElementById("toggleOrbit").onclick = () => {{
          autoOrbit = !autoOrbit;
          document.getElementById("toggleOrbit").textContent = autoOrbit ? "⏸ Pause Orbit" : "▶ Auto Orbit";
        }};
        document.getElementById("resetCam").onclick = () => {{ yaw = 0.45; pitch = 0.34; zoom = 1.0; }};

        const STATUS_COLOR = {{
          healthy: "#10b981",
          warning: "#f59e0b",
          critical: "#ef4444",
          info: "#22d3ee"
        }};

        // Build 3D positions on tilted dual orbital rings
        const rawNodes = DATA.nodes || [];
        const nodes3D = rawNodes.map((n, i) => {{
          const count = Math.max(rawNodes.length, 1);
          const angle = (i / count) * Math.PI * 2;
          const ring = (i % 2 === 0) ? 148 : 205;
          const yLift = Math.sin(angle * 2 + i) * 48;
          return {{
            ...n,
            x: Math.cos(angle) * ring,
            y: yLift,
            z: Math.sin(angle) * ring,
            color: STATUS_COLOR[n.state || "info"] || "#22d3ee",
            radius: Math.max(10, Math.min(24, Number(n.size || 14))),
            phase: i * 0.7
          }};
        }});

        const escJs = (s) => String(s || "").replace(/[&<>"']/g, m => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[m]));

        // Starfield particles in 3D
        const stars = Array.from({{ length: 70 }}, (_, i) => ({{
          x: (Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1) * 560 - 280,
          y: (Math.abs(Math.cos(i * 78.233) * 19341.12) % 1) * 320 - 160,
          z: (Math.abs(Math.sin(i * 45.164) * 28411.7) % 1) * 560 - 280,
          r: 0.8 + (i % 3) * 0.55
        }}));

        function project(x, y, z) {{
          const cy = Math.cos(yaw), sy = Math.sin(yaw);
          const cp = Math.cos(pitch), sp = Math.sin(pitch);
          const x1 = x * cy - z * sy;
          const z1 = x * sy + z * cy;
          const y2 = y * cp - z1 * sp;
          const z2 = y * sp + z1 * cp;
          const fov = 520 * zoom;
          const dist = fov / (fov + z2 + 240);
          return {{ sx: W / 2 + x1 * dist, sy: H / 2 + y2 * dist, scale: dist, z: z2 }};
        }}

        function drawSphere(sx, sy, rad, color, pulse, isCore) {{
          if (pulse) {{
            ctx.beginPath();
            ctx.arc(sx, sy, rad + pulse, 0, Math.PI * 2);
            ctx.strokeStyle = color + "55";
            ctx.lineWidth = 2;
            ctx.stroke();
          }}
          const grad = ctx.createRadialGradient(sx - rad * 0.35, sy - rad * 0.35, rad * 0.12, sx, sy, rad);
          grad.addColorStop(0, "#ffffff");
          grad.addColorStop(0.28, color);
          grad.addColorStop(1, "#070b18");
          ctx.beginPath();
          ctx.arc(sx, sy, rad, 0, Math.PI * 2);
          ctx.fillStyle = grad;
          ctx.shadowColor = color;
          ctx.shadowBlur = isCore ? 26 : 14;
          ctx.fill();
          ctx.shadowBlur = 0;
        }}

        let t = 0;
        function frame() {{
          t += 0.018;
          if (autoOrbit && !dragging) yaw += 0.0042;
          ctx.clearRect(0, 0, W, H);

          // 3D Floor Cyber Grid (y = +110)
          ctx.strokeStyle = "rgba(34, 211, 238, 0.09)";
          ctx.lineWidth = 1;
          for (let g = -220; g <= 220; g += 55) {{
            const a = project(g, 115, -220), b = project(g, 115, 220);
            ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy); ctx.stroke();
            const c = project(-220, 115, g), d = project(220, 115, g);
            ctx.beginPath(); ctx.moveTo(c.sx, c.sy); ctx.lineTo(d.sx, d.sy); ctx.stroke();
          }}

          // Stars
          for (const s of stars) {{
            const p = project(s.x, s.y, s.z);
            ctx.fillStyle = "rgba(148, 163, 184, 0.35)";
            ctx.beginPath(); ctx.arc(p.sx, p.sy, Math.max(0.5, s.r * p.scale), 0, Math.PI * 2); ctx.fill();
          }}

          // Orbital Guide Ring
          ctx.beginPath();
          for (let a = 0; a <= 64; a++) {{
            const ang = (a / 64) * Math.PI * 2;
            const p = project(Math.cos(ang) * 175, 0, Math.sin(ang) * 175);
            if (a === 0) ctx.moveTo(p.sx, p.sy); else ctx.lineTo(p.sx, p.sy);
          }}
          ctx.strokeStyle = "rgba(129, 140, 248, 0.16)";
          ctx.stroke();

          const coreP = project(0, 0, 0);
          const projected = nodes3D.map(n => ({{
            node: n,
            p: project(n.x, n.y + Math.sin(t + n.phase) * 5, n.z)
          }}));

          // Connections + Animated 3D Telemetry Packets
          for (const item of projected) {{
            const {{ node, p }} = item;
            ctx.beginPath();
            ctx.moveTo(coreP.sx, coreP.sy);
            ctx.lineTo(p.sx, p.sy);
            ctx.strokeStyle = node.color + "55";
            ctx.lineWidth = node.state === "critical" ? 2.2 : 1.3;
            ctx.stroke();

            const pkt = (t * 0.45 + node.phase) % 1.0;
            const px = coreP.sx + (p.sx - coreP.sx) * pkt;
            const py = coreP.sy + (p.sy - coreP.sy) * pkt;
            ctx.beginPath();
            ctx.arc(px, py, 2.8 * p.scale, 0, Math.PI * 2);
            ctx.fillStyle = "#ffffff";
            ctx.shadowColor = node.color;
            ctx.shadowBlur = 10;
            ctx.fill();
            ctx.shadowBlur = 0;
          }}

          // Depth-sort all spheres (back to front)
          const drawQueue = [
            {{ isCore: true, z: coreP.z, p: coreP, color: "#22d3ee", rad: 25 * coreP.scale }},
            ...projected.map(it => ({{
              isCore: false,
              z: it.p.z,
              p: it.p,
              node: it.node,
              color: it.node.color,
              rad: it.node.radius * it.p.scale
            }}))
          ].sort((a, b) => b.z - a.z);

          let hovered = null;
          for (const d of drawQueue) {{
            if (d.isCore) {{
              drawSphere(d.p.sx, d.p.sy, d.rad, "#22d3ee", (Math.sin(t * 2.5) * 4 + 8), true);
              ctx.fillStyle = "#e0f2fe";
              ctx.font = "700 11px Inter, sans-serif";
              ctx.textAlign = "center";
              ctx.fillText(DATA.center_label, d.p.sx, d.p.sy + d.rad + 15);
            }} else {{
              const pulse = d.node.state === "critical" ? (Math.sin(t * 5) * 4 + 7) : 0;
              drawSphere(d.p.sx, d.p.sy, d.rad, d.color, pulse, false);
              ctx.fillStyle = "#e2e8f0";
              ctx.font = "600 10.5px JetBrains Mono, monospace";
              ctx.textAlign = "center";
              ctx.fillText(d.node.label, d.p.sx, d.p.sy + d.rad + 13);

              const dx = mouseX - d.p.sx, dy = mouseY - d.p.sy;
              if (Math.hypot(dx, dy) <= d.rad + 8) hovered = d;
            }}
          }}

          if (hovered) {{
            tip.style.display = "block";
            tip.style.left = Math.min(W - 245, Math.max(10, hovered.p.sx + 14)) + "px";
            tip.style.top = Math.min(H - 95, Math.max(10, hovered.p.sy - 16)) + "px";
            tip.innerHTML = `<strong style="color:${{hovered.color}}">${{escJs(hovered.node.label)}}</strong><br>${{hovered.node.detail || ""}}`;
          }} else {{
            tip.style.display = "none";
          }}

          requestAnimationFrame(frame);
        }}
        frame();
      </script>
    </body>
    </html>
    """
    components.html(html_doc, height=height + 8, scrolling=False)


def render_3d_vector_constellation(
    query: str,
    results: List[Dict[str, Any]],
    height: int = 330,
) -> None:
    """
    Renders an interactive 3D FAISS Semantic Similarity Constellation:
    Query sits at the 3D origin; matched logs orbit at radius proportional to (1 - similarity).
    """
    nodes = []
    for item in results[:15]:
        sim_pct = float(item.get("similarity_pct", 50.0))
        sev = str(item.get("level", "INFO")).upper()
        state = "critical" if sev in ("CRITICAL", "FATAL") else ("warning" if sev in ("ERROR", "WARN") else "healthy")
        nodes.append({
            "label": f"#{item.get('rank')} {item.get('service', 'svc')} ({sim_pct:.0f}%)",
            "state": state,
            "size": max(10.0, min(20.0, sim_pct / 5.5)),
            "detail": f"[{sev}] {sim_pct:.1f}% Match<br>{esc(str(item.get('message', ''))[:95])}",
        })
    render_3d_topology_scene(
        nodes=nodes,
        center_label=f"Query: {query[:22]}",
        center_sub="384-dim Vector Space",
        title="3D Semantic Vector Constellation (FAISS Cosine Proximity)",
        height=height,
    )


def render_stage_badge(stage_name: str, status: str) -> None:
    """Renders a compact status badge."""
    css_class = "stage-active" if status == "COMPLETED" else "stage-upcoming"
    icon = "✓" if status == "COMPLETED" else "⏱"
    st.markdown(
        f"""
        <span class="stage-pill {css_class}">
            <span>{icon}</span> {esc(stage_name)}: {esc(status)}
        </span>
        """,
        unsafe_allow_html=True,
    )
