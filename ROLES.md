# Roles, Workflow & Definition of Done

## Role Summary

| # | Member | Role | Primary files |
|---|--------|------|---------------|
| 1 | **Adel Ashour** | **Project Lead / Orchestration + Agent Engineer B** | `src/orchestrator.py`, `src/llm.py`, `src/config.py`, `src/errors.py`, `.github/workflows/ci.yml`, `src/agents/retriever.py`, `src/agents/verdict.py` |
| 2 | **Salih Özgür Seçen** | **RAG / Vector DB Engineer** | `src/rag/*`, `scripts/ingest.py` |
| 3 | **Bilal Aksel** | **Agent Engineer A** (Claim + Credibility) | `src/agents/claim_extractor.py`, `src/agents/credibility.py` |
| 4 | TBD | **Safety & Monitoring Engineer** | `src/safety/*`, observability dashboards in UI metrics tab |
| 5 | **Talib Yeşildal** | **UI + Evaluation Engineer** | `src/ui/app.py`, `src/eval/scifact.py`, `scripts/run_eval.py` |
| 6 | **Ecem** | **Documentation & Presentation Lead** | Final PDF report, slide deck, backup video, demo rehearsal coordination |

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
| D1 | Repo bootstrap, `contracts.py` finalized, `.env.example`, CI green | Adel (M1) |
| D2 | RAG ingestion of corpus + retrieve() returns valid Evidence | Salih (M2) |
| D3 | Claim Extractor, Evidence Retriever agents pass unit tests | Bilal (M3), Adel (M4) |
| D4 | Credibility + Verdict agents working with FakeClient | Bilal (M3), Adel (M4) |
| D5 | Safety Monitor v1 (citation grounding + simple bias check) | TBD (M5) |
| D6 | Orchestrator wires all agents end-to-end with structured logs | Adel (M1) |
| D7 | Streamlit UI shows verdict + sources + safety flags | Talib (M6) |
| D8 | SciFact eval pipeline runs and writes `eval/results.json` | Talib (M6) |
| D9 | Bug bash, prompt tuning, demo polish | All |
| D10 | Final PDF report compiled, slide deck ready, backup video recorded | Ecem (lead) + All |

## Report Sections (PDF)

Each technical lead drafts their section; **Ecem compiles, edits for consistency, and produces the final PDF**.

| Section | Drafted by | Compiled & polished by |
|---------|-----------|------------------------|
| Cover page (all names + responsibilities) | Adel | Ecem |
| Project overview & objectives | Adel | Ecem |
| Software architecture | Adel | Ecem |
| Knowledge base & vector DB indexing | Salih | Ecem |
| Claim Extractor + Source Credibility | Bilal | Ecem |
| Evidence Retriever + Verdict Synthesizer | Adel | Ecem |
| Risk management & safety monitoring | TBD (M5) | Ecem |
| Evaluation pipeline & results | Talib | Ecem |
| UI design | Talib | Ecem |
| Conclusion & future work | Ecem (synthesizes input from all) | Ecem |

**Drafting deadline:** all members hand drafts to Ecem by **D8**. Ecem locks the final PDF on **D10**.

## Demo Script (10 minutes)

Ecem owns the slide deck and presentation flow. Each technical lead presents their own segment.

1. (1 min) Problem statement & motivation — Adel (intro) + Ecem (slides)
2. (2 min) Architecture walkthrough — Adel
3. (3 min) Live demo: 3 claims (true / false / ambiguous) — Talib
4. (2 min) Safety + evaluation results — TBD (M5) + Talib
5. (1 min) Closing & Q&A — Adel + Ecem

**Backup video:** Ecem records and uploads. Submitted as a link, not a file.

## How to Use AI Assistants Productively

Each member has a doc at `docs/member-N-*.md`. Open it, paste it into Claude Code (or ChatGPT) along with `CONTRACTS.md`, and say:

> "I'm Member N on this project. Here's the contract and my role doc. Start by scaffolding the entry function with type hints and a failing test, then implement it step by step."

Always paste `CONTRACTS.md` — it's the source of truth.
