"""Verdict Synthesizer. Owner: Member 1+4 (Adel Ashour).

Public entry: synthesize(claim, evidence, credibility, llm) -> Verdict

CRITICAL: every source_id in Verdict.citations MUST appear in `evidence`.
Ungrounded citations are stripped before returning (defense in depth — the
Safety Monitor will also check this).
"""

from __future__ import annotations

import json
from pathlib import Path

from src.contracts import Claim, CredibilityOutput, Evidence, Verdict
from src.errors import AgentError
from src.llm import LLMClient
from src.logging_setup import get_logger

log = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "verdict.txt"

_VALID_LABELS = {"Supported", "Refuted", "Insufficient Evidence"}
_MAX_PASSAGE_CHARS = 800


def _strip_code_fence(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.endswith("```"):
            s = s.rsplit("```", 1)[0]
    return s.strip()


def _format_evidence(evidence: list[Evidence], credibility: CredibilityOutput) -> str:
    cred_map = {s.source_id: s.score for s in credibility.scored_sources}
    parts: list[str] = []
    for e in evidence:
        c = cred_map.get(e.source_id, 0.5)
        passage = e.text[:_MAX_PASSAGE_CHARS]
        if len(e.text) > _MAX_PASSAGE_CHARS:
            passage += "…"
        parts.append(f"[{e.source_id}] (credibility={c:.2f}) {e.title}\n{passage}")
    return "\n\n".join(parts)


def synthesize(
    claim: Claim,
    evidence: list[Evidence],
    credibility: CredibilityOutput,
    llm: LLMClient,
) -> Verdict:
    """Produce a Verdict for the given claim.

    Args:
        claim: parsed claim under investigation.
        evidence: retrieved evidence passages (may be empty).
        credibility: per-source credibility scores aligned to ``evidence``.
        llm: the LLM client used to draft the verdict.

    Returns:
        A Verdict with grounded citations only.

    Raises:
        AgentError: if the LLM returns malformed output that cannot be parsed.
    """
    log.info("verdict.start", claim_id=claim.id, n_evidence=len(evidence))

    if not evidence:
        log.info("verdict.done", claim_id=claim.id, label="Insufficient Evidence", reason="no_evidence")
        return Verdict(
            claim_id=claim.id,
            label="Insufficient Evidence",
            confidence=0.0,
            reasoning="No evidence was retrieved for this claim.",
            citations=[],
        )

    user = f"CLAIM: {claim.text}\n\nEVIDENCE:\n{_format_evidence(evidence, credibility)}"
    raw = llm.complete(system=_PROMPT_PATH.read_text(encoding="utf-8"), user=user)

    try:
        data = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        log.error("verdict.invalid_json", raw=raw[:300])
        raise AgentError(f"Verdict synthesizer returned invalid JSON: {raw[:200]}") from exc

    label = data.get("label")
    if label not in _VALID_LABELS:
        log.warning("verdict.invalid_label", label=label)
        label = "Insufficient Evidence"

    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    valid_ids = {e.source_id for e in evidence}
    raw_citations = data.get("citations", []) or []
    citations = [c for c in raw_citations if isinstance(c, str) and c in valid_ids]

    # If the model claimed Supported/Refuted but cited nothing valid, downgrade to Insufficient
    if label in ("Supported", "Refuted") and not citations:
        log.warning("verdict.no_valid_citations", original_label=label)
        label = "Insufficient Evidence"
        confidence = min(confidence, 0.4)

    reasoning = str(data.get("reasoning", "")).strip() or "No reasoning provided."

    verdict = Verdict(
        claim_id=claim.id,
        label=label,
        confidence=confidence,
        reasoning=reasoning,
        citations=citations,
    )

    log.info(
        "verdict.done",
        claim_id=claim.id,
        label=verdict.label,
        confidence=verdict.confidence,
        n_citations=len(verdict.citations),
        n_dropped_citations=len(raw_citations) - len(citations),
    )
    return verdict
