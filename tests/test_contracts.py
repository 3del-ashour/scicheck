"""Smoke test that contracts.py is import-clean."""
from src.contracts import (
    Claim,
    ClaimExtractorOutput,
    CredibilityOutput,
    CredibilityScore,
    Evidence,
    FinalResponse,
    PerClaimResult,
    RetrievalOutput,
    SafetyReport,
    Verdict,
)


def test_models_construct():
    claim = Claim(id="c1", text="x", type="health")
    ev = Evidence(source_id="s1", title="t", text="body", score=0.9)
    cred = CredibilityOutput(
        claim_id="c1",
        scored_sources=[CredibilityScore(source_id="s1", score=0.8, reasoning="ok")],
    )
    verdict = Verdict(
        claim_id="c1", label="Refuted", confidence=0.9, reasoning="…", citations=["s1"]
    )
    safety = SafetyReport(passed=True, flags=[], notes="")
    final = FinalResponse(
        trace_id="t",
        claim_text="x",
        per_claim=[
            PerClaimResult(
                claim=claim,
                evidence=[ev],
                credibility=cred,
                verdict=verdict,
                safety=safety,
            )
        ],
    )
    assert final.per_claim[0].verdict.label == "Refuted"
    assert ClaimExtractorOutput(raw_input="x", claims=[claim]).claims[0].id == "c1"
    assert RetrievalOutput(claim_id="c1", evidence=[ev]).evidence[0].score == 0.9
