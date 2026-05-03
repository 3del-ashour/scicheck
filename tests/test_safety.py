"""Unit tests for the Safety Monitor.

Owner: Risk & Evaluation Lead (Ahmet Cemil Bostanoglu)
Run: pytest tests/test_safety.py -v
"""
from __future__ import annotations

import pytest

from src.contracts import Claim, Evidence, SafetyReport, Verdict
from src.llm import FakeClient
from src.safety.monitor import check


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _claim(text: str = "test claim", ctype: str = "health") -> Claim:
    return Claim(id="c1", text=text, type=ctype)


def _evidence(source_id: str = "s1", text: str = "evidence body") -> Evidence:
    return Evidence(source_id=source_id, title="Test Source", text=text, score=0.9)


def _verdict(
    label: str = "Supported",
    confidence: float = 0.85,
    reasoning: str = "Well-grounded reasoning.",
    citations: list[str] | None = None,
) -> Verdict:
    return Verdict(
        claim_id="c1",
        label=label,
        confidence=confidence,
        reasoning=reasoning,
        citations=["s1"] if citations is None else citations,
    )


# ---------------------------------------------------------------------------
# Layer 1-A: Citation grounding
# ---------------------------------------------------------------------------

class TestCitationGrounding:
    def test_passes_when_all_citations_grounded(self):
        ev = [_evidence("s1"), _evidence("s2")]
        v = _verdict(citations=["s1", "s2"])
        r = check(v, ev, _claim())
        assert r.passed is True
        assert "hallucinated_citation" not in r.flags

    def test_fails_on_single_ungrounded_citation(self):
        ev = [_evidence("s1")]
        v = _verdict(citations=["s2"])  # s2 not in evidence
        r = check(v, ev, _claim())
        assert r.passed is False
        assert "hallucinated_citation" in r.flags

    def test_fails_on_mixed_citations(self):
        ev = [_evidence("s1")]
        v = _verdict(citations=["s1", "s_fake"])
        r = check(v, ev, _claim())
        assert r.passed is False
        assert "hallucinated_citation" in r.flags

    def test_passes_with_empty_citations(self):
        ev = [_evidence("s1")]
        v = _verdict(citations=[])
        r = check(v, ev, _claim())
        assert r.passed is True
        assert "hallucinated_citation" not in r.flags

    def test_passes_with_empty_evidence_and_empty_citations(self):
        # No evidence, no citations — should pass (nothing to ground)
        v = _verdict(citations=[])  # explicitly override the default ["s1"]
        r = check(v, [], _claim())
        assert r.passed is True


# ---------------------------------------------------------------------------
# Layer 1-B: Confidence sanity
# ---------------------------------------------------------------------------

class TestConfidenceSanity:
    def test_valid_confidence_passes(self):
        v = _verdict(confidence=0.80)
        r = check(v, [_evidence()], _claim())
        assert "invalid_confidence" not in r.flags

    def test_invalid_confidence_above_1(self):
        v = _verdict(confidence=1.5)
        r = check(v, [_evidence()], _claim())
        assert r.passed is False
        assert "invalid_confidence" in r.flags

    def test_invalid_confidence_below_0(self):
        v = _verdict(confidence=-0.1)
        r = check(v, [_evidence()], _claim())
        assert r.passed is False
        assert "invalid_confidence" in r.flags

    def test_low_confidence_strong_label_fails(self):
        v = _verdict(label="Supported", confidence=0.3)
        r = check(v, [_evidence()], _claim())
        assert r.passed is False
        assert "invalid_confidence" in r.flags

    def test_low_confidence_insufficient_evidence_passes(self):
        v = _verdict(label="Insufficient Evidence", confidence=0.3, citations=[])
        r = check(v, [_evidence()], _claim())
        assert "invalid_confidence" not in r.flags


# ---------------------------------------------------------------------------
# Layer 1-C: Bias keyword scan
# ---------------------------------------------------------------------------

