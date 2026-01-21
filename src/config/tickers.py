"""
Ticker watchlist configuration with sector metadata.

This module defines the stocks to track:
1. FNILX top 50 holdings (aggregated for fund-level analysis)
2. FZILX top 40 holdings (aggregated for fund-level analysis)
3. Individual stocks (analyzed separately)

Holdings are dynamically fetched from Scraper and cached.
The dictionaries below serve as fallbacks if fetching fails.

Sector tags enable the LLM to provide accurate industry-specific insights
without having to guess the business model.
"""

from typing import Dict, List
import logging
from src.utils.persistence import load_monitored_funds, load_monitored_stocks, load_holdings_cache, save_holdings_cache

logger = logging.getLogger(__name__)

# ============================================================================
# Ticker registries
# ============================================================================

FUND_HOLDINGS: Dict[str, Dict[str, str]] = {}
INDIVIDUAL_TICKERS_WITH_SECTORS: Dict[str, str] = {}
TICKER_METADATA: Dict[str, str] = {}

def _map_sector_name(raw_sector: str) -> str:
    """Map raw sector strings to internal format. (Moved up for use in init)"""
    s = raw_sector.lower()
    if 'tech' in s or 'computation' in s: return 'Tech/General'
    if 'health' in s or 'pharma' in s: return 'Healthcare/General'
    if 'financial' in s or 'finance' in s or 'bank' in s: return 'Financials/General'
    if 'energy' in s or 'oil' in s: return 'Energy/General'
    if 'consumer' in s or 'retail' in s: return 'Consumer/General'
    if 'industrial' in s: return 'Industrials/General'
    if 'utility' in s: return 'Utilities/General'
    if 'material' in s: return 'Materials/General'
    if 'estate' in s: return 'RealEstate/General'
    if 'communication' in s or 'telecom' in s: return 'Tech/Internet'
    return f"Other/{raw_sector.capitalize()}"

def _initialize_from_persistence():
    """Load monitored funds/stocks and populate holdings from cache."""
    # 1. Initialize Funds
    monitored_funds = load_monitored_funds()
    for fund in monitored_funds:
        FUND_HOLDINGS[fund] = {}
        cached_holdings = load_holdings_cache(fund)
        if cached_holdings:
            logger.info(f"Loaded {len(cached_holdings)} holdings for {fund} from cache")
            ticker_sectors = {}
            for h in cached_holdings:
                ticker = h['ticker']
                sector = _map_sector_name(h.get('sector', 'Unknown'))
                name = h.get('name', ticker)
                ticker_sectors[ticker] = sector
                if ticker not in TICKER_METADATA:
                    TICKER_METADATA[ticker] = name
            FUND_HOLDINGS[fund] = ticker_sectors
            
    # 2. Initialize Individual Stocks
    monitored_stocks = load_monitored_stocks()
    for ticker in monitored_stocks:
        # Default sector for individual stocks if not known
        # UURAF special case for backward compatibility of sector name
        sector = "Energy/Uranium" if ticker == "UURAF" else "Unknown"
        INDIVIDUAL_TICKERS_WITH_SECTORS[ticker] = sector
        if ticker not in TICKER_METADATA:
            TICKER_METADATA[ticker] = ticker

# Initialize immediately
_initialize_from_persistence()

# Backwards compatibility aliases (deprecated) - ensure they exist even if empty
FNILX_TOP50_WITH_SECTORS = FUND_HOLDINGS.get("FNILX", {})
FZILX_TOP40_WITH_SECTORS = FUND_HOLDINGS.get("FZILX", {})

# ============================================================================
# Aggregated Lists for Pipeline Use
# ============================================================================

def _rebuild_all_tickers():
    """Helper to rebuild the ALL_TICKERS list from current holdings."""
    tickers = set()
    for holdings in FUND_HOLDINGS.values():
        tickers.update(holdings.keys())
    tickers.update(INDIVIDUAL_TICKERS_WITH_SECTORS.keys())
    return list(tickers)

ALL_TICKERS = _rebuild_all_tickers()

# Analysis targets (Funds + Individual Stocks)
ANALYSIS_TARGETS = list(FUND_HOLDINGS.keys()) + list(INDIVIDUAL_TICKERS_WITH_SECTORS.keys())

# Magnificent 7 (for breadth analysis in FNILX)
MAGNIFICENT_7 = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]


