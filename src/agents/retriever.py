"""Evidence Retriever agent. Owner: Member 4.

Public entry: retrieve_for_claim(claim, k) -> RetrievalOutput

Wraps the RAG service (src.rag.service.retrieve). May expand the query
(e.g. paraphrase, add scientific keywords) before calling RAG.
"""
from __future__ import annotations

from src.contracts import Claim, RetrievalOutput
from src.llm import LLMClient


def retrieve_for_claim(
    claim: Claim, llm: LLMClient, k: int = 5
) -> RetrievalOutput:
    raise NotImplementedError("Member 4: see docs/member-4-agent-retrieval-verdict.md")
