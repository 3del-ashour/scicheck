"""ChromaDB store wrapper. Owner: Member 2.

Provides a thin abstraction over ChromaDB so that no other module
needs to import chromadb directly.  Collection uses HNSW index with
cosine distance (the Chroma default when ``hnsw:space`` is ``cosine``).

Persist path is read from ``src.config.get_settings().chroma_path``.
"""

from __future__ import annotations

import chromadb

from src.config import get_settings
from src.logging_setup import get_logger

log = get_logger(__name__)

_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    """Return a singleton PersistentClient."""
    global _client
    if _client is None:
        path = get_settings().chroma_path
        log.info("chroma.init", path=path)
        _client = chromadb.PersistentClient(path=path)
    return _client


def get_collection(
    name: str = "scicheck",
) -> chromadb.Collection:
    """Get or create the named ChromaDB collection.

    Args:
        name: Collection name. Defaults to ``"scicheck"``.

    Returns:
        A ``chromadb.Collection`` configured with cosine distance.
    """
    client = _get_client()
    collection = client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
    log.info("chroma.collection_ready", name=name, count=collection.count())
    return collection


def reset_client() -> None:
    """Reset the cached client (useful for testing)."""
    global _client
    _client = None
