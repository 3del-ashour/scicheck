"""Inter-module contracts.

Every cross-module function input/output must be one of these models.
Changes require a PR with 2 reviewers (one must be the Project Lead).
See CONTRACTS.md for the rules.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ClaimType = Literal["scientific", "health", "general"]
VerdictLabel = Literal["Supported", "Refuted", "Insufficient Evidence"]


class Claim(BaseModel):
    id: str
    text: str
    type: ClaimType


class ClaimExtractorOutput(BaseModel):
    raw_input: str
    claims: list[Claim]


class Evidence(BaseModel):
    source_id: str
    title: str
    url: str | None = None
    text: str
    score: float
    metadata: dict = Field(default_factory=dict)


class RetrievalOutput(BaseModel):
    claim_id: str
    evidence: list[Evidence]


class CredibilityScore(BaseModel):
    source_id: str
    score: float
    reasoning: str
    flags: list[str] = Field(default_factory=list)


class CredibilityOutput(BaseModel):
    claim_id: str
    scored_sources: list[CredibilityScore]


class Verdict(BaseModel):
    claim_id: str
    label: VerdictLabel
    confidence: float
    reasoning: str
    citations: list[str]


class SafetyReport(BaseModel):
    passed: bool
    flags: list[str]
    notes: str


class PerClaimResult(BaseModel):
    claim: Claim
    evidence: list[Evidence]
    credibility: CredibilityOutput
    verdict: Verdict
    safety: SafetyReport


class FinalResponse(BaseModel):
    trace_id: str
    claim_text: str
    per_claim: list[PerClaimResult]
