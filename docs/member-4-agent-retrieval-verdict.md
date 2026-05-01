# Member 4 — Agent Engineer B (Evidence Retriever + Verdict Synthesizer)

> **Before starting:** read `README.md`, `ARCHITECTURE.md`, `CONTRACTS.md`, `ROLES.md`.
> Paste this file + `CONTRACTS.md` into Claude Code / ChatGPT for AI assistance.

## Your Mission

You build the two agents at the heart of the pipeline:

1. **Evidence Retriever** — turns a `Claim` into the best query for the RAG service, calls Member 2's `retrieve()`, returns ranked evidence.
2. **Verdict Synthesizer** — reads the claim, the evidence, and credibility scores, and outputs a `Supported / Refuted / Insufficient Evidence` verdict with citations.

## Files You Own

```
src/agents/retriever.py
src/agents/verdict.py
tests/test_retriever.py
tests/test_verdict.py
prompts/query_expansion.txt
prompts/verdict.txt
```

You **call** Member 2's `src.rag.service.retrieve` — you never touch ChromaDB directly.

---

## Agent 1: Evidence Retriever

### Goal

A naive retrieval just embeds the claim text and runs nearest neighbors. We do better:

- **Query expansion:** rewrite the claim into 1–3 search queries that include scientific terminology.
- **Deduplication:** merge near-duplicate passages.
- **Rerank by credibility hint:** boost titles that mention "meta-analysis", "systematic review".

### Step-by-Step

**Step 1 — Query expansion prompt** (`prompts/query_expansion.txt`):

```
You convert a fact-checkable claim into 1–3 search queries optimized for retrieving scientific abstracts.
Include scientific terminology when relevant (e.g., "MMR vaccine autism" not just "vaccines autism").
Return JSON: {"queries": ["...", "..."]}
```

**Step 2 — Implement** (`src/agents/retriever.py`):

```python
import json
from pathlib import Path
from src.contracts import Claim, Evidence, RetrievalOutput
from src.rag.service import retrieve as rag_retrieve
from src.llm import LLMClient
from src.errors import AgentError

_PROMPT = Path(__file__).parent.parent.parent / "prompts" / "query_expansion.txt"

def _expand(claim_text: str, llm: LLMClient) -> list[str]:
    raw = llm.complete(system=_PROMPT.read_text(), user=claim_text)
    try:
        return json.loads(raw)["queries"]
    except Exception:
        return [claim_text]  # fall back to literal text

def _dedupe(items: list[Evidence]) -> list[Evidence]:
    seen: set[str] = set()
    out: list[Evidence] = []
    for ev in items:
        if ev.source_id in seen:
            continue
        seen.add(ev.source_id)
        out.append(ev)
    return out

def retrieve_for_claim(claim: Claim, llm: LLMClient, k: int = 5) -> RetrievalOutput:
    queries = _expand(claim.text, llm) or [claim.text]
    pool: list[Evidence] = []
    for q in queries:
        pool.extend(rag_retrieve(q, k=k))
    pool = _dedupe(pool)
    pool.sort(key=lambda e: e.score, reverse=True)
    return RetrievalOutput(claim_id=claim.id, evidence=pool[:k])
```

**Step 3 — Test** (`tests/test_retriever.py`):

```python
import json
from src.contracts import Claim, Evidence
from src.agents.retriever import retrieve_for_claim
from src.llm import FakeClient

def test_retrieves_and_dedupes(monkeypatch):
    canned = [
        Evidence(source_id="s1", title="t", text="…", score=0.9),
        Evidence(source_id="s1", title="t", text="…", score=0.9),  # duplicate
        Evidence(source_id="s2", title="t", text="…", score=0.7),
    ]
    monkeypatch.setattr("src.agents.retriever.rag_retrieve", lambda q, k: canned)
    fake = FakeClient(responses={"vaccines": json.dumps({"queries": ["mmr autism"]})})
    out = retrieve_for_claim(Claim(id="c1", text="Vaccines cause autism", type="health"), llm=fake, k=5)
    assert {e.source_id for e in out.evidence} == {"s1", "s2"}
```

---

## Agent 2: Verdict Synthesizer

### Goal

Decide whether the claim is **Supported / Refuted / Insufficient Evidence**, with reasoning and a list of `source_id` citations.

**Hard rule (CONTRACTS.md Rule 10):** every citation must be a `source_id` that appears in `evidence`. No making up references.

### Step-by-Step

**Step 1 — Prompt** (`prompts/verdict.txt`):

