"""Tests for the Evidence Retriever agent (Adel — M4)."""
from __future__ import annotations

import json

import pytest

from src.agents.retriever import retrieve_for_claim
from src.contracts import Claim, Evidence
from src.errors import AgentError
from src.llm import FakeClient


def test_retrieves_dedupes_and_keeps_top_k(monkeypatch):
    canned = [
        Evidence(source_id="s1", title="t", text="x", score=0.91),
        Evidence(source_id="s1", title="t", text="x", score=0.95),  # better dup wins
        Evidence(source_id="s2", title="t", text="x", score=0.70),
        Evidence(source_id="s3", title="t", text="x", score=0.60),
    ]
    monkeypatch.setattr("src.agents.retriever.rag_retrieve", lambda q, k: canned)
    fake = FakeClient(responses={"vaccines": json.dumps({"queries": ["mmr autism"]})})
    out = retrieve_for_claim(
        Claim(id="c1", text="Vaccines cause autism", type="health"), llm=fake, k=2
    )
    assert out.claim_id == "c1"
    assert [e.source_id for e in out.evidence] == ["s1", "s2"]
    assert out.evidence[0].score == 0.95


def test_falls_back_to_literal_when_expansion_returns_garbage(monkeypatch):
    monkeypatch.setattr(
        "src.agents.retriever.rag_retrieve",
        lambda q, k: [Evidence(source_id="s1", title="t", text="x", score=0.8)],
    )
    fake = FakeClient(responses={})  # returns "" → JSON parse fails → fallback
    out = retrieve_for_claim(
        Claim(id="c1", text="anything", type="general"), llm=fake, k=5
    )
    assert len(out.evidence) == 1


def test_raises_agent_error_when_rag_completely_unavailable(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("vector db offline")

    monkeypatch.setattr("src.agents.retriever.rag_retrieve", boom)
    fake = FakeClient(responses={"x": json.dumps({"queries": ["one"]})})
    with pytest.raises(AgentError):
        retrieve_for_claim(Claim(id="c1", text="x", type="general"), llm=fake, k=5)
