"""
CSV logger for tracking sentiment history over time.

Provides:
- Append sentiment results to CSV
- Load and query historical data
- Calculate sentiment trends
- Pandas-based operations for efficiency
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from src.config.settings import Settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SentimentLogger:
    """Logger for sentiment analysis results."""

    def __init__(self, csv_path: Path = None):
        """
        Initialize sentiment logger.

        Args:
            csv_path: Path to CSV file (defaults to Settings.SENTIMENT_CSV_PATH)
        """
        self.csv_path = csv_path or Settings.SENTIMENT_CSV_PATH
        self._ensure_csv_exists()

    def _ensure_csv_exists(self):
        """Create CSV file with headers if it doesn't exist."""
        if not self.csv_path.exists():
            # Ensure parent directory exists
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)

            # Create CSV with headers
            df = pd.DataFrame(columns=[
                'timestamp',
                'ticker',
                'sentiment_score',
                'insights',
                'rationale',
                'news_count',
                'success'
            ])
            df.to_csv(self.csv_path, index=False)
            logger.info(f"Created new sentiment CSV at {self.csv_path}")

    def append_sentiment(
        self,
        ticker: str,
        sentiment_score: int,
        top_insights: List[str],
        rationale: str,
        news_count: int = 0,
        success: bool = True
    ):
        """
        Append sentiment analysis result to CSV.

        Args:
            ticker: Ticker symbol or fund name (FNILX, UURAF)
            sentiment_score: Sentiment score (1-10)
            top_insights: List of key insights
            rationale: Analysis rationale
            news_count: Number of news articles analyzed
            success: Whether analysis succeeded
        """
        # Format insights as pipe-separated string
        insights_str = "|".join(top_insights) if top_insights else ""

        # Create new row
        new_row = {
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'sentiment_score': sentiment_score if success else None,
            'insights': insights_str,
            'rationale': rationale,
            'news_count': news_count,
            'success': success
        }

        try:
            # Read existing CSV
            df = pd.read_csv(self.csv_path)

            # Append new row
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

            # Save back to CSV
            df.to_csv(self.csv_path, index=False)

            logger.info(f"Logged sentiment for {ticker}: Score {sentiment_score}/10")

        except Exception as e:
            logger.error(f"Failed to append sentiment to CSV: {e}")
            raise

    def append_result(self, result: dict):
        """
        Append analysis result dict to CSV.

        Convenience method that accepts the full result dict from groq_client.

        Args:
            result: Result dict from sentiment analysis
                    {"ticker": "FNILX", "sentiment_score": 7, "top_insights": [...], "rationale": "..."}
        """
        self.append_sentiment(
            ticker=result.get('ticker', 'Unknown'),
            sentiment_score=result.get('sentiment_score', 0),
            top_insights=result.get('top_insights', []),
            rationale=result.get('rationale', ''),
            news_count=result.get('news_count', 0),
            success=True
        )

    def load_history(
        self,
        ticker: Optional[str] = None,
        days: int = 30
    ) -> pd.DataFrame:
        """
        Load historical sentiment data.

        Args:
            ticker: Filter by ticker (None = all tickers)
            days: Number of days to load (default: 30)

        Returns:
            DataFrame with historical data
        """
        try:
            df = pd.read_csv(self.csv_path)

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Filter by date
            cutoff_date = datetime.now() - timedelta(days=days)
            df = df[df['timestamp'] >= cutoff_date]

            # Filter by ticker if specified
            if ticker:
                df = df[df['ticker'] == ticker]

            logger.debug(f"Loaded {len(df)} records from CSV (ticker={ticker}, days={days})")

            return df

        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return pd.DataFrame()

    def get_sentiment_trend(
        self,
        ticker: str,
        days: int = 30
    ) -> dict:
        """
        Calculate sentiment trend statistics for a ticker.

        Args:
            ticker: Ticker symbol or fund name
            days: Number of days to analyze

        Returns:
            Dict with trend statistics
        """
        df = self.load_history(ticker=ticker, days=days)

        if df.empty:
            return {
                'ticker': ticker,
                'days': days,
                'count': 0,
                'mean': None,
                'median': None,
                'min': None,
                'max': None,
                'trend': None
            }

        # Filter successful analyses only
        df = df[df['success'] == True]

        if df.empty:
            return {
                'ticker': ticker,
                'days': days,
                'count': 0,
                'mean': None,
                'median': None,
                'min': None,
                'max': None,
                'trend': None
            }

        # Calculate statistics
        scores = df['sentiment_score'].dropna()

        # Calculate trend (simple linear regression)
        trend = None
        if len(scores) >= 2:
            # Positive = upward trend, Negative = downward trend
            first_half_mean = scores.iloc[:len(scores)//2].mean()
            second_half_mean = scores.iloc[len(scores)//2:].mean()
            trend = second_half_mean - first_half_mean

        return {
            'ticker': ticker,
            'days': days,
            'count': len(scores),
            'mean': scores.mean(),
            'median': scores.median(),
            'min': scores.min(),
            'max': scores.max(),
            'trend': trend,
            'latest': scores.iloc[-1] if len(scores) > 0 else None,
            'latest_date': df['timestamp'].iloc[-1].strftime('%Y-%m-%d') if len(df) > 0 else None
        }

    def get_latest_sentiment(self, ticker: str) -> Optional[dict]:
        """
        Get most recent sentiment for a ticker.

        Args:
            ticker: Ticker symbol or fund name

        Returns:
            Dict with latest sentiment or None if not found
        """
        df = self.load_history(ticker=ticker, days=7)  # Last week

        if df.empty:
            return None

        # Sort by timestamp descending
        df = df.sort_values('timestamp', ascending=False)

        # Get latest row
        latest = df.iloc[0]

        return {
            'ticker': latest['ticker'],
            'timestamp': latest['timestamp'],
            'sentiment_score': latest['sentiment_score'],
            'insights': latest['insights'].split('|') if latest['insights'] else [],
            'rationale': latest['rationale'],
            'news_count': latest['news_count'],
            'success': latest['success']
        }

    def get_summary_stats(self) -> dict:
        """
        Get summary statistics across all tickers.

        Returns:
            Dict with overall statistics
        """
        try:
            df = pd.read_csv(self.csv_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            return {
                'total_entries': len(df),
                'date_range': {
                    'first': df['timestamp'].min().strftime('%Y-%m-%d') if len(df) > 0 else None,
                    'last': df['timestamp'].max().strftime('%Y-%m-%d') if len(df) > 0 else None
                },
                'tickers': df['ticker'].unique().tolist(),
                'success_rate': (df['success'].sum() / len(df) * 100) if len(df) > 0 else 0
            }

        except Exception as e:
            logger.error(f"Failed to get summary stats: {e}")
            return {}


# Convenience function for easy access
def log_sentiment(result: dict):
    """
    Log sentiment result to CSV (convenience function).

    Args:
        result: Result dict from sentiment analysis
    """
    logger_instance = SentimentLogger()
    logger_instance.append_result(result)
