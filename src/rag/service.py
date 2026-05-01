"""RAG service. Owner: Member 2.

Public entry: retrieve(query, k) -> list[Evidence]

Implementation notes (to be filled in):
- Use chromadb.PersistentClient(path=settings.chroma_path)
- Collection name: "scicheck"
- Embed query with sentence-transformers (settings.embedding_model)
- Map raw Chroma results into contracts.Evidence (DO NOT return dicts)
"""
from __future__ import annotations

from src.contracts import Evidence


def retrieve(query: str, k: int = 5) -> list[Evidence]:
    raise NotImplementedError("Member 2: implement against ChromaDB.")
