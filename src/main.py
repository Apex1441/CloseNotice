"""
Main orchestration script for Stock News Analysis System.

Pipeline Flow:
1. Fetch news for all 92 tickers (FNILX 51 + FZILX 40 + UURAF 1)
2. Check for market quiet scenario (weekends/holidays)
3. Aggregate FNILX holdings news + FZILX holdings news vs UURAF individual
4. Analyze with Groq LLM (3 API calls: FNILX aggregate + FZILX aggregate + UURAF)
5. Log results to CSV
6. Send Telegram report
7. Handle errors gracefully
"""

import time
import sys
from datetime import datetime
from typing import List, Dict

from src.config.settings import Settings
from src.config.tickers import (
    ALL_TICKERS,
    FNILX_TOP50_WITH_SECTORS,
    FZILX_TOP40_WITH_SECTORS,
    INDIVIDUAL_TICKERS_WITH_SECTORS,
    get_fnilx_tickers,
    get_fzilx_tickers,
    update_fund_holdings_from_scraper,
    get_holdings_summary
)
from src.data.finnhub_client import FinnhubClient
# from src.data.fmp_client import FmpClient
from src.data.holdings_scraper import HoldingsScraper
from src.analysis.groq_client import GroqClient
from src.storage.csv_logger import SentimentLogger
from src.delivery.telegram_client import TelegramClient
from src.utils.logger import setup_logger
from src.utils.error_handler import (
    send_critical_alert,
    alert_on_failure,
    InsufficientDataError,
    APIAuthenticationError
)

logger = setup_logger(__name__)


