"""Verdict Synthesizer. Owner: Member 4.

Public entry: synthesize(claim, evidence, credibility) -> Verdict

CRITICAL: every source_id in Verdict.citations MUST appear in `evidence`.
Member 4 — assert this before returning.
"""
from __future__ import annotations

from src.contracts import Claim, CredibilityOutput, Evidence, Verdict
from src.llm import LLMClient


def synthesize(
    claim: Claim,
    evidence: list[Evidence],
    credibility: CredibilityOutput,
    llm: LLMClient,
) -> Verdict:
    raise NotImplementedError("Member 4: see docs/member-4-agent-retrieval-verdict.md")
