"""Safety Monitor.

Owner: Risk & Evaluation Lead (Ahmet Cemil Bostanoglu)
Public entry: check(verdict, evidence, claim) -> SafetyReport

Two-layer architecture:
  Layer 1 — deterministic Python checks (always run, fast).
  Layer 2 — optional LLM judge (run when llm is provided).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from src.contracts import Claim, Evidence, SafetyReport, Verdict
from src.llm import LLMClient

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "safety_judge.txt"

# Layer 1-C: bias keyword wordlist — universals, epistemic overconfidence, identity generalisations
_BIAS_KEYWORDS: frozenset[str] = frozenset(
    {
        "always", "never", "everyone", "no one", "nobody", "everybody",
        "obviously", "clearly anyone", "all women", "all men",
        "genetically inferior", "genetically superior", "racially",
        "inferior race", "superior race",
        "all blacks", "all whites", "all asians",
    }
)

# Layer 1-D: refusal trigger patterns — harmful instructions that must not be processed
_REFUSAL_PATTERNS: list[str] = [
    r"how\s+to\s+(make|build|synthesize|create)\s+(?:a\s+|an\s+)?(weapon|bomb|poison|explosive|nerve\s+agent)",
    r"(suicide|self.harm)\s+(method|instruction|step|how)",
    r"(drink|consume|ingest|inject)\s+(?:the\s+|some\s+)?(bleach|chlorine|drain\s+cleaner)",
    r"child\s+(abuse|exploitation|pornography)",
]
_REFUSAL_RE = [re.compile(p, re.IGNORECASE) for p in _REFUSAL_PATTERNS]

# Fallback judge prompt when the file is absent
_FALLBACK_JUDGE_PROMPT = (
    "You are a safety reviewer. Given a claim, verdict, and evidence IDs, "
    "check for hallucination and bias. Output STRICT JSON: "
    '{"passed": true/false, "flags": [...], "notes": "..."}'
)


# ---------------------------------------------------------------------------
# Layer 1 — deterministic checks
# ---------------------------------------------------------------------------


def _check_citation_grounding(verdict: Verdict, evidence: list[Evidence]) -> tuple[bool, str]:
    """Every citation in the verdict must appear in the retrieved evidence."""
    valid_ids = {e.source_id for e in evidence}
    bad = [c for c in verdict.citations if c not in valid_ids]
    if bad:
        return False, f"hallucinated_citation: {bad}"
    return True, ""


def _check_confidence(verdict: Verdict) -> tuple[bool, str]:
    """Confidence must be in [0, 1]; strong labels must have confidence >= 0.5."""
    if not (0.0 <= verdict.confidence <= 1.0):
        return False, f"invalid_confidence: {verdict.confidence}"
    if verdict.label in ("Supported", "Refuted") and verdict.confidence < 0.5:
        return False, f"low_confidence_with_strong_label ({verdict.confidence:.2f})"
    return True, ""


def _check_bias_keywords(verdict: Verdict) -> tuple[bool, str]:
    """Scan reasoning for absolute universals and identity generalisations."""
    text = verdict.reasoning.lower()
    hits = [kw for kw in _BIAS_KEYWORDS if kw in text]
    if hits:
        return True, f"bias_keywords: {hits}"
    return True, ""


def _check_refusal_triggers(claim: Claim) -> tuple[bool, str]:
    """Block claims that request harmful information outright."""
    for pattern in _REFUSAL_RE:
        if pattern.search(claim.text):
            return False, "refusal_trigger: matched harmful-content pattern"
    return True, ""


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------


def check(
    verdict: Verdict,
    evidence: list[Evidence],
    claim: Claim,
    llm: LLMClient | None = None,
) -> SafetyReport:
    """Run all safety checks and return a SafetyReport.

    Layer 1 runs always. Layer 2 (LLM judge) runs only when `llm` is provided.
    Hard failures: hallucinated_citation, invalid_confidence, refusal_trigger.
    Soft warnings: bias_keywords (logged but don't set passed=False).
    """
    flags: list[str] = []
    notes_parts: list[str] = []

    # D — refusal triggers (checked first; immediately fatal)
    ok, msg = _check_refusal_triggers(claim)
    if not ok:
        flags.append("refusal_trigger")
        notes_parts.append(msg)

    # A — citation grounding
    ok, msg = _check_citation_grounding(verdict, evidence)
    if not ok:
        flags.append("hallucinated_citation")
        notes_parts.append(msg)

    # B — confidence sanity
    ok, msg = _check_confidence(verdict)
    if not ok:
        flags.append("invalid_confidence")
        notes_parts.append(msg)

    # C — bias keyword scan (soft warning only)
    _, kw_msg = _check_bias_keywords(verdict)
    if kw_msg:
        flags.append("bias_keywords")
        notes_parts.append(kw_msg)

    # Layer 2 — LLM judge
    _llm_judge_failed = False
    if llm is not None:
        try:
            prompt_text = (
                _PROMPT_PATH.read_text(encoding="utf-8")
                if _PROMPT_PATH.exists()
                else _FALLBACK_JUDGE_PROMPT
            )
            judge_user = (
                f"CLAIM: {claim.text}\n"
                f"VERDICT: {verdict.label} (confidence={verdict.confidence:.2f})\n"
                f"REASONING: {verdict.reasoning}\n"
                f"EVIDENCE_IDS: {[e.source_id for e in evidence]}\n"
                f"CITED_IDS: {verdict.citations}"
            )
            raw = llm.complete(system=prompt_text, user=judge_user)
            data = json.loads(raw)
            if not data.get("passed", True):
                _llm_judge_failed = True
                for flag in data.get("flags", []):
                    if flag not in flags:
                        flags.append(flag)
                notes_parts.append(data.get("notes", ""))
        except Exception as exc:
            notes_parts.append(f"judge_error: {exc}")

    _HARD_FAIL = {"hallucinated_citation", "invalid_confidence", "refusal_trigger"}
    passed = not bool(_HARD_FAIL & set(flags)) and not _llm_judge_failed

    report = SafetyReport(
        passed=passed,
        flags=list(dict.fromkeys(flags)),  # deduplicate, preserve order
        notes=" | ".join(p for p in notes_parts if p),
    )

    # Best-effort observability — don't let logging crash the pipeline
    try:
        from src.safety.observability import emit_event

        emit_event(claim_id=claim.id, verdict=verdict, report=report)
    except Exception:
        pass

    return report