class StockAnalysisPipeline:
    """Main pipeline for stock news analysis."""

    def __init__(self):
        """Initialize pipeline components."""
        self.finnhub = FinnhubClient()
        # self.fmp = FmpClient()
        self.groq = GroqClient()
        self.csv_logger = SentimentLogger()
        self.telegram = TelegramClient()
        self.start_time = time.time()

    def run(self) -> bool:
        """
        Execute the full analysis pipeline.

        Returns:
            True if successful, False otherwise
        """
        logger.info("=" * 80)
        logger.info("Starting Stock News Analysis Pipeline")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # Step 1: Validate configuration
            logger.info("\n[Step 1/7] Validating configuration...")
            Settings.validate()
            logger.info(f"✓ Configuration validated")

            # Step 2: Fetch fund holdings (dynamic via Scraper)
            logger.info("\n[Step 2/7] Fetching fund holdings via Scraper...")
            self._fetch_fund_holdings()
            summary = get_holdings_summary()
            logger.info(f"✓ Holdings loaded")
            logger.info(f"  - FNILX holdings: {summary['fnilx_count']}")
            logger.info(f"  - FZILX holdings: {summary['fzilx_count']}")
            logger.info(f"  - Individual stocks: {summary['individual_count']}")
            logger.info(f"  - Total tickers: {summary['total_count']}")

            # Step 3: Fetch news for all tickers
            logger.info("\n[Step 3/7] Fetching news from Finnhub...")
            news_data = self._fetch_all_news()

            # Step 4: Check for market quiet scenario
            total_articles = sum(len(articles) for articles in news_data.values())
            logger.info(f"✓ News fetched: {len(news_data)} tickers have news ({total_articles} total articles)")

            if total_articles == 0:
                logger.info("No news found - market quiet scenario")
                self.telegram.send_market_quiet_notification()
                logger.info("✓ Market quiet notification sent")
                return True

            # Step 5: Analyze sentiment (3 LLM calls: FNILX + FZILX + UURAF)
            logger.info("\n[Step 4/7] Analyzing sentiment with Groq LLM...")
            results, errors, no_news_tickers = self._analyze_sentiment(news_data)

            # Step 6: Log results to CSV
            logger.info("\n[Step 5/7] Logging results to CSV...")
            self._log_results(results, news_data)

            # Step 7: Send Telegram report
            logger.info("\n[Step 6/7] Sending Telegram report...")
            runtime = time.time() - self.start_time
            self._send_report(results, total_articles, errors, runtime, no_news_tickers)

            # Summary
            logger.info("\n[Step 7/7] Pipeline complete")
            logger.info(f"✓ Analyses completed: {len(results)}/2")
            logger.info(f"✓ Errors: {len(errors)}")
            logger.info(f"✓ Total runtime: {runtime:.1f}s")
            logger.info("=" * 80)

            return len(results) > 0

        except APIAuthenticationError as e:
            logger.critical(f"Authentication failure: {e}")
            send_critical_alert(
                error_type="API Authentication Failure",
                error_message=str(e),
                additional_info="Check API keys in GitHub Secrets or .env file"
            )
            return False

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.telegram.send_error_notification(f"Pipeline failed: {str(e)}")
            return False

    def _fetch_fund_holdings(self):
        """
        Fetch fund holdings from Scraper and update config.
        Includes any extra funds passed via CLI.
        """
        # Get base funds plus any that were requested via CLI args
        import sys
        
        # Check for force refresh flag
        force_refresh = "--refresh" in sys.argv
        
        # Simple CLI parsing for extra funds: python src/main.py SPY QQQ
        # This is a basic way to inject them.
        extra_funds = [arg.upper() for arg in sys.argv[1:] if not arg.startswith('-')]
        
        # Start with default funds from tickers.py
        from src.config.tickers import get_all_funds, get_fund_holdings
        funds_to_fetch = set(get_all_funds())
        
        # Add extra funds
        for f in extra_funds:
            funds_to_fetch.add(f)

        for fund_symbol in funds_to_fetch:
            try:
                # Check if we already have holdings (from cache)
                current_holdings = get_fund_holdings(fund_symbol)
                
                if current_holdings and not force_refresh:
                     logger.info(f"✓ Using cached holdings for {fund_symbol} ({len(current_holdings)} stocks)")
                     continue
                     
                logger.info(f"Scraping holdings for {fund_symbol}...")
                holdings = HoldingsScraper.get_holdings(fund_symbol)

                if holdings:
                    update_fund_holdings_from_scraper(fund_symbol, holdings)
                    logger.info(f"✓ Updated {fund_symbol} with {len(holdings)} holdings from Scraper")
                else:
                    logger.warning(f"No holdings found for {fund_symbol} - keeping existing if any")

            except Exception as e:
                logger.error(f"Error scraping {fund_symbol}: {e}")

    @alert_on_failure("Finnhub API Failure")
    def _fetch_all_news(self) -> Dict[str, List[dict]]:
        """
        Fetch news for all tickers with error handling.

        Returns:
            Dict mapping tickers to their news articles
        """
        from src.config.tickers import TICKER_METADATA

        news_data = self.finnhub.batch_fetch_news(
            tickers=ALL_TICKERS,
            ticker_metadata=TICKER_METADATA
        )

        # Check if zero news fetched (possible API issue)
        if len(news_data) == 0:
            logger.warning("Zero tickers have news - possible API issue or weekend")

        return news_data

    def _format_error_detail(self, error: Exception, ticker: str) -> str:
        """
        Format error details into a user-friendly message.

        Args:
            error: The exception that occurred
            ticker: The ticker that failed

        Returns:
            Formatted error message
        """
        import requests

        error_str = str(error)

        # HTTP status code errors
        if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            status_code = error.response.status_code
            if status_code == 401:
                return "401 Unauthorized - check API key"
            elif status_code == 429:
                return "Rate limit exceeded - too many requests"
            elif status_code == 503:
                return "503 Service unavailable - API temporarily down"
            elif status_code >= 500:
                return f"{status_code} Server error - API having issues"
            elif status_code >= 400:
                return f"{status_code} Client error - invalid request"

        # Timeout errors
        if isinstance(error, (requests.exceptions.Timeout, TimeoutError)):
            return "Connection timeout - API not responding"

        # Connection errors
        if isinstance(error, (requests.exceptions.ConnectionError, ConnectionError)):
            return "Connection failed - network issue or API down"

        # JSON decode errors (from LLM responses)
        if isinstance(error, (ValueError, KeyError)) and ('json' in error_str.lower() or 'parse' in error_str.lower()):
            return "LLM returned invalid format - analysis failed"

        # Insufficient data error
        if isinstance(error, InsufficientDataError):
            return "Insufficient data for analysis"

        # Generic error - truncate to 100 chars
        return error_str[:100] + "..." if len(error_str) > 100 else error_str

    def _analyze_sentiment(
        self,
        news_data: Dict[str, List[dict]]
    ) -> tuple[List[dict], List[dict], List[str]]:
        """
        Analyze sentiment for ALL funds and individual stocks.

        Args:
            news_data: Dict mapping tickers to news articles

        Returns:
            Tuple of (results, errors, no_news_tickers)
        """
        results = []
        errors = []
        no_news_tickers = []

        from src.config.tickers import get_fund_holdings, get_all_funds

        # 1. Analyze Funds
        for fund_symbol in get_all_funds():
            holdings = get_fund_holdings(fund_symbol)
            fund_tickers = list(holdings.keys())
            
            # Filter news for this fund
            fund_news = {
                ticker: news_data[ticker]
                for ticker in fund_tickers
                if ticker in news_data
            }

            if fund_news:
                logger.info(f"Analyzing {fund_symbol} aggregate ({len(fund_news)} holdings with news)...")
                try:
                    fund_result = self.groq.analyze_aggregate_sentiment(
                        fund_name=fund_symbol,
                        ticker_news_dict=fund_news,
                        ticker_sectors=holdings
                    )

                    # Add news count
                    fund_result['news_count'] = sum(len(articles) for articles in fund_news.values())

                    results.append(fund_result)
                    logger.info(f"✓ {fund_symbol} analysis complete: Score {fund_result['sentiment_score']}/10")

                except InsufficientDataError as e:
                    logger.warning(f"Insufficient data for {fund_symbol}: {e}")
                    error_detail = self._format_error_detail(e, fund_symbol)
                    errors.append({
                        'ticker': fund_symbol,
                        'error': error_detail,
                        'type': 'InsufficientDataError'
                    })

                except Exception as e:
                    logger.error(f"{fund_symbol} analysis failed: {e}", exc_info=True)
                    error_detail = self._format_error_detail(e, fund_symbol)
                    errors.append({
                        'ticker': fund_symbol,
                        'error': error_detail,
                        'type': type(e).__name__
                    })
            else:
                logger.info(f"No news for {fund_symbol} holdings - skipping aggregate analysis")
                no_news_tickers.append(fund_symbol)

        # 2. Analyze Individual Stocks
        from src.config.tickers import get_individual_tickers
        
        for ticker in get_individual_tickers():
            if ticker in news_data:
                logger.info(f"Analyzing {ticker} ({len(news_data[ticker])} articles)...")
                try:
                    stock_result = self.groq.analyze_individual_sentiment(
                        ticker=ticker,
                        articles=news_data[ticker]
                    )

                    # Add news count
                    stock_result['news_count'] = len(news_data[ticker])

                    results.append(stock_result)
                    logger.info(f"✓ {ticker} analysis complete: Score {stock_result['sentiment_score']}/10")

                except InsufficientDataError as e:
                    logger.warning(f"Insufficient data for {ticker}: {e}")
                    error_detail = self._format_error_detail(e, ticker)
                    errors.append({
                        'ticker': ticker,
                        'error': error_detail,
                        'type': 'InsufficientDataError'
                    })

                except Exception as e:
                    logger.error(f"{ticker} analysis failed: {e}", exc_info=True)
                    error_detail = self._format_error_detail(e, ticker)
                    errors.append({
                        'ticker': ticker,
                        'error': error_detail,
                        'type': type(e).__name__
                    })
            else:
                logger.info(f"No news for {ticker} - skipping individual analysis")
                no_news_tickers.append(ticker)

        return results, errors, no_news_tickers

    def _log_results(self, results: List[dict], news_data: Dict[str, List[dict]]):
        """
        Log analysis results to CSV.

        Args:
            results: List of analysis results
            news_data: Original news data for news count
        """
        for result in results:
            try:
                self.csv_logger.append_result(result)
                logger.info(f"✓ Logged {result['ticker']} to CSV")
            except Exception as e:
                logger.error(f"Failed to log {result['ticker']} to CSV: {e}")

    def _send_report(
        self,
        results: List[dict],
        total_articles: int,
        errors: List[dict],
        runtime: float,
        no_news_tickers: List[str]
    ):
        """
        Send Telegram report.

        Args:
            results: Analysis results
            total_articles: Total articles analyzed
            errors: List of errors
            runtime: Runtime in seconds
            no_news_tickers: List of tickers with no news
        """
        try:
            success = self.telegram.send_daily_report(
                analysis_results=results,
                total_articles=total_articles,
                errors=errors,
                runtime_seconds=runtime,
                no_news_tickers=no_news_tickers
            )

            if success:
                logger.info("✓ Telegram report sent successfully")
            else:
                logger.error("Failed to send Telegram report")

        except Exception as e:
            logger.error(f"Failed to send Telegram report: {e}")


def main():
    """Main entry point."""
    try:
        # Initialize and run pipeline
        pipeline = StockAnalysisPipeline()
        success = pipeline.run()

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("\nPipeline interrupted by user")
        sys.exit(1)

    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
