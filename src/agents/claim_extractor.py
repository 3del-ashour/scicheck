"""Claim Extractor agent. Owner: Member 3.

Public entry: extract_claims(user_input) -> ClaimExtractorOutput
"""
from __future__ import annotations

from src.contracts import ClaimExtractorOutput
from src.llm import LLMClient


def extract_claims(user_input: str, llm: LLMClient) -> ClaimExtractorOutput:
    raise NotImplementedError("Member 3: see docs/member-3-agent-claim-credibility.md")
