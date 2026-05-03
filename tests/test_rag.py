"""Tests for the RAG pipeline. Owner: Member 2.

Contains both CI-safe unit tests (mocked ChromaDB + embedder) and
integration tests that require a populated vector DB.

Run unit tests:      pytest tests/test_rag.py
Run integration:     pytest tests/test_rag.py -m integration
"""

from __future__ import annotations

import pytest

from src.contracts import Evidence

# =========================================================================
# Unit tests (CI-safe, no real DB or model)
# =========================================================================


class FakeEmbedder:
    """Fake embedder that returns zero vectors."""

    dim = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dim for _ in texts]


class FakeCollection:
    """Fake ChromaDB collection that returns canned results."""

    def query(self, **_kwargs):
        return {
            "ids": [["doc_101", "doc_202"]],
            "documents": [
                [
                    "Vaccination is an effective method for disease prevention.",
                    "Clinical trials demonstrate the safety profile of modern vaccines.",
                ]
            ],
            "metadatas": [
                [
                    {"title": "Vaccine Efficacy Review", "structured": False},
                    {"title": "Vaccine Safety Trials", "structured": True},
                ]
            ],
            "distances": [[0.15, 0.30]],
        }

    def count(self):
        return 2


def test_retrieve_returns_evidence_list(monkeypatch):
    """retrieve() should return a list of Evidence with correct fields."""
    import src.rag.service as svc

    monkeypatch.setattr(svc, "_embedder", FakeEmbedder())
    monkeypatch.setattr(svc, "get_collection", lambda: FakeCollection())

    results = svc.retrieve("vaccine safety", k=2)

    assert isinstance(results, list)
    assert len(results) == 2
    for e in results:
        assert isinstance(e, Evidence)


def test_retrieve_scores_are_valid(monkeypatch):
    """Similarity scores must be in [0, 1]."""
    import src.rag.service as svc

    monkeypatch.setattr(svc, "_embedder", FakeEmbedder())
    monkeypatch.setattr(svc, "get_collection", lambda: FakeCollection())

    results = svc.retrieve("test query", k=2)

    for e in results:
        assert 0.0 <= e.score <= 1.0


def test_retrieve_maps_source_id_correctly(monkeypatch):
    """source_id must come from ChromaDB document IDs."""
    import src.rag.service as svc

    monkeypatch.setattr(svc, "_embedder", FakeEmbedder())
    monkeypatch.setattr(svc, "get_collection", lambda: FakeCollection())

    results = svc.retrieve("query", k=2)

    assert results[0].source_id == "doc_101"
    assert results[1].source_id == "doc_202"


def test_retrieve_maps_title_correctly(monkeypatch):
    """title must come from metadata, not be left empty."""
    import src.rag.service as svc

    monkeypatch.setattr(svc, "_embedder", FakeEmbedder())
    monkeypatch.setattr(svc, "get_collection", lambda: FakeCollection())

    results = svc.retrieve("query", k=2)

    assert results[0].title == "Vaccine Efficacy Review"
    assert results[1].title == "Vaccine Safety Trials"


def test_retrieve_cosine_distance_to_similarity(monkeypatch):
    """Score should be 1 - distance (cosine distance → similarity)."""
    import src.rag.service as svc

    monkeypatch.setattr(svc, "_embedder", FakeEmbedder())
    monkeypatch.setattr(svc, "get_collection", lambda: FakeCollection())

    results = svc.retrieve("query", k=2)

    assert abs(results[0].score - 0.85) < 0.001
    assert abs(results[1].score - 0.70) < 0.001


class EmptyCollection:
    """Returns no results."""

    def query(self, **_kwargs):
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    def count(self):
        return 0


def test_retrieve_handles_empty_results(monkeypatch):
    """retrieve() should return an empty list when nothing matches."""
    import src.rag.service as svc

    monkeypatch.setattr(svc, "_embedder", FakeEmbedder())
    monkeypatch.setattr(svc, "get_collection", lambda: EmptyCollection())

    results = svc.retrieve("completely unrelated gibberish", k=3)

    assert results == []


def test_retrieve_raises_rag_error_on_failure(monkeypatch):
    """retrieve() should wrap exceptions in RAGError."""
    import src.rag.service as svc
    from src.errors import RAGError

    def broken_embed(texts):
        raise RuntimeError("model crashed")

    monkeypatch.setattr(svc, "_embedder", type("E", (), {"embed": broken_embed})())

    with pytest.raises(RAGError):
        svc.retrieve("anything", k=1)


# =========================================================================
# Integration tests (require populated ChromaDB)
# =========================================================================


@pytest.mark.integration
def test_retrieve_from_real_db():
    """End-to-end: requires ``python scripts/ingest.py`` to have been run."""
    from src.rag.service import retrieve

    results = retrieve("vaccines and autism", k=5)

    assert len(results) <= 5
    assert len(results) > 0
    for e in results:
        assert isinstance(e, Evidence)
        assert 0.0 <= e.score <= 1.0
        assert e.source_id
        assert e.text
