"""Tests for the Verdict Synthesizer agent (Adel — M4)."""
from __future__ import annotations

import json

import pytest

from src.agents.verdict import synthesize
from src.contracts import Claim, CredibilityOutput, CredibilityScore, Evidence
from src.errors import AgentError
from src.llm import FakeClient


def _make_claim() -> Claim:
    return Claim(id="c1", text="Vaccines cause autism.", type="health")


def _make_evidence() -> list[Evidence]:
    return [
        Evidence(source_id="s1", title="Meta-analysis", text="No association found.", score=0.92),
        Evidence(source_id="s2", title="Cohort", text="Confirms no link.", score=0.85),
    ]


def _make_credibility() -> CredibilityOutput:
    return CredibilityOutput(
        claim_id="c1",
        scored_sources=[
            CredibilityScore(source_id="s1", score=0.95, reasoning="meta"),
            CredibilityScore(source_id="s2", score=0.80, reasoning="cohort"),
        ],
    )


def test_no_evidence_returns_insufficient_evidence_with_zero_confidence():
    fake = FakeClient(responses={})
    v = synthesize(_make_claim(), [], CredibilityOutput(claim_id="c1", scored_sources=[]), llm=fake)
    assert v.label == "Insufficient Evidence"
    assert v.confidence == 0.0
    assert v.citations == []


def test_strips_ungrounded_citations():
    canned = json.dumps(
        {
            "label": "Refuted",
            "confidence": 0.95,
            "reasoning": "Strong meta-analysis [s1].",
            "citations": ["s1", "FAKE_ID", "s99"],
        }
    )
    fake = FakeClient(responses={"Vaccines cause autism": canned})
    v = synthesize(_make_claim(), _make_evidence(), _make_credibility(), llm=fake)
    assert v.label == "Refuted"
    assert v.citations == ["s1"]


def test_downgrades_to_insufficient_when_citations_all_invalid():
    canned = json.dumps(
        {
            "label": "Supported",
            "confidence": 0.9,
            "reasoning": "Strong support.",
            "citations": ["FAKE_ONLY"],
        }
    )
    fake = FakeClient(responses={"Vaccines cause autism": canned})
    v = synthesize(_make_claim(), _make_evidence(), _make_credibility(), llm=fake)
    assert v.label == "Insufficient Evidence"
    assert v.citations == []
    assert v.confidence <= 0.4


def test_handles_markdown_code_fence():
    canned = (
        "```json\n"
        + json.dumps(
            {
                "label": "Supported",
                "confidence": 0.7,
                "reasoning": "Yes [s1].",
                "citations": ["s1"],
            }
        )
        + "\n```"
    )
    fake = FakeClient(responses={"Vaccines cause autism": canned})
    v = synthesize(_make_claim(), _make_evidence(), _make_credibility(), llm=fake)
    assert v.label == "Supported"
    assert v.citations == ["s1"]


def test_invalid_json_raises_agent_error():
    fake = FakeClient(responses={"Vaccines cause autism": "not json at all"})
    with pytest.raises(AgentError):
        synthesize(_make_claim(), _make_evidence(), _make_credibility(), llm=fake)


def test_clamps_confidence_to_unit_interval():
    canned = json.dumps(
        {"label": "Supported", "confidence": 5.0, "reasoning": "x [s1].", "citations": ["s1"]}
    )
    fake = FakeClient(responses={"Vaccines cause autism": canned})
    v = synthesize(_make_claim(), _make_evidence(), _make_credibility(), llm=fake)
    assert 0.0 <= v.confidence <= 1.0
