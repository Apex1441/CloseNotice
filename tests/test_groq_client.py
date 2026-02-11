import pytest
from src.analysis.groq_client import GroqClient

@pytest.fixture
def groq_client():
    return GroqClient(api_key="test_key")

def test_validate_result_valid(groq_client):
    valid_result = {
        "ticker": "AAPL",
        "sentiment_score": 8,
        "top_insights": ["Insight 1", "Insight 2"],
        "rationale": "This is a long enough rationale for the test."
    }
    validated = groq_client._validate_result(valid_result)
    assert validated["sentiment_score"] == 8
    assert len(validated["top_insights"]) == 2

def test_validate_result_invalid_score(groq_client):
    invalid_result = {
        "ticker": "AAPL",
        "sentiment_score": 15,
        "top_insights": ["Insight 1", "Insight 2"],
        "rationale": "This is a long enough rationale for the test."
    }
    with pytest.raises(ValueError, match="Invalid sentiment_score"):
        groq_client._validate_result(invalid_result)

def test_validate_result_missing_field(groq_client):
    invalid_result = {
        "ticker": "AAPL",
        "sentiment_score": 8,
        "rationale": "This is a long enough rationale for the test."
    }
    with pytest.raises(ValueError, match="Missing required fields"):
        groq_client._validate_result(invalid_result)

def test_validate_result_short_rationale(groq_client):
    invalid_result = {
        "ticker": "AAPL",
        "sentiment_score": 8,
        "top_insights": ["Insight 1", "Insight 2"],
        "rationale": "Short"
    }
    with pytest.raises(ValueError, match="Rationale too short"):
        groq_client._validate_result(invalid_result)

def test_parse_llm_response_json(groq_client):
    raw = '{"ticker": "AAPL", "sentiment_score": 5, "top_insights": ["A"], "rationale": "Long enough rationale for test"}'
    parsed = groq_client.parse_llm_response(raw)
    assert parsed["ticker"] == "AAPL"

def test_parse_llm_response_markdown(groq_client):
    raw = 'Some text before\n```json\n{"ticker": "AAPL", "sentiment_score": 5, "top_insights": ["A"], "rationale": "Long enough rationale for test"}\n```\nSome text after'
    parsed = groq_client.parse_llm_response(raw)
    assert parsed["ticker"] == "AAPL"
