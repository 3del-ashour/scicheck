import pytest
import json
from src.agents.credibility import score_sources
from src.llm import FakeClient
from src.contracts import Evidence, CredibilityOutput

def test_score_sources_success():
    evidence = [
        Evidence(source_id="s1", title="Title 1", text="Text 1", score=0.9),
        Evidence(source_id="s2", title="Title 2", text="Text 2", score=0.8)
    ]
    
    mock_json = {
        "scores": [
            {"source_id": "s1", "score": 0.95, "reasoning": "High quality RCT", "flags": ["rct", "peer_reviewed"]},
            {"source_id": "s2", "score": 0.4, "reasoning": "Small sample size", "flags": ["small_sample"]}
        ]
    }
    
    llm = FakeClient(responses={"Claim ID: c1": json.dumps(mock_json)})
    
    output = score_sources("c1", evidence, llm)
    
    assert isinstance(output, CredibilityOutput)
    assert output.claim_id == "c1"
    assert len(output.scored_sources) == 2
    assert output.scored_sources[0].source_id == "s1"
    assert output.scored_sources[0].score == 0.95
    assert "RCT" in output.scored_sources[0].reasoning
    assert "rct" in output.scored_sources[0].flags

def test_score_sources_no_evidence():
    llm = FakeClient()
    output = score_sources("c1", [], llm)
    assert len(output.scored_sources) == 0

def test_score_sources_malformed_llm_response():
    evidence = [Evidence(source_id="s1", title="t", text="b", score=0.9)]
    llm = FakeClient(responses={"c1": "not json"})
    
    with pytest.raises(Exception):
        score_sources("c1", evidence, llm)
