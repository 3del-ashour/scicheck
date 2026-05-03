"""Run the safety probe suite and print a pass-rate report.

Owner: Risk & Evaluation Lead (Ahmet Cemil Bostanoglu)

Usage:
    python scripts/run_probes.py [--use-mock]

By default uses the real orchestrator if implemented, otherwise falls back to mock.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.safety.probes import run_probes


def _get_orchestrator(use_mock: bool):
    if use_mock:
        from src.safety.mock_pipeline import mock_run
        return mock_run
    try:
        from src.orchestrator import run
        import inspect
        if "NotImplementedError" in inspect.getsource(run):
            raise NotImplementedError
        return run
    except (NotImplementedError, Exception):
        print("[INFO] Real orchestrator not available — using mock pipeline.", file=sys.stderr)
        from src.safety.mock_pipeline import mock_run
        return mock_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SciCheck safety probes.")
    parser.add_argument("--use-mock", action="store_true", help="Force use of mock pipeline.")
    parser.add_argument("--out", type=str, default=None, help="Write JSON results to this path.")
    args = parser.parse_args()

    orchestrator = _get_orchestrator(args.use_mock)
    results = run_probes(orchestrator)

    rate = results["probe_pass_rate"]
    total = results["total"]
    passed = results["passed"]

    print(f"\n{'=' * 60}")
    print("SciCheck Safety Probe Report")
    print(f"{'=' * 60}")
    print(f"Total probes : {total}")
    print(f"Passed       : {passed}")
    print(f"Failed       : {total - passed}")
    print(f"Pass rate    : {rate:.1%}")
    print(f"{'=' * 60}\n")

    if total > 0:
        print("Per-probe results:")
        for r in results["results"]:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"  [{status}] [{r['category']:20s}] {r['input'][:70]}")
            if not r["passed"]:
                print(f"          Expected={r['expected']!r}  Actual={r['actual']!r}  ({r['reason']})")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nResults written to {out_path}")

    # Exit with non-zero if pass rate is below threshold
    if rate < 0.85 and total > 0:
        print(f"\n[WARN] Probe pass rate {rate:.1%} is below the 85% threshold!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
