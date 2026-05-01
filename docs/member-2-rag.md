# Member 2 — RAG / Vector DB Engineer

> **Before starting:** read `README.md`, `ARCHITECTURE.md`, `CONTRACTS.md`, `ROLES.md`.
> Paste this file + `CONTRACTS.md` into Claude Code / ChatGPT for AI assistance.

## Your Mission

You build the knowledge base that makes the agents trustworthy. You ingest scientific literature into ChromaDB, expose a single retrieve function, and own the data pipeline end to end.

## Files You Own

```
src/rag/__init__.py
src/rag/service.py        # public retrieve()
src/rag/embeddings.py     # embedding model wrapper
src/rag/store.py          # ChromaDB wrapper
scripts/ingest.py         # one-shot ingestion script
data/raw/                 # gitignored
data/processed/           # gitignored
```

## Knowledge Base Choice (pick one)

| Source | Pros | Cons |
|--------|------|------|
| **SciFact corpus** (HuggingFace `allenai/scifact`) | Aligned with our eval benchmark, ~5k abstracts | Limited domain coverage |
| **PubMed abstracts** (via `pubmed_parser` or HF `ncbi/pubmed`) | Huge, biomedical | Requires more cleaning |
| **Cochrane / WHO guidelines** | High-credibility | Smaller volume |

**Recommendation:** start with **SciFact corpus** for D1–D2, then add a small slice of PubMed for breadth. SciFact gives you a known-good evaluation pipeline (Member 6 needs it).

## Step-by-Step Build

### Step 1 — Load the corpus

```python
# scripts/ingest.py
from datasets import load_dataset

ds = load_dataset("allenai/scifact", "corpus", split="train")
# fields: doc_id, title, abstract (list[str]), structured
```

### Step 2 — Chunk

For SciFact each abstract is already short. Just join sentences:

```python
def to_passage(row) -> dict:
    return {
        "source_id": str(row["doc_id"]),
        "title": row["title"],
        "text": " ".join(row["abstract"]),
        "metadata": {"structured": row.get("structured", False)},
    }
```

For longer documents (PubMed full text), use a 512-token sliding window with 50-token overlap.

### Step 3 — Embeddings (`src/rag/embeddings.py`)

```python
from sentence_transformers import SentenceTransformer
from src.config import get_settings

class Embedder:
    def __init__(self) -> None:
        self.model = SentenceTransformer(get_settings().embedding_model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()
```

`all-MiniLM-L6-v2` produces 384-dim vectors; fast on CPU; good enough for SciFact.

### Step 4 — Store (`src/rag/store.py`)

```python
import chromadb
from src.config import get_settings

def get_collection():
    client = chromadb.PersistentClient(path=get_settings().chroma_path)
    return client.get_or_create_collection(
        name="scicheck",
        metadata={"hnsw:space": "cosine"},
    )
```

### Step 5 — Ingest

```python
# scripts/ingest.py (continued)
from src.rag.embeddings import Embedder
from src.rag.store import get_collection

def main():
    coll = get_collection()
    embedder = Embedder()
    rows = [to_passage(r) for r in ds]
    embeddings = embedder.embed([r["text"] for r in rows])
    coll.upsert(
        ids=[r["source_id"] for r in rows],
        documents=[r["text"] for r in rows],
        metadatas=[{"title": r["title"], **r["metadata"]} for r in rows],
        embeddings=embeddings,
    )
    print(f"Ingested {len(rows)} passages.")

if __name__ == "__main__":
    main()
```

### Step 6 — Retrieve (`src/rag/service.py`) — THE CONTRACT

```python
from src.contracts import Evidence
from src.rag.embeddings import Embedder
from src.rag.store import get_collection
from src.config import get_settings

_embedder: Embedder | None = None  # lazy singleton

def _emb() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder

def retrieve(query: str, k: int | None = None) -> list[Evidence]:
    k = k or get_settings().top_k
    coll = get_collection()
    q_emb = _emb().embed([query])[0]
    res = coll.query(
        query_embeddings=[q_emb],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    out: list[Evidence] = []
    ids = res["ids"][0]
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    for sid, doc, meta, dist in zip(ids, docs, metas, dists):
        out.append(Evidence(
            source_id=sid,
            title=meta.get("title", ""),
            text=doc,
            score=1.0 - float(dist),   # cosine distance → similarity
            metadata=meta,
        ))
    return out
```

### Step 7 — Indexing technique notes (for the report)

- **Index type:** HNSW (Chroma default). Approximate nearest neighbor — sub-ms queries on millions of vectors.
- **Distance metric:** cosine (we normalize embeddings, so equivalent to inner product).
- **Trade-offs to mention:** HNSW vs IVF vs flat. We chose HNSW for low-latency interactive use.

### Step 8 — Tests

`tests/test_rag.py`:

```python
from src.contracts import Evidence
from src.rag.service import retrieve

def test_retrieve_returns_evidence():
    out = retrieve("vaccine safety", k=3)
    assert len(out) <= 3
    for e in out:
        assert isinstance(e, Evidence)
        assert 0.0 <= e.score <= 1.0
```

This test requires a populated DB. Mark it with `@pytest.mark.integration` and skip in CI unless a fixture seeds a tiny in-memory collection.

For CI-friendly tests, use a **mock collection**:

```python
def test_retrieve_with_fake_collection(monkeypatch):
    class FakeColl:
        def query(self, **_):
            return {
                "ids": [["s1"]],
                "documents": [["text"]],
                "metadatas": [[{"title": "t"}]],
                "distances": [[0.1]],
            }
    monkeypatch.setattr("src.rag.service.get_collection", lambda: FakeColl())
    monkeypatch.setattr("src.rag.service._emb", lambda: type("E", (), {"embed": lambda *_: [[0.0]*384]})())
    out = retrieve("q", k=1)
    assert out[0].source_id == "s1"
```

## Best Practices for You

- **Chunk first, embed once, store forever.** Don't re-embed on every dev iteration. Save processed chunks to `data/processed/passages.jsonl` so re-ingestion is fast.
- **Stable IDs.** `source_id` should be deterministic (e.g., `doc_id` or hash of text). Other agents cite by this ID.
- **Don't expose ChromaDB types.** Other members only see `Evidence`. Keep ChromaDB inside `src/rag/`.
- **Document your indexing parameters** — the report needs this section.
- **Track corpus size and ingestion time** — useful numbers for the report.

## Definition of Done for Member 2

- [ ] `python scripts/ingest.py` populates `data/chroma/` end-to-end.
- [ ] `retrieve("vaccines and autism", k=5)` returns 5 valid `Evidence` instances.
- [ ] `tests/test_rag.py` passes both unit (mocked) and integration (real DB) tests.
- [ ] Recall@5 measured on a 50-claim sample (write to `eval/rag_metrics.json`).
- [ ] Report section on indexing technique drafted (~1 page).

## Report Sections You Write

- Knowledge base description (sources, size, license)
- Vector DB indexing techniques (HNSW, cosine, embedding model choice)
- RAG-level metrics (recall@k, MRR)
