from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from src.contracts import PerClaimResult

LABEL_COLORS = {
    "Supported": "green",
    "Refuted": "red",
    "Insufficient Evidence": "orange",
}

def inject_custom_css():
    st.markdown("""
        <style>
        /* Import Design System Fonts & Icons */
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');
        
        html, body, [class*="st-"] {
            font-family: 'Space Grotesk', sans-serif !important;
        }

        /* Deep Space Theme */
        .stApp {
            background-color: #0A0E14;
            background-image: 
                url("data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGcgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMDUpIiBzdHJva2Utd2lkdGg9IjEiIGZpbGw9Im5vbmUiPjxwb2x5Z29uIHBvaW50cz0iMzAsMCA2MCwzMCAzMCw2MCAwLDMwIi8+PC9nPjwvc3ZnPg==");
            background-size: 120px 120px;
        }

        /* Hide Streamlit components */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {background: transparent !important;}

        /* Sharp Glass Panels (0px radius as per Design system) */
        .glass-panel {
            background: rgba(18, 24, 38, 0.4);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(60, 73, 78, 0.3);
            box-shadow: inset 0 0 20px rgba(0, 212, 255, 0.05);
            border-radius: 0px !important;
            padding: 24px;
            margin-bottom: 20px;
        }
        
        .glass-panel-glow {
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.2), inset 0 0 20px rgba(0, 212, 255, 0.1);
            border-color: rgba(0, 212, 255, 0.5) !important;
        }

        /* AI Scanner Animation */
        .ai-scanner {
            height: 2px;
            width: 100%;
            background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.8), transparent);
            box-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
            position: absolute;
            z-index: 10;
            animation: scan 3s infinite ease-in-out;
        }
        
        @keyframes scan {
            0% { top: 0%; }
            50% { top: 100%; }
            100% { top: 0%; }
        }

        /* Badges & Status */
        .status-chip {
            padding: 4px 12px;
            border-radius: 0px;
            font-weight: 700;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .status-supported { 
            background: rgba(0, 245, 155, 0.1);
            color: #00F59B;
            border-color: rgba(0, 245, 155, 0.3);
            box-shadow: 0 0 10px rgba(0, 245, 155, 0.1);
        }
        .status-refuted { 
            background: rgba(255, 68, 68, 0.1);
            color: #FF4444;
            border-color: rgba(255, 68, 68, 0.3);
        }

        /* Streamlit Widget Overrides */
        div[data-baseweb="textarea"] {
            background-color: rgba(10, 14, 20, 0.6) !important;
            border: 1px solid rgba(60, 73, 78, 0.3) !important;
            border-radius: 0px !important;
        }
        
        button[data-testid="baseButton-primary"] {
            background-color: #00D4FF !important;
            color: #000000 !important;
            border-radius: 0px !important;
            border: none !important;
            font-weight: 700 !important;
            letter-spacing: 0.05em !important;
            text-transform: uppercase !important;
            width: 100%;
        }
        
        button[data-testid="baseButton-secondary"] {
            background-color: transparent !important;
            border: 1px solid rgba(0, 212, 255, 0.3) !important;
            color: #00D4FF !important;
            border-radius: 0px !important;
            transition: all 0.3s ease !important;
        }
        
        button[data-testid="baseButton-secondary"]:hover {
            border-color: #00D4FF !important;
            background-color: rgba(0, 212, 255, 0.05) !important;
        }

        /* Agent Step Style */
        .agent-node {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
            padding: 15px;
            border: 1px solid rgba(60, 73, 78, 0.2);
            transition: all 0.3s ease;
        }
        
        .agent-node-active {
            border-color: #00D4FF;
            background: rgba(0, 212, 255, 0.05);
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.1);
        }
        </style>
    """, unsafe_allow_html=True)

