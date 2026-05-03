import sys
from pathlib import Path

# Project root dizinini Python yoluna ekle
root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

import streamlit as st
import uuid
from src.contracts import (
    FinalResponse, PerClaimResult, Claim, Evidence, 
    Verdict, CredibilityOutput, CredibilityScore, SafetyReport
)
from src.ui.components import render_per_claim, render_metrics_tab

# --- MOCK ORCHESTRATOR ---
def mock_run(user_input: str) -> FinalResponse:
    """Simulates the orchestrator output for UI development."""
    trace_id = str(uuid.uuid4())
    
    # Mock Claim
    claim = Claim(id="c1", text=user_input, type="scientific")
    
    # Mock Evidence
    evidence = [
        Evidence(
            source_id="s1", 
            title="The Lancet: Study on Vaccines", 
            text="Comprehensive analysis shows no link between vaccines and autism...", 
            score=0.95,
            url="https://example.com/lancet"
        ),
        Evidence(
            source_id="s2", 
            title="WHO Report 2023", 
            text="Global vaccination data confirms safety profiles across all age groups.", 
            score=0.88
        )
    ]
    
    # Mock Credibility
    credibility = CredibilityOutput(
        claim_id="c1",
        scored_sources=[
            CredibilityScore(source_id="s1", score=0.98, reasoning="Peer-reviewed top-tier journal."),
            CredibilityScore(source_id="s2", score=0.92, reasoning="International health organization.")
        ]
    )
    
    # Mock Verdict
    verdict = Verdict(
        claim_id="c1",
        label="Refuted" if "autism" in user_input.lower() else "Supported",
        confidence=0.94,
        reasoning="Multiple high-quality peer-reviewed studies and health organizations refute this claim with high confidence.",
        citations=["s1", "s2"]
    )
    
    # Mock Safety
    safety = SafetyReport(passed=True, flags=[], notes="No issues detected.")
    
    per_claim = [
        PerClaimResult(
            claim=claim,
            evidence=evidence,
            credibility=credibility,
            verdict=verdict,
            safety=safety
        )
    ]
    
    return FinalResponse(trace_id=trace_id, claim_text=user_input, per_claim=per_claim)

# --- STREAMLIT APP ---
st.set_page_config(page_title="SciCheck AI", page_icon="🔬", layout="wide")

# Custom Title with Emoji and Subtitle
st.markdown("""
    <div style="text-align: center; padding: 20px 0 40px 0;">
        <h1 style="font-size: 3.5em; font-weight: 800; margin-bottom: 0;">🔬 SciCheck <span style="color: #646cff;">AI</span></h1>
        <p style="font-size: 1.2em; opacity: 0.7;">Advanced Multi-Agent Scientific Fact-Checking System</p>
    </div>
""", unsafe_allow_html=True)

tab_check, tab_metrics, tab_safety = st.tabs(["Fact-Check", "Metrics", "Safety Log"])

with tab_check:
    # Sidebar for Demo Claims
    with st.sidebar:
        st.header("Demo Examples")
        examples = [
            "Vaccines cause autism.",
            "Drinking bleach cures COVID-19.",
            "Vitamin C prevents the common cold.",
            "The earth is round."
        ]
        for ex in examples:
            if st.button(ex):
                st.session_state["claim_input"] = ex

    # Input Area
    user_input = st.text_area(
        "Enter a claim to analyze:",
        value=st.session_state.get("claim_input", ""),
        placeholder="e.g. Vaccines cause autism.",
        height=100,
        key="main_input"
    )

    if st.button("Analyze Claim", type="primary"):
        if user_input.strip():
            with st.spinner("Agents are collaborating..."):
                # Simulating agent steps for "WOW" effect
                progress_bar = st.progress(0)
                status = st.empty()
                
                status.text("🤖 Claim Extractor: Analyzing input...")
                import time; time.sleep(0.5); progress_bar.progress(25)
                
                status.text("🔍 Evidence Retriever: Searching knowledge base...")
                time.sleep(0.5); progress_bar.progress(50)
                
                status.text("⚖️ Verdict Synthesizer: Weighing evidence...")
                time.sleep(0.5); progress_bar.progress(75)
                
                status.text("🛡️ Safety Monitor: Checking for bias...")
                time.sleep(0.5); progress_bar.progress(100)
                
                # Get the mock response
                response = mock_run(user_input)
                status.empty()
                progress_bar.empty()

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
