"""
Tests for LLM prompt templates.
"""
import pytest
from src.analysis.prompts import (
    format_aggregate_prompt,
    format_individual_prompt,
    get_sentiment_label,
    get_sentiment_emoji
)


def test_get_sentiment_label_bearish():
    """Test bearish sentiment labels."""
    assert get_sentiment_label(1) == "Bearish"
    assert get_sentiment_label(2) == "Bearish"
    assert get_sentiment_label(3) == "Bearish"


def test_get_sentiment_label_neutral():
    """Test neutral sentiment labels."""
    assert get_sentiment_label(4) == "Neutral"
    assert get_sentiment_label(5) == "Neutral"
    assert get_sentiment_label(6) == "Neutral"


def test_get_sentiment_label_bullish():
    """Test bullish sentiment labels."""
    assert get_sentiment_label(7) == "Bullish"
    assert get_sentiment_label(8) == "Bullish"
    assert get_sentiment_label(9) == "Bullish"
    assert get_sentiment_label(10) == "Bullish"


def test_get_sentiment_emoji_bearish():
    """Test bearish emoji."""
    assert get_sentiment_emoji(1) == "📉"
    assert get_sentiment_emoji(3) == "📉"


def test_get_sentiment_emoji_neutral():
    """Test neutral emoji."""
    assert get_sentiment_emoji(4) == "➖"
    assert get_sentiment_emoji(6) == "➖"


def test_get_sentiment_emoji_bullish():
    """Test bullish emoji."""
    assert get_sentiment_emoji(7) == "📈"
    assert get_sentiment_emoji(10) == "📈"


def test_format_aggregate_prompt():
    """Test aggregate prompt formatting."""
    articles = [
        {
            "ticker": "AAPL",
            "sector": "Tech/Hardware",
            "headline": "Apple Q4 beats expectations",
            "summary": "Strong iPhone sales drive record revenue",
            "source": "Reuters"
        }
    ]

    prompt = format_aggregate_prompt(
        fund_name="FNILX",
        articles=articles,
        active_count=25,
        total_holdings=50
    )

    assert "FNILX" in prompt
    assert "25 out of 50" in prompt
    assert "AAPL" in prompt
    assert "Tech/Hardware" in prompt
    assert "Apple Q4" in prompt


def test_format_aggregate_prompt_empty_articles():
    """Test aggregate prompt with no articles."""
    prompt = format_aggregate_prompt(
        fund_name="FNILX",
        articles=[],
        active_count=0,
        total_holdings=50
    )

    assert "FNILX" in prompt
    assert "0 out of 50" in prompt


def test_format_individual_prompt():
    """Test individual prompt formatting."""
    articles = [
        {
            "headline": "UURAF announces new mine development",
            "summary": "Uranium energy company expands production capacity",
            "source": "Mining Weekly"
        }
    ]

    prompt = format_individual_prompt(
        ticker="UURAF",
        sector="Energy/Uranium",
        articles=articles
    )

    assert "UURAF" in prompt
    assert "Energy/Uranium" in prompt
    assert "new mine development" in prompt


def test_format_individual_prompt_multiple_articles():
    """Test individual prompt with multiple articles."""
    articles = [
        {"headline": "Article 1", "summary": "Summary 1", "source": "Source 1"},
        {"headline": "Article 2", "summary": "Summary 2", "source": "Source 2"},
    ]

    prompt = format_individual_prompt(
        ticker="NVDA",
        sector="Tech/AI",
        articles=articles
    )

    assert "Article 1" in prompt
    assert "Article 2" in prompt
    assert "Tech/AI" in prompt
