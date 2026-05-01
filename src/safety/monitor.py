"""Safety Monitor. Owner: Member 5.

Public entry: check(verdict, evidence, claim) -> SafetyReport

Checks:
- Citation grounding: every Verdict.citations id is in `evidence`.
- Confidence sanity: confidence in [0,1].
- Bias keywords: scan reasoning for representational/allocational bias terms.
- Optional LLM-judge over a checklist.
"""
from __future__ import annotations

from src.contracts import Claim, Evidence, SafetyReport, Verdict
from src.llm import LLMClient


def check(
    verdict: Verdict,
    evidence: list[Evidence],
    claim: Claim,
    llm: LLMClient | None = None,
) -> SafetyReport:
    raise NotImplementedError("Member 5: see docs/member-5-safety-monitoring.md")
