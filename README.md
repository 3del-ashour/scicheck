# SciCheck — Science & Health Misinformation Detector

A multi-agent LLM system that fact-checks science and health claims using Retrieval-Augmented Generation (RAG).

## Team

| # | Member | Role | Owns |
|---|--------|------|------|
| 1 | TBD | Project Lead / Orchestration Engineer | LangGraph orchestrator, integration, repo hygiene |
| 2 | TBD | RAG / Vector DB Engineer | ChromaDB, ingestion pipeline, retrieval API |
| 3 | TBD | Agent Engineer A | Claim Extractor + Source Credibility Analyzer |
| 4 | TBD | Agent Engineer B | Evidence Retriever Agent + Verdict Synthesizer |
| 5 | TBD | Safety & Monitoring Engineer | Safety Monitor agent, bias/hallucination checks, logging |
| 6 | TBD | UI + Evaluation Engineer | Streamlit UI, SciFact benchmark eval pipeline |

> Replace "TBD" with names before submitting the report (the cover page requires every student's name and responsibilities).

## How It Works

1. User submits a science/health claim through the Streamlit UI.
2. **Claim Extractor** parses the input into atomic claims.
3. **Evidence Retriever** queries ChromaDB for relevant scientific sources.
4. **Source Credibility Analyzer** scores how reliable each source is.
5. **Verdict Synthesizer** outputs `Supported / Refuted / Insufficient Evidence` with citations.
6. **Safety Monitor** screens the final output for hallucinations and bias.

## Tech Stack

- **Python 3.11+**
- **LangGraph** + **LangChain** — agent orchestration
- **ChromaDB** — vector database
- **sentence-transformers** (`all-MiniLM-L6-v2`) — embeddings (free, local)
- **OpenAI API** (`gpt-4o-mini`) — LLM backbone (cheap, fast)
- **Streamlit** — UI
- **Pydantic v2** — inter-agent contracts
- **pytest** — testing
- **ruff** + **black** — lint/format

## Repository Layout

```
scicheck/
├── README.md                    # this file
├── ARCHITECTURE.md              # system diagram + data flow
├── CONTRACTS.md                 # integration contracts (READ THIS FIRST)
├── ROLES.md                     # team roles + git workflow
├── requirements.txt
├── .env.example
├── docs/                        # per-member detailed plans
│   ├── member-1-orchestration.md
│   ├── member-2-rag.md
│   ├── member-3-agent-claim-credibility.md
│   ├── member-4-agent-retrieval-verdict.md
│   ├── member-5-safety-monitoring.md
│   └── member-6-ui-evaluation.md
├── src/
│   ├── contracts.py             # Pydantic schemas — DO NOT EDIT WITHOUT TEAM APPROVAL
│   ├── orchestrator.py          # Member 1
│   ├── rag/                     # Member 2
│   ├── agents/                  # Members 3 & 4
│   ├── safety/                  # Member 5
│   ├── ui/                      # Member 6
│   └── eval/                    # Member 6
├── tests/
├── data/                        # raw + processed datasets (gitignored)
└── scripts/                     # ingestion, eval scripts
```

## Quick Start

```bash
git clone https://github.com/3del-ashour/scicheck.git
cd scicheck
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your OPENAI_API_KEY
python scripts/ingest.py   # build the vector DB
streamlit run src/ui/app.py
```

## Reading Order for New Members

1. This README
2. `ARCHITECTURE.md`
3. `CONTRACTS.md` ← critical, defines how modules talk to each other
4. `ROLES.md` ← git workflow, branch rules, definition of done
5. Your own `docs/member-N-*.md`

## Deadlines

- **Final submission:** 06.05.2025 Wednesday 15:00
- **Internal milestones** in `ROLES.md`
