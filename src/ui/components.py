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
        /* Main Background and Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        html, body, [class*="st-"] {
            font-family: 'Inter', sans-serif;
        }

        /* Glassmorphism Card Structure */
        .premium-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 20px;
            transition: transform 0.3s ease;
        }
        
        .premium-card:hover {
            transform: translateY(-5px);
            border-color: rgba(255, 255, 255, 0.2);
        }

        /* Verdict Badges */
        .badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .badge-supported { background-color: #00C851; color: white; }
        .badge-refuted { background-color: #ff4444; color: white; }
        .badge-insufficient { background-color: #ffbb33; color: black; }

        /* Metric Cards */
        .metric-container {
            background: linear-gradient(135deg, #1e1e2f 0%, #252540 100%);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid #3f3f5f;
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
                <div style="background: rgba(255,255,255,0.03); border-radius: 10px; padding: 15px; border-left: 4px solid {score_color}; height: 100%;">
                    <h5 style="margin: 0;">{e.title}</h5>
                    <p style="font-size: 0.8em; color: {score_color}; font-weight: bold;">Credibility: {cred.score if cred else 'N/A'}</p>
                    <p style="font-size: 0.9em; opacity: 0.8;">{e.text[:200]}...</p>
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
            import json
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
