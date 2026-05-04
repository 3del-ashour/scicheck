# Member 2 — RAG & Vector DB Engineering Report

> **Author:** Salih Özgür Seçen — RAG / Vector DB Engineer
> **Project:** SciCheck — Scientific Claim Verification System

---

## 1. Introduction

This document provides a technical explanation of the **Knowledge Base Construction**, **Vector Indexing**, and **RAG (Retrieval-Augmented Generation) Pipeline** components of the SciCheck project. It details how the evidence base used for verifying scientific claims is constructed, the vector indexing strategy, and how real-time similarity search operates.

## 2. Knowledge Base Construction

### 2.1 Dataset: SciFact Corpus

The **SciFact** dataset (`allenai/scifact`) by Allen AI was used as the knowledge base. This dataset is downloaded as a tar.gz archive from SciFact's official S3 repository.

| Property | Value |
|----------|-------|
| **Source** | SciFact S3 — `allenai/scifact` (corpus split) |
| **Number of documents** | ~5,183 scientific abstracts |
| **Domain** | Biomedical / health sciences |
| **Format** | Each document: `doc_id`, `title`, `abstract` (list of sentences), `structured` flag |
| **License** | CC BY-NC 2.0 |

**Why SciFact?**
- The project's evaluation pipeline (Member 6) also uses the SciFact benchmark, ensuring that retrieval and end-to-end metrics can be measured consistently on the same dataset.
- The abstracts are already concise and do not require additional preprocessing.
- Claim-evidence pairings are verified, enabling gold-standard retrieval testing.

### 2.2 Chunking Strategy

SciFact abstracts average **~150 words** in length, which aligns well with the ideal input length of our embedding model (256-token window, with support up to 512). Therefore:

- **Each abstract is processed as a single passage.** The sentence list (`abstract` field) is joined with spaces (`" ".join(abstract)`) to produce a single string.
- Sub-chunking has not been applied because semantic coherence may be lost in texts of this length.
- If longer documents (e.g., full-text PubMed articles) are added in the future, a 512-token sliding window + 50-token overlap strategy is recommended.

```python
def to_passage(row: dict) -> dict:
    abstract_text = " ".join(row["abstract"]) if row.get("abstract") else ""
    return {
        "source_id": str(row["doc_id"]),
        "title": row.get("title", ""),
        "text": abstract_text,
        "metadata": {"structured": row.get("structured", False)},
    }
```

### 2.3 Data Preprocessing and Storage

Processed passages are saved to `data/processed/passages.jsonl`. This ensures:
- No need to re-download from the source on repeated runs.
- The passage structure can be inspected in JSON format.
- Re-ingestion is faster.

## 3. Vector Indexing

### 3.1 Embedding Model

| Parameter | Value |
|-----------|-------|
| **Model** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Dimensions** | 384-dimensional vectors |
| **Normalization** | L2-normalized (cosine similarity == inner product) |
| **Training data** | 1B+ sentence pairs (NLI, paraphrase, QA) |
| **Speed** | ~14,000 sentences/second on CPU |

Reasons for selecting this model:
1. **Low dimensionality (384-d)**: Reduces storage and query costs.
2. **High performance**: Best performance/speed ratio for its size on the MTEB benchmark.
3. **CPU compatibility**: Does not require a GPU; runs easily in development environments.
4. **Normalization support**: With `normalize_embeddings=True`, vectors are scaled to unit length, reducing cosine similarity computation to a simple dot product.

### 3.2 Vector Database: ChromaDB

| Parameter | Value |
|-----------|-------|
| **Database** | ChromaDB (PersistentClient) |
| **Storage path** | `./data/chroma` (configurable) |
| **Collection name** | `scicheck` |
| **Index type** | HNSW (Hierarchical Navigable Small World) |
| **Distance metric** | Cosine distance |
| **Query complexity** | O(log n) — sub-ms response time even at million-scale |

**Why HNSW?**
ChromaDB uses the HNSW index by default. Comparison with alternatives:

| Index Type | Advantage | Disadvantage |
|------------|-----------|--------------|
| **Flat (Brute-force)** | 100% exact results | O(n) — slow on large datasets |
| **IVF (Inverted File)** | Medium speed, low memory | Requires a training phase, risk of low recall |
| **HNSW** ✅ | O(log n) query, high recall (~98%+) | Higher memory usage |

At the 5K document scale, flat search would also suffice; however, HNSW is the natural choice for scalability and ChromaDB integration.

### 3.3 Cosine Distance → Cosine Similarity Conversion

ChromaDB returns cosine **distance** (0 = identical, 2 = opposite). We convert this to a **similarity** score:

```
similarity = 1.0 - distance
```

This score is returned in the `Evidence.score` field, normalized to the [0, 1] range.

## 4. RAG Pipeline

### 4.1 Architecture Overview

