import json
from pathlib import Path

from src.contracts import CredibilityOutput, Evidence, CredibilityScore
from src.llm import LLMClient
from src.logging_setup import get_logger
from src.errors import AgentError

log = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "credibility.txt"


def score_sources(
    claim_id: str, evidence: list[Evidence], llm: LLMClient
) -> CredibilityOutput:
    """Scores the credibility of retrieved evidence for a specific claim."""
    log.info("credibility_analyzer.start", claim_id=claim_id, n_evidence=len(evidence))

    if not evidence:
        log.info("credibility_analyzer.no_evidence", claim_id=claim_id)
        return CredibilityOutput(claim_id=claim_id, scored_sources=[])

    try:
        if not _PROMPT_PATH.exists():
            raise AgentError(f"Prompt file not found: {_PROMPT_PATH}")
        
        system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")
        
        # Prepare user message
        # Format the evidence list for the LLM as suggested in docs
        evidence_str = "\n\n".join(
            [f"[{e.source_id}] Title: {e.title}\nText: {e.text[:800]}\nMetadata: {e.metadata}" for e in evidence]
        )
        user_message = f"Claim ID: {claim_id}\n\nEvidence to evaluate:\n{evidence_str}"
        
        # Call LLM
        response_text = llm.complete(system=system_prompt, user=user_message)
        
        # Strip potential code fences
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_text = "\n".join(lines).strip()

        # Parse JSON
        try:
            data = json.loads(clean_text)
            scores_data = data.get("scores", [])
            
            # Map back to CredibilityScore and ensure all requested source_ids are present
            valid_ids = {e.source_id for e in evidence}
            scored_sources = []
            
            for item in scores_data:
                sid = item.get("source_id")
                if sid in valid_ids:
                    scored_sources.append(CredibilityScore(**item))
                else:
                    log.warning("credibility_analyzer.unknown_source_id", source_id=sid)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            log.error("credibility_analyzer.parse_failed", error=str(e), response=response_text)
            raise AgentError(f"Failed to parse LLM response for credibility: {e}")

        output = CredibilityOutput(claim_id=claim_id, scored_sources=scored_sources)
        log.info("credibility_analyzer.done", claim_id=claim_id, n_scored=len(output.scored_sources))
        return output

    except Exception as e:
        log.error("credibility_analyzer.failed", claim_id=claim_id, error=str(e))
        if isinstance(e, AgentError):
            raise
        raise AgentError(f"Unexpected error in credibility analyzer: {e}")
