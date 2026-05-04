"""Evidence Retriever agent. Owner: Member 1+4 (Adel Ashour).

Public entry: retrieve_for_claim(claim, llm, k) -> RetrievalOutput

Wraps the RAG service. Optionally expands a claim into multiple search
queries via the LLM, then dedupes and reranks the union of results.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.contracts import Claim, Evidence, RetrievalOutput
from src.errors import AgentError
from src.llm import LLMClient
from src.logging_setup import get_logger
from src.rag.service import retrieve as rag_retrieve

log = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "query_expansion.txt"


def _strip_code_fence(text: str) -> str:
    """Remove ```json fences if the model wrapped its output."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.endswith("```"):
            s = s.rsplit("```", 1)[0]
    return s.strip()


def _expand(claim_text: str, llm: LLMClient) -> list[str]:
    """Return 1–3 search queries derived from the claim. Falls back to literal."""
    try:
        prompt = _PROMPT_PATH.read_text(encoding="utf-8")
        raw = llm.complete(system=prompt, user=claim_text)
        data = json.loads(_strip_code_fence(raw))
        queries = [q for q in data.get("queries", []) if isinstance(q, str) and q.strip()]
        return queries or [claim_text]
    except Exception as exc:
        log.warning("retriever.expand_fallback", error=str(exc))
        return [claim_text]


def _dedupe(items: list[Evidence]) -> list[Evidence]:
    """Keep the highest-scoring entry per source_id."""
    best: dict[str, Evidence] = {}
    for ev in items:
        cur = best.get(ev.source_id)
        if cur is None or ev.score > cur.score:
            best[ev.source_id] = ev
    return list(best.values())


def retrieve_for_claim(
    claim: Claim, llm: LLMClient, k: int = 5
) -> RetrievalOutput:
    """Run query expansion → RAG → dedup → top-k.

    Args:
        claim: the parsed claim to investigate.
        llm: the LLM client used for query expansion.
        k: max number of evidence items returned.

    Returns:
        RetrievalOutput with up to ``k`` Evidence items, ordered by score desc.

    Raises:
        AgentError: if the underlying RAG call fails irrecoverably.
    """
    log.info("retriever.start", claim_id=claim.id, claim_text=claim.text[:120])

    queries = _expand(claim.text, llm)
    pool: list[Evidence] = []
    n_queries_attempted = 0
    n_queries_succeeded = 0
    last_error: Exception | None = None

    for q in queries:
        n_queries_attempted += 1
        try:
            pool.extend(rag_retrieve(q, k=k))
            n_queries_succeeded += 1
        except Exception as exc:
            last_error = exc
            log.warning("retriever.rag_query_failed", query=q[:120], error=str(exc))

    # last-resort: try the literal claim text if expansion produced different queries
    # AND no expanded query has succeeded so far
    if not pool and queries != [claim.text]:
        n_queries_attempted += 1
        try:
            pool.extend(rag_retrieve(claim.text, k=k))
            n_queries_succeeded += 1
        except Exception as exc:
            last_error = exc
            log.warning("retriever.rag_query_failed", query=claim.text[:120], error=str(exc))

    if n_queries_attempted > 0 and n_queries_succeeded == 0:
        raise AgentError(
            f"retriever: all {n_queries_attempted} RAG calls failed: {last_error}"
        ) from last_error

    pool = _dedupe(pool)
    pool.sort(key=lambda e: e.score, reverse=True)
    top = pool[:k]

    log.info(
        "retriever.done",
        claim_id=claim.id,
        n_queries=len(queries),
        n_evidence=len(top),
        top_score=top[0].score if top else None,
    )
    return RetrievalOutput(claim_id=claim.id, evidence=top)