def render_per_claim(pcr: PerClaimResult) -> None:
    inject_custom_css()
    
    badge_class = f"status-{pcr.verdict.label.lower().replace(' ', '-')}"
    status_icon = "verified" if pcr.verdict.label == "Supported" else "cancel" if pcr.verdict.label == "Refuted" else "balance"
    
    # Claim Header
    st.markdown(f"""
        <div class="glass-panel glass-panel-glow">
            <div class="status-chip {badge_class}">
                <span class="material-symbols-outlined" style="font-size: 16px;">{status_icon}</span>
                {pcr.verdict.label}
            </div>
            <h2 style="margin-top: 20px; font-weight: 700; font-size: 28px; color: #dfe2eb; letter-spacing: -0.01em;">{pcr.claim.text}</h2>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.05);">
                <p style="color: #859398; font-size: 14px; text-transform: uppercase; letter-spacing: 0.1em; margin: 0;">PRECISION ANALYSIS</p>
                <p style="color: #00D4FF; font-weight: 700; margin: 0;">CONFIDENCE: {pcr.verdict.confidence:.1%}</p>
            </div>
            <div style="margin-top: 25px;">
                <h4 style="color: #a8e8ff; font-size: 14px; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 10px;">REASONING ENGINE OUTPUT</h4>
                <p style="line-height: 1.6; color: #bbc9cf;">{pcr.verdict.reasoning}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Evidence Section
    st.markdown("<h4 style='color: #dfe2eb; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 20px;'>📚 VERIFICATION SOURCES</h4>", unsafe_allow_html=True)
    cols = st.columns(len(pcr.evidence) if pcr.evidence else 1)
    
    cred_map = {s.source_id: s for s in pcr.credibility.scored_sources}
    
    for i, e in enumerate(pcr.evidence):
        with cols[i]:
            cred = cred_map.get(e.source_id)
            is_high = cred and cred.score > 0.8
            score_color = "#00F59B" if is_high else "#FF8800"
            
            st.markdown(f"""
                <div class="glass-panel" style="padding: 20px; border-top: 2px solid {score_color}; height: 100%;">
                    <h5 style="margin: 0; font-size: 16px; color: #dfe2eb; line-height: 1.4;">{e.title}</h5>
                    <div style="margin: 15px 0;">
                        <span style="color: {score_color}; font-size: 12px; font-weight: 700; letter-spacing: 0.05em; border: 1px solid {score_color}44; padding: 2px 8px;">
                            CREDIBILITY: {cred.score if cred else 'N/A'}
                        </span>
                    </div>
                    <p style="font-size: 14px; color: #859398; line-height: 1.6; margin-bottom: 0;">{e.text[:200]}...</p>
                </div>
            """, unsafe_allow_html=True)

    # Safety
    if not pcr.safety.passed:
        st.error(f"⚠️ **SAFETY ALERT:** {', '.join(pcr.safety.flags).upper()}\n\n{pcr.safety.notes}")

def render_metrics_tab(data: dict | None = None) -> None:
    inject_custom_css()
    st.markdown("<h3 style='text-transform: uppercase; letter-spacing: 0.1em;'>📊 SYSTEM ANALYTICS</h3>", unsafe_allow_html=True)
    
    if data is None:
        p = Path("eval/results.json")
        if not p.exists():
            st.info("📊 Evaluation results are not available yet.")
            return
        try:
            data = json.loads(p.read_text())
        except Exception as e:
            st.error(f"Error: {e}")
            return

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="glass-panel" style="text-align: center;"><h3 style="color: #00D4FF; font-size: 40px; margin: 0;">{data.get("accuracy", 0):.1%}</h3><p style="color: #859398; font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em; margin: 10px 0 0 0;">Accuracy</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="glass-panel" style="text-align: center;"><h3 style="color: #00D4FF; font-size: 40px; margin: 0;">{data.get("macro_f1", 0):.3f}</h3><p style="color: #859398; font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em; margin: 10px 0 0 0;">Macro F1</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="glass-panel" style="text-align: center;"><h3 style="color: #00D4FF; font-size: 40px; margin: 0;">{data.get("citation_precision", 0):.1%}</h3><p style="color: #859398; font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em; margin: 10px 0 0 0;">Citation Prec.</p></div>', unsafe_allow_html=True)
    
    if 'per_class_f1' in data:
        st.bar_chart(data['per_class_f1'])
