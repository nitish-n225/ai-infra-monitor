"""
Custom UI Components and Styling for Streamlit.
"""
import streamlit as st

def apply_custom_styles():
    """Applies modern dark-mode enterprise CSS styling to the Streamlit app."""
    st.markdown(
        """
        <style>
        /* Modern Typography & Dark Slate Palette */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* Metric Card Container */
        .metric-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.85));
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 1.1rem 1.25rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            border-color: rgba(6, 182, 212, 0.4);
        }
        .metric-label {
            font-size: 0.72rem;
            font-weight: 700;
            color: #94a3b8;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }
        .metric-value {
            font-size: 1.85rem;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            color: #f8fafc;
            line-height: 1.2;
        }
        .metric-desc {
            font-size: 0.75rem;
            color: #64748b;
            margin-top: 0.25rem;
        }

        /* Stage Badges */
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

        /* Critical Banner */
        .critical-banner {
            background: linear-gradient(90deg, rgba(239, 68, 68, 0.12), rgba(239, 68, 68, 0.04));
            border-left: 4px solid #ef4444;
            border-radius: 8px;
            padding: 0.85rem 1.1rem;
            margin-bottom: 1rem;
        }

        /* Info Box */
        .info-card {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 10px;
            padding: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def render_metric_card(label: str, value: Any, subtext: str = "", color: str = "#f8fafc"):
    """Renders a styled metric card."""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color: {color};">{value}</div>
            <div class="metric-desc">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_stage_badge(stage_name: str, status: str):
    """Renders a stage indicator badge."""
    css_class = "stage-active" if status == "COMPLETED" else "stage-upcoming"
    icon = "✓" if status == "COMPLETED" else "⏱"
    st.markdown(
        f"""
        <span class="stage-pill {css_class}">
            <span>{icon}</span> {stage_name}: {status}
        </span>
        """,
        unsafe_allow_html=True
    )
