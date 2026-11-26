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
        [data-testid="stHeader"] {
            background: transparent !important;
        }

        @keyframes cyberGridFlow {
            0%   { background-position: 0 0, 0 0; }
            100% { background-position: 0 60px, 0 60px; }
        }

        @keyframes auroraDrift {
            0%   { transform: translate3d(-2%, -1%, 0) scale(1); }
            50%  { transform: translate3d(2%, 2%, 0) scale(1.06); }
            100% { transform: translate3d(-2%, -1%, 0) scale(1); }
        }

        /* 3D Spatial Deep-Space Backdrop */
        .stApp {
            position: relative;
            background-color: #030612;
            background-image:
                radial-gradient(ellipse 80% 50% at 15% -5%, rgba(34, 211, 238, 0.20), transparent 62%),
                radial-gradient(ellipse 65% 48% at 88% 4%, rgba(139, 92, 246, 0.19), transparent 60%),
                radial-gradient(ellipse 70% 45% at 50% 105%, rgba(16, 185, 129, 0.12), transparent 65%);
            overflow-x: hidden;
        }

        /* 3D Vanishing-Point Perspective Floor Grid */
        [data-testid="stAppViewContainer"] {
            position: relative;
            overflow-x: hidden;
        }
        [data-testid="stAppViewContainer"]::before {
            content: "";
            position: fixed;
            left: -25%;
            right: -25%;
            bottom: -18%;
            height: 72vh;
            pointer-events: none;
            z-index: 0;
            background-image:
                linear-gradient(to right, rgba(34, 211, 238, 0.18) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(129, 140, 248, 0.18) 1px, transparent 1px);
            background-size: 60px 60px;
            transform-origin: 50% 100%;
            transform: perspective(560px) rotateX(68deg);
            -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,0.92) 0%, rgba(0,0,0,0.4) 48%, transparent 82%);
            mask-image: linear-gradient(to top, rgba(0,0,0,0.92) 0%, rgba(0,0,0,0.4) 48%, transparent 82%);
            animation: cyberGridFlow 7s linear infinite;
        }

        /* 3D Volumetric Floating Aurora Halos */
        [data-testid="stAppViewContainer"]::after {
            content: "";
            position: fixed;
            inset: -10%;
            pointer-events: none;
            z-index: 0;
            background:
                radial-gradient(circle at 22% 24%, rgba(34, 211, 238, 0.14) 0%, transparent 32%),
                radial-gradient(circle at 78% 28%, rgba(168, 85, 247, 0.14) 0%, transparent 34%),
                radial-gradient(circle at 52% 76%, rgba(16, 185, 129, 0.10) 0%, transparent 36%);
            filter: blur(28px);
            animation: auroraDrift 16s ease-in-out infinite;
        }

        .block-container {
            position: relative;
            z-index: 1;
            padding-top: 1.4rem;
            padding-bottom: 2.5rem;
            max-width: 1440px;
            perspective: 1400px;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(8, 13, 28, 0.86) 0%, rgba(4, 7, 18, 0.94) 100%);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border-right: 1px solid rgba(34, 211, 238, 0.22);
            box-shadow: 12px 0 38px rgba(0, 0, 0, 0.55);
        }

        /* 3D Glassmorphic Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.68), rgba(8, 13, 28, 0.82));
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            padding: 0.42rem;
            border-radius: 14px;
            border: 1px solid rgba(148, 163, 184, 0.2);
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.1),
                0 12px 30px -8px rgba(0, 0, 0, 0.6);
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
            border-radius: 9px;
            font-weight: 600;
            font-size: 0.8rem;
            padding: 0.32rem 0.72rem;
            min-height: 2.05rem;
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
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.78), rgba(7, 11, 24, 0.88));
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(34, 211, 238, 0.32);
            border-radius: 16px;
            padding: 1.15rem 1.45rem;
            margin-bottom: 1.15rem;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.18),
                0 22px 48px -14px rgba(0, 0, 0, 0.72),
                0 0 42px -12px rgba(34, 211, 238, 0.28);
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
            background: linear-gradient(155deg, rgba(20, 30, 54, 0.68), rgba(7, 11, 24, 0.86));
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 14px;
            padding: 1rem 1.15rem;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.16),
                inset 0 -1px 0 rgba(0, 0, 0, 0.4),
                0 18px 38px -12px rgba(0, 0, 0, 0.72);
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
        if (window.ResizeObserver) new ResizeObserver(resize).observe(wrap);

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
    height: int = 350,
) -> None:
    """
    Renders a distinct, industry-grade 3D FAISS Vector Space Hypercube & Cosine Radar:
    - 3D Bounding Hypercube + X/Y/Z embedding axes + concentric cosine shells
    - Radiant 3D Query Star Crystal at the origin (0,0,0)
    - Matched log vectors placed in 3D Fibonacci sphere coordinates at radius ~ (100 - similarity_pct)
    """
    pts = []
    top_score = 0.0
    for item in results[:18]:
        sim_pct = float(item.get("similarity_pct", 50.0))
        top_score = max(top_score, sim_pct)
        raw_cos = item.get("similarity_score", round((sim_pct / 100.0) * 2.0 - 1.0, 3))
        sev = str(item.get("level", "INFO")).upper()
        pts.append({
            "rank": item.get("rank", len(pts) + 1),
            "service": str(item.get("service", "svc")),
            "sev": sev,
            "sim_pct": sim_pct,
            "raw_cos": raw_cos,
            "detail": (
                f"Rank #{esc(item.get('rank'))} &bull; [{esc(sev)}] &bull; "
                f"{sim_pct:.1f}% Match (cos={esc(raw_cos)})<br>"
                f"{esc(str(item.get('message', ''))[:105])}"
            ),
        })

    payload_json = json.dumps({
        "query": query[:34],
        "points": pts,
        "top_score": f"{top_score:.1f}%",
    }, default=str)

    html_doc = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{
        background: radial-gradient(circle at 50% 50%, #140f2d 0%, #050814 80%);
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
        border: 1px solid rgba(168, 85, 247, 0.36);
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,0.12),
          0 18px 40px rgba(0,0,0,0.68),
          0 0 36px -12px rgba(168, 85, 247, 0.28);
        overflow: hidden;
      }}
      canvas {{ display: block; width: 100%; height: 100%; cursor: grab; }}
      canvas:active {{ cursor: grabbing; }}
      .hud-top {{
        position: absolute; top: 10px; left: 12px; right: 12px;
        display: flex; justify-content: space-between; align-items: center;
        pointer-events: none;
      }}
      .hud-title {{
        background: rgba(9, 7, 24, 0.84);
        border: 1px solid rgba(192, 132, 252, 0.42);
        padding: 5px 12px; border-radius: 999px;
        font-size: 11.5px; font-weight: 700; color: #f3e8ff;
        letter-spacing: 0.03em;
      }}
      .hud-btns {{ display: flex; gap: 6px; pointer-events: auto; }}
      .hud-btn {{
        background: rgba(15, 23, 42, 0.86);
        border: 1px solid rgba(148, 163, 184, 0.28);
        color: #cbd5e1; border-radius: 7px; padding: 4px 9px;
        font-size: 11px; font-weight: 600; cursor: pointer;
      }}
      .hud-btn:hover {{ border-color: #c084fc; color: #fff; }}
      .hud-bottom {{
        position: absolute; bottom: 10px; left: 12px; right: 12px;
        display: flex; justify-content: space-between; align-items: center;
        pointer-events: none; font-size: 11px;
      }}
      .chips {{ display: flex; gap: 7px; flex-wrap: wrap; }}
      .chip {{
        background: rgba(9, 7, 24, 0.84);
        border: 1px solid rgba(192, 132, 252, 0.28);
        padding: 4px 9px; border-radius: 8px; color: #cbd5e1;
        font-family: "JetBrains Mono", monospace; font-size: 10.5px;
      }}
      .tip {{
        position: absolute; display: none; pointer-events: none;
        background: rgba(8, 6, 22, 0.96);
        border: 1px solid rgba(192, 132, 252, 0.6);
        border-radius: 10px; padding: 8px 11px;
        font-size: 11.5px; line-height: 1.45; color: #f1f5f9;
        box-shadow: 0 14px 30px rgba(0,0,0,0.75);
        max-width: 265px; z-index: 12;
      }}
    </style>
    </head>
    <body>
      <div class="wrap" id="wrap">
        <canvas id="vspace"></canvas>
        <div class="hud-top">
          <div class="hud-title">✨ 3D FAISS VECTOR HYPERCUBE &bull; &ldquo;{esc(query[:28])}&rdquo;</div>
          <div class="hud-btns">
            <button class="hud-btn" id="pauseBtn">⏸ Pause</button>
            <button class="hud-btn" id="resetBtn">⟲ Reset 3D</button>
          </div>
        </div>
        <div class="hud-bottom">
          <div class="chips">
            <span class="chip">SPACE: <strong style="color:#c084fc;">384-DIM</strong></span>
            <span class="chip">INDEX: <strong style="color:#22d3ee;">IndexFlatIP</strong></span>
            <span class="chip">MATCHES: <strong>{len(pts)}</strong></span>
            <span class="chip">TOP MATCH: <strong style="color:#10b981;">{top_score:.1f}%</strong></span>
          </div>
          <span style="color:#94a3b8;">Closer to crystal = Higher similarity</span>
        </div>
        <div class="tip" id="tip"></div>
      </div>
      <script>
        const CFG = {payload_json};
        const canvas = document.getElementById("vspace");
        const ctx = canvas.getContext("2d");
        const wrap = document.getElementById("wrap");
        const tip = document.getElementById("tip");
        const escJs = (s) => String(s || "").replace(/[&<>"']/g, m => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[m]));

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
        if (window.ResizeObserver) new ResizeObserver(resize).observe(wrap);

        let yaw = 0.58, pitch = 0.32, zoom = 1.0, autoSpin = true;
        let dragging = false, lx = 0, ly = 0, mx = -999, my = -999;
        canvas.addEventListener("mousedown", e => {{ dragging = true; lx = e.clientX; ly = e.clientY; }});
        window.addEventListener("mouseup", () => {{ dragging = false; }});
        window.addEventListener("mousemove", e => {{
          const r = canvas.getBoundingClientRect();
          mx = e.clientX - r.left; my = e.clientY - r.top;
          if (dragging) {{
            yaw += (e.clientX - lx) * 0.0075;
            pitch = Math.max(-1.2, Math.min(1.2, pitch + (e.clientY - ly) * 0.0075));
            lx = e.clientX; ly = e.clientY;
          }}
        }});
        canvas.addEventListener("wheel", e => {{
          e.preventDefault();
          zoom = Math.max(0.55, Math.min(1.85, zoom - e.deltaY * 0.0008));
        }}, {{ passive: false }});
        document.getElementById("pauseBtn").onclick = () => {{
          autoSpin = !autoSpin;
          document.getElementById("pauseBtn").textContent = autoSpin ? "⏸ Pause" : "▶ Orbit";
        }};
        document.getElementById("resetBtn").onclick = () => {{ yaw = 0.58; pitch = 0.32; zoom = 1.0; }};

        // Wireframe Hypercube corners & edges
        const C = 138;
        const cubeV = [];
        for (const x of [-C, C]) for (const y of [-C, C]) for (const z of [-C, C]) cubeV.push([x, y, z]);
        const cubeE = [];
        for (let i = 0; i < 8; i++) for (let j = i + 1; j < 8; j++) {{
          const d = (cubeV[i][0] !== cubeV[j][0]) + (cubeV[i][1] !== cubeV[j][1]) + (cubeV[i][2] !== cubeV[j][2]);
          if (d === 1) cubeE.push([i, j]);
        }}

        // Place matched vectors in 3D Fibonacci sphere coordinates; closer = higher cosine match!
        const goldenAngle = Math.PI * (3 - Math.sqrt(5));
        const pts3D = CFG.points.map((pt, idx) => {{
          const n = Math.max(CFG.points.length, 1);
          const yDir = 1 - (idx / Math.max(n - 1, 1)) * 1.6 - 0.2;
          const rAtY = Math.sqrt(Math.max(0.05, 1 - yDir * yDir));
          const theta = goldenAngle * idx;
          // Radial distance inversely maps similarity (95% -> ~58px, 45% -> ~132px)
          const radial = Math.max(52, Math.min(134, 150 - pt.sim_pct * 0.95));
          const col = pt.sev === "CRITICAL" || pt.sev === "FATAL" ? "#ef4444"
                    : (pt.sim_pct >= 72 ? "#10b981" : (pt.sim_pct >= 55 ? "#22d3ee" : "#c084fc"));
          return {{
            ...pt,
            x: Math.cos(theta) * rAtY * radial,
            y: yDir * radial * 0.85,
            z: Math.sin(theta) * rAtY * radial,
            color: col
          }};
        }});

        function proj(x, y, z) {{
          const cy = Math.cos(yaw), sy = Math.sin(yaw);
          const cp = Math.cos(pitch), sp = Math.sin(pitch);
          const x1 = x * cy - z * sy;
          const z1 = x * sy + z * cy;
          const y2 = y * cp - z1 * sp;
          const z2 = y * sp + z1 * cp;
          const fov = 540 * zoom;
          const sc = fov / (fov + z2 + 260);
          return {{ sx: W / 2 + x1 * sc, sy: H / 2 + y2 * sc, sc, z: z2 }};
        }}

        function drawCrystal(sx, sy, r, t) {{
          const top = {{ x: sx, y: sy - r * 1.35 }};
          const bot = {{ x: sx, y: sy + r * 1.35 }};
          const lft = {{ x: sx - r * 1.05, y: sy }};
          const rgt = {{ x: sx + r * 1.05, y: sy }};
          const mid = {{ x: sx + Math.sin(t * 2) * r * 0.28, y: sy + r * 0.12 }};
          const faces = [
            [top, lft, mid, "rgba(250, 204, 21, 0.9)"],
            [top, mid, rgt, "rgba(34, 211, 238, 0.92)"],
            [bot, lft, mid, "rgba(168, 85, 247, 0.85)"],
            [bot, mid, rgt, "rgba(56, 189, 248, 0.88)"]
          ];
          ctx.shadowColor = "#fde047";
          ctx.shadowBlur = 22;
          for (const [a, b, c, fill] of faces) {{
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.lineTo(c.x, c.y); ctx.closePath();
            ctx.fillStyle = fill; ctx.fill();
            ctx.strokeStyle = "rgba(255,255,255,0.65)"; ctx.lineWidth = 0.8; ctx.stroke();
          }}
          ctx.shadowBlur = 0;
        }}

        let t = 0;
        function render() {{
          t += 0.016;
          if (autoSpin && !dragging) yaw += 0.0038;
          ctx.clearRect(0, 0, W, H);

          // 1. 3D Wireframe Vector Hypercube
          const cv = cubeV.map(v => proj(v[0], v[1], v[2]));
          ctx.strokeStyle = "rgba(168, 85, 247, 0.22)";
          ctx.lineWidth = 1.1;
          for (const [a, b] of cubeE) {{
            ctx.beginPath(); ctx.moveTo(cv[a].sx, cv[a].sy); ctx.lineTo(cv[b].sx, cv[b].sy); ctx.stroke();
          }}

          // 2. 3D X/Y/Z Embedding Axes
          const axes = [
            [[-150, 0, 0], [150, 0, 0], "Dim-X", "rgba(34,211,238,0.45)"],
            [[0, -150, 0], [0, 150, 0], "Dim-Y", "rgba(192,132,252,0.45)"],
            [[0, 0, -150], [0, 0, 150], "Dim-Z", "rgba(16,185,129,0.45)"]
          ];
          for (const [p1, p2, lbl, col] of axes) {{
            const a = proj(p1[0], p1[1], p1[2]), b = proj(p2[0], p2[1], p2[2]);
            ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy);
            ctx.strokeStyle = col; ctx.setLineDash([4, 4]); ctx.stroke(); ctx.setLineDash([]);
            ctx.fillStyle = col; ctx.font = "600 10px JetBrains Mono, monospace";
            ctx.fillText(lbl, b.sx + 6, b.sy);
          }}

          // 3. Cosine Proximity Guide Rings
          for (const rad of [65, 110]) {{
            ctx.beginPath();
            for (let k = 0; k <= 48; k++) {{
              const ang = (k / 48) * Math.PI * 2;
              const p = proj(Math.cos(ang) * rad, 0, Math.sin(ang) * rad);
              if (k === 0) ctx.moveTo(p.sx, p.sy); else ctx.lineTo(p.sx, p.sy);
            }}
            ctx.strokeStyle = "rgba(192, 132, 252, 0.14)";
            ctx.stroke();
          }}

          const origin = proj(0, 0, 0);
          const projected = pts3D.map((pt, i) => ({{
            pt,
            p: proj(pt.x, pt.y + Math.sin(t + i) * 3, pt.z)
          }}));

          // 4. Cosine Vector Rays from Origin to Matches
          for (const it of projected) {{
            const {{ pt, p }} = it;
            const grad = ctx.createLinearGradient(origin.sx, origin.sy, p.sx, p.sy);
            grad.addColorStop(0, "rgba(253, 224, 71, 0.7)");
            grad.addColorStop(1, pt.color);
            ctx.beginPath(); ctx.moveTo(origin.sx, origin.sy); ctx.lineTo(p.sx, p.sy);
            ctx.strokeStyle = grad;
            ctx.lineWidth = pt.rank === 1 ? 2.4 : 1.35;
            ctx.stroke();

            // Midpoint cosine badge for top 3 matches
            if (pt.rank <= 3) {{
              const mxp = (origin.sx + p.sx) / 2, myp = (origin.sy + p.sy) / 2;
              ctx.fillStyle = "rgba(8, 6, 22, 0.85)";
              ctx.fillRect(mxp - 16, myp - 8, 32, 14);
              ctx.fillStyle = pt.color;
              ctx.font = "700 9.5px JetBrains Mono, monospace";
              ctx.textAlign = "center";
              ctx.fillText(Math.round(pt.sim_pct) + "%", mxp, myp + 2);
            }}
          }}

          // 5. Depth-Sort Query Crystal + Matched Vector Nodes
          const drawItems = [
            {{ isCrystal: true, z: origin.z, p: origin }},
            ...projected.map(it => ({{ isCrystal: false, z: it.p.z, p: it.p, pt: it.pt }}))
          ].sort((a, b) => b.z - a.z);

          let hovered = null;
          for (const d of drawItems) {{
            if (d.isCrystal) {{
              drawCrystal(d.p.sx, d.p.sy, 16 * d.p.sc, t);
              ctx.fillStyle = "#fef08a";
              ctx.font = "700 10.5px Inter, sans-serif";
              ctx.textAlign = "center";
              ctx.fillText("QUERY", d.p.sx, d.p.sy + 26 * d.p.sc);
            }} else {{
              const rad = Math.max(8, (d.pt.rank === 1 ? 15 : 11.5) * d.p.sc);
              const rg = ctx.createRadialGradient(d.p.sx - rad * 0.3, d.p.sy - rad * 0.3, rad * 0.1, d.p.sx, d.p.sy, rad);
              rg.addColorStop(0, "#ffffff");
              rg.addColorStop(0.32, d.pt.color);
              rg.addColorStop(1, "#060414");
              ctx.beginPath(); ctx.arc(d.p.sx, d.p.sy, rad, 0, Math.PI * 2);
              ctx.fillStyle = rg;
              ctx.shadowColor = d.pt.color; ctx.shadowBlur = d.pt.rank === 1 ? 20 : 12;
              ctx.fill(); ctx.shadowBlur = 0;

              ctx.fillStyle = "#f1f5f9";
              ctx.font = "600 10px JetBrains Mono, monospace";
              ctx.textAlign = "center";
              ctx.fillText(`#${{d.pt.rank}} ${{d.pt.service}}`, d.p.sx, d.p.sy + rad + 12);

              if (Math.hypot(mx - d.p.sx, my - d.p.sy) <= rad + 8) hovered = d;
            }}
          }}

          if (hovered) {{
            tip.style.display = "block";
            tip.style.left = Math.min(W - 270, Math.max(10, hovered.p.sx + 14)) + "px";
            tip.style.top = Math.min(H - 95, Math.max(10, hovered.p.sy - 14)) + "px";
            tip.innerHTML = `<strong style="color:${{hovered.pt.color}}">#${{hovered.pt.rank}} ${{escJs(hovered.pt.service)}}</strong><br>${{hovered.pt.detail}}`;
          }} else {{
            tip.style.display = "none";
          }}

          requestAnimationFrame(render);
        }}
        render();
      </script>
    </body>
    </html>
    """
    components.html(html_doc, height=height + 8, scrolling=False)


def render_3d_rca_fault_graph(
    incidents: List[Dict[str, Any]],
    live_mode: bool = False,
    height: int = 340,
) -> None:
    """
    Renders an interactive 3D Root Cause Analysis (RCA) & Incident Fault-Tree Graph.
    Works for both static analyzer RCA results and live backend fleet incidents.
    """
    nodes = []
    for inc in incidents[:18]:
        sev = str(inc.get("severity", "HIGH")).upper()
        status = str(inc.get("status", "OPEN")).upper()
        if status == "RESOLVED":
            state = "healthy"
        elif sev in ("CRITICAL", "FATAL") or status == "OPEN":
            state = "critical" if sev in ("CRITICAL", "FATAL") else "warning"
        else:
            state = "warning"

        title_short = str(inc.get("title") or inc.get("category") or "Incident")[:28]
        if live_mode:
            host = inc.get("hostname", "host")
            conf = inc.get("confidence_pct", 80)
            cause = inc.get("possible_root_cause") or "Under investigation"
            label = f"{host}: {title_short}"[:30]
            detail = (
                f"[{sev}] [{status}] Confidence: {esc(conf)}%<br>"
                f"Cause: {esc(str(cause)[:100])}"
            )
            size = max(12.0, min(22.0, float(conf) / 4.8))
        else:
            ev_count = int(inc.get("evidence_count", 1))
            conf_lbl = inc.get("confidence_label", "HIGH")
            cause = inc.get("likely_root_cause") or "Under investigation"
            label = title_short
            detail = (
                f"[{sev}] Evidence: {ev_count} line(s) &bull; {esc(conf_lbl)}<br>"
                f"Root Cause: {esc(str(cause)[:105])}"
            )
            size = min(22.0, 12.0 + ev_count * 1.4)

        nodes.append({
            "label": label,
            "state": state,
            "size": size,
            "detail": detail,
        })

    render_3d_topology_scene(
        nodes=nodes,
        center_label="RCA Fault Core",
        center_sub="Root Cause Graph",
        title="Interactive 3D Incident & Root Cause Fault Graph",
        height=height,
    )


def render_3d_ai_neural_core(
    context_label: str,
    intent_label: str = "STANDBY",
    confidence_label: str = "READY",
    evidence_items: Optional[List[Dict[str, Any]]] = None,
    signals: Optional[List[Dict[str, str]]] = None,
    height: int = 320,
) -> None:
    """
    Renders a distinct, industry-grade 3D Neural Reasoning Engine & Evidence Matrix:
    - Left 3D plane: Grounding pipelines (Parser, RCA, FAISS, Health, Risk)
    - Center: Rotating 3D wireframe Icosahedron + inner 3D Tesseract + 3 gyroscope rings
    - Right 3D plane: Cited ground-truth log evidence nodes connected by neural beams
    """
    ev_list = []
    for idx, ev in enumerate((evidence_items or [])[:6]):
        sev = str(ev.get("level", "INFO")).upper()
        svc = str(ev.get("service", "system"))
        line_no = ev.get("line_no")
        prefix = f"L{line_no} " if line_no else ""
        ev_list.append({
            "label": f"{prefix}[{svc}]"[:22],
            "sev": sev,
            "detail": f"[{sev}] {esc(ev.get('timestamp', 'N/A'))}<br>{esc(str(ev.get('message', ''))[:105])}",
        })
    if not ev_list:
        ev_list = [
            {"label": "Evidence Gate", "sev": "INFO", "detail": "Awaiting query — all answers strictly cite verified log lines."},
            {"label": "Safety Guard", "sev": "INFO", "detail": "Live execution blocked; advisory dry-run playbooks only."},
        ]

    sig_list = signals or [
        {"label": "Log Parser", "detail": "Normalized multi-format event stream"},
        {"label": "RCA Fault Tree", "detail": "6-domain deterministic root cause classifier"},
        {"label": "FAISS 384-d", "detail": "Vector cosine similarity retrieval"},
        {"label": "Health & Risk", "detail": "Explainable score & trajectory weighting"},
    ]

    payload_json = json.dumps({
        "context": context_label[:40],
        "intent": intent_label,
        "confidence": confidence_label,
        "signals": sig_list[:5],
        "evidence": ev_list,
    }, default=str)

    html_doc = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{
        background: radial-gradient(circle at 50% 48%, #0b1633 0%, #040711 82%);
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
        border: 1px solid rgba(129, 140, 248, 0.32);
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,0.12),
          0 18px 40px rgba(0,0,0,0.68),
          0 0 36px -12px rgba(34, 211, 238, 0.25);
        overflow: hidden;
      }}
      canvas {{ display: block; width: 100%; height: 100%; cursor: grab; }}
      canvas:active {{ cursor: grabbing; }}
      .hud-top {{
        position: absolute; top: 10px; left: 12px; right: 12px;
        display: flex; justify-content: space-between; align-items: center;
        pointer-events: none;
      }}
      .hud-title {{
        background: rgba(6, 10, 24, 0.82);
        border: 1px solid rgba(129, 140, 248, 0.38);
        padding: 5px 12px; border-radius: 999px;
        font-size: 11.5px; font-weight: 700; color: #e0e7ff;
        letter-spacing: 0.04em;
      }}
      .hud-btns {{ display: flex; gap: 6px; pointer-events: auto; }}
      .hud-btn {{
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(148, 163, 184, 0.26);
        color: #cbd5e1; border-radius: 7px; padding: 4px 9px;
        font-size: 11px; font-weight: 600; cursor: pointer;
      }}
      .hud-btn:hover {{ border-color: #818cf8; color: #fff; }}
      .hud-bottom {{
        position: absolute; bottom: 10px; left: 12px; right: 12px;
        display: flex; justify-content: space-between; align-items: center;
        pointer-events: none; font-size: 11px;
      }}
      .hud-chips {{ display: flex; gap: 8px; flex-wrap: wrap; }}
      .chip {{
        background: rgba(6, 10, 24, 0.82);
        border: 1px solid rgba(34, 211, 238, 0.25);
        padding: 4px 9px; border-radius: 8px; color: #cbd5e1;
        font-family: "JetBrains Mono", monospace; font-size: 10.5px;
      }}
      .tip {{
        position: absolute; display: none; pointer-events: none;
        background: rgba(5, 9, 20, 0.95);
        border: 1px solid rgba(129, 140, 248, 0.55);
        border-radius: 10px; padding: 8px 11px;
        font-size: 11.5px; line-height: 1.45; color: #f1f5f9;
        box-shadow: 0 14px 30px rgba(0,0,0,0.75);
        max-width: 260px; z-index: 12;
      }}
    </style>
    </head>
    <body>
      <div class="wrap" id="wrap">
        <canvas id="neural"></canvas>
        <div class="hud-top">
          <div class="hud-title">🧠 3D AI NEURAL REASONING ENGINE &bull; {esc(context_label[:32])}</div>
          <div class="hud-btns">
            <button class="hud-btn" id="pauseBtn">⏸ Freeze</button>
            <button class="hud-btn" id="resetBtn">⟲ Reset</button>
          </div>
        </div>
        <div class="hud-bottom">
          <div class="hud-chips">
            <span class="chip">INTENT: <strong style="color:#22d3ee;">{esc(intent_label)}</strong></span>
            <span class="chip">CONFIDENCE: <strong style="color:#10b981;">{esc(confidence_label)}</strong></span>
            <span class="chip">EVIDENCE: <strong>{len(evidence_items or [])}</strong></span>
            <span class="chip" style="border-color:rgba(16,185,129,0.35);">GATE: <strong style="color:#10b981;">ADVISORY ONLY</strong></span>
          </div>
          <span style="color:#64748b;">Drag 3D &bull; Scroll Zoom</span>
        </div>
        <div class="tip" id="tip"></div>
      </div>
      <script>
        const CFG = {payload_json};
        const canvas = document.getElementById("neural");
        const ctx = canvas.getContext("2d");
        const wrap = document.getElementById("wrap");
        const tip = document.getElementById("tip");
        const escJs = (s) => String(s || "").replace(/[&<>"']/g, m => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[m]));

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
        if (window.ResizeObserver) new ResizeObserver(resize).observe(wrap);

        let yaw = 0.25, pitch = 0.18, zoom = 1.0, spinning = true;
        let dragging = false, lx = 0, ly = 0, mx = -999, my = -999;
        canvas.addEventListener("mousedown", e => {{ dragging = true; lx = e.clientX; ly = e.clientY; }});
        window.addEventListener("mouseup", () => {{ dragging = false; }});
        window.addEventListener("mousemove", e => {{
          const r = canvas.getBoundingClientRect();
          mx = e.clientX - r.left; my = e.clientY - r.top;
          if (dragging) {{
            yaw += (e.clientX - lx) * 0.007;
            pitch = Math.max(-1.0, Math.min(1.0, pitch + (e.clientY - ly) * 0.007));
            lx = e.clientX; ly = e.clientY;
          }}
        }});
        canvas.addEventListener("wheel", e => {{
          e.preventDefault();
          zoom = Math.max(0.6, Math.min(1.75, zoom - e.deltaY * 0.0008));
        }}, {{ passive: false }});
        document.getElementById("pauseBtn").onclick = () => {{
          spinning = !spinning;
          document.getElementById("pauseBtn").textContent = spinning ? "⏸ Freeze" : "▶ Resume";
        }};
        document.getElementById("resetBtn").onclick = () => {{ yaw = 0.25; pitch = 0.18; zoom = 1.0; }};

        // 3D Geodesic Icosahedron geometry
        const phi = (1 + Math.sqrt(5)) / 2;
        const rawVerts = [
          [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
          [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
          [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1]
        ].map(v => {{
          const len = Math.hypot(v[0], v[1], v[2]);
          return [v[0] / len * 66, v[1] / len * 66, v[2] / len * 66];
        }});
        const icoEdges = [];
        for (let i = 0; i < rawVerts.length; i++) {{
          for (let j = i + 1; j < rawVerts.length; j++) {{
            const d = Math.hypot(
              rawVerts[i][0] - rawVerts[j][0],
              rawVerts[i][1] - rawVerts[j][1],
              rawVerts[i][2] - rawVerts[j][2]
            );
            if (d < 74) icoEdges.push([i, j]);
          }}
        }}

        // Inner 3D cube vertices
        const cubeVerts = [];
        for (const sx of [-26, 26]) for (const sy of [-26, 26]) for (const sz of [-26, 26]) cubeVerts.push([sx, sy, sz]);
        const cubeEdges = [];
        for (let i = 0; i < 8; i++) for (let j = i + 1; j < 8; j++) {{
          const diff = (cubeVerts[i][0] !== cubeVerts[j][0]) + (cubeVerts[i][1] !== cubeVerts[j][1]) + (cubeVerts[i][2] !== cubeVerts[j][2]);
          if (diff === 1) cubeEdges.push([i, j]);
        }}

        const SEV_COLOR = {{ CRITICAL: "#ef4444", FATAL: "#ef4444", ERROR: "#f97316", WARN: "#f59e0b", WARNING: "#f59e0b", INFO: "#10b981" }};
        const coreColor = CFG.confidence === "INSUFFICIENT_EVIDENCE" ? "#f59e0b" : (CFG.evidence.some(e => e.sev === "CRITICAL") ? "#22d3ee" : "#818cf8");

        // Left & Right 3D neural layer nodes
        const sigNodes = CFG.signals.map((s, idx) => {{
          const n = CFG.signals.length;
          const y = (idx - (n - 1) / 2) * 46;
          const z = Math.sin(idx * 1.4) * 45;
          return {{ ...s, x: -205, y, z, color: "#22d3ee", side: "INPUT" }};
        }});
        const evNodes = CFG.evidence.map((e, idx) => {{
          const n = CFG.evidence.length;
          const y = (idx - (n - 1) / 2) * 44;
          const z = Math.cos(idx * 1.3) * 48;
          return {{ ...e, x: 205, y, z, color: SEV_COLOR[e.sev] || "#10b981", side: "EVIDENCE" }};
        }});

        function proj(x, y, z, extraYaw = 0, extraPitch = 0) {{
          const cy = Math.cos(yaw + extraYaw), sy = Math.sin(yaw + extraYaw);
          const cp = Math.cos(pitch + extraPitch), sp = Math.sin(pitch + extraPitch);
          const x1 = x * cy - z * sy;
          const z1 = x * sy + z * cy;
          const y2 = y * cp - z1 * sp;
          const z2 = y * sp + z1 * cp;
          const fov = 560 * zoom;
          const sc = fov / (fov + z2 + 240);
          return {{ sx: W / 2 + x1 * sc, sy: H / 2 + y2 * sc, sc, z: z2 }};
        }}

        function drawDiamond(sx, sy, r, color) {{
          ctx.beginPath();
          ctx.moveTo(sx, sy - r);
          ctx.lineTo(sx + r * 0.85, sy);
          ctx.lineTo(sx, sy + r);
          ctx.lineTo(sx - r * 0.85, sy);
          ctx.closePath();
          const g = ctx.createLinearGradient(sx - r, sy - r, sx + r, sy + r);
          g.addColorStop(0, "#ffffff");
          g.addColorStop(0.35, color);
          g.addColorStop(1, "#060a18");
          ctx.fillStyle = g;
          ctx.shadowColor = color;
          ctx.shadowBlur = 14;
          ctx.fill();
          ctx.shadowBlur = 0;
          ctx.strokeStyle = "#ffffff55";
          ctx.lineWidth = 1;
          ctx.stroke();
        }}

        let t = 0;
        function render() {{
          t += 0.02;
          if (spinning && !dragging) yaw += 0.0028;
          ctx.clearRect(0, 0, W, H);

          // Perspective horizon grid
          ctx.strokeStyle = "rgba(129, 140, 248, 0.08)";
          ctx.lineWidth = 1;
          for (let g = -240; g <= 240; g += 60) {{
            const a = proj(g, 118, -180), b = proj(g, 118, 180);
            ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy); ctx.stroke();
            const c = proj(-240, 118, g * 0.75), d = proj(240, 118, g * 0.75);
            ctx.beginPath(); ctx.moveTo(c.sx, c.sy); ctx.lineTo(d.sx, d.sy); ctx.stroke();
          }}

          // Holographic 3D Gyroscope Rings around core
          for (let ring = 0; ring < 3; ring++) {{
            const rad = 84 + ring * 13;
            const tiltX = ring * 0.72 + t * (ring % 2 === 0 ? 0.35 : -0.28);
            const tiltY = ring * 1.1 - t * 0.22;
            ctx.beginPath();
            for (let k = 0; k <= 48; k++) {{
              const ang = (k / 48) * Math.PI * 2;
              const rx = Math.cos(ang) * rad;
              const ry = Math.sin(ang) * rad * Math.cos(tiltX);
              const rz = Math.sin(ang) * rad * Math.sin(tiltX);
              const p = proj(rx * Math.cos(tiltY) - rz * Math.sin(tiltY), ry, rx * Math.sin(tiltY) + rz * Math.cos(tiltY));
              if (k === 0) ctx.moveTo(p.sx, p.sy); else ctx.lineTo(p.sx, p.sy);
            }}
            ctx.strokeStyle = ring === 0 ? "rgba(34,211,238,0.28)" : (ring === 1 ? "rgba(129,140,248,0.25)" : "rgba(16,185,129,0.22)");
            ctx.lineWidth = 1.25;
            ctx.stroke();
          }}

          const centerP = proj(0, 0, 0);

          // Neural Synapses: Inputs -> Core -> Evidence
          const projInputs = sigNodes.map((n, i) => ({{ n, p: proj(n.x, n.y + Math.sin(t + i) * 4, n.z) }}));
          const projEvs = evNodes.map((n, i) => ({{ n, p: proj(n.x, n.y + Math.cos(t + i) * 4, n.z) }}));

          for (let i = 0; i < projInputs.length; i++) {{
            const {{ n, p }} = projInputs[i];
            ctx.beginPath(); ctx.moveTo(p.sx, p.sy); ctx.lineTo(centerP.sx, centerP.sy);
            ctx.strokeStyle = "rgba(34, 211, 238, 0.32)"; ctx.lineWidth = 1.4; ctx.stroke();
            const f = (t * 0.65 + i * 0.23) % 1;
            const px = p.sx + (centerP.sx - p.sx) * f, py = p.sy + (centerP.sy - p.sy) * f;
            ctx.beginPath(); ctx.arc(px, py, 2.6, 0, Math.PI * 2);
            ctx.fillStyle = "#67e8f9"; ctx.fill();
          }}
          for (let i = 0; i < projEvs.length; i++) {{
            const {{ n, p }} = projEvs[i];
            ctx.beginPath(); ctx.moveTo(centerP.sx, centerP.sy); ctx.lineTo(p.sx, p.sy);
            ctx.strokeStyle = n.color + "66"; ctx.lineWidth = 1.6; ctx.stroke();
            const f = (t * 0.65 + i * 0.19) % 1;
            const px = centerP.sx + (p.sx - centerP.sx) * f, py = centerP.sy + (p.sy - centerP.sy) * f;
            ctx.beginPath(); ctx.arc(px, py, 2.8, 0, Math.PI * 2);
            ctx.fillStyle = "#ffffff"; ctx.shadowColor = n.color; ctx.shadowBlur = 8; ctx.fill(); ctx.shadowBlur = 0;
          }}

          // Inner Counter-Rotating 3D Tesseract Cube
          const cProj = cubeVerts.map(v => proj(v[0], v[1], v[2], -t * 0.9, t * 0.55));
          ctx.strokeStyle = "rgba(34, 211, 238, 0.72)";
          ctx.lineWidth = 1.5;
          for (const [a, b] of cubeEdges) {{
            ctx.beginPath(); ctx.moveTo(cProj[a].sx, cProj[a].sy); ctx.lineTo(cProj[b].sx, cProj[b].sy); ctx.stroke();
          }}

          // Outer Rotating 3D Icosahedron Neural Mesh
          const iProj = rawVerts.map(v => proj(v[0], v[1], v[2], t * 0.55, t * 0.25));
          ctx.strokeStyle = coreColor;
          ctx.lineWidth = 1.6;
          ctx.shadowColor = coreColor;
          ctx.shadowBlur = 10;
          for (const [a, b] of icoEdges) {{
            ctx.beginPath(); ctx.moveTo(iProj[a].sx, iProj[a].sy); ctx.lineTo(iProj[b].sx, iProj[b].sy); ctx.stroke();
          }}
          ctx.shadowBlur = 0;
          for (const vp of iProj) {{
            ctx.beginPath(); ctx.arc(vp.sx, vp.sy, 2.6 * vp.sc, 0, Math.PI * 2);
            ctx.fillStyle = "#e0e7ff"; ctx.fill();
          }}

          // Draw Layer Nodes + Hover Check
          let hovered = null;
          const allNodes = [...projInputs, ...projEvs].sort((a, b) => b.p.z - a.p.z);
          for (const it of allNodes) {{
            const rad = (it.n.side === "EVIDENCE" ? 13 : 11.5) * it.p.sc;
            drawDiamond(it.p.sx, it.p.sy, rad, it.n.color);
            ctx.fillStyle = "#e2e8f0";
            ctx.font = "600 10.5px JetBrains Mono, monospace";
            ctx.textAlign = "center";
            ctx.fillText(it.n.label, it.p.sx, it.p.sy + rad + 13);
            if (Math.hypot(mx - it.p.sx, my - it.p.sy) <= rad + 8) hovered = it;
          }}

          if (hovered) {{
            tip.style.display = "block";
            tip.style.left = Math.min(W - 265, Math.max(10, hovered.p.sx + 14)) + "px";
            tip.style.top = Math.min(H - 95, Math.max(10, hovered.p.sy - 14)) + "px";
            tip.innerHTML = `<strong style="color:${{hovered.n.color}}">${{escJs(hovered.n.label)}}</strong><br>${{hovered.n.detail || ""}}`;
          }} else {{
            tip.style.display = "none";
          }}

          requestAnimationFrame(render);
        }}
        render();
      </script>
    </body>
    </html>
    """
    components.html(html_doc, height=height + 8, scrolling=False)


ASSISTANT_FAQS_PRIMARY = [
    ("🚨 Incidents", "What are the most critical incidents?"),
    ("💥 DB Fail", "Why is the database failing?"),
    ("🌐 Services", "Which services are affected?"),
    ("🩺 Health", "How was the health score calculated?"),
    ("⚡ Risk", "What factors increased the infrastructure risk score?"),
    ("🛠️ Recovery", "What recovery steps are recommended?"),
]

ASSISTANT_FAQS_EXTRA = [
    ("📋 Summarize Logs", "Summarize the logs"),
    ("⏱️ Outage Timeline", "What happened first in the timeline?"),
    ("🧠 Memory & OOM Logs", "Find logs related to memory exhaustion."),
    ("📑 Supporting Evidence", "Show the evidence supporting this suspected root cause."),
    ("🛡️ Test Anti-Hallucination", "What is the GPU thermal throttling temperature?"),
]


def render_assistant_faq_grid(key_prefix: str) -> Optional[str]:
    """Renders a compact single-row FAQ pill bar + 'More' popover for the AI Assistant."""
    selected: Optional[str] = None
    cols = st.columns([1, 1, 1, 1, 1, 1, 0.9])
    for idx, (label, prompt_text) in enumerate(ASSISTANT_FAQS_PRIMARY):
        if cols[idx].button(label, use_container_width=True, key=f"{key_prefix}_faq_{idx}"):
            selected = prompt_text

    with cols[6]:
        with st.popover("❓ More", use_container_width=True):
            st.caption("More FAQ & Verification Prompts")
            for idx, (label, prompt_text) in enumerate(ASSISTANT_FAQS_EXTRA):
                if st.button(label, use_container_width=True, key=f"{key_prefix}_faq_ex_{idx}"):
                    selected = prompt_text
    return selected


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
