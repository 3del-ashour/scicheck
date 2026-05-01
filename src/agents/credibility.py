"""Source Credibility Analyzer. Owner: Member 3.

Public entry: score_sources(claim_id, evidence) -> CredibilityOutput
"""
from __future__ import annotations

from src.contracts import CredibilityOutput, Evidence
from src.llm import LLMClient


def score_sources(
    claim_id: str, evidence: list[Evidence], llm: LLMClient
) -> CredibilityOutput:
    raise NotImplementedError("Member 3: see docs/member-3-agent-claim-credibility.md")