def get_sector(ticker: str) -> str:
    """Get sector tag for a ticker."""
    # Check all funds
    for holdings in FUND_HOLDINGS.values():
        if ticker in holdings:
            return holdings[ticker]
            
    return INDIVIDUAL_TICKERS_WITH_SECTORS.get(ticker, "Unknown")


def get_company_name(ticker: str) -> str:
    """Get company name for a ticker."""
    return TICKER_METADATA.get(ticker, ticker)


def is_magnificent_7(ticker: str) -> bool:
    """Check if ticker is part of the Magnificent 7."""
    return ticker in MAGNIFICENT_7


def get_fnilx_tickers() -> list:
    """Get list of FNILX holdings (Helper for legacy support)."""
    return list(FUND_HOLDINGS.get("FNILX", {}).keys())


def get_fzilx_tickers() -> list:
    """Get list of FZILX holdings (Helper for legacy support)."""
    return list(FUND_HOLDINGS.get("FZILX", {}).keys())


def get_fund_holdings(fund_symbol: str) -> Dict[str, str]:
    """Get holdings dict for a specific fund."""
    return FUND_HOLDINGS.get(fund_symbol, {})

def get_all_funds() -> List[str]:
    """Get list of all tracked funds."""
    return list(FUND_HOLDINGS.keys())

def get_individual_tickers() -> list:
    """Get list of individual stocks to track."""
    return list(INDIVIDUAL_TICKERS_WITH_SECTORS.keys())


def update_fund_holdings_from_scraper(
    fund_symbol: str,
    holdings: List[Dict[str, str]]
) -> Dict[str, str]:
    """
    Update fund holdings from Scraper data.
    Dynamically registers new funds if they don't exist.
    """
    global FUND_HOLDINGS, TICKER_METADATA, ALL_TICKERS, ANALYSIS_TARGETS
    
    # Save to cache first
    try:
        save_holdings_cache(fund_symbol, holdings)
    except Exception as e:
        logger.error(f"Failed to cache holdings for {fund_symbol}: {e}")

    ticker_sectors = {}
    for holding in holdings:
        ticker = holding['ticker']
        raw_sector = holding.get('sector', 'Unknown')
        sector = _map_sector_name(raw_sector)
        name = holding.get('name', ticker)

        ticker_sectors[ticker] = sector

        # Update metadata
        if ticker not in TICKER_METADATA:
            TICKER_METADATA[ticker] = name

    # Update or create fund entry
    FUND_HOLDINGS[fund_symbol] = ticker_sectors
    
    # Update legacy pointers if applicable
    if fund_symbol == "FNILX":
        global FNILX_TOP50_WITH_SECTORS
        FNILX_TOP50_WITH_SECTORS = ticker_sectors
    elif fund_symbol == "FZILX":
        global FZILX_TOP40_WITH_SECTORS
        FZILX_TOP40_WITH_SECTORS = ticker_sectors

    # Rebuild aggregates
    ALL_TICKERS.clear()
    ALL_TICKERS.extend(_rebuild_all_tickers())
    
    # Update analysis targets if new fund
    if fund_symbol not in ANALYSIS_TARGETS:
        ANALYSIS_TARGETS.append(fund_symbol)

    return ticker_sectors

def _map_sector_name(raw_sector: str) -> str:
    """Map raw sector strings to internal format."""
    s = raw_sector.lower()
    if 'tech' in s or 'computation' in s: return 'Tech/General'
    if 'health' in s or 'pharma' in s: return 'Healthcare/General'
    if 'financial' in s or 'finance' in s or 'bank' in s: return 'Financials/General'
    if 'energy' in s or 'oil' in s: return 'Energy/General'
    if 'consumer' in s or 'retail' in s: return 'Consumer/General'
    if 'industrial' in s: return 'Industrials/General'
    if 'utility' in s: return 'Utilities/General'
    if 'material' in s: return 'Materials/General'
    if 'estate' in s: return 'RealEstate/General'
    if 'communication' in s or 'telecom' in s: return 'Tech/Internet'
    return f"Other/{raw_sector.capitalize()}"


def get_holdings_summary() -> Dict[str, int]:
    """Get summary of current holdings configuration."""
    summary = {
        'individual_count': len(INDIVIDUAL_TICKERS_WITH_SECTORS),
        'total_count': len(ALL_TICKERS)
    }
    for fund, holdings in FUND_HOLDINGS.items():
        summary[f"{fund.lower()}_count"] = len(holdings)
    return summary
