"""Embedding model wrapper. Owner: Member 2.

Wraps sentence-transformers to provide a clean embed() interface.
Uses the model name from centralized config (default: all-MiniLM-L6-v2, 384-dim).
Embeddings are L2-normalized so cosine similarity == inner product.
"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

from src.config import get_settings
from src.logging_setup import get_logger

log = get_logger(__name__)


class Embedder:
    """Lazy-loaded sentence-transformers wrapper with normalized output."""

    def __init__(self, model_name: str | None = None) -> None:
        model_name = model_name or get_settings().embedding_model
        log.info("embedder.loading", model=model_name)
        self.model = SentenceTransformer(model_name)
        self._dim = self.model.get_sentence_embedding_dimension()
        log.info("embedder.ready", model=model_name, dim=self._dim)

    @property
    def dim(self) -> int:
        """Embedding dimensionality (e.g. 384 for all-MiniLM-L6-v2)."""
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Encode a batch of texts into normalized embedding vectors.

        Args:
            texts: List of strings to embed.

        Returns:
            List of float lists, each of length ``self.dim``.
        """
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 64,
        )
        return vectors.tolist()