```
You are a scientific fact-checker. Given a claim and a list of retrieved evidence passages
(with credibility scores), decide whether the claim is:
- "Supported": evidence clearly supports the claim.
- "Refuted": evidence clearly contradicts the claim.
- "Insufficient Evidence": evidence is mixed, off-topic, or too weak to decide.

Rules:
- Cite ONLY source_ids that appear in the provided evidence list.
- Weight more credible sources more heavily.
- Be cautious. If credibility is low overall, prefer "Insufficient Evidence".
- Output STRICT JSON:
  {
    "label": "Supported" | "Refuted" | "Insufficient Evidence",
    "confidence": 0.0,
    "reasoning": "...",
    "citations": ["source_id_1", ...]
  }
```

**Step 2 — Implement** (`src/agents/verdict.py`):

```python
import json
from pathlib import Path
from src.contracts import Claim, CredibilityOutput, Evidence, Verdict
from src.llm import LLMClient
from src.errors import AgentError

_PROMPT = Path(__file__).parent.parent.parent / "prompts" / "verdict.txt"

def _format_evidence(evidence: list[Evidence], cred: CredibilityOutput) -> str:
    cred_map = {s.source_id: s.score for s in cred.scored_sources}
    parts = []
    for e in evidence:
        c = cred_map.get(e.source_id, 0.5)
        parts.append(f"[{e.source_id}] (credibility={c:.2f}) {e.title}\n{e.text[:800]}")
    return "\n\n".join(parts)

def synthesize(
    claim: Claim,
    evidence: list[Evidence],
    credibility: CredibilityOutput,
    llm: LLMClient,
) -> Verdict:
    if not evidence:
        return Verdict(
            claim_id=claim.id,
            label="Insufficient Evidence",
            confidence=0.0,
            reasoning="No evidence retrieved.",
            citations=[],
        )
    user = f"CLAIM: {claim.text}\n\nEVIDENCE:\n{_format_evidence(evidence, credibility)}"
    raw = llm.complete(system=_PROMPT.read_text(), user=user)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise AgentError(f"Verdict invalid JSON: {raw[:200]}") from e

    valid_ids = {e.source_id for e in evidence}
    citations = [c for c in data.get("citations", []) if c in valid_ids]

    return Verdict(
        claim_id=claim.id,
        label=data["label"],
        confidence=float(data.get("confidence", 0.5)),
        reasoning=data.get("reasoning", ""),
        citations=citations,
    )
```

**Step 3 — Test** (`tests/test_verdict.py`):

```python
import json
from src.contracts import Claim, CredibilityOutput, CredibilityScore, Evidence
from src.agents.verdict import synthesize
from src.llm import FakeClient

def test_refutes_with_grounded_citations():
    claim = Claim(id="c1", text="Vaccines cause autism.", type="health")
    ev = [Evidence(source_id="s1", title="Meta", text="No association found", score=0.9)]
    cred = CredibilityOutput(claim_id="c1", scored_sources=[CredibilityScore(source_id="s1", score=0.95, reasoning="")])
    canned = json.dumps({
        "label": "Refuted",
        "confidence": 0.95,
        "reasoning": "Strong meta-analysis finds no association.",
        "citations": ["s1", "FAKE_ID"]   # the fake one must be filtered out
    })
    fake = FakeClient(responses={"Vaccines cause autism": canned})
    v = synthesize(claim, ev, cred, llm=fake)
    assert v.label == "Refuted"
    assert v.citations == ["s1"]   # FAKE_ID stripped
```

---

## Best Practices for You

- **Always include `_format_evidence` style numbering** so the LLM has stable IDs to cite.
- **Truncate passage text to ~800 chars** before sending — keeps prompts small and cheap.
- **Strip ungrounded citations** (defense in depth — Member 5's Safety Monitor will also catch them).
- **Default to "Insufficient Evidence"** when in doubt. Cautious is better than wrong.
- **Tune `confidence` range carefully** — Member 6 may use thresholds in the eval pipeline.

## Definition of Done for Member 4

- [ ] `retrieve_for_claim(claim)` returns deduped, ranked `Evidence` list.
- [ ] `synthesize(...)` returns a `Verdict` whose citations are 100% grounded.
- [ ] Unit tests pass with `FakeClient`.
- [ ] At least 3 sample claims demonstrated in a notebook or smoke script.

## Report Sections You Write

- Evidence retrieval pipeline (query expansion, dedup, rerank)
- Verdict synthesis (prompt, citation grounding, confidence calibration)
