"""Run the bias/consistency test suite and report results.

Owner: Risk & Evaluation Lead (Ahmet Cemil Bostanoglu)

Tests whether the pipeline produces consistent verdicts across semantically
equivalent paraphrases of the same claim.

Usage:
    python scripts/run_bias_test.py [--n N] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.safety.bias_testing import run_bias_test_suite

# Representative test claims covering different scientific domains and edge cases
_DEFAULT_CLAIMS = [
    # Vaccine claims
    "Vaccines cause autism.",
    "The MMR vaccine is linked to autism in children.",
    "Vaccination reduces the risk of measles.",
    # Nutrition claims
    "Vitamin C supplements prevent the common cold.",
    "Sugar consumption increases the risk of type 2 diabetes.",
    "Omega-3 fatty acids reduce inflammation.",
    # Medical treatments
    "Aspirin reduces the risk of heart attack.",
    "Antibiotics are effective against viral infections.",
    "Statins reduce LDL cholesterol.",
    # Mental health
    "Regular exercise reduces symptoms of depression.",
    "Meditation lowers cortisol levels.",
    # Controversial / edge cases
    "Homeopathic remedies are more effective than conventional medicine.",
    "Cell phones cause brain tumors.",
    "Organic food is healthier than conventionally grown food.",
    "High-dose vitamin D supplements cure multiple sclerosis.",
]


def _get_orchestrator():
    try:
        from src.orchestrator import run
        import inspect
        if "NotImplementedError" in inspect.getsource(run):
            raise NotImplementedError
        return run
    except (NotImplementedError, Exception):
        print("[INFO] Using mock pipeline for bias testing.", file=sys.stderr)
        from src.safety.mock_pipeline import mock_run
        return mock_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bias/consistency tests.")
    parser.add_argument("--n", type=int, default=len(_DEFAULT_CLAIMS),
                        help="Number of claims to test (default: all).")
    parser.add_argument("--out", type=str, default=None, help="Write JSON results to this path.")
    args = parser.parse_args()

    orchestrator = _get_orchestrator()
    claims = _DEFAULT_CLAIMS[: args.n]

    print(f"\nRunning bias/consistency tests on {len(claims)} claims...")
    results = run_bias_test_suite(claims, orchestrator)

    rate = results["consistency_rate"]
    n_inc = results["n_inconsistent"]
    n_total = results["n_claims_tested"]

    print(f"\n{'=' * 60}")
    print("SciCheck Bias / Consistency Test Report")
    print(f"{'=' * 60}")
    print(f"Claims tested       : {n_total}")
    print(f"Consistent          : {n_total - n_inc}")
    print(f"Inconsistent        : {n_inc}")
    print(f"Consistency rate    : {rate:.1%}")
    print(f"Inconsistency rate  : {1 - rate:.1%}")
    print(f"{'=' * 60}\n")

    if n_inc > 0:
        print("Inconsistent claims (potential bias):")
        for r in results["results"]:
            if not r["consistent"]:
                print(f"\n  Claim   : {r['claim']}")
                print(f"  Verdicts: {r['verdicts']}")
                print(f"  Reason  : {r['inconsistency_reason']}")
                for i, para in enumerate(r["paraphrases"], 1):
                    print(f"  Para {i}  : {para}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
        print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    main()
