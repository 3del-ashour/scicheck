"""Hallucination detection module.

Owner: Risk & Evaluation Lead (Ahmet Cemil Bostanoglu)

İki strateji:
  1. Structural — Verdict.citations içindeki ID'ler retrieved evidence'da yok mu?
  2. Lexical — Reasoning'deki sayısal iddialar evidence text'inde geçiyor mu?
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.contracts import Evidence, FinalResponse, PerClaimResult, Verdict


@dataclass
class CitationHallucinationResult:
    claim_id: str
    claim_text: str
    verdict_label: str
    cited_ids: list[str]
    retrieved_ids: list[str]
    hallucinated_ids: list[str]
    is_hallucinated: bool


def check_citation_grounding(pcr: PerClaimResult) -> CitationHallucinationResult:
    """Verdict.citations içindeki her ID evidence listesinde var mı kontrol eder."""
    retrieved_ids = {e.source_id for e in pcr.evidence}
    cited_ids = pcr.verdict.citations
    hallucinated = [c for c in cited_ids if c not in retrieved_ids]
    return CitationHallucinationResult(
        claim_id=pcr.claim.id,
        claim_text=pcr.claim.text,
        verdict_label=pcr.verdict.label,
        cited_ids=list(cited_ids),
        retrieved_ids=list(retrieved_ids),
        hallucinated_ids=hallucinated,
        is_hallucinated=len(hallucinated) > 0,
    )


_NUMERIC_RE = re.compile(r"\b\d[\d,\.]*\s*%|\b\d+[\d,\.]*(?:\s*(?:fold|times|x)\b)")
_STUDY_SIZE_RE = re.compile(
    r"\b\d[\d,\.]+\s*(?:patients|subjects|participants|people|cases)\b", re.I
)


def check_lexical_grounding(pcr: PerClaimResult) -> dict:
    """Reasoning'deki sayısal/istatistiksel iddiaların evidence'da geçip geçmediğine bakar."""
    reasoning = pcr.verdict.reasoning
    evidence_corpus = " ".join(e.text for e in pcr.evidence).lower()

    factual_claims = list(set(_NUMERIC_RE.findall(reasoning) + _STUDY_SIZE_RE.findall(reasoning)))
    ungrounded = [fc for fc in factual_claims if fc.lower() not in evidence_corpus]

    return {
        "claim_id": pcr.claim.id,
        "factual_claims_in_reasoning": factual_claims,
        "ungrounded_in_evidence": ungrounded,
        "lexical_hallucination_suspected": len(ungrounded) > 0,
    }


@dataclass
class HallucinationReport:
    trace_id: str
    claim_text: str
    citation_results: list[CitationHallucinationResult] = field(default_factory=list)
    lexical_results: list[dict] = field(default_factory=list)
    any_citation_hallucination: bool = False
    any_lexical_hallucination: bool = False

    @property
    def is_clean(self) -> bool:
        return not self.any_citation_hallucination and not self.any_lexical_hallucination


def analyze_response(response: FinalResponse) -> HallucinationReport:
    """Bir FinalResponse üzerinde tüm hallucination kontrollerini çalıştırır."""
    report = HallucinationReport(trace_id=response.trace_id, claim_text=response.claim_text)
    for pcr in response.per_claim:
        cit = check_citation_grounding(pcr)
        lex = check_lexical_grounding(pcr)
        report.citation_results.append(cit)
        report.lexical_results.append(lex)
        if cit.is_hallucinated:
            report.any_citation_hallucination = True
        if lex["lexical_hallucination_suspected"]:
            report.any_lexical_hallucination = True
    return report


def evaluate_hallucination_rate(responses: list[FinalResponse]) -> dict:
    """FinalResponse listesi üzerinde hallucination istatistikleri hesaplar."""
    if not responses:
        return {"n": 0, "citation_hallucination_rate": 0.0, "lexical_hallucination_rate": 0.0, "examples": []}

    reports = [analyze_response(r) for r in responses]
    n = len(reports)
    n_cit = sum(1 for r in reports if r.any_citation_hallucination)
    n_lex = sum(1 for r in reports if r.any_lexical_hallucination)

    examples = []
    for rpt in reports:
        if rpt.any_citation_hallucination:
            for cr in rpt.citation_results:
                if cr.is_hallucinated:
                    examples.append({
                        "type": "citation_hallucination",
                        "claim": cr.claim_text[:120],
                        "hallucinated_ids": cr.hallucinated_ids,
                        "retrieved_ids": cr.retrieved_ids,
                    })
        if rpt.any_lexical_hallucination:
            for lr in rpt.lexical_results:
                if lr["lexical_hallucination_suspected"]:
                    examples.append({
                        "type": "lexical_hallucination",
                        "claim": rpt.claim_text[:120],
                        "ungrounded_facts": lr["ungrounded_in_evidence"],
                    })

    return {
        "n": n,
        "n_citation_hallucinations": n_cit,
        "n_lexical_hallucinations": n_lex,
        "citation_hallucination_rate": n_cit / n,
        "lexical_hallucination_rate": n_lex / n,
        "examples": examples[:10],
    }
