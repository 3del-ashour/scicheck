"""End-to-end orchestrator tests (Adel — M1).

Uses FakeClient and monkeypatches every external dependency so the test
runs offline (no OpenAI, no ChromaDB).
"""
from __future__ import annotations

import json

from src.contracts import Evidence, FinalResponse
from src.llm import FakeClient
from src.orchestrator import run


def _seed_pipeline(monkeypatch, label: str = "Refuted"):
    """Replace RAG + LLM responses so the whole pipeline runs offline."""
    monkeypatch.setattr(
        "src.agents.retriever.rag_retrieve",
        lambda q, k: [
            Evidence(source_id="s1", title="Meta", text="evidence body", score=0.9),
            Evidence(source_id="s2", title="Cohort", text="another body", score=0.8),
        ],
    )

    canned_verdict = json.dumps(
        {
            "label": label,
            "confidence": 0.9,
            "reasoning": "Test reasoning [s1].",
            "citations": ["s1"],
        }
    )
    canned_query = json.dumps({"queries": ["expanded query"]})

    return FakeClient(
        responses={
            "search-query writer": canned_query,  # query expansion system prompt
            "scientific fact-checker": canned_verdict,  # verdict system prompt
            "expanded query": canned_query,
            "Vaccines cause autism": canned_verdict,
            "anything": canned_verdict,
        }
    )


def test_run_returns_valid_final_response_end_to_end(monkeypatch):
    fake = _seed_pipeline(monkeypatch, label="Refuted")
    response = run("Vaccines cause autism.", llm=fake)

    assert isinstance(response, FinalResponse)
    assert response.trace_id
    assert response.claim_text == "Vaccines cause autism."
    assert len(response.per_claim) == 1

    pcr = response.per_claim[0]
    assert pcr.claim.text == "Vaccines cause autism."
    assert len(pcr.evidence) == 2
    assert pcr.verdict.label in {"Supported", "Refuted", "Insufficient Evidence"}
    assert all(c in {e.source_id for e in pcr.evidence} for c in pcr.verdict.citations)


def test_empty_input_yields_empty_per_claim(monkeypatch):
    fake = _seed_pipeline(monkeypatch)
    response = run("   ", llm=fake)
    assert response.per_claim == []


def test_orchestrator_degrades_safely_on_rag_failure(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("rag offline")

    monkeypatch.setattr("src.agents.retriever.rag_retrieve", boom)
    fake = FakeClient(responses={"queries": json.dumps({"queries": ["q"]})})
    response = run("Some claim.", llm=fake)

    assert isinstance(response, FinalResponse)
    assert len(response.per_claim) == 1
    pcr = response.per_claim[0]
    assert pcr.verdict.label == "Insufficient Evidence"
    assert "pipeline_error" in pcr.safety.flags
