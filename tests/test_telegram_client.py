import pytest
import requests_mock
from src.delivery.telegram_client import TelegramClient


@pytest.fixture
def telegram_client():
    return TelegramClient(bot_token="test_token", chat_id="test_chat")


def test_format_report_success(telegram_client):
    analysis_results = [
        {
            "ticker": "AAPL",
            "sentiment_score": 8,
            "top_insights": ["Insight 1", "Insight 2"],
            "rationale": "Test rationale"
        }
    ]
    report = telegram_client.format_report(analysis_results, total_articles=5)
    assert "AAPL" in report
    assert "Score: 8/10" in report
    assert "Articles analyzed: 5" in report


def test_format_report_no_news(telegram_client):
    report = telegram_client.format_report([], total_articles=0, no_news_tickers=["MSFT"])
    assert "No news today: MSFT" in report


def test_format_error_report(telegram_client):
    errors = [{"ticker": "AAPL", "error": "API Error"}]
    report = telegram_client.format_error_report(errors)
    assert "AAPL: API Error" in report
    assert "Errors (1)" in report


def test_format_report_with_runtime(telegram_client):
    """Test report formatting includes runtime."""
    results = [{"ticker": "FNILX", "sentiment_score": 7, "top_insights": ["A"], "rationale": "R"}]
    report = telegram_client.format_report(results, total_articles=50, runtime_seconds=135)
    assert "2m 15s" in report
    assert "Articles analyzed: 50" in report


def test_format_report_with_errors(telegram_client):
    """Test report formatting includes errors."""
    results = [{"ticker": "FNILX", "sentiment_score": 7, "top_insights": ["A"], "rationale": "R"}]
    errors = [{"ticker": "UURAF", "error": "API timeout"}]
    report = telegram_client.format_report(results, total_articles=40, errors=errors)
    assert "FNILX" in report
    assert "1 error" in report
    assert "UURAF: API timeout" in report


def test_format_report_multiple_results(telegram_client):
    """Test formatting with multiple analysis results."""
    results = [
        {"ticker": "FNILX", "sentiment_score": 7, "top_insights": ["Tech rally", "Energy weak"], "rationale": "R1"},
        {"ticker": "UURAF", "sentiment_score": 5, "top_insights": ["Uranium stable"], "rationale": "R2"}
    ]
    report = telegram_client.format_report(results, total_articles=100)
    assert "FNILX" in report
    assert "UURAF" in report
    assert "Score: 7/10" in report
    assert "Score: 5/10" in report


def test_format_error_report_with_partial_results(telegram_client):
    """Test error report includes partial results."""
    partial = [{"ticker": "FNILX", "sentiment_score": 7, "top_insights": ["OK"], "rationale": "R"}]
    errors = [{"ticker": "UURAF", "error": "Failed"}]
    report = telegram_client.format_error_report(errors, partial_results=partial)
    assert "FNILX" in report
    assert "Partial results" in report
    assert "UURAF: Failed" in report


def test_send_message_success(telegram_client):
    """Test successful message sending."""
    with requests_mock.Mocker() as m:
        m.post("https://api.telegram.org/bottest_token/sendMessage", json={"ok": True})
        result = telegram_client.send_message("Test message")
        assert result is True


def test_send_message_failure(telegram_client):
    """Test failed message sending."""
    with requests_mock.Mocker() as m:
        m.post("https://api.telegram.org/bottest_token/sendMessage", status_code=400)
        result = telegram_client.send_message("Test message")
        assert result is False


def test_send_daily_report(telegram_client):
    """Test sending daily report."""
    with requests_mock.Mocker() as m:
        m.post("https://api.telegram.org/bottest_token/sendMessage", json={"ok": True})
        results = [{"ticker": "FNILX", "sentiment_score": 7, "top_insights": ["A"], "rationale": "R"}]
        result = telegram_client.send_daily_report(results, total_articles=50)
        assert result is True


def test_send_market_quiet_notification(telegram_client):
    """Test market quiet notification."""
    with requests_mock.Mocker() as m:
        m.post("https://api.telegram.org/bottest_token/sendMessage", json={"ok": True})
        result = telegram_client.send_market_quiet_notification()
        assert result is True


def test_send_error_notification(telegram_client):
    """Test error notification."""
    with requests_mock.Mocker() as m:
        m.post("https://api.telegram.org/bottest_token/sendMessage", json={"ok": True})
        result = telegram_client.send_error_notification("Test error message")
        assert result is True


def test_send_test_message(telegram_client):
    """Test test message functionality."""
    with requests_mock.Mocker() as m:
        m.post("https://api.telegram.org/bottest_token/sendMessage", json={"ok": True})
        result = telegram_client.send_test_message()
        assert result is True
