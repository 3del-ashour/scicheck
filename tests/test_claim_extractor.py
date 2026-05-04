import pytest
import json
from src.agents.claim_extractor import extract_claims
from src.llm import FakeClient
from src.contracts import ClaimExtractorOutput

def test_extract_claims_success():
    # Setup mock LLM response
    mock_json = {
        "claims": [
            {"id": "c1", "text": "Vaccines cause autism.", "type": "health"},
            {"id": "c2", "text": "The earth is flat.", "type": "scientific"}
        ]
    }
    llm = FakeClient(responses={"Vaccines": json.dumps(mock_json)})
    
    user_input = "Vaccines cause autism and the earth is flat."
    output = extract_claims(user_input, llm)
    
    assert isinstance(output, ClaimExtractorOutput)
    assert output.raw_input == user_input
    assert len(output.claims) == 2
    assert output.claims[0].id == "c1"
    assert output.claims[0].type == "health"
    assert output.claims[1].text == "The earth is flat."

def test_extract_claims_empty():
    mock_json = {"claims": []}
    llm = FakeClient(responses={"Hello": json.dumps(mock_json)})
    
    output = extract_claims("Hello world", llm)
    assert len(output.claims) == 0

def test_extract_claims_invalid_json():
    llm = FakeClient(responses={"bad": "invalid json here"})
    
    with pytest.raises(Exception): # AgentError is expected
        extract_claims("bad input", llm)