```
User Claim
    │
    ▼
┌───────────────────┐
│  Embedding Model  │  ← sentence-transformers/all-MiniLM-L6-v2
│  (query encode)   │
└────────┬──────────┘
         │ 384-d vector
         ▼
┌───────────────────┐
│    ChromaDB       │  ← HNSW index, cosine distance
│  (similarity      │
│   search, top-k)  │
└────────┬──────────┘
         │ ids, documents, metadatas, distances
         ▼
┌───────────────────┐
│  Evidence Mapper  │  ← ChromaDB results → contracts.Evidence
│  (score norm.)    │
└────────┬──────────┘
         │ list[Evidence]
         ▼
   Orchestrator / Agents
```

### 4.2 `retrieve()` Function — Contract Surface

```python
def retrieve(query: str, k: int = 5) -> list[Evidence]:
```

This function is the project's **sole retrieval interface**. Other team members (especially Member 4 — Evidence Retriever) do not access ChromaDB directly; they only call this function.

**Behavior:**
1. Vectorizes the query string using the embedding model.
2. Performs a cosine similarity search on the ChromaDB collection.
3. Maps raw results to the `contracts.Evidence` Pydantic model.
4. Returns a list sorted by descending similarity score.

**Error handling:**
- Any embedding or database error is wrapped and raised as a `RAGError` exception.
- The Orchestrator catches this error and applies graceful degradation.

### 4.3 Lazy Singleton Pattern

The embedding model is loaded on the first call and reused on subsequent calls:

```python
_embedder: Embedder | None = None

def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
```

This pattern:
- Limits cold-start time to the first query only (~2–3 seconds for model loading).
- Provides ~10ms latency on subsequent queries.
- Optimizes memory usage (single model instance).

### 4.4 Structured Logging

All operations are logged in JSON format using `structlog`:

```json
{"event": "rag.retrieve.start", "query": "vaccines cause autism", "k": 5, "timestamp": "..."}
{"event": "rag.retrieve.done", "n_results": 5, "top_score": 0.87, "timestamp": "..."}
```

The `trace_id` is propagated as a context variable, allowing all logs for a single user query to be correlated.

## 5. Ingestion Pipeline

### 5.1 Usage

```bash
# Full ingestion
python scripts/ingest.py

# Development/testing — only the first 100 documents
python scripts/ingest.py --limit 100
```

### 5.2 Pipeline Steps

| Step | Description | Duration (approx.) |
|------|-------------|---------------------|
| 1. Dataset loading | Download SciFact corpus from S3 | ~5s (first time), <1s after cache |
| 2. Passage conversion | Join abstract sentences, filter empty | <1s |
| 3. Embedding | Vectorize all passages in batches | ~8–10s (CPU) |
| 4. ChromaDB upsert | Write vectors to database in batches | ~6s |
| 5. JSONL export | Save processed passages to disk | <1s |
| **Total** | | **~22s** |

### 5.3 Batch Processing

Both embedding and ChromaDB upsert operations are performed in batches of 256:
- Prevents memory overflow.
- Progress is logged.
- Scalable to larger datasets.

## 6. Testing Strategy

### 6.1 Unit Tests (CI-Safe)

Tests that do not require a real database or model loading, using `monkeypatch` to mock ChromaDB and the embedding model:

| Test | Verified Behavior |
|------|-------------------|
| `test_retrieve_returns_evidence_list` | Return type is `list[Evidence]` |
| `test_retrieve_scores_are_valid` | Scores are within the [0, 1] range |
| `test_retrieve_maps_source_id_correctly` | ChromaDB IDs are mapped correctly |
| `test_retrieve_maps_title_correctly` | Title is extracted from metadata |
| `test_retrieve_cosine_distance_to_similarity` | Distance → similarity conversion is correct |
| `test_retrieve_handles_empty_results` | Empty result case is handled |
| `test_retrieve_raises_rag_error_on_failure` | Errors are wrapped in `RAGError` |

### 6.2 Integration Tests

Tests marked with `@pytest.mark.integration` run against a real ChromaDB instance and embedding model:

```bash
pytest tests/test_rag.py -m integration
```

## 7. File Structure

```
src/rag/
├── __init__.py          # Package init
├── embeddings.py        # Embedding model wrapper (Embedder class)
├── store.py             # ChromaDB wrapper (get_collection)
└── service.py           # Public API: retrieve() — CONTRACT

scripts/
└── ingest.py            # One-shot ingestion pipeline

tests/
└── test_rag.py          # Unit + integration tests

data/
├── raw/
│   └── corpus.jsonl     # Downloaded raw data (cache)
├── chroma/              # ChromaDB persistent storage (gitignored)
└── processed/
    └── passages.jsonl   # Processed passages cache (gitignored)
```

## 8. Configuration

All settings are read as environment variables via `src/config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `CHROMA_PATH` | `./data/chroma` | ChromaDB storage path |
| `TOP_K` | `5` | Default number of retrieval results |

## 9. Conclusion and Future Work

The current RAG pipeline provides a consistent and reliable retrieval infrastructure using the SciFact corpus. In the future:

- **PubMed expansion**: PubMed abstracts can be added for broader biomedical coverage.
- **Hybrid search**: Sparse (BM25) + dense (embedding) retrieval can be combined.
- **Re-ranking**: Top-k results can be re-ranked using a cross-encoder.
- **Chunking strategy**: Sliding window chunking can be added for longer documents.
