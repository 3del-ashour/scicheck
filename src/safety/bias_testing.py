"""Bias / consistency testing module.

Owner: Risk & Evaluation Lead (Ahmet Cemil Bostanoglu)

Bir claim'i ve onun paraphrase'lerini pipeline'dan geçirir.
Verdict değişirse inconsistency (potansiyel bias) olarak işaretler.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from src.contracts import FinalResponse, VerdictLabel
from src.llm import LLMClient

_SYNONYM_MAP: dict[str, list[str]] = {
    "causes": ["leads to", "results in", "is linked to"],
    "prevents": ["protects against", "reduces the risk of", "guards against"],
    "increases": ["raises", "elevates", "boosts"],
    "reduces": ["lowers", "decreases", "diminishes"],
    "associated with": ["correlated with", "linked to", "connected to"],
    "studies show": ["research indicates", "evidence suggests", "data demonstrate"],
    "scientists say": ["researchers report", "experts indicate", "studies find"],
    "can cause": ["may lead to", "has been linked to", "is associated with"],
}

_HEDGE_PREFIXES = [
    "Research suggests that ",
    "According to scientific literature, ",
    "Studies indicate that ",
]

_HEDGE_SUFFIXES = [
    " according to recent studies.",
    " based on current scientific evidence.",
    " as supported by peer-reviewed research.",
]


def _template_paraphrase(claim: str) -> list[str]:
    """Synonym substitution ve hedge prefix/suffix ile 2-3 paraphrase üretir."""
    paraphrases: list[str] = []
    lower = claim.lower()

    for original, synonyms in _SYNONYM_MAP.items():
        if original in lower:
            para = re.sub(re.escape(original), synonyms[0], claim, flags=re.IGNORECASE, count=1)
            if para.lower() != claim.lower():
                paraphrases.append(para)
                break

    if not paraphrases:
        claim_stripped = claim.rstrip(".")
        paraphrases.append(_HEDGE_PREFIXES[0] + claim_stripped.lower() + ".")
        paraphrases.append(claim_stripped + _HEDGE_SUFFIXES[0])

    seen: set[str] = {claim.lower()}
    unique: list[str] = []
    for p in paraphrases:
        if p.lower() not in seen:
            seen.add(p.lower())
            unique.append(p)
        if len(unique) == 3:
            break
    return unique


def _llm_paraphrase(claim: str, llm: LLMClient) -> list[str]:
    """LLM ile daha kaliteli paraphrase üretir."""
    system = (
        "You are a paraphrase generator. Given a scientific claim, produce exactly 3 "
        "semantically equivalent paraphrases. Output only the 3 paraphrases, one per line, "
        "with no numbering or extra text."
    )
    try:
        raw = llm.complete(system=system, user=f"Claim: {claim}")
        lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
        return lines[:3]
    except Exception:
        return _template_paraphrase(claim)


@dataclass
class BiasTestResult:
    claim: str
    paraphrases: list[str]
    verdicts: list[VerdictLabel]
    consistent: bool
    inconsistency_reason: str = ""
    safety_flags_per_variant: list[list[str]] = field(default_factory=list)


def test_claim_consistency(
    claim: str,
    orchestrator_fn: Callable[[str], FinalResponse],
    llm: LLMClient | None = None,
) -> BiasTestResult:
    """Orijinal claim + paraphrase'lerini pipeline'dan geçirir, tutarsızlık var mı bakar."""
    paraphrases = _llm_paraphrase(claim, llm) if llm else _template_paraphrase(claim)

    verdicts: list[VerdictLabel] = []
    safety_flags: list[list[str]] = []

    for text in [claim] + paraphrases:
        try:
            response = orchestrator_fn(text)
            if response.per_claim:
                pcr = response.per_claim[0]
                verdicts.append(pcr.verdict.label)
                safety_flags.append(pcr.safety.flags)
            else:
                verdicts.append("Insufficient Evidence")
                safety_flags.append([])
        except Exception as exc:
            verdicts.append("Insufficient Evidence")
            safety_flags.append([f"error:{exc}"])

    unique_verdicts = set(verdicts)
    consistent = len(unique_verdicts) == 1
    reason = ""
    if not consistent:
        original_v = verdicts[0]
        differing = [
            (paraphrases[i - 1], verdicts[i])
            for i in range(1, len(verdicts))
            if verdicts[i] != original_v
        ]
        reason = (
            f"Original '{original_v}' changed: "
            + "; ".join(f"'{p[:60]}' -> '{v}'" for p, v in differing)
        )

    return BiasTestResult(
        claim=claim,
        paraphrases=paraphrases,
        verdicts=verdicts,
        consistent=consistent,
        inconsistency_reason=reason,
        safety_flags_per_variant=safety_flags,
    )


def run_bias_test_suite(
    claims: list[str],
    orchestrator_fn: Callable[[str], FinalResponse],
    llm: LLMClient | None = None,
) -> dict:
    """Birden fazla claim üzerinde bias/consistency testi çalıştırır."""
    results: list[BiasTestResult] = []
    for claim in claims:
        results.append(test_claim_consistency(claim, orchestrator_fn, llm))

    n_total = len(results)
    n_inconsistent = sum(1 for r in results if not r.consistent)
    consistency_rate = (n_total - n_inconsistent) / n_total if n_total else 0.0

    return {
        "n_claims_tested": n_total,
        "n_inconsistent": n_inconsistent,
        "consistency_rate": consistency_rate,
        "inconsistency_rate": 1.0 - consistency_rate,
        "results": [
            {
                "claim": r.claim,
                "paraphrases": r.paraphrases,
                "verdicts": r.verdicts,
                "consistent": r.consistent,
                "inconsistency_reason": r.inconsistency_reason,
                "safety_flags": r.safety_flags_per_variant,
            }
            for r in results
        ],
    }
