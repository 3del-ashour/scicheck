# Member 1 — Project Lead / Orchestration Engineer (Adel)

> **Before starting:** read `README.md`, `ARCHITECTURE.md`, `CONTRACTS.md`, `ROLES.md`.
> Paste this file + `CONTRACTS.md` into Claude Code / ChatGPT for AI assistance.
>
> **Adel covers two roles: M1 (this doc) and M4 (Retriever + Verdict, see `docs/member-4-agent-retrieval-verdict.md`).** Build M1 first to unblock the team, then move to M4.

## Your Mission

You are the integrator. Your job is to make the other members' modules work together. You write the LangGraph orchestrator that calls each agent in order, manages shared state, and returns a `FinalResponse` to the UI.

You also own repo hygiene: CI, env config, the LLM client interface, error handling, logging. After M1 is stable, you build the Evidence Retriever and Verdict Synthesizer agents (M4).

## Files You Own

```
src/orchestrator.py
src/llm.py
src/config.py
src/errors.py
src/logging_setup.py
.github/workflows/ci.yml
.env.example
README.md, ARCHITECTURE.md, CONTRACTS.md, ROLES.md  (custodian)
```

## Architecture You're Implementing

```
START
  │
  ▼
extract_claims(user_input) → ClaimExtractorOutput
  │
  ▼ (for each claim, sequentially or parallel)
retrieve_for_claim(claim) → RetrievalOutput
  │
  ▼
score_sources(claim_id, evidence) → CredibilityOutput
  │
  ▼
synthesize(claim, evidence, credibility) → Verdict
  │
  ▼
check(verdict, evidence, claim) → SafetyReport
  │
  ▼
END → FinalResponse (aggregated PerClaimResult list)
```

Use **LangGraph** because it gives free state management and clean visualization for the demo. If LangGraph feels heavy, a plain function pipeline is acceptable — but you must still maintain a typed `GraphState` Pydantic model.

## Step-by-Step Build

### Step 1 — `src/config.py` (already scaffolded)

Already done. Verify by running:

```bash
python -c "from src.config import get_settings; print(get_settings())"
```

### Step 2 — `src/llm.py` (already scaffolded)

Already done. Add a test in `tests/test_llm.py`:

```python
from src.llm import FakeClient

def test_fake_client_canned():
    fake = FakeClient(responses={"hello": "world"})
    assert fake.complete("sys", "say hello please") == "world"
    assert len(fake.calls) == 1
```

### Step 3 — `src/logging_setup.py` (already scaffolded)

Already done. Call `configure_logging()` from `orchestrator.run()` once.

### Step 4 — `src/errors.py` (already scaffolded)

Already done. Pattern: agents raise `AgentError` for recoverable issues; orchestrator catches and degrades to `"Insufficient Evidence"`.

### Step 5 — Define `GraphState`

Add to `src/orchestrator.py`:

```python
from pydantic import BaseModel, Field
from src.contracts import Claim, Evidence, CredibilityOutput, Verdict, SafetyReport, PerClaimResult

class GraphState(BaseModel):
    user_input: str
    claims: list[Claim] = Field(default_factory=list)
    per_claim_results: list[PerClaimResult] = Field(default_factory=list)
    trace_id: str
```

### Step 6 — Implement `run(user_input)`

```python
import uuid
from src.contracts import FinalResponse, PerClaimResult
from src.llm import OpenAIClient
from src.agents.claim_extractor import extract_claims
from src.agents.retriever import retrieve_for_claim
from src.agents.credibility import score_sources
from src.agents.verdict import synthesize
from src.safety.monitor import check
from src.logging_setup import configure_logging, get_logger
from src.errors import SciCheckError

log = get_logger(__name__)

def run(user_input: str) -> FinalResponse:
    configure_logging()
    trace_id = str(uuid.uuid4())
    llm = OpenAIClient()

    log.info("orchestrator.start", trace_id=trace_id, input_len=len(user_input))
    extracted = extract_claims(user_input, llm=llm)

    per_claim: list[PerClaimResult] = []
    for claim in extracted.claims:
        try:
            retrieval = retrieve_for_claim(claim, llm=llm)
            credibility = score_sources(claim.id, retrieval.evidence, llm=llm)
            verdict = synthesize(claim, retrieval.evidence, credibility, llm=llm)
            safety = check(verdict, retrieval.evidence, claim, llm=llm)
            if not safety.passed:
                # one retry with a stricter system prompt is allowed
                verdict = synthesize(claim, retrieval.evidence, credibility, llm=llm)
                safety = check(verdict, retrieval.evidence, claim, llm=llm)
        except SciCheckError as e:
            log.warning("orchestrator.claim_failed", claim_id=claim.id, error=str(e))
            # build a degraded result — see CONTRACTS.md Rule 9
            ...
        per_claim.append(PerClaimResult(
            claim=claim,
            evidence=retrieval.evidence,
            credibility=credibility,
            verdict=verdict,
            safety=safety,
        ))
    log.info("orchestrator.done", trace_id=trace_id, n_claims=len(per_claim))
    return FinalResponse(trace_id=trace_id, claim_text=user_input, per_claim=per_claim)
```

### Step 7 — Optionally migrate to LangGraph

Once the linear version works, wrap it in LangGraph for visualization:

```python
from langgraph.graph import StateGraph, END

def build_graph():
    g = StateGraph(GraphState)
    g.add_node("extract", node_extract)
    g.add_node("retrieve", node_retrieve)
    g.add_node("credibility", node_credibility)
    g.add_node("verdict", node_verdict)
    g.add_node("safety", node_safety)
    g.set_entry_point("extract")
    g.add_edge("extract", "retrieve")
    g.add_edge("retrieve", "credibility")
    g.add_edge("credibility", "verdict")
    g.add_edge("verdict", "safety")
    g.add_edge("safety", END)
    return g.compile()
```

You can render `graph.get_graph().draw_mermaid()` and embed in the report.

### Step 8 — Add an integration test

`tests/test_orchestrator.py`:

```python
from src.orchestrator import run
# Use FakeClient + a mocked retriever to assert end-to-end flow without hitting APIs.
```

You'll likely need to make the `OpenAIClient` injectable (`run(user_input, llm=None)`) so tests can pass a `FakeClient`.

### Step 9 — CI

Already scaffolded. Verify it goes green on the first PR.

### Step 10 — Pre-commit (optional but pro)

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks: [{id: ruff}]
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks: [{id: black}]
```

## Best Practices for You

- **You are the gatekeeper of `contracts.py`.** Reject PRs that mutate it without a 2-reviewer approval.
- **Fail loudly during dev, gracefully at runtime.** Raise during testing; degrade in `run()`.
- **Trace everything.** Use `structlog.contextvars.bind_contextvars(trace_id=...)` so every log line in one request shares an ID.
- **Keep `run()` under 80 lines.** If it grows, extract per-claim processing into a helper.

## Definition of Done for Member 1

- [ ] `run("Vaccines cause autism.")` returns a valid `FinalResponse` end-to-end.
- [ ] `tests/test_orchestrator.py` passes with `FakeClient` (no network).
- [ ] CI is green on `main`.
- [ ] `.env.example` covers every env var the code reads.
- [ ] Architecture diagram in report matches `ARCHITECTURE.md`.

## Report Sections You Write

- Cover page (name list)
- Project overview
- Software architecture
