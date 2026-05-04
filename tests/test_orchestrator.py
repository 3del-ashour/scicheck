"""End-to-end orchestrator tests (Adel — M1).

Uses FakeClient and monkeypatches every external dependency so the test
runs offline (no real LLM, no ChromaDB).

There are four LLM calls per claim, each keyed on a unique phrase from
its system prompt:
  - claim_extractor   ← "scientific claim extractor"
  - query_expansion   ← "search-query writer"
  - credibility       ← "research credibility analyst"
  - verdict           ← "scientific fact-checker"
"""
from __future__ import annotations

import json

from src.contracts import Evidence, FinalResponse
from src.llm import FakeClient
from src.orchestrator import run


def _seed_pipeline(monkeypatch, label: str = "Refuted") -> FakeClient:
    """Replace RAG + LLM responses so the whole pipeline runs offline."""
    monkeypatch.setattr(
        "src.agents.retriever.rag_retrieve",
        lambda q, k: [
            Evidence(source_id="s1", title="Meta", text="evidence body", score=0.9),
            Evidence(source_id="s2", title="Cohort", text="another body", score=0.8),
        ],
    )

    canned_extract = json.dumps(
        {"claims": [{"id": "c1", "text": "Vaccines cause autism.", "type": "health"}]}
    )
    canned_query = json.dumps({"queries": ["expanded query"]})
    canned_credibility = json.dumps(
        {
            "scores": [
                {"source_id": "s1", "score": 0.9, "reasoning": "meta", "flags": ["meta_analysis"]},
                {"source_id": "s2", "score": 0.7, "reasoning": "cohort", "flags": ["cohort"]},
            ]
        }
    )
    canned_verdict = json.dumps(
        {
            "label": label,
            "confidence": 0.9,
            "reasoning": "Test reasoning [s1].",
            "citations": ["s1"],
        }
    )

    return FakeClient(
        responses={
            "scientific claim extractor": canned_extract,
            "search-query writer": canned_query,
            "research credibility analyst": canned_credibility,
            "scientific fact-checker": canned_verdict,
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
    # Override the extractor response specifically for the blank case.
    fake.responses["scientific claim extractor"] = json.dumps({"claims": []})
    response = run("   ", llm=fake)
    assert response.per_claim == []


def test_orchestrator_degrades_safely_on_rag_failure(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("rag offline")

    monkeypatch.setattr("src.agents.retriever.rag_retrieve", boom)
    fake = FakeClient(
        responses={
            "scientific claim extractor": json.dumps(
                {"claims": [{"id": "c1", "text": "Some claim.", "type": "general"}]}
            ),
            "search-query writer": json.dumps({"queries": ["q"]}),
        }
    )
    response = run("Some claim.", llm=fake)

    assert isinstance(response, FinalResponse)
    assert len(response.per_claim) == 1
    pcr = response.per_claim[0]
    assert pcr.verdict.label == "Insufficient Evidence"
    assert "pipeline_error" in pcr.safety.flags
