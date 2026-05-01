# Member 3 — Agent Engineer A (Claim Extractor + Source Credibility)

> **Before starting:** read `README.md`, `ARCHITECTURE.md`, `CONTRACTS.md`, `ROLES.md`.
> Paste this file + `CONTRACTS.md` into Claude Code / ChatGPT for AI assistance.

## Your Mission

You build two agents:

1. **Claim Extractor** — turns messy user input into atomic, fact-checkable claims.
2. **Source Credibility Analyzer** — scores how trustworthy each retrieved source is.

Both are pure functions over Pydantic types (no global state). Both call an `LLMClient` injected by the orchestrator.

## Files You Own

```
src/agents/claim_extractor.py
src/agents/credibility.py
tests/test_claim_extractor.py
tests/test_credibility.py
prompts/claim_extractor.txt        (optional, store prompts as text files)
prompts/credibility.txt
```

---

## Agent 1: Claim Extractor

### Goal

Input: a free-text user query (may contain multiple claims, opinions, or questions).
Output: a list of atomic, fact-checkable claims with type tags.

### Examples

| Input | Output claims |
|-------|--------------|
| `"Vaccines cause autism."` | `[Claim(id="c1", text="Vaccines cause autism.", type="health")]` |
| `"Coffee causes cancer but vitamin D prevents it."` | `[Claim("c1", "Coffee causes cancer.", "health"), Claim("c2", "Vitamin D prevents cancer.", "health")]` |
| `"Is the earth flat?"` | `[Claim("c1", "The earth is flat.", "scientific")]` |
| `"What time is it?"` | `[]` (no fact-checkable claim) |

### Step-by-Step

**Step 1 — Write the system prompt** (`prompts/claim_extractor.txt`):

```
You are a scientific claim extractor. Given user input, extract atomic claims that can be fact-checked.

Rules:
- Each claim must be a single, declarative sentence.
- Convert questions into the asserted claim ("Is X true?" -> "X is true.").
- Tag each claim's type as one of: "scientific", "health", "general".
- Ignore opinions, instructions, and meta-commentary.
- Return STRICT JSON: {"claims": [{"id": "c1", "text": "...", "type": "..."}]}
- If no fact-checkable claims, return {"claims": []}.
```

**Step 2 — Implement** (`src/agents/claim_extractor.py`):

```python
import json
from pathlib import Path
from src.contracts import Claim, ClaimExtractorOutput
from src.llm import LLMClient
from src.errors import AgentError

_PROMPT = Path(__file__).parent.parent.parent / "prompts" / "claim_extractor.txt"

def extract_claims(user_input: str, llm: LLMClient) -> ClaimExtractorOutput:
    system = _PROMPT.read_text()
    raw = llm.complete(system=system, user=user_input)
    try:
        data = json.loads(raw)
        claims = [Claim(**c) for c in data.get("claims", [])]
    except (json.JSONDecodeError, ValueError) as e:
        raise AgentError(f"Claim extractor returned invalid JSON: {raw[:200]}") from e
    return ClaimExtractorOutput(raw_input=user_input, claims=claims)
```

**Step 3 — Test** (`tests/test_claim_extractor.py`):

```python
import json
from src.agents.claim_extractor import extract_claims
from src.llm import FakeClient

def test_extracts_single_claim():
    canned = json.dumps({"claims": [{"id": "c1", "text": "Vaccines cause autism.", "type": "health"}]})
    fake = FakeClient(responses={"Vaccines cause autism": canned})
    out = extract_claims("Vaccines cause autism.", llm=fake)
    assert len(out.claims) == 1
    assert out.claims[0].type == "health"

def test_no_claim_for_pure_question():
    fake = FakeClient(responses={"What time": json.dumps({"claims": []})})
    out = extract_claims("What time is it?", llm=fake)
    assert out.claims == []
```

**Step 4 — Robustness:**

- Use OpenAI's `response_format={"type": "json_object"}` if available — wrap that in your `OpenAIClient.complete()` (coordinate with Member 1).
- Add `temperature=0.0` for deterministic extraction.
- If the LLM returns extra text, strip code fences before `json.loads`.

---

## Agent 2: Source Credibility Analyzer

### Goal

Input: a list of `Evidence` (retrieved passages).
Output: per-source credibility score + flags + reasoning.

