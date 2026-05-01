# Integration Contracts

> **Read this before writing any code.**
>
> These are the rules every member must follow so the modules plug together on integration day. The Pydantic schemas in `src/contracts.py` are the **only** allowed format for inter-module communication.

## Rule 1 — Communicate via Pydantic models, never raw dicts

If your function returns data that another member consumes, it **must** return one of the models defined in `src/contracts.py`. No `dict[str, Any]`. No tuples. No JSON strings.

## Rule 2 — Don't edit `src/contracts.py` alone

Any change to `contracts.py` requires a PR with at least 2 reviewers (must include Member 1). Breaking changes in this file = breaking the team.

## Rule 3 — Each module exposes a single entry function

| Module | File | Entry function | Signature |
|--------|------|----------------|-----------|
| RAG service | `src/rag/service.py` | `retrieve(query: str, k: int = 5) -> list[Evidence]` | M2 |
| Claim Extractor | `src/agents/claim_extractor.py` | `extract_claims(user_input: str) -> ClaimExtractorOutput` | M3 |
| Source Credibility | `src/agents/credibility.py` | `score_sources(claim_id: str, evidence: list[Evidence]) -> CredibilityOutput` | M3 |
| Evidence Retriever | `src/agents/retriever.py` | `retrieve_for_claim(claim: Claim, k: int = 5) -> RetrievalOutput` | M4 |
| Verdict Synthesizer | `src/agents/verdict.py` | `synthesize(claim: Claim, evidence: list[Evidence], credibility: CredibilityOutput) -> Verdict` | M4 |
| Safety Monitor | `src/safety/monitor.py` | `check(verdict: Verdict, evidence: list[Evidence], claim: Claim) -> SafetyReport` | M5 |
| Orchestrator | `src/orchestrator.py` | `run(user_input: str) -> FinalResponse` | M1 |
| UI | `src/ui/app.py` | Streamlit script (no exports) | M6 |
| Eval | `src/eval/scifact.py` | `evaluate(n_samples: int = 200) -> dict` | M6 |

If you need a new entry function, propose it in a PR — don't add side-channels.

## Rule 4 — The Pydantic schemas (canonical reference)

```python
# src/contracts.py
from pydantic import BaseModel, Field
from typing import Literal

ClaimType = Literal["scientific", "health", "general"]
VerdictLabel = Literal["Supported", "Refuted", "Insufficient Evidence"]


class Claim(BaseModel):
    id: str                                    # e.g. "c1", "c2"
    text: str
    type: ClaimType


class ClaimExtractorOutput(BaseModel):
    raw_input: str
    claims: list[Claim]


class Evidence(BaseModel):
    source_id: str                             # stable ID inside the vector DB
    title: str
    url: str | None = None
    text: str                                  # the retrieved passage
    score: float                               # cosine similarity, 0..1
    metadata: dict = Field(default_factory=dict)


class RetrievalOutput(BaseModel):
    claim_id: str
    evidence: list[Evidence]


class CredibilityScore(BaseModel):
    source_id: str
    score: float                               # 0..1
    reasoning: str
    flags: list[str] = Field(default_factory=list)   # e.g. ["preprint", "industry_funded"]


class CredibilityOutput(BaseModel):
    claim_id: str
    scored_sources: list[CredibilityScore]


class Verdict(BaseModel):
    claim_id: str
    label: VerdictLabel
    confidence: float                          # 0..1
    reasoning: str
    citations: list[str]                       # source_ids, must be subset of evidence


class SafetyReport(BaseModel):
    passed: bool
    flags: list[str]                           # e.g. ["hallucinated_citation", "bias_detected"]
    notes: str


class FinalResponse(BaseModel):
    trace_id: str                              # uuid4
    claim_text: str
    per_claim: list["PerClaimResult"]


class PerClaimResult(BaseModel):
    claim: Claim
    evidence: list[Evidence]
    credibility: CredibilityOutput
    verdict: Verdict
    safety: SafetyReport
```

## Rule 5 — Determinism in tests

Anywhere your code calls an LLM, gate it behind a `LLMClient` interface so tests can inject a fake. Reference implementation:

```python
# src/llm.py (Member 1 owns this)
from abc import ABC, abstractmethod

class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, **kwargs) -> str: ...

class OpenAIClient(LLMClient): ...
class FakeClient(LLMClient): ...   # used in tests
```

Every agent takes `llm: LLMClient` as a constructor argument. **Do not call `openai.ChatCompletion.create` directly inside an agent.**

## Rule 6 — Never mutate inputs

Agents return new objects. If you receive a `Claim`, don't change its fields — produce a new model.

## Rule 7 — Logging format

Use `structlog` (configured by Member 1). Every agent logs an event when it starts and finishes:

```python
log.info("claim_extractor.start", input_len=len(user_input))
log.info("claim_extractor.done", n_claims=len(out.claims))
```

The `trace_id` from `FinalResponse` propagates through `contextvars` so all logs for one user query share an ID.

## Rule 8 — Configuration via env vars

Read config through `src/config.py` (Member 1 owns). Never read `os.environ` directly in agents. Required keys:

```
OPENAI_API_KEY=...
CHROMA_PATH=./data/chroma
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_MODEL=gpt-4o-mini
TOP_K=5
LOG_LEVEL=INFO
```

## Rule 9 — Errors

Each entry function may raise `SciCheckError` (defined in `src/errors.py`). Orchestrator catches and returns a `FinalResponse` with `verdict.label="Insufficient Evidence"` and `safety.flags=["pipeline_error"]`. Don't let exceptions leak to the UI.

## Rule 10 — Citations must be grounded

In `Verdict.citations`, every `source_id` must appear in the `evidence` passed in. If you cite something that wasn't retrieved, the Safety Monitor will fail you. Member 4 — enforce this with an assert.
