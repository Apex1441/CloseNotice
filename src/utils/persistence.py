import json
import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.getcwd(), 'data')
CONFIG_DIR = os.path.join(DATA_DIR, 'config')
CACHE_DIR = os.path.join(DATA_DIR, 'cache')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'monitored_items.json')

# Defaults if config doesn't exist
DEFAULT_FUNDS = ["FNILX", "FZILX"]
DEFAULT_STOCKS = ["UURAF"]

def ensure_dirs():
    """Ensure data directories exist."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)

def load_monitored_items() -> Dict[str, List[str]]:
    """Load all monitored items (funds and stocks)."""
    ensure_dirs()
    if not os.path.exists(CONFIG_FILE):
        # Migrating from old funds-only file if it exists
        old_file = os.path.join(CONFIG_DIR, 'monitored_funds.json')
        if os.path.exists(old_file):
            try:
                with open(old_file, 'r') as f:
                    old_data = json.load(f)
                    funds = old_data.get('funds', DEFAULT_FUNDS)
                    save_monitored_items(funds, DEFAULT_STOCKS)
                    os.remove(old_file)
            except Exception:
                save_monitored_items(DEFAULT_FUNDS, DEFAULT_STOCKS)
        else:
            save_monitored_items(DEFAULT_FUNDS, DEFAULT_STOCKS)
            
    try:
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            return {
                'funds': data.get('funds', DEFAULT_FUNDS),
                'stocks': data.get('stocks', DEFAULT_STOCKS)
            }
    except Exception as e:
        logger.error(f"Error loading monitored items: {e}")
        return {'funds': DEFAULT_FUNDS, 'stocks': DEFAULT_STOCKS}

def save_monitored_items(funds: List[str], stocks: List[str]):
    """Save both funds and stocks to monitor."""
    ensure_dirs()
    funds = sorted(list(set([f.upper() for f in funds])))
    stocks = sorted(list(set([s.upper() for s in stocks])))
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({
                'funds': funds, 
                'stocks': stocks,
                'updated_at': datetime.now().isoformat()
            }, f, indent=2)
        logger.info(f"Saved {len(funds)} funds and {len(stocks)} stocks to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Error saving monitored items: {e}")

def load_monitored_funds() -> List[str]:
    """Load list of funds to monitor."""
    return load_monitored_items()['funds']

def load_monitored_stocks() -> List[str]:
    """Load list of individual stocks to monitor."""
    return load_monitored_items()['stocks']

def add_item(symbol: str, is_fund: bool = True) -> Dict[str, List[str]]:
    """Add a fund or stock to the list."""
    items = load_monitored_items()
    key = 'funds' if is_fund else 'stocks'
    if symbol.upper() not in items[key]:
        items[key].append(symbol.upper())
        save_monitored_items(items['funds'], items['stocks'])
    return items

def remove_item(symbol: str) -> Dict[str, List[str]]:
    """Remove a symbol from either list."""
    items = load_monitored_items()
    if symbol.upper() in items['funds']:
        items['funds'].remove(symbol.upper())
    if symbol.upper() in items['stocks']:
        items['stocks'].remove(symbol.upper())
    
    save_monitored_items(items['funds'], items['stocks'])
    return items

def save_holdings_cache(ticker: str, holdings: List[Dict[str, Any]]):
    """Save holdings to cache."""
    ensure_dirs()
    ticker = ticker.upper()
    file_path = os.path.join(CACHE_DIR, f"{ticker}_holdings.json")
    try:
        data = {
            'ticker': ticker,
            'updated_at': datetime.now().isoformat(),
            'holdings': holdings
        }
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Cached holdings for {ticker}")
    except Exception as e:
        logger.error(f"Error caching holdings for {ticker}: {e}")

def load_holdings_cache(ticker: str) -> Optional[List[Dict[str, Any]]]:
    """Load holdings from cache if exists."""
    ticker = ticker.upper()
    file_path = os.path.join(CACHE_DIR, f"{ticker}_holdings.json")
    
    if not os.path.exists(file_path):
        return None
        
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data.get('holdings')
    except Exception as e:
        logger.error(f"Error loading cache for {ticker}: {e}")
        return None
