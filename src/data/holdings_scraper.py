
import requests
import pandas as pd
import io
import json
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class HoldingsScraper:
    """Scraper for ETF and Mutual Fund holdings from StockAnalysis.com."""
    
    BASE_URL = "https://stockanalysis.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    @staticmethod
    def _clean_ticker(ticker_str: str) -> str:
        """Clean ticker symbols (e.g., 'TPE: 2330' -> '2330')."""
        if not ticker_str or pd.isna(ticker_str) or str(ticker_str).lower() == 'nan':
            return ""
        
        ticker_str = str(ticker_str).strip()
        
        # Remove exchange prefixes
        if ":" in ticker_str:
            ticker_str = ticker_str.split(":")[-1].strip()
            
        return ticker_str

    @staticmethod
    def get_holdings(ticker: str) -> Optional[List[Dict[str, str]]]:
        """
        Scrape top holdings for a ticker.
        
        Args:
            ticker: Fund symbol (e.g. FNILX, SPY)
            
        Returns:
            List of dicts with keys: 'ticker', 'name', 'sector', 'weightPercentage'
            or None if failed.
        """
        ticker = ticker.upper()
        
        # Try multiple URL patterns
        urls = [
            f"{HoldingsScraper.BASE_URL}/etf/{ticker.lower()}/holdings/",
            f"{HoldingsScraper.BASE_URL}/mutual-fund/{ticker.lower()}/holdings/",
            f"{HoldingsScraper.BASE_URL}/quote/mutf/{ticker.upper()}/holdings/",
            f"{HoldingsScraper.BASE_URL}/quote/otc/{ticker.upper()}/holdings/", 
            f"{HoldingsScraper.BASE_URL}/stocks/{ticker.lower()}/holdings/"
        ]

        response = None
        for url in urls:
            try:
                r = requests.get(url, headers=HoldingsScraper.HEADERS, timeout=10)
                if r.status_code == 200:
                    response = r
                    logger.info(f"Successfully connected to {url}")
                    if "/stocks/" in url or "/quote/otc/" in url:
                        logger.warning(f"Ticker {ticker} appears to be a Stock/OTC, not a fund.")
                        return [] 
                    break
            except Exception as e:
                continue
        
        if not response:
            logger.error(f"Failed to fetch holdings page for {ticker}")
            return None

        # Try JSON extraction first (contains Sector data often)
        try:
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', response.text, re.DOTALL)
            if match:
                json_data = json.loads(match.group(1))
                holdings = HoldingsScraper._parse_json_holdings(json_data)
                if holdings:
                    logger.info(f"Extracted {len(holdings)} holdings via JSON for {ticker}")
                    return holdings
        except Exception as e:
            logger.warning(f"JSON parsing failed for {ticker}: {e}")

        # Fallback to HTML table (usually no sector data, just Ticker/Name/%)
        try:
            dfs = pd.read_html(io.StringIO(response.text))
            for df in dfs:
                cols = [str(c).lower() for c in df.columns]
                if any("symbol" in c for c in cols) and any("%" in c for c in cols):
                    return HoldingsScraper._parse_html_holdings(df)
        except Exception as e:
            logger.error(f"HTML parsing failed for {ticker}: {e}")

        logger.warning(f"No holdings found for {ticker}")
        return None

    @staticmethod
    def _parse_json_holdings(json_data: dict) -> Optional[List[Dict[str, str]]]:
        """Recursively search JSON for holdings list."""
        def find_list(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ['holdings', 'data'] and isinstance(v, list) and len(v) > 0:
                        first = v[0]
                        if isinstance(first, dict) and 'symbol' in first:
                            return v
                    res = find_list(v)
                    if res: return res
            elif isinstance(obj, list):
                for item in obj:
                    res = find_list(item)
                    if res: return res
            return None

        data_list = find_list(json_data)
        if not data_list:
            return None

        results = []
        for item in data_list:
            # Map standard keys
            ticker = HoldingsScraper._clean_ticker(item.get('symbol', ''))
            if not ticker:
                continue # Skip cash/index futures
                
            name = item.get('name', '') or item.get('companyName', '')
            # Try to find sector if available (sometimes 'sector', 'industry', etc)
            sector = item.get('sector', '') or item.get('industry', 'Unknown')
            
            # Parse weight
            weight = item.get('% Weight', 0)
            if not weight:
                 weight = item.get('weight', 0) # formatted like "7.20%" or float
            
            # Clean numeric weight if string
            if isinstance(weight, str):
                weight = weight.replace('%', '').strip()
                try:
                    weight = float(weight)
                except:
                    weight = 0.0

            if ticker:
                results.append({
                    "ticker": ticker,
                    "name": name,
                    "sector": sector,
                    "weightPercentage": weight
                })
        return results

    @staticmethod
    def _parse_html_holdings(df: pd.DataFrame) -> List[Dict[str, str]]:
        """Parse DataFrame from HTML table."""
        results = []
        # Standardize column names
        df.columns = [str(c).strip() for c in df.columns]
        
        # Identify columns
        symbol_col = next((c for c in df.columns if 'Symbol' in c or 'Ticker' in c), None)
        name_col = next((c for c in df.columns if 'Name' in c or 'Company' in c), None)
        weight_col = next((c for c in df.columns if '%' in c or 'Weight' in c), None)
        
        if not symbol_col:
            return []

        for _, row in df.iterrows():
            ticker = HoldingsScraper._clean_ticker(str(row[symbol_col]))
            if not ticker:
                continue
                
            name = str(row[name_col]) if name_col else ticker
            weight_str = str(row[weight_col]).replace('%', '') if weight_col else "0"
            try:
                weight = float(weight_str)
            except:
                weight = 0.0

            results.append({
                "ticker": ticker,
                "name": name,
                "sector": "Unknown", # HTML table rarely has sector
                "weightPercentage": weight
            })
        return results
