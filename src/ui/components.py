"""
Custom UI Components and Design System for Enterprise AI Infrastructure Monitor.
"""
import html
from typing import Any, Optional
import streamlit as st


def esc(value: Any) -> str:
    """Escapes untrusted text safely before embedding in HTML fragments."""
    return html.escape("" if value is None else str(value), quote=True)


def apply_custom_styles() -> None:
    """Applies a clean, modern dark AIOps design system to the Streamlit app."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {
            --bg-root: #090d16;
            --bg-surface: rgba(17, 24, 39, 0.78);
            --bg-surface-strong: rgba(15, 23, 42, 0.94);
            --border-subtle: rgba(148, 163, 184, 0.14);
            --border-accent: rgba(34, 211, 238, 0.35);
            --text-primary: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-cyan: #22d3ee;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #ef4444;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* Clean up unnecessary Streamlit chrome */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        [data-testid="stDecoration"] { display: none; }
        .stDeployButton { display: none; }

        .stApp {
            background:
                radial-gradient(circle at 12% 0%, rgba(34, 211, 238, 0.08), transparent 36%),
                radial-gradient(circle at 88% 8%, rgba(16, 185, 129, 0.06), transparent 32%),
                var(--bg-root);
        }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2.5rem;
            max-width: 1400px;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b1120 0%, #090d16 100%);
            border-right: 1px solid var(--border-subtle);
        }

        /* Modern Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.45rem;
            background: rgba(15, 23, 42, 0.65);
            padding: 0.35rem;
            border-radius: 12px;
            border: 1px solid var(--border-subtle);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 0.45rem 0.95rem;
            font-weight: 600;
            font-size: 0.86rem;
            color: var(--text-muted);
            border: none;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(34, 211, 238, 0.16), rgba(56, 189, 248, 0.08)) !important;
            color: #e0f2fe !important;
            border: 1px solid rgba(34, 211, 238, 0.32) !important;
        }
        .stTabs [data-baseweb="tab-highlight"] {
            display: none;
        }

        /* Buttons & Inputs */
        .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
            border-radius: 9px;
            font-weight: 600;
            border: 1px solid var(--border-subtle);
            transition: all 0.18s ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            border-color: var(--border-accent);
            transform: translateY(-1px);
        }

        /* Hero Command Header */
        .hero-header {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            background: linear-gradient(135deg, rgba(17, 24, 39, 0.88), rgba(15, 23, 42, 0.95));
            border: 1px solid var(--border-subtle);
            border-radius: 14px;
            padding: 1.05rem 1.35rem;
            margin-bottom: 1.15rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.28);
        }
        .hero-title {
            font-size: 1.35rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: var(--text-primary);
            margin: 0;
        }
        .hero-subtitle {
            font-size: 0.84rem;
            color: var(--text-muted);
            margin-top: 0.2rem;
        }

        /* Metric & Glass Cards */
        .metric-card {
            background: linear-gradient(145deg, var(--bg-surface), var(--bg-surface-strong));
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 1rem 1.15rem;
            box-shadow: 0 6px 22px rgba(0, 0, 0, 0.24);
            transition: transform 0.18s ease, border-color 0.18s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            border-color: var(--border-accent);
        }
        .metric-label {
            font-size: 0.7rem;
            font-weight: 700;
            color: var(--text-muted);
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }
        .metric-value {
            font-size: 1.75rem;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-primary);
            line-height: 1.15;
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
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid var(--border-subtle);
            border-radius: 10px;
            padding: 0.55rem 0.95rem;
            margin-bottom: 1rem;
            font-size: 0.8rem;
        }

        /* Resource Progress Bar */
        .res-row {
            margin-top: 0.35rem;
        }
        .res-head {
            display: flex;
            justify-content: space-between;
            font-size: 0.74rem;
            color: #cbd5e1;
            margin-bottom: 0.15rem;
        }
        .res-track {
            width: 100%;
            height: 6px;
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.14);
            overflow: hidden;
        }
        .res-fill {
            height: 100%;
            border-radius: 999px;
            transition: width 0.25s ease;
        }

        /* Status Pills */
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.22rem 0.68rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.03em;
        }

        /* Critical Banner */
        .critical-banner {
            background: linear-gradient(90deg, rgba(239, 68, 68, 0.13), rgba(239, 68, 68, 0.03));
            border: 1px solid rgba(239, 68, 68, 0.22);
            border-left: 4px solid #ef4444;
            border-radius: 10px;
            padding: 0.85rem 1.05rem;
            margin-bottom: 0.75rem;
        }

        /* Stage Badges (kept for compatibility) */
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
    """Renders the top command-center header with a live connection badge."""
    pill_fg = "#10b981" if status_ok else "#f59e0b"
    pill_bg = "rgba(16, 185, 129, 0.14)" if status_ok else "rgba(245, 158, 11, 0.14)"
    dot = "●"
    st.markdown(
        f"""
        <div class="hero-header">
            <div>
                <div class="hero-title">🛡️ {esc(title)}</div>
                <div class="hero-subtitle">{esc(subtitle)}</div>
            </div>
            <div>
                <span class="status-pill" style="color:{pill_fg}; background:{pill_bg}; border:1px solid {pill_fg}55;">
                    <span>{dot}</span> {esc(status_label)}
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
    """Renders a styled KPI metric card."""
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


def resource_bar_html(label: str, value_pct: Optional[float]) -> str:
    """Returns compact HTML for a color-coded CPU/RAM/Disk utilization bar."""
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
        f"<div class='res-track'><div class='res-fill' style='width:{clamped:.1f}%; background:{bar_color};'></div></div></div>"
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
