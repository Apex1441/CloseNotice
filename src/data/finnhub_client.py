"""
Finnhub API client for fetching company news.

Features:
- Rate limiting with exponential backoff (tenacity)
- Empty ticker filtering (only return tickers with news)
- Relevance filtering (remove "Microsoft Excel" noise)
- Weekend gap handling (72-hour lookback on Sunday/Monday)
- Retry logic for 429 rate limit errors
"""

import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from src.config.settings import Settings
from src.config.tickers import get_company_name, get_sector
from src.config.validators import is_valid_ticker
from src.utils.logger import setup_logger, log_api_call
from src.utils.error_handler import APIAuthenticationError, ErrorContext

logger = setup_logger(__name__)


class RateLimitError(Exception):
    """Raised when API rate limit is hit."""
    pass


class FinnhubClient:
    """Client for interacting with Finnhub API."""

    def __init__(self, api_key: str = None):
        """
        Initialize Finnhub client.

        Args:
            api_key: Finnhub API key (defaults to Settings.FINNHUB_API_KEY)
        """
        self.api_key = api_key or Settings.FINNHUB_API_KEY
        self.base_url = Settings.FINNHUB_BASE_URL

        if not self.api_key:
            raise APIAuthenticationError("Finnhub API key not configured")

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(Settings.MAX_RETRIES),
        wait=wait_exponential(
            multiplier=1,
            min=Settings.RETRY_MIN_WAIT,
            max=Settings.RETRY_MAX_WAIT
        )
    )
    def fetch_company_news(
        self,
        ticker: str,
        from_date: str,
        to_date: str
    ) -> List[dict]:
        """
        Fetch news for a single company.

        This method includes retry logic with exponential backoff for rate limits.
        It will retry up to MAX_RETRIES times with increasing delays:
        2s → 4s → 8s → 16s → 30s

        Args:
            ticker: Stock ticker symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of news articles (empty list if none found)

        Raises:
            RateLimitError: If rate limit hit (will trigger retry)
            APIAuthenticationError: If authentication fails
            ValueError: If ticker format is invalid
        """
        if not is_valid_ticker(ticker):
            raise ValueError(f"Invalid ticker format: {ticker}")

        url = f"{self.base_url}/company-news"
        params = {
            'symbol': ticker,
            'from': from_date,
            'to': to_date,
            'token': self.api_key
        }

        try:
            response = requests.get(url, params=params, timeout=10)

            # Handle rate limiting (429) - will trigger retry
            if response.status_code == 429:
                logger.warning(f"Rate limit hit for {ticker}, will retry...")
                log_api_call(logger, "Finnhub", f"company-news/{ticker}", "RATE_LIMIT")
                raise RateLimitError(f"Rate limit exceeded for {ticker}")

            # Handle authentication errors (401, 403)
            if response.status_code in [401, 403]:
                log_api_call(logger, "Finnhub", f"company-news/{ticker}", "AUTH_FAILURE")
                raise APIAuthenticationError(
                    f"Finnhub authentication failed: {response.status_code}"
                )

            # Handle other errors
            if response.status_code != 200:
                logger.error(f"Finnhub API error for {ticker}: {response.status_code}")
                log_api_call(logger, "Finnhub", f"company-news/{ticker}", "FAILURE")
                return []

            # Parse response
            articles = response.json()

            if articles:
                log_api_call(logger, "Finnhub", f"company-news/{ticker}", "SUCCESS")
                logger.debug(f"Fetched {len(articles)} articles for {ticker}")
            else:
                logger.debug(f"No articles found for {ticker}")

            return articles

        except RateLimitError:
            # Re-raise to trigger retry
            raise
        except APIAuthenticationError:
            # Re-raise critical auth errors
            raise
        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {e}")
            return []

    def batch_fetch_news(
        self,
        tickers: List[str],
        ticker_metadata: Dict[str, str] = None
    ) -> Dict[str, List[dict]]:
        """
        Fetch news for multiple tickers with rate limiting and relevance filtering.

        This method implements:
        1. Preventative rate limiting (1.1s delay between ALL requests)
        2. Weekend gap handling (72-hour lookback on Sunday/Monday)
        3. Empty ticker filtering (only return tickers with news)
        4. Relevance filtering (check if ticker/company mentioned in article)

        Args:
            tickers: List of ticker symbols
            ticker_metadata: Dict mapping tickers to company names (optional)

        Returns:
            Dict mapping tickers to their articles (ONLY tickers with relevant news)
        """
        news_data = {}

        # Determine lookback period (weekend gap handling)
        today = datetime.now()
        if today.weekday() in [0, 6]:  # Monday=0, Sunday=6
            lookback_hours = Settings.WEEKEND_LOOKBACK_HOURS
            logger.info(f"Weekend detected - using {lookback_hours}-hour lookback")
        else:
            lookback_hours = Settings.DEFAULT_LOOKBACK_HOURS

        from_date = (today - timedelta(hours=lookback_hours)).strftime('%Y-%m-%d')
        to_date = today.strftime('%Y-%m-%d')

        logger.info(f"Fetching news from {from_date} to {to_date} for {len(tickers)} tickers")

        # Fetch news for each ticker
        for idx, ticker in enumerate(tickers, 1):
            logger.info(f"Processing {idx}/{len(tickers)}: {ticker}")

            try:
                # Fetch articles
                articles = self.fetch_company_news(ticker, from_date, to_date)

                if articles:
                    # Apply relevance filtering
                    relevant_articles = self._filter_relevant_articles(
                        ticker,
                        articles,
                        ticker_metadata
                    )

                    # Only include if relevant articles found
                    if relevant_articles:
                        # Limit to MAX_ARTICLES_PER_TICKER
                        news_data[ticker] = relevant_articles[:Settings.MAX_ARTICLES_PER_TICKER]
                        logger.info(
                            f"✓ {ticker}: {len(relevant_articles)} relevant articles "
                            f"(kept {len(news_data[ticker])})"
                        )

            except APIAuthenticationError:
                # Critical error - abort entire batch
                logger.critical("Finnhub authentication failed - aborting batch fetch")
                raise

            except Exception as e:
                # Log error but continue with other tickers
                logger.error(f"Failed to fetch news for {ticker}: {e}")
                continue

            finally:
                # CRITICAL: Preventative delay between ALL requests
                # This is Layer 1 defense - prevents hitting 30/sec limit
                time.sleep(Settings.API_CALL_DELAY)

        total_articles = sum(len(articles) for articles in news_data.values())
        logger.info(
            f"Batch fetch complete: {len(news_data)}/{len(tickers)} tickers have news "
            f"({total_articles} total articles)"
        )

        return news_data

    def _filter_relevant_articles(
        self,
        ticker: str,
        articles: List[dict],
        ticker_metadata: Dict[str, str] = None
    ) -> List[dict]:
        """
        Filter articles to only include those relevant to the ticker.

        Removes noise like "Microsoft Excel tutorial" or "Apple fruit" articles.

        Args:
            ticker: Stock ticker symbol
            articles: List of articles from API
            ticker_metadata: Dict mapping tickers to company names

        Returns:
            List of relevant articles
        """
        if not articles:
            return []

        # Get company name for better matching
        company_name = ticker_metadata.get(ticker, ticker) if ticker_metadata else ticker

        relevant_articles = []

        for article in articles:
            headline = article.get('headline', '').lower()
            summary = article.get('summary', '')[:100].lower()  # First 100 chars only

            # Check if ticker or company name mentioned
            ticker_mentioned = ticker.lower() in headline or ticker.lower() in summary
            company_mentioned = company_name.lower() in headline or company_name.lower() in summary

            if ticker_mentioned or company_mentioned:
                relevant_articles.append(article)
            else:
                logger.debug(f"Filtered irrelevant article for {ticker}: {article.get('headline', '')[:50]}")

        return relevant_articles

    def get_news_summary(self, ticker: str, articles: List[dict]) -> dict:
        """
        Get summary statistics for news articles.

        Args:
            ticker: Stock ticker symbol
            articles: List of articles

        Returns:
            Summary dict with counts and metadata
        """
        return {
            'ticker': ticker,
            'article_count': len(articles),
            'sources': list(set(article.get('source', 'Unknown') for article in articles)),
            'date_range': {
                'earliest': min(article.get('datetime', 0) for article in articles) if articles else 0,
                'latest': max(article.get('datetime', 0) for article in articles) if articles else 0
            }
        }


# Convenience function for easy access
def fetch_all_news(tickers: List[str]) -> Dict[str, List[dict]]:
    """
    Fetch news for all tickers (convenience function).

    Args:
        tickers: List of ticker symbols

    Returns:
        Dict mapping tickers to their articles
    """
    from src.config.tickers import TICKER_METADATA

    client = FinnhubClient()
    return client.batch_fetch_news(tickers, ticker_metadata=TICKER_METADATA)
