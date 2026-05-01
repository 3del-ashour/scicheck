"""Run the SciFact eval and write JSON. Owner: Member 6."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from src.eval.scifact import evaluate


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    results = evaluate(n_samples=n)
    out = Path("eval/results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
