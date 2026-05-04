import json
from pathlib import Path

from src.contracts import ClaimExtractorOutput, Claim
from src.llm import LLMClient
from src.logging_setup import get_logger
from src.errors import AgentError

log = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "claim_extractor.txt"


def extract_claims(user_input: str, llm: LLMClient) -> ClaimExtractorOutput:
    """Extracts atomic claims from user input using LLM."""
    log.info("claim_extractor.start", input_len=len(user_input))

    try:
        if not _PROMPT_PATH.exists():
            raise AgentError(f"Prompt file not found: {_PROMPT_PATH}")
        
        system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")
        
        # Call LLM
        response_text = llm.complete(system=system_prompt, user=user_input)
        
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
            claims = [Claim(**c) for c in data.get("claims", [])]
        except (json.JSONDecodeError, ValueError) as e:
            log.error("claim_extractor.parse_failed", error=str(e), response=response_text)
            raise AgentError(f"Failed to parse LLM response: {e}")

        output = ClaimExtractorOutput(raw_input=user_input, claims=claims)
        log.info("claim_extractor.done", n_claims=len(output.claims))
        return output

    except Exception as e:
        log.error("claim_extractor.failed", error=str(e))
        if isinstance(e, AgentError):
            raise
        raise AgentError(f"Unexpected error in claim extractor: {e}")
