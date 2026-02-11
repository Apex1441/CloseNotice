import pytest
import requests_mock
from src.data.finnhub_client import FinnhubClient, RateLimitError
from src.utils.error_handler import APIAuthenticationError

def test_fetch_company_news_success():
    client = FinnhubClient(api_key="test_key")
    with requests_mock.Mocker() as m:
        m.get("https://finnhub.io/api/v1/company-news", json=[{"headline": "Test"}])
        articles = client.fetch_company_news("AAPL", "2023-01-01", "2023-01-02")
        assert len(articles) == 1
        assert articles[0]["headline"] == "Test"

def test_fetch_company_news_rate_limit():
    """Test that rate limit errors are raised correctly.

    Note: Tenacity wraps the final error in RetryError after exhausting retries.
    We test that the retry mechanism properly raises after all attempts.
    """
    from tenacity import RetryError
    client = FinnhubClient(api_key="test_key")

    with requests_mock.Mocker() as m:
        m.get("https://finnhub.io/api/v1/company-news", status_code=429)
        # After exhausting retries, tenacity raises RetryError wrapping RateLimitError
        with pytest.raises((RateLimitError, RetryError)):
            client.fetch_company_news("AAPL", "2023-01-01", "2023-01-02")

def test_fetch_company_news_auth_error():
    client = FinnhubClient(api_key="test_key")
    with requests_mock.Mocker() as m:
        m.get("https://finnhub.io/api/v1/company-news", status_code=401)
        with pytest.raises(APIAuthenticationError):
            client.fetch_company_news("AAPL", "2023-01-01", "2023-01-02")

def test_fetch_company_news_invalid_ticker():
    client = FinnhubClient(api_key="test_key")
    with pytest.raises(ValueError, match="Invalid ticker format"):
        client.fetch_company_news("INVALID_TICKER_NAME", "2023-01-01", "2023-01-02")


def test_fetch_company_news_empty_response():
    """Test handling of empty response."""
    client = FinnhubClient(api_key="test_key")
    with requests_mock.Mocker() as m:
        m.get("https://finnhub.io/api/v1/company-news", json=[])
        articles = client.fetch_company_news("AAPL", "2023-01-01", "2023-01-02")
        assert articles == []


def test_fetch_company_news_server_error():
    """Test handling of server errors."""
    client = FinnhubClient(api_key="test_key")
    with requests_mock.Mocker() as m:
        m.get("https://finnhub.io/api/v1/company-news", status_code=500)
        articles = client.fetch_company_news("AAPL", "2023-01-01", "2023-01-02")
        assert articles == []


def test_filter_relevant_articles():
    """Test article relevance filtering."""
    client = FinnhubClient(api_key="test_key")

    articles = [
        {"headline": "AAPL stock rises 5%", "summary": "Apple Inc reported strong earnings"},
        {"headline": "Microsoft Excel tutorial", "summary": "Learn spreadsheet basics"},
        {"headline": "Apple announces new product", "summary": "Tech company launches device"},
    ]

    relevant = client._filter_relevant_articles("AAPL", articles, {"AAPL": "Apple"})

    # Should include articles mentioning AAPL or Apple
    assert len(relevant) == 2
    assert any("AAPL" in a.get("headline", "") for a in relevant)


def test_filter_relevant_articles_empty():
    """Test filtering with no articles."""
    client = FinnhubClient(api_key="test_key")
    result = client._filter_relevant_articles("AAPL", [], {})
    assert result == []


def test_filter_relevant_articles_no_metadata():
    """Test filtering without company metadata."""
    client = FinnhubClient(api_key="test_key")

    articles = [{"headline": "NVDA sets new high", "summary": "GPU maker leads market"}]
    relevant = client._filter_relevant_articles("NVDA", articles, None)

    assert len(relevant) == 1


def test_get_news_summary():
    """Test news summary generation."""
    client = FinnhubClient(api_key="test_key")

    articles = [
        {"headline": "Test 1", "source": "Reuters", "datetime": 1700000000},
        {"headline": "Test 2", "source": "Bloomberg", "datetime": 1700001000},
    ]

    summary = client.get_news_summary("AAPL", articles)

    assert summary['ticker'] == "AAPL"
    assert summary['article_count'] == 2
    assert "Reuters" in summary['sources']
    assert "Bloomberg" in summary['sources']


def test_get_news_summary_empty():
    """Test news summary with no articles."""
    client = FinnhubClient(api_key="test_key")

    summary = client.get_news_summary("AAPL", [])

    assert summary['ticker'] == "AAPL"
    assert summary['article_count'] == 0
    assert summary['date_range']['earliest'] == 0
