"""
Tests for ticker configuration and utilities.
"""
import pytest
from src.config import tickers


def test_map_sector_name_tech():
    """Test tech sector mapping."""
    assert tickers._map_sector_name("Technology") == "Tech/General"
    assert tickers._map_sector_name("Computation Services") == "Tech/General"


def test_map_sector_name_health():
    """Test healthcare sector mapping."""
    assert tickers._map_sector_name("Healthcare") == "Healthcare/General"
    assert tickers._map_sector_name("Pharmaceutical") == "Healthcare/General"


def test_map_sector_name_financials():
    """Test financials sector mapping."""
    assert tickers._map_sector_name("Financial Services") == "Financials/General"
    assert tickers._map_sector_name("Banking") == "Financials/General"


def test_map_sector_name_energy():
    """Test energy sector mapping."""
    assert tickers._map_sector_name("Energy") == "Energy/General"
    assert tickers._map_sector_name("Oil & Gas") == "Energy/General"


def test_map_sector_name_consumer():
    """Test consumer sector mapping."""
    assert tickers._map_sector_name("Consumer Goods") == "Consumer/General"
    assert tickers._map_sector_name("Retail Trade") == "Consumer/General"


def test_map_sector_name_other():
    """Test fallback sector mapping."""
    result = tickers._map_sector_name("Aerospace")
    assert "Aerospace" in result


def test_magnificent_7():
    """Test Magnificent 7 list."""
    assert "NVDA" in tickers.MAGNIFICENT_7
    assert "AAPL" in tickers.MAGNIFICENT_7
    assert "MSFT" in tickers.MAGNIFICENT_7
    assert len(tickers.MAGNIFICENT_7) == 7


def test_get_all_funds():
    """Test get_all_funds returns list."""
    funds = tickers.get_all_funds()
    assert isinstance(funds, list)


def test_get_individual_tickers():
    """Test get_individual_tickers returns list."""
    stocks = tickers.get_individual_tickers()
    assert isinstance(stocks, list)


def test_get_fund_holdings():
    """Test get_fund_holdings returns dict."""
    result = tickers.get_fund_holdings("FNILX")
    assert isinstance(result, dict)


def test_get_fund_holdings_unknown():
    """Test get_fund_holdings for unknown fund."""
    result = tickers.get_fund_holdings("UNKNOWN_FUND")
    assert result == {}


def test_get_holdings_summary():
    """Test get_holdings_summary returns summary dict."""
    summary = tickers.get_holdings_summary()
    assert 'individual_count' in summary
    assert 'total_count' in summary


def test_get_company_name_known():
    """Test getting company name for known ticker."""
    # This will depend on what's in TICKER_METADATA
    result = tickers.get_company_name("AAPL")
    assert isinstance(result, str)


def test_get_company_name_unknown():
    """Test getting company name for unknown ticker."""
    result = tickers.get_company_name("UNKNOWN_TICKER_XYZ")
    assert result == "UNKNOWN_TICKER_XYZ"


def test_get_sector_unknown():
    """Test getting sector for unknown ticker."""
    result = tickers.get_sector("UNKNOWN_TICKER_XYZ")
    assert result == "Unknown"


def test_is_magnificent_7():
    """Test Magnificent 7 detection."""
    assert tickers.is_magnificent_7("NVDA") is True
    assert tickers.is_magnificent_7("AAPL") is True
    assert tickers.is_magnificent_7("UURAF") is False


def test_rebuild_all_tickers():
    """Test all tickers list rebuild."""
    all_tickers = tickers._rebuild_all_tickers()
    assert isinstance(all_tickers, list)


def test_analysis_targets():
    """Test analysis targets list exists."""
    assert isinstance(tickers.ANALYSIS_TARGETS, list)


def test_fund_holdings_dict():
    """Test FUND_HOLDINGS is a dict."""
    assert isinstance(tickers.FUND_HOLDINGS, dict)


def test_individual_tickers_dict():
    """Test INDIVIDUAL_TICKERS_WITH_SECTORS is a dict."""
    assert isinstance(tickers.INDIVIDUAL_TICKERS_WITH_SECTORS, dict)
