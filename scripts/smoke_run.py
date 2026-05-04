"""End-to-end smoke run for local dev. Owner: Adel (M1+M4).

Usage:
    python scripts/smoke_run.py
    python scripts/smoke_run.py "Vaccines cause autism."

Prereqs:
    - .env with a working OPENAI_API_KEY
    - data/chroma populated (run `python scripts/ingest.py` first)

Prints the FinalResponse for each demo claim. Useful before the live demo.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.logging_setup import configure_logging  # noqa: E402
from src.orchestrator import run  # noqa: E402

DEMO_CLAIMS = [
    "Vaccines cause autism.",
    "The earth is round.",
    "Drinking bleach cures COVID-19.",
    "Vitamin C prevents the common cold.",
]


def main() -> int:
    configure_logging()
    claims = sys.argv[1:] or DEMO_CLAIMS
    for claim in claims:
        print(f"\n========== {claim} ==========")
        response = run(claim)
        if not response.per_claim:
            print("  (no fact-checkable claims extracted)")
            continue
        for pcr in response.per_claim:
            print(f"  Claim:      {pcr.claim.text}")
            print(f"  Verdict:    {pcr.verdict.label} (confidence {pcr.verdict.confidence:.2f})")
            print(f"  Reasoning:  {pcr.verdict.reasoning}")
            print(f"  Citations:  {pcr.verdict.citations}")
            print(f"  Evidence:   {[(e.source_id, round(e.score, 2)) for e in pcr.evidence]}")
            print(f"  Safety:     passed={pcr.safety.passed} flags={pcr.safety.flags}")
        print(f"  Trace ID:   {response.trace_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
