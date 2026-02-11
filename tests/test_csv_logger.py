import pytest
import pandas as pd
from pathlib import Path
from src.storage.csv_logger import SentimentLogger

@pytest.fixture
def temp_csv(tmp_path):
    return tmp_path / "test_sentiment.csv"

def test_ensure_csv_exists(temp_csv):
    logger = SentimentLogger(csv_path=temp_csv)
    assert temp_csv.exists()
    df = pd.read_csv(temp_csv)
    assert list(df.columns) == [
        'timestamp', 'ticker', 'sentiment_score', 
        'insights', 'rationale', 'news_count', 'success'
    ]

def test_append_sentiment(temp_csv):
    logger = SentimentLogger(csv_path=temp_csv)
    logger.append_sentiment(
        ticker="AAPL",
        sentiment_score=8,
        top_insights=["Bullish"],
        rationale="Growth is strong"
    )
    df = pd.read_csv(temp_csv)
    assert len(df) == 1
    assert df.iloc[0]['ticker'] == "AAPL"
    assert df.iloc[0]['sentiment_score'] == 8

def test_deduplication(temp_csv):
    logger = SentimentLogger(csv_path=temp_csv)
    # Append same ticker twice for same day
    logger.append_sentiment("AAPL", 5, ["A"], "R1")
    logger.append_sentiment("AAPL", 8, ["B"], "R2")
    
    df = pd.read_csv(temp_csv)
    assert len(df) == 1
    assert df.iloc[0]['sentiment_score'] == 8  # Should keep latest

def test_load_history(temp_csv):
    logger = SentimentLogger(csv_path=temp_csv)
    logger.append_sentiment("AAPL", 8, ["A"], "R")
    history = logger.load_history(ticker="AAPL")
    assert not history.empty
    assert history.iloc[0]['ticker'] == "AAPL"


def test_append_result(temp_csv):
    """Test append_result convenience method."""
    logger = SentimentLogger(csv_path=temp_csv)
    result = {
        "ticker": "FNILX",
        "sentiment_score": 7,
        "top_insights": ["Tech rally", "Energy weak"],
        "rationale": "Overall bullish due to tech sector",
        "news_count": 42
    }
    logger.append_result(result)

    df = pd.read_csv(temp_csv)
    assert len(df) == 1
    assert df.iloc[0]['ticker'] == "FNILX"
    assert df.iloc[0]['sentiment_score'] == 7
    assert "Tech rally" in df.iloc[0]['insights']


def test_get_sentiment_trend(temp_csv):
    """Test sentiment trend calculation."""
    logger = SentimentLogger(csv_path=temp_csv)

    # Add some historical data
    logger.append_sentiment("FNILX", 5, ["A"], "R1")
    logger.append_sentiment("FNILX", 6, ["B"], "R2")  # Will dedupe with above

    trend = logger.get_sentiment_trend("FNILX", days=30)

    assert trend['ticker'] == "FNILX"
    assert trend['count'] >= 1
    assert trend['mean'] is not None


def test_get_sentiment_trend_empty(temp_csv):
    """Test sentiment trend with no data."""
    logger = SentimentLogger(csv_path=temp_csv)

    trend = logger.get_sentiment_trend("NONEXISTENT", days=30)

    assert trend['ticker'] == "NONEXISTENT"
    assert trend['count'] == 0
    assert trend['mean'] is None


def test_get_latest_sentiment(temp_csv):
    """Test getting latest sentiment."""
    logger = SentimentLogger(csv_path=temp_csv)
    logger.append_sentiment("UURAF", 6, ["Uranium up", "Policy change"], "Bullish")

    latest = logger.get_latest_sentiment("UURAF")

    assert latest is not None
    assert latest['ticker'] == "UURAF"
    assert latest['sentiment_score'] == 6
    assert "Uranium up" in latest['insights']


def test_get_latest_sentiment_not_found(temp_csv):
    """Test getting latest sentiment for nonexistent ticker."""
    logger = SentimentLogger(csv_path=temp_csv)

    latest = logger.get_latest_sentiment("NONEXISTENT")

    assert latest is None


def test_get_summary_stats(temp_csv):
    """Test summary statistics."""
    logger = SentimentLogger(csv_path=temp_csv)
    logger.append_sentiment("FNILX", 7, ["A"], "R")
    logger.append_sentiment("UURAF", 6, ["B"], "R")

    stats = logger.get_summary_stats()

    assert stats['total_entries'] == 2
    assert 'FNILX' in stats['tickers']
    assert 'UURAF' in stats['tickers']
    assert stats['success_rate'] == 100.0


def test_multiple_tickers(temp_csv):
    """Test logging multiple tickers."""
    logger = SentimentLogger(csv_path=temp_csv)
    logger.append_sentiment("FNILX", 7, ["Tech up"], "Bullish")
    logger.append_sentiment("UURAF", 5, ["Uranium stable"], "Neutral")

    df = pd.read_csv(temp_csv)
    assert len(df) == 2

    fnilx_history = logger.load_history(ticker="FNILX")
    uuraf_history = logger.load_history(ticker="UURAF")

    assert len(fnilx_history) == 1
    assert len(uuraf_history) == 1
