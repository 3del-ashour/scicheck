# SciCheck — Science & Health Misinformation Detector

A multi-agent LLM system that fact-checks science and health claims using Retrieval-Augmented Generation (RAG).

## Team

| # | Member | Role | Owns | Read these docs |
|---|--------|------|------|-----------------|
| 1 | **Adel Ashour** | Project Lead / Orchestration + Agent Engineer B | LangGraph orchestrator, integration, repo hygiene, Evidence Retriever + Verdict Synthesizer | [member-1](docs/member-1-orchestration.md) + [member-4](docs/member-4-agent-retrieval-verdict.md) |
| 2 | **Salih Özgür Seçen** | RAG / Vector DB Engineer | ChromaDB, ingestion pipeline, retrieval API | [member-2](docs/member-2-rag.md) |
| 3 | **Bilal Aksel** | Agent Engineer A | Claim Extractor + Source Credibility Analyzer | [member-3](docs/member-3-agent-claim-credibility.md) |
| 4 | Ahmet Cemil Bostanoğlu | Safety & Monitoring Engineer | Safety Monitor agent, bias/hallucination checks, logging | [member-5](docs/member-5-safety-monitoring.md) |
| 5 | **Talib Yeşildal** | UI + Evaluation Engineer | Streamlit UI, SciFact benchmark eval pipeline | [member-6](docs/member-6-ui-evaluation.md) |
| 6 | **Ecem** | Documentation & Presentation Lead | Final PDF report, slide deck, backup video, demo script | [member-7](docs/member-7-documentation-presentation.md) |



## How It Works

1. User submits a science/health claim through the Streamlit UI.
2. **Claim Extractor** parses the input into atomic claims.
3. **Evidence Retriever** queries ChromaDB for relevant scientific sources.
4. **Source Credibility Analyzer** scores how reliable each source is.
5. **Verdict Synthesizer** outputs `Supported / Refuted / Insufficient Evidence` with citations.
6. **Safety Monitor** screens the final output for hallucinations and bias.

## Tech Stack

- **Python 3.9+** (3.11+ recommended)
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

## How to Run

```bash
# 1. Clone the repo
git clone https://github.com/3del-ashour/scicheck.git
cd scicheck

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Set up environment
cp .env.example .env

# 4. Start the app
python3 -m streamlit run src/ui/app.py
```

Open **http://localhost:8501** in your browser.

> The app runs in **Mock Mode** by default (no API key needed). To enable real LLM fact-checking, open `.env` and add your API key — see `.env.example` for supported providers (OpenAI, Groq, Ollama).

## Reading Order for New Members

1. This README
2. `ARCHITECTURE.md`
3. `CONTRACTS.md` ← critical, defines how modules talk to each other
4. `ROLES.md` ← git workflow, branch rules, definition of done
5. Your own `docs/member-N-*.md`

## Deadlines

- **Final submission:** 06.05.2026 Wednesday 15:00
- **Internal milestones** in `ROLES.md`
