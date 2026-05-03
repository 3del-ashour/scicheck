"""Safety event logger.

Owner: Risk & Evaluation Lead (Ahmet Cemil Bostanoglu)
Writes structured JSONL events for every Safety Monitor invocation.
The Streamlit UI tails this file for the Safety Log tab.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.contracts import SafetyReport, Verdict

_LOG = Path("logs/safety_events.jsonl")


def emit_event(claim_id: str, verdict: Verdict, report: SafetyReport) -> None:
    """Append one safety event to logs/safety_events.jsonl."""
    _LOG.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": datetime.now(UTC).isoformat(),
        "claim_id": claim_id,
        "label": verdict.label,
        "confidence": verdict.confidence,
        "passed": report.passed,
        "flags": report.flags,
        "notes": report.notes,
    }
    with _LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def load_events(max_events: int = 500) -> list[dict]:
    """Load the most recent safety events from the log file."""
    if not _LOG.exists():
        return []
    lines = _LOG.read_text(encoding="utf-8").splitlines()
    events = []
    for line in lines[-max_events:]:
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events
