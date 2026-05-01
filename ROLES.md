# Roles, Workflow & Definition of Done

## Role Summary

| # | Member | Role | Primary files |
|---|--------|------|---------------|
| 1 | TBD | **Project Lead / Orchestration Engineer** | `src/orchestrator.py`, `src/llm.py`, `src/config.py`, `src/errors.py`, `.github/workflows/ci.yml`, root configs |
| 2 | TBD | **RAG / Vector DB Engineer** | `src/rag/*`, `scripts/ingest.py` |
| 3 | TBD | **Agent Engineer A** (Claim + Credibility) | `src/agents/claim_extractor.py`, `src/agents/credibility.py` |
| 4 | TBD | **Agent Engineer B** (Retrieval + Verdict) | `src/agents/retriever.py`, `src/agents/verdict.py` |
| 5 | TBD | **Safety & Monitoring Engineer** | `src/safety/*`, observability dashboards in UI metrics tab |
| 6 | TBD | **UI + Evaluation Engineer** | `src/ui/app.py`, `src/eval/scifact.py`, `scripts/run_eval.py` |

## Git Workflow

- `main` is protected. Never push directly.
- Branch naming: `<member-id>/<short-description>`, e.g. `m4/verdict-prompt-v2`.
- Commit style: [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `docs:`, `test:`, `refactor:`.
- One PR per feature. Keep PRs under ~400 LOC where possible.
- Every PR needs **1 reviewer minimum** (2 if it touches `contracts.py`).
- CI must pass before merge: `ruff`, `black --check`, `pytest`.

## Daily Standup (Async, Slack/WhatsApp)

Each member posts daily:
```
Yesterday: ...
Today: ...
Blocked by: ...
```

## Definition of Done (per module)

A module is "done" when **all** of these are true:

1. Entry function in `CONTRACTS.md` is implemented and matches the signature exactly.
2. Returns a `contracts.py` Pydantic model (no raw dicts).
3. Has a unit test in `tests/` with at least one happy-path and one edge case.
4. Test uses `FakeClient` for LLM calls (no real API hits in CI).
5. Has a docstring at the top of the file describing inputs/outputs.
6. Logged with `structlog` at `start` and `done`.
7. Code passes `ruff check .` and `black --check .`.

## Internal Milestones

> Final deadline: **06.05.2025 15:00**. Reverse-planned below — adjust dates to your real start.

| Day | Deliverable | Owners |
|-----|-------------|--------|
| D1 | Repo bootstrap, `contracts.py` finalized, `.env.example`, CI green | M1 |
| D2 | RAG ingestion of corpus + retrieve() returns valid Evidence | M2 |
| D3 | Claim Extractor, Evidence Retriever agents pass unit tests | M3, M4 |
| D4 | Credibility + Verdict agents working with FakeClient | M3, M4 |
| D5 | Safety Monitor v1 (citation grounding + simple bias check) | M5 |
| D6 | Orchestrator wires all agents end-to-end with structured logs | M1 |
| D7 | Streamlit UI shows verdict + sources + safety flags | M6 |
| D8 | SciFact eval pipeline runs and writes `eval/results.json` | M6 |
| D9 | Bug bash, prompt tuning, demo polish | All |
| D10 | Record backup video, finalize PDF report | All |

## Report Sections (PDF)

The unified report's sections and primary author:

1. Cover page (all names + responsibilities) — M1
2. Project overview & objectives — M1
3. Software architecture — M1
4. Knowledge base & vector DB indexing — M2
5. Agents (claim extractor, retriever, credibility, verdict) — M3 + M4
6. Risk management & safety monitoring — M5
7. Evaluation pipeline & results — M6
8. UI design — M6
9. Conclusion & future work — All

## Demo Script (10 minutes)

1. (1 min) Problem statement & motivation — M1
2. (2 min) Architecture walkthrough — M1
3. (3 min) Live demo: 3 claims (true / false / ambiguous) — M6
4. (2 min) Safety + evaluation results — M5 + M6
5. (1 min) Closing & Q&A — All

## How to Use AI Assistants Productively

Each member has a doc at `docs/member-N-*.md`. Open it, paste it into Claude Code (or ChatGPT) along with `CONTRACTS.md`, and say:

> "I'm Member N on this project. Here's the contract and my role doc. Start by scaffolding the entry function with type hints and a failing test, then implement it step by step."

Always paste `CONTRACTS.md` — it's the source of truth.
