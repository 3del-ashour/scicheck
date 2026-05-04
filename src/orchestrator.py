"""Orchestrator. Owner: Member 1 (Adel Ashour).

Public entry: run(user_input, llm=None) -> FinalResponse

Wires the five agents in sequence:
    extract_claims → retrieve_for_claim → score_sources → synthesize → check

Provides minimal in-process dev fallbacks for any agent that has not yet
been implemented by its owning team member, so the pipeline always produces
a valid FinalResponse during integration. Fallbacks are loud (warning logs +
``stub_used`` flag in SafetyReport) so we never quietly ship a stub.
"""

from __future__ import annotations

import uuid

import structlog

from src.agents.claim_extractor import extract_claims
from src.agents.credibility import score_sources
from src.agents.retriever import retrieve_for_claim
from src.agents.verdict import synthesize
from src.contracts import (
    Claim,
    ClaimExtractorOutput,
    CredibilityOutput,
    CredibilityScore,
    Evidence,
    FinalResponse,
    PerClaimResult,
    SafetyReport,
    Verdict,
)
from src.errors import SciCheckError
from src.llm import LLMClient, OpenAIClient
from src.logging_setup import configure_logging, get_logger
from src.safety.monitor import check as safety_check

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Dev fallbacks — only used when an agent still raises NotImplementedError
# (i.e. the teammate hasn't pushed yet). They keep integration unblocked.
# ---------------------------------------------------------------------------


def _fallback_extract(user_input: str, llm: LLMClient) -> ClaimExtractorOutput:
    log.warning("orchestrator.stub_used", agent="claim_extractor")
    text = user_input.strip()
    if not text:
        return ClaimExtractorOutput(raw_input=user_input, claims=[])
    return ClaimExtractorOutput(
        raw_input=user_input,
        claims=[Claim(id="c1", text=text, type="general")],
    )


def _fallback_credibility(
    claim_id: str, evidence: list[Evidence], llm: LLMClient
) -> CredibilityOutput:
    log.warning("orchestrator.stub_used", agent="credibility")
    return CredibilityOutput(
        claim_id=claim_id,
        scored_sources=[
            CredibilityScore(
                source_id=e.source_id,
                score=0.5,
                reasoning="default credibility (M3 stub)",
                flags=["stub_used"],
            )
            for e in evidence
        ],
    )


def _safe_extract(user_input: str, llm: LLMClient) -> ClaimExtractorOutput:
    try:
        return extract_claims(user_input, llm=llm)
    except NotImplementedError:
        return _fallback_extract(user_input, llm)


def _safe_credibility(
    claim_id: str, evidence: list[Evidence], llm: LLMClient
) -> CredibilityOutput:
    try:
        return score_sources(claim_id, evidence, llm=llm)
    except NotImplementedError:
        return _fallback_credibility(claim_id, evidence, llm)


# ---------------------------------------------------------------------------
# Per-claim processing
# ---------------------------------------------------------------------------


def _degraded_result(
    claim: Claim, evidence: list[Evidence], reason: str
) -> PerClaimResult:
    """Build a safe, well-typed PerClaimResult for the failure path."""
    return PerClaimResult(
        claim=claim,
        evidence=evidence,
        credibility=CredibilityOutput(claim_id=claim.id, scored_sources=[]),
        verdict=Verdict(
            claim_id=claim.id,
            label="Insufficient Evidence",
            confidence=0.0,
            reasoning=f"Pipeline degraded: {reason}",
            citations=[],
        ),
        safety=SafetyReport(passed=False, flags=["pipeline_error"], notes=reason),
    )


def _process_claim(claim: Claim, llm: LLMClient) -> PerClaimResult:
    structlog.contextvars.bind_contextvars(claim_id=claim.id)
    try:
        retrieval = retrieve_for_claim(claim, llm=llm)
        credibility = _safe_credibility(claim.id, retrieval.evidence, llm=llm)
        verdict = synthesize(claim, retrieval.evidence, credibility, llm=llm)
        safety = safety_check(verdict, retrieval.evidence, claim, llm=llm)

        # One conservative retry if Safety Monitor blocks the verdict.
        if not safety.passed and "hallucinated_citation" in safety.flags:
            log.warning("orchestrator.safety_retry", claim_id=claim.id, flags=safety.flags)
            verdict = synthesize(claim, retrieval.evidence, credibility, llm=llm)
            safety = safety_check(verdict, retrieval.evidence, claim, llm=llm)

        return PerClaimResult(
            claim=claim,
            evidence=retrieval.evidence,
            credibility=credibility,
            verdict=verdict,
            safety=safety,
        )
    except SciCheckError as exc:
        log.warning("orchestrator.claim_failed", claim_id=claim.id, error=str(exc))
        return _degraded_result(claim, [], str(exc))
    except Exception as exc:  # last-resort guard so the UI never sees a raw exception
        log.error("orchestrator.unexpected_error", claim_id=claim.id, error=str(exc))
        return _degraded_result(claim, [], f"unexpected_error: {exc}")
    finally:
        structlog.contextvars.unbind_contextvars("claim_id")


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------


def run(user_input: str, llm: LLMClient | None = None) -> FinalResponse:
    """Run the full SciCheck pipeline on a user query.

    Args:
        user_input: free-text claim or question from the UI.
        llm: optional LLMClient injection (tests pass a FakeClient). If None,
             a real OpenAIClient is constructed.

    Returns:
        FinalResponse — always a valid Pydantic object; failures degrade to
        ``Insufficient Evidence`` per CONTRACTS.md Rule 9.
    """
    configure_logging()
    trace_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(trace_id=trace_id)

    log.info("orchestrator.start", input_len=len(user_input))

    if llm is None:
        llm = OpenAIClient()

    extracted = _safe_extract(user_input, llm=llm)

    if not extracted.claims:
        log.info("orchestrator.no_claims_extracted")
        return FinalResponse(trace_id=trace_id, claim_text=user_input, per_claim=[])

    per_claim = [_process_claim(c, llm=llm) for c in extracted.claims]

    log.info(
        "orchestrator.done",
        n_claims=len(per_claim),
        labels=[p.verdict.label for p in per_claim],
    )
    structlog.contextvars.unbind_contextvars("trace_id")

    return FinalResponse(
        trace_id=trace_id,
        claim_text=user_input,
        per_claim=per_claim,
    )
