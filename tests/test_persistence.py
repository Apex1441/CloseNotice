"""
Tests for persistence utilities.
"""
import pytest
import os
import json
from src.utils import persistence


@pytest.fixture
def temp_data_dir(tmp_path, monkeypatch):
    """Set up temporary data directories for tests."""
    data_dir = tmp_path / "data"
    config_dir = data_dir / "config"
    cache_dir = data_dir / "cache"

    monkeypatch.setattr(persistence, 'DATA_DIR', str(data_dir))
    monkeypatch.setattr(persistence, 'CONFIG_DIR', str(config_dir))
    monkeypatch.setattr(persistence, 'CACHE_DIR', str(cache_dir))
    monkeypatch.setattr(persistence, 'CONFIG_FILE', str(config_dir / 'monitored_items.json'))

    return tmp_path


def test_ensure_dirs(temp_data_dir):
    """Test that directories are created."""
    persistence.ensure_dirs()

    assert os.path.exists(persistence.CONFIG_DIR)
    assert os.path.exists(persistence.CACHE_DIR)


def test_load_monitored_items_default(temp_data_dir):
    """Test loading default monitored items when config doesn't exist."""
    items = persistence.load_monitored_items()

    assert 'funds' in items
    assert 'stocks' in items
    assert 'FNILX' in items['funds']
    assert 'UURAF' in items['stocks']


def test_save_and_load_monitored_items(temp_data_dir):
    """Test saving and loading monitored items."""
    funds = ["SPY", "QQQ"]
    stocks = ["NVDA", "AAPL"]

    persistence.save_monitored_items(funds, stocks)
    items = persistence.load_monitored_items()

    assert items['funds'] == sorted(funds)
    assert items['stocks'] == sorted(stocks)


def test_load_monitored_funds(temp_data_dir):
    """Test loading just funds."""
    persistence.save_monitored_items(["VOO", "VTI"], ["TSLA"])

    funds = persistence.load_monitored_funds()
    assert "VOO" in funds
    assert "VTI" in funds


def test_load_monitored_stocks(temp_data_dir):
    """Test loading just stocks."""
    persistence.save_monitored_items(["SPY"], ["GOOG", "MSFT"])

    stocks = persistence.load_monitored_stocks()
    assert "GOOG" in stocks
    assert "MSFT" in stocks


def test_add_item_fund(temp_data_dir):
    """Test adding a fund."""
    persistence.save_monitored_items(["FNILX"], ["UURAF"])

    items = persistence.add_item("SPY", is_fund=True)

    assert "SPY" in items['funds']
    assert "FNILX" in items['funds']


def test_add_item_stock(temp_data_dir):
    """Test adding a stock."""
    persistence.save_monitored_items(["FNILX"], ["UURAF"])

    items = persistence.add_item("NVDA", is_fund=False)

    assert "NVDA" in items['stocks']
    assert "UURAF" in items['stocks']


def test_add_item_duplicate(temp_data_dir):
    """Test adding duplicate item doesn't create duplicates."""
    persistence.save_monitored_items(["FNILX"], ["UURAF"])

    items = persistence.add_item("FNILX", is_fund=True)

    assert items['funds'].count("FNILX") == 1


def test_remove_item(temp_data_dir):
    """Test removing an item."""
    persistence.save_monitored_items(["FNILX", "SPY"], ["UURAF"])

    items = persistence.remove_item("FNILX")

    assert "FNILX" not in items['funds']
    assert "SPY" in items['funds']


def test_save_and_load_holdings_cache(temp_data_dir):
    """Test caching holdings."""
    holdings = [
        {"ticker": "AAPL", "weight": 0.05},
        {"ticker": "MSFT", "weight": 0.04}
    ]

    persistence.save_holdings_cache("FNILX", holdings)
    loaded = persistence.load_holdings_cache("FNILX")

    assert loaded is not None
    assert len(loaded) == 2
    assert loaded[0]['ticker'] == "AAPL"


def test_load_holdings_cache_not_found(temp_data_dir):
    """Test loading nonexistent cache returns None."""
    result = persistence.load_holdings_cache("NONEXISTENT")

    assert result is None


def test_case_insensitive_ticker(temp_data_dir):
    """Test that tickers are normalized to uppercase."""
    persistence.save_monitored_items(["fnilx"], ["uuraf"])
    items = persistence.load_monitored_items()

    assert "FNILX" in items['funds']
    assert "UURAF" in items['stocks']
