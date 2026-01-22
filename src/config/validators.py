import re
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Ticker format: 1 to 5 uppercase letters (standard US tickers)
# This can be expanded if international markets are added (e.g., TSX:RY)
TICKER_REGEX = re.compile(r'^[A-Z0-9.\-\:]{1,12}$')

def is_valid_ticker(ticker: str) -> bool:
    """
    Validate the format of a stock/fund ticker symbol.
    
    Args:
        ticker: The ticker symbol to validate.
        
    Returns:
        bool: True if valid, False otherwise.
    """
    if not ticker or not isinstance(ticker, str):
        return False
        
    # Standardize to uppercase for check
    clean_ticker = ticker.strip().upper()
    
    if TICKER_REGEX.match(clean_ticker):
        return True
    
    logger.warning(f"Invalid ticker format detected: '{ticker}'")
    return False

def validate_ticker_list(tickers: list) -> list:
    """
    Filter a list of tickers, returning only the valid ones.
    """
    return [t for t in tickers if is_valid_ticker(t)]
