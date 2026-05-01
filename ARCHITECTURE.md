# Architecture

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Streamlit UI (Member 6)                      │
│              user types claim → renders verdict + sources            │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ FinalResponse
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LangGraph Orchestrator (Member 1)                 │
│                                                                      │
│   START → ClaimExtractor → Retriever → Credibility → Verdict →      │
│                                              SafetyMonitor → END    │
│                                                                      │
│   Maintains shared `GraphState` (Pydantic). Logs every transition.  │
└──┬───────────────┬──────────────┬───────────────┬──────────────┬────┘
   │               │              │               │              │
   ▼               ▼              ▼               ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐ ┌─────────┐ ┌────────────┐
│ Claim    │  │ Evidence │  │ Source       │ │ Verdict │ │ Safety     │
│ Extractor│  │ Retriever│  │ Credibility  │ │ Synth   │ │ Monitor    │
│ (M3)     │  │ (M4)     │  │ Analyzer (M3)│ │ (M4)    │ │ (M5)       │
└──────────┘  └─────┬────┘  └──────────────┘ └─────────┘ └────────────┘
                    │
                    ▼
              ┌────────────────────────┐
              │  RAG Service (M2)      │
              │  ChromaDB +            │
              │  sentence-transformers │
              └────────────────────────┘

         ┌─────────────────────────────────────────────────┐
         │  Evaluation Pipeline (Member 6)                 │
         │  SciFact benchmark → metrics → JSON report      │
         └─────────────────────────────────────────────────┘
```

## Data Flow (Happy Path)

1. **User input** → `UserQuery(text="Vaccines cause autism.")`
2. **Claim Extractor** → `ClaimExtractorOutput(claims=[Claim(id="c1", text="Vaccines cause autism.", type="health")])`
3. **Evidence Retriever** (calls RAG service) → `RetrievalOutput(claim_id="c1", evidence=[Evidence(...), ...])`
4. **Source Credibility Analyzer** → `CredibilityOutput(claim_id="c1", scored_sources=[...])`
5. **Verdict Synthesizer** → `Verdict(claim_id="c1", label="Refuted", confidence=0.94, citations=[...])`
6. **Safety Monitor** → `SafetyReport(passed=True, flags=[], notes="...")`
7. **Final Response** → `FinalResponse(...)` returned to UI.

If Safety Monitor flags an issue (`passed=False`), the orchestrator either re-runs verdict synthesis with stricter prompting (max 1 retry) or falls back to `"Insufficient Evidence"`.

## Why This Design

- **Separation of concerns:** each agent is a pure function over typed Pydantic inputs/outputs. Easy to unit-test in isolation.
- **Single source of truth for state:** the orchestrator owns `GraphState`. Agents never share globals.
- **RAG is a service:** Member 4 calls a stable retrieval API owned by Member 2. Member 4 never touches ChromaDB directly.
- **Safety is a separate node, not a wrapper:** allows independent monitoring metrics and easy disabling for ablation studies.

## Risk Management Strategy (per project requirement #2)

| Risk | Mitigation | Owner |
|------|-----------|-------|
| Hallucinated citations | Verdict Synthesizer must only cite source IDs returned by Retriever; Safety Monitor verifies | M4 + M5 |
| Allocational/representational bias | Bias detection in Safety Monitor (regex + LLM-judge over a checklist) | M5 |
| Stale or low-quality sources | Credibility Analyzer scores sources; verdicts weight by credibility | M3 |
| Prompt injection from claim text | Input sanitizer + system prompt hardening | M1 + M5 |
| Insufficient evidence treated as "Refuted" | Verdict prompt explicitly defines "Insufficient Evidence" label | M4 |

## Evaluation Strategy (per project requirement #3)

- **Intrinsic:** retrieval recall@k, MRR, embedding similarity distribution.
- **Extrinsic (SciFact benchmark):** label accuracy (Supported/Refuted/NEI), F1, citation precision.
- **Safety:** hallucination rate (citations not in retrieved set), bias-flag rate on a curated probe set.
- Reported in `eval/results.json` and rendered in the Streamlit "Metrics" tab.