A source is more credible if:
- It's a peer-reviewed journal vs preprint vs blog.
- It's recent (recency depends on field).
- It's a meta-analysis or RCT vs single observational study.
- It has no obvious conflicts of interest.

Source is less credible if:
- Predatory journal markers in metadata.
- Industry-funded with relevant conflict.
- Retracted (check metadata if available).

### Step-by-Step

**Step 1 — Prompt** (`prompts/credibility.txt`):

```
You are a research credibility analyst. For each scientific passage, score it 0.0–1.0 on credibility and explain why.

Signals:
- Study design (meta-analysis > RCT > cohort > case-report > opinion)
- Publication venue (top-tier journal > mid-tier > preprint > blog)
- Sample size and methodology rigor as inferable from the passage
- Conflicts of interest mentioned
- Retraction or correction notices

Output STRICT JSON:
{
  "scores": [
    {"source_id": "...", "score": 0.0, "reasoning": "...", "flags": ["preprint", ...]}
  ]
}

Allowed flags: "peer_reviewed", "preprint", "meta_analysis", "rct", "cohort", "case_report",
"industry_funded", "retracted", "small_sample", "old_study", "high_quality_journal".
```

**Step 2 — Implement** (`src/agents/credibility.py`):

```python
import json
from pathlib import Path
from src.contracts import CredibilityOutput, CredibilityScore, Evidence
from src.llm import LLMClient
from src.errors import AgentError

_PROMPT = Path(__file__).parent.parent.parent / "prompts" / "credibility.txt"

def score_sources(claim_id: str, evidence: list[Evidence], llm: LLMClient) -> CredibilityOutput:
    if not evidence:
        return CredibilityOutput(claim_id=claim_id, scored_sources=[])
    payload = "\n\n".join(
        f"[{e.source_id}] Title: {e.title}\nText: {e.text[:800]}\nMetadata: {e.metadata}"
        for e in evidence
    )
    raw = llm.complete(system=_PROMPT.read_text(), user=payload)
    try:
        data = json.loads(raw)
        scores = [CredibilityScore(**s) for s in data["scores"]]
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise AgentError(f"Credibility analyzer invalid JSON: {raw[:200]}") from e
    # Defensive: keep only scores for sources we actually passed in
    valid_ids = {e.source_id for e in evidence}
    scores = [s for s in scores if s.source_id in valid_ids]
    return CredibilityOutput(claim_id=claim_id, scored_sources=scores)
```

**Step 3 — Test** (`tests/test_credibility.py`):

```python
import json
from src.contracts import Evidence
from src.agents.credibility import score_sources
from src.llm import FakeClient

def test_scores_each_source():
    ev = [
        Evidence(source_id="s1", title="Meta-analysis of vaccine safety", text="…", score=0.9),
        Evidence(source_id="s2", title="Anti-vax blog post", text="…", score=0.7),
    ]
    canned = json.dumps({"scores": [
        {"source_id": "s1", "score": 0.95, "reasoning": "meta", "flags": ["meta_analysis"]},
        {"source_id": "s2", "score": 0.10, "reasoning": "blog", "flags": []},
    ]})
    fake = FakeClient(responses={"s1": canned})
    out = score_sources("c1", ev, llm=fake)
    assert len(out.scored_sources) == 2
    assert out.scored_sources[0].score > 0.9
```

---

## Best Practices for You

- **Prompt versioning.** Keep prompts in `prompts/*.txt` so you can A/B test without code changes.
- **One agent = one responsibility.** The Claim Extractor doesn't fact-check; the Credibility Analyzer doesn't decide truth.
- **Be defensive with LLM JSON.** Strip ```json fences. Validate with Pydantic.
- **Empty input is valid input.** Both agents must handle empty cases without crashing.
- **Don't fail the whole pipeline on one bad source.** Filter, don't crash.

## Definition of Done for Member 3

- [ ] `extract_claims("Vaccines cause autism")` returns 1 claim with `type="health"`.
- [ ] `score_sources(...)` returns one credibility score per evidence item.
- [ ] Both agents have unit tests using `FakeClient` (no real API in CI).
- [ ] Both agents return Pydantic models from `contracts.py`.
- [ ] Prompts are stored as text files and version-controlled.

## Report Sections You Write

- Claim Extractor design (prompt strategy, examples, failure modes)
- Source Credibility Analyzer (scoring rubric, flag taxonomy)
