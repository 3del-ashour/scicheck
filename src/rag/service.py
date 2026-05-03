"""RAG service. Owner: Member 2.

Public entry: retrieve(query, k) -> list[Evidence]

This module is the **only** interface other team members use to access
the vector knowledge base.  It lazy-loads the embedding model, queries
ChromaDB with cosine similarity, and maps raw results into the
``contracts.Evidence`` Pydantic model.

Implementation details:
- ChromaDB PersistentClient at ``settings.chroma_path``
- Collection name: ``"scicheck"``
- Embedding model: ``settings.embedding_model`` (default: all-MiniLM-L6-v2)
- Distance metric: cosine  →  similarity = 1 - distance
"""
from __future__ import annotations

from src.config import get_settings
from src.contracts import Evidence
from src.errors import RAGError
from src.logging_setup import get_logger
from src.rag.embeddings import Embedder
from src.rag.store import get_collection

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Lazy singleton for the embedding model (loaded once, reused across calls)
# ---------------------------------------------------------------------------
_embedder: Embedder | None = None


def _get_embedder() -> Embedder:
    """Return (or create) the singleton Embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


# ---------------------------------------------------------------------------
# Public API — this is the contract surface for the rest of the project
# ---------------------------------------------------------------------------


def retrieve(query: str, k: int = 5) -> list[Evidence]:
    """Retrieve the top-k most relevant evidence passages for a claim.

    Args:
        query: The claim or question text to search for.
        k: Number of results to return.  Falls back to ``settings.top_k``
           when the caller passes the default.

    Returns:
        A list of ``Evidence`` objects ordered by descending similarity.

    Raises:
        RAGError: If the vector DB query or embedding step fails.
    """
    k = k or get_settings().top_k
    log.info("rag.retrieve.start", query=query[:120], k=k)

    try:
        embedder = _get_embedder()
        collection = get_collection()

        # Embed the query
        query_embedding = embedder.embed([query])[0]

        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        # Map raw Chroma output → list[Evidence]
        evidence_list: list[Evidence] = []

        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for source_id, doc_text, meta, dist in zip(ids, documents, metadatas, distances):
            similarity = 1.0 - float(dist)  # cosine distance → cosine similarity
            evidence_list.append(
                Evidence(
                    source_id=source_id,
                    title=meta.get("title", ""),
                    text=doc_text,
                    score=round(max(0.0, min(1.0, similarity)), 6),
                    metadata={k: v for k, v in meta.items() if k != "title"},
                )
            )

        log.info(
            "rag.retrieve.done",
            n_results=len(evidence_list),
            top_score=evidence_list[0].score if evidence_list else None,
        )
        return evidence_list

    except Exception as exc:
        log.error("rag.retrieve.error", error=str(exc))
        raise RAGError(f"Retrieval failed: {exc}") from exc