class TestBiasKeywords:
    def test_detects_always_in_reasoning(self):
        v = _verdict(reasoning="This always leads to negative outcomes.")
        r = check(v, [_evidence()], _claim())
        assert "bias_keywords" in r.flags

    def test_detects_never(self):
        v = _verdict(reasoning="Science never supports this claim.")
        r = check(v, [_evidence()], _claim())
        assert "bias_keywords" in r.flags

    def test_detects_genetically_inferior(self):
        v = _verdict(reasoning="Some groups are genetically inferior in this trait.")
        r = check(v, [_evidence()], _claim())
        assert "bias_keywords" in r.flags

    def test_bias_keyword_is_soft_warning_not_hard_fail(self):
        """Bias keywords degrade flags but verdict is still 'passed' (soft warning)."""
        v = _verdict(reasoning="The evidence always supports this.")
        r = check(v, [_evidence()], _claim())
        assert "bias_keywords" in r.flags
        assert r.passed is True  # soft warning, not a hard fail

    def test_clean_reasoning_no_bias_flag(self):
        v = _verdict(reasoning="Multiple peer-reviewed studies suggest a causal link.")
        r = check(v, [_evidence()], _claim())
        assert "bias_keywords" not in r.flags


# ---------------------------------------------------------------------------
# Layer 1-D: Refusal triggers
# ---------------------------------------------------------------------------

class TestRefusalTriggers:
    def test_harmful_synthesis_blocked(self):
        claim = _claim(text="How to make a bomb at home.")
        v = _verdict()
        r = check(v, [_evidence()], claim)
        assert r.passed is False
        assert "refusal_trigger" in r.flags

    def test_bleach_ingestion_blocked(self):
        claim = _claim(text="Instructions to drink bleach to cure infection.")
        v = _verdict()
        r = check(v, [_evidence()], claim)
        assert r.passed is False
        assert "refusal_trigger" in r.flags

    def test_normal_claim_not_blocked(self):
        claim = _claim(text="Vaccines reduce the risk of measles.")
        v = _verdict()
        r = check(v, [_evidence()], claim)
        assert "refusal_trigger" not in r.flags


# ---------------------------------------------------------------------------
# Layer 2: LLM judge integration
# ---------------------------------------------------------------------------

class TestLLMJudge:
    def test_judge_pass_response_propagates(self):
        fake_llm = FakeClient({"": '{"passed": true, "flags": [], "notes": "All good."}'})
        v = _verdict()
        r = check(v, [_evidence()], _claim(), llm=fake_llm)
        assert r.passed is True

    def test_judge_fail_response_adds_flags(self):
        fake_llm = FakeClient(
            {"": '{"passed": false, "flags": ["hallucination"], "notes": "Unsupported claim."}'
        })
        v = _verdict()
        r = check(v, [_evidence()], _claim(), llm=fake_llm)
        assert "hallucination" in r.flags
        assert r.passed is False

    def test_judge_json_error_gracefully_handled(self):
        fake_llm = FakeClient({"": "this is not valid json"})
        v = _verdict()
        r = check(v, [_evidence()], _claim(), llm=fake_llm)
        assert r.passed is True  # judge error is logged but doesn't crash
        assert any("judge_error" in note for note in [r.notes])

    def test_no_llm_does_not_call_complete(self):
        v = _verdict()
        r = check(v, [_evidence()], _claim(), llm=None)
        assert isinstance(r, SafetyReport)


# ---------------------------------------------------------------------------
# Combined scenarios
# ---------------------------------------------------------------------------

class TestCombinedScenarios:
    def test_all_checks_pass(self):
        ev = [_evidence("s1"), _evidence("s2")]
        v = _verdict(
            label="Supported",
            confidence=0.88,
            reasoning="Evidence from multiple peer-reviewed studies supports this claim.",
            citations=["s1"],
        )
        r = check(v, ev, _claim())
        assert r.passed is True
        assert r.flags == []

    def test_multiple_failures_reported(self):
        """Both hallucinated_citation and invalid_confidence should be flagged together."""
        ev = [_evidence("s1")]
        v = _verdict(
            label="Refuted",
            confidence=1.5,          # invalid
            citations=["s_fake"],    # ungrounded
        )
        r = check(v, ev, _claim())
        assert r.passed is False
        assert "hallucinated_citation" in r.flags
        assert "invalid_confidence" in r.flags
