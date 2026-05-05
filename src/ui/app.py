import sys
from pathlib import Path

# Add project root to Python path
root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

import streamlit as st
import uuid
from src.orchestrator import run
from src.ui.components import render_per_claim, render_metrics_tab, inject_custom_css

# --- PIPELINE WRAPPER ---
def run_pipeline(user_input: str):
    """Calls the real orchestrator with a fallback to mock on any failure."""
    try:
        return run(user_input), False
    except (NotImplementedError, Exception) as e:
        # Fallback to mock if orchestrator is not ready or fails (e.g. missing API key)
        from src.safety.mock_pipeline import mock_run
        return mock_run(user_input), True

# --- STREAMLIT APP ---
st.set_page_config(page_title="SciCheck AI", page_icon="🔬", layout="wide")

# Inject premium CSS at the start
inject_custom_css()

# Custom Title with Emoji and Subtitle
st.markdown("""
    <div style="text-align: center; padding: 40px 0 50px 0;">
        <h1 class="text-glow" style="font-size: 4.5em; font-weight: 800; margin-bottom: 0; letter-spacing: -2px;">
            🔬 SciCheck <span style="background: linear-gradient(135deg, #646cff 0%, #00C851 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AI</span>
        </h1>
        <p style="font-size: 1.3em; opacity: 0.8; font-weight: 300; letter-spacing: 1px; margin-top: 10px;">
            Advanced Multi-Agent Scientific Fact-Checking System
        </p>
    </div>
""", unsafe_allow_html=True)

tab_check, tab_metrics, tab_safety = st.tabs(["Fact-Check", "Metrics", "Safety Log"])

with tab_check:
    # Sidebar for Demo Claims
    with st.sidebar:
        st.markdown("<h3 style='margin-bottom: 20px;'>🧪 Demo Examples</h3>", unsafe_allow_html=True)
        examples = [
            "Non-CpG cytosine methylation is the major type of methylation in human PBMC cells.",
            "Exposure to sunlight influences the cutaneous production of vitamin D.",
            "Vitamin C prevents the common cold.",
        ]
        for ex in examples:
            if st.button(ex, use_container_width=True):
                st.session_state["claim_input"] = ex
                st.session_state["main_input"] = ex
                st.rerun()

    # Input Area
    user_input = st.text_area(
        "Enter a claim to analyze:",
        value=st.session_state.get("claim_input", ""),
        placeholder="e.g. Non-CpG cytosine methylation is the major type of methylation in human PBMC cells.",
        height=120,
        key="main_input",
        label_visibility="collapsed"
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_btn = st.button("🚀 Analyze Claim", type="primary", use_container_width=True)

    if analyze_btn:
        if user_input.strip():
            st.divider()
            st.markdown("<h3 style='text-align: center; margin-bottom: 30px;'>🧠 AI Agent Pipeline Active</h3>", unsafe_allow_html=True)
            
            # Premium Pipeline Simulation
            pipeline_container = st.empty()
            
            steps = [
                ("🤖 Claim Extractor", "Analyzing input and breaking down atomic claims...", 25),
                ("🔍 Evidence Retriever", "Querying ChromaDB for scientific literature...", 50),
                ("⚖️ Verdict Synthesizer", "Weighing evidence and calculating credibility...", 75),
                ("🛡️ Safety Monitor", "Screening for bias, hallucinations, and formatting...", 100)
            ]
            
            import time
            for icon, desc, prog in steps:
                pipeline_container.markdown(f"""
                    <div class="premium-card agent-step-active" style="display: flex; align-items: center; gap: 20px; padding: 20px 30px;">
                        <div style="font-size: 2.5em;">{icon.split(' ')[0]}</div>
                        <div>
                            <h4 style="margin: 0; color: #E2E8F0;">{icon.split(' ', 1)[1]}</h4>
                            <p style="margin: 5px 0 0 0; color: #94A3B8; font-size: 0.9em;">{desc}</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                time.sleep(0.7)
            
            # Clear pipeline animation
            pipeline_container.empty()
            
            # Get the response
            with st.spinner("Finalizing results..."):
                response, is_mock = run_pipeline(user_input)

            if is_mock:
                st.warning("⚠️ Orchestrator (Member 1) not yet implemented. Running in **Mock Mode** using heuristic logic.")

            st.divider()
            st.success(f"Analysis Complete! (Trace ID: {response.trace_id})")
            
            for pcr in response.per_claim:
                render_per_claim(pcr)
        else:
            st.warning("Please enter a claim first.")

with tab_metrics:
    st.header("Model Performance")
    mock_metrics = {
        "accuracy": 0.82,
        "macro_f1": 0.795,
        "citation_precision": 0.88,
        "per_class_f1": [0.85, 0.78, 0.75]
    }
    render_metrics_tab(mock_metrics)

with tab_safety:
    st.header("Safety & Guardrail Logs")
    st.info("This tab will show logs of flagged claims (hallucinations, bias, etc.)")
    st.dataframe([
        {"timestamp": "2026-05-03 14:20", "claim": "...", "passed": False, "flags": ["hallucination"]},
        {"timestamp": "2026-05-03 15:10", "claim": "...", "passed": True, "flags": []}
    ])
