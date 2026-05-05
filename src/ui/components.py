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
        /* Modern Typography */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
        
        html, body, [class*="st-"] {
            font-family: 'Outfit', sans-serif !important;
        }

        /* Dark Premium Background */
        .stApp {
            background-color: #0B0E14;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(100, 108, 255, 0.1) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(0, 200, 81, 0.05) 0%, transparent 40%);
        }

        /* Hide Streamlit default elements for a cleaner app look */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {background: transparent !important;}

        /* Glassmorphism Cards */
        .premium-card {
            background: rgba(20, 24, 34, 0.6);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            margin-bottom: 25px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        
        .premium-card:hover {
            transform: translateY(-8px);
            border-color: rgba(100, 108, 255, 0.3);
            box-shadow: 0 15px 40px 0 rgba(100, 108, 255, 0.15);
        }

        /* Glowing Text Effect */
        .text-glow {
            text-shadow: 0 0 20px rgba(100, 108, 255, 0.6);
        }

        /* Badges */
        .badge {
            padding: 8px 16px;
            border-radius: 30px;
            font-weight: 700;
            font-size: 0.8em;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            display: inline-block;
        }
        
        .badge-supported { 
            background: linear-gradient(135deg, #00C851 0%, #007E33 100%);
            color: white; 
            border: 1px solid rgba(0,200,81,0.4);
        }
        .badge-refuted { 
            background: linear-gradient(135deg, #ff4444 0%, #CC0000 100%);
            color: white; 
            border: 1px solid rgba(255,68,68,0.4);
        }
        .badge-insufficient { 
            background: linear-gradient(135deg, #ffbb33 0%, #FF8800 100%);
            color: black; 
            border: 1px solid rgba(255,187,51,0.4);
        }

        /* Metric Cards */
        .metric-container {
            background: rgba(20, 24, 34, 0.8);
            border-radius: 16px;
            padding: 25px 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.05);
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            position: relative;
            overflow: hidden;
        }
        
        .metric-container::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 3px;
            background: linear-gradient(90deg, #646cff, #00C851);
        }

        .metric-container h3 {
            font-size: 2.5em;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(135deg, #ffffff 0%, #a0a5ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .metric-container p {
            color: #8892b0;
            font-size: 0.9em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 10px;
        }
        
        /* Agent Step Animations */
        @keyframes pulse-glow {
            0% { opacity: 0.6; transform: scale(0.98); }
            50% { opacity: 1; transform: scale(1.02); filter: drop-shadow(0 0 10px rgba(100, 108, 255, 0.5)); }
            100% { opacity: 0.6; transform: scale(0.98); }
        }
        
        .agent-step-active {
            animation: pulse-glow 1.5s infinite ease-in-out;
            border-left: 4px solid #646cff !important;
            background: rgba(100, 108, 255, 0.1) !important;
        }
        </style>
    """, unsafe_allow_html=True)

def render_per_claim(pcr: PerClaimResult) -> None:
    inject_custom_css()
    
    color = LABEL_COLORS.get(pcr.verdict.label, "gray")
    badge_class = f"badge-{pcr.verdict.label.lower().replace(' ', '-')}"
    
    # Claim Header
    st.markdown(f"""
        <div class="premium-card">
            <span class="badge {badge_class}">{pcr.verdict.label}</span>
            <h2 style="margin-top: 15px; font-weight: 700;">{pcr.claim.text}</h2>
            <p style="color: #aaa; font-style: italic;">Scientific Analysis — Confidence: {pcr.verdict.confidence:.2%}</p>
            <hr style="border-color: rgba(255,255,255,0.1);">
            <h4>Analysis Reasoning</h4>
            <p style="line-height: 1.6;">{pcr.verdict.reasoning}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Evidence Section
    st.markdown("### 📚 Supporting Evidence")
    cols = st.columns(len(pcr.evidence) if pcr.evidence else 1)
    
    cred_map = {s.source_id: s for s in pcr.credibility.scored_sources}
    
    for i, e in enumerate(pcr.evidence):
        with cols[i]:
            cred = cred_map.get(e.source_id)
            score_color = "#00C851" if (cred and cred.score > 0.8) else "#ffbb33"
            
            st.markdown(f"""
                <div style="background: rgba(20, 24, 34, 0.8); border-radius: 16px; padding: 20px; border: 1px solid rgba(255,255,255,0.05); border-left: 4px solid {score_color}; height: 100%; box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: all 0.3s ease;" onmouseover="this.style.transform='translateY(-3px)'; this.style.borderColor='rgba(255,255,255,0.1)'" onmouseout="this.style.transform='translateY(0)'; this.style.borderColor='rgba(255,255,255,0.05)'">
                    <h5 style="margin: 0; font-size: 1.1em; color: #E2E8F0; line-height: 1.4;">{e.title}</h5>
                    <div style="margin: 12px 0;">
                        <span style="background: rgba({ '0,200,81' if score_color == '#00C851' else '255,187,51' }, 0.1); color: {score_color}; padding: 4px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 700; letter-spacing: 0.5px; border: 1px solid rgba({ '0,200,81' if score_color == '#00C851' else '255,187,51' }, 0.2);">
                            CREDIBILITY SCORE: {cred.score if cred else 'N/A'}
                        </span>
                    </div>
                    <p style="font-size: 0.95em; color: #94A3B8; line-height: 1.6; margin-bottom: 0;">{e.text[:200]}...</p>
                </div>
            """, unsafe_allow_html=True)

    # Safety
    if not pcr.safety.passed:
        st.warning(f"🛡️ **Safety Flag:** {', '.join(pcr.safety.flags)}\n\n{pcr.safety.notes}")

def render_metrics_tab(data: dict | None = None) -> None:
    inject_custom_css()
    st.markdown("### 📊 System Performance Metrics")
    
    if data is None:
        p = Path("eval/results.json")
        if not p.exists():
            st.info("📊 Evaluation results are not available yet. Run `python scripts/run_eval.py 200` to generate results.")
            return
        try:
            data = json.loads(p.read_text())
        except Exception as e:
            st.error(f"Could not read results file: {e}")
            return

    if "error" in data:
        st.error(f"❌ Evaluation error: {data['error']}")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metric-container"><h3>{data.get("accuracy", 0):.1%}</h3><p>Accuracy</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-container"><h3>{data.get("macro_f1", 0):.3f}</h3><p>Macro F1</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-container"><h3>{data.get("citation_precision", 0):.1%}</h3><p>Citation Prec.</p></div>', unsafe_allow_html=True)
    
    st.write("")
    st.markdown("#### Performance by Class")
    if 'per_class_f1' in data:
        st.bar_chart(data['per_class_f1'])
    
    st.divider()
    st.subheader("Raw Data")
    st.json(data)
