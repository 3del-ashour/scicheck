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
st.set_page_config(page_title="SciCheck - Command Center", page_icon="🔬", layout="wide")

# Inject premium CSS at the start
inject_custom_css()

# Top App Bar style header
st.markdown("""
    <div style="width: 100%; margin-bottom: 40px; padding-bottom: 15px;">
        <div style="font-family: 'Space Grotesk'; font-size: 42px; font-weight: 700; color: #00D4FF; letter-spacing: -1.5px; line-height: 1;">
            SciCheck
        </div>
        <div style="font-family: 'Space Grotesk'; font-size: 14px; color: #859398; margin-top: 8px; letter-spacing: 0.5px; font-weight: 400; opacity: 0.8;">
            Advanced Multi-Agent Scientific Fact-Checking System
        </div>
    </div>
""", unsafe_allow_html=True)

tab_check, tab_metrics, tab_safety = st.tabs(["[ VERIFY ]", "[ ANALYTICS ]", "[ SAFETY ]"])

with tab_check:
    # Sidebar for Demo Claims
    with st.sidebar:
        st.markdown("<p style='font-size: 12px; color: #859398; font-weight: 700; letter-spacing: 0.2em; margin-bottom: 15px;'>CORE DATASETS</p>", unsafe_allow_html=True)
        examples = [
            "Non-CpG cytosine methylation is the major type of methylation in human PBMC cells.",
            "Exposure to sunlight influences the cutaneous production of vitamin D.",
            "Vitamin C prevents the common cold.",
        ]
        for ex in examples:
            if st.button(ex, use_container_width=True, type="secondary"):
                st.session_state["claim_input"] = ex
                st.session_state["main_input"] = ex
                st.rerun()

    # Central Query Hub
    col_l, col_c, col_r = st.columns([1, 4, 1])
    with col_c:
        st.markdown("<h2 style='text-align: center; font-size: 40px; margin-bottom: 30px; font-weight: 600;'>Verify Scientific Claims</h2>", unsafe_allow_html=True)
        
        # Input Area
        user_input = st.text_area(
            "Enter a scientific claim to verify...",
            value=st.session_state.get("claim_input", ""),
            placeholder="Enter a scientific claim to verify...",
            height=100,
            key="main_input",
            label_visibility="collapsed"
        )

        analyze_btn = st.button("EXECUTE ANALYSIS", type="primary", use_container_width=True)

    if analyze_btn:
        if user_input.strip():
            st.write("")
            # Dynamic Agent Pipeline
            st.markdown("<p style='text-align: center; font-size: 12px; color: #859398; letter-spacing: 0.2em; margin-bottom: 20px;'>MULTI-AGENT PIPELINE STATUS</p>", unsafe_allow_html=True)
            
            p_cols = st.columns(4)
            agent_names = ["CLAIM EXTRACTOR", "EVIDENCE RETRIEVER", "VERDICT SYNTHESIZER", "SAFETY MONITOR"]
            agent_icons = ["data_exploration", "find_in_page", "psychology", "health_and_safety"]
            
            pipeline_placeholders = [c.empty() for c in p_cols]
            
            # Show static idle nodes first
            for i, p in enumerate(pipeline_placeholders):
                p.markdown(f"""
                    <div class="agent-node">
                        <span class="material-symbols-outlined" style="font-size: 32px; color: #3c494e;">{agent_icons[i]}</span>
                        <p style="font-size: 10px; color: #859398; text-align: center; margin:0;">{agent_names[i]}</p>
                    </div>
                """, unsafe_allow_html=True)

            import time
            for i in range(4):
                # Active state
                pipeline_placeholders[i].markdown(f"""
                    <div class="agent-node agent-node-active">
                        <span class="material-symbols-outlined" style="font-size: 32px; color: #00D4FF;">{agent_icons[i]}</span>
                        <p style="font-size: 10px; color: #00D4FF; text-align: center; margin:0;">{agent_names[i]}</p>
                    </div>
                """, unsafe_allow_html=True)
                time.sleep(0.6)
            
            # Analysis Area with Scanner
            analysis_placeholder = st.empty()
            with analysis_placeholder:
                st.markdown(f"""
                    <div class="glass-panel" style="position: relative; min-height: 200px; margin-top: 30px;">
                        <div class="ai-scanner"></div>
                        <p style="font-family: monospace; color: #00D4FF; font-size: 12px;">> INITIALIZING SCANNER...</p>
                        <p style="font-family: monospace; color: #859398; font-size: 12px;">> ANALYZING CLAIM: "{user_input[:50]}..."</p>
                        <p style="font-family: monospace; color: #859398; font-size: 12px;">> SCANNING CHROMA VECTOR DATABASE...</p>
                        <p style="font-family: monospace; color: #859398; font-size: 12px;">> CROSS-REFERENCING SCIENTIFIC LITERATURE...</p>
                    </div>
                """, unsafe_allow_html=True)
            
            time.sleep(1.0) # Visual duration

            # Get the response
            response, is_mock = run_pipeline(user_input)

            # Finish Animation / Clear
            analysis_placeholder.markdown(f"""
                <div class="glass-panel glass-panel-glow" style="position: relative; min-height: 100px; margin-top: 30px; border-color: #00F59B !important;">
                    <p style="font-family: monospace; color: #00F59B; font-size: 12px;">> ANALYSIS COMPLETE</p>
                    <p style="font-family: monospace; color: #dfe2eb; font-size: 12px;">> GENERATING FINAL VERDICT FOR TRACE ID: {response.trace_id}</p>
                </div>
            """, unsafe_allow_html=True)
            time.sleep(0.8)
            analysis_placeholder.empty() # Results will follow

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
