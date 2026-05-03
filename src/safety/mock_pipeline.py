"""Mock pipeline — sadece src/safety/ testleri için kullanılır.

Owner: Risk & Evaluation Lead (Ahmet Cemil Bostanoglu)

Gerçek orchestrator (Member 1) hazır olmadan bias/hallucination testlerini
çalıştırmak için keyword-heuristic tabanlı simüle pipeline.
"""
from __future__ import annotations

import hashlib
import random
import uuid

from src.contracts import (
    Claim,
    CredibilityOutput,
    CredibilityScore,
    Evidence,
    FinalResponse,
    PerClaimResult,
    SafetyReport,
    Verdict,
)

_MOCK_SOURCES = [
    {"id": "pub_nejm_001", "title": "NEJM: Systematic Review of Vaccine Safety", "domain": "nejm.org"},
    {"id": "pub_lancet_002", "title": "The Lancet: COVID-19 Treatment Efficacy", "domain": "thelancet.com"},
    {"id": "pub_nature_003", "title": "Nature Medicine: Genomic Research", "domain": "nature.com"},
    {"id": "pub_who_004", "title": "WHO Technical Report 2023", "domain": "who.int"},
    {"id": "pub_cdc_005", "title": "CDC Epidemiology & Prevention Reports", "domain": "cdc.gov"},
    {"id": "pub_jama_006", "title": "JAMA: Clinical Trials Meta-Analysis", "domain": "jamanetwork.com"},
    {"id": "pub_bmj_007", "title": "BMJ: Observational Cohort Study", "domain": "bmj.com"},
    {"id": "pub_pmc_008", "title": "PubMed Central: Open Access Research", "domain": "pubmed.ncbi.nih.gov"},
    {"id": "pub_nih_009", "title": "NIH: National Toxicology Program Report", "domain": "nih.gov"},
    {"id": "pub_cell_010", "title": "Cell: Molecular Biology Advances", "domain": "cell.com"},
]

_REFUTED_SIGNALS = frozenset(
    {
        "does not cause", "does not increase", "no causal link", "no evidence",
        "myth", "disproven", "false", "no significant", "not associated",
        "autism", "bleach", "5g", "microchip", "chemtrail", "flat earth",
        "homeopathy cures", "miracle cure",
    }
)
_SUPPORTED_SIGNALS = frozenset(
    {
        "increases risk", "reduces risk", "protective effect", "associated with",
        "shown to", "evidence supports", "clinical trials confirm",
        "linked to", "effective against", "significantly reduces", "prevents",
        "improves survival", "beneficial", "statistically significant",
    }
)


def _stable_hash(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest(), 16)


def _heuristic_label(claim_text: str, rng: random.Random) -> tuple[str, float]:
    lower = claim_text.lower()
    refuted_hits = sum(1 for kw in _REFUTED_SIGNALS if kw in lower)
    supported_hits = sum(1 for kw in _SUPPORTED_SIGNALS if kw in lower)

    if refuted_hits > supported_hits:
        return "Refuted", round(rng.uniform(0.72, 0.94), 2)
    elif supported_hits > 0:
        return "Supported", round(rng.uniform(0.68, 0.92), 2)
    else:
        h = _stable_hash(claim_text)
        labels = ["Supported", "Refuted", "Insufficient Evidence"]
        label = labels[h % 3]
        return label, round(rng.uniform(0.55, 0.80), 2)


def mock_run(user_input: str, inject_hallucination: bool = False) -> FinalResponse:
    """Simüle pipeline — bias ve hallucination testleri için."""
    h = _stable_hash(user_input)
    rng = random.Random(h)

    claim = Claim(id="c1", text=user_input, type="scientific")

    n_evidence = rng.randint(2, 4)
    source_pool = rng.sample(_MOCK_SOURCES, n_evidence)
    evidence: list[Evidence] = [
        Evidence(
            source_id=s["id"],
            title=s["title"],
            url=f"https://{s['domain']}/article/{h % 99999:05d}",
            text=(
                f"[Simulated abstract] This study examines: '{user_input[:100]}'. "
                f"Analysis of {rng.randint(100, 8000):,} subjects provides relevant evidence."
            ),
            score=round(rng.uniform(0.55, 0.96), 3),
            metadata={"domain": s["domain"], "simulated": True},
        )
        for s in source_pool
    ]

    _HIGH_CRED = {"nejm.org", "thelancet.com", "nature.com", "who.int", "nih.gov", "cell.com"}
    credibility = CredibilityOutput(
        claim_id="c1",
        scored_sources=[
            CredibilityScore(
                source_id=e.source_id,
                score=round(rng.uniform(0.82, 0.99), 2)
                if e.metadata.get("domain") in _HIGH_CRED
                else round(rng.uniform(0.65, 0.85), 2),
                reasoning=f"Peer-reviewed publication from {e.metadata.get('domain', 'unknown')}.",
                flags=["preprint"] if rng.random() < 0.08 else [],
            )
            for e in evidence
        ],
    )

    label, confidence = _heuristic_label(user_input, rng)
    cited = [e.source_id for e in rng.sample(evidence, min(2, len(evidence)))]

    if inject_hallucination:
        cited = cited + ["hallucinated_source_xyz"]

    verdict = Verdict(
        claim_id="c1",
        label=label,
        confidence=confidence,
        reasoning=(
            f"Based on {len(evidence)} retrieved scientific sources, the claim is assessed as "
            f"'{label}'. Evidence from cited sources provides "
            + (
                "supporting data." if label == "Supported"
                else "contradicting evidence." if label == "Refuted"
                else "inconclusive data."
            )
        ),
        citations=cited,
    )

    try:
        from src.safety.monitor import check as safety_check
        safety = safety_check(verdict, evidence, claim)
    except Exception:
        safety = SafetyReport(passed=True, flags=[], notes="safety_check_unavailable")

    return FinalResponse(
        trace_id=str(uuid.uuid4()),
        claim_text=user_input,
        per_claim=[
            PerClaimResult(
                claim=claim,
                evidence=evidence,
                credibility=credibility,
                verdict=verdict,
                safety=safety,
            )
        ],
    )
