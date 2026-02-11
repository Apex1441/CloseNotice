import pytest
from src.config.validators import is_valid_ticker, validate_ticker_list

def test_is_valid_ticker_standard():
    assert is_valid_ticker("AAPL") is True
    assert is_valid_ticker("MSFT") is True
    assert is_valid_ticker("BRK.B") is True
    assert is_valid_ticker("AMD") is True

def test_is_valid_ticker_international():
    assert is_valid_ticker("SWX:ROG") is True
    assert is_valid_ticker("LON:AZN") is True
    assert is_valid_ticker("TSX:RY") is True

def test_is_valid_ticker_invalid():
    assert is_valid_ticker("TOOLONGTICKER") is False
    assert is_valid_ticker("aapl") is True  # Should be True because it strips and uppers
    assert is_valid_ticker("") is False
    assert is_valid_ticker(None) is False
    assert is_valid_ticker("!!!") is False

def test_validate_ticker_list():
    tickers = ["AAPL", "INVALID!!!", "MSFT", "TOO_LONG_TICKER"]
    valid_tickers = validate_ticker_list(tickers)
    assert valid_tickers == ["AAPL", "MSFT"]
