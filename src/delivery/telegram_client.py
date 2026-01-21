"""
Telegram Bot client for delivering daily reports.

Features:
- Format analysis results into readable messages
- Send messages with retry logic
- Handle errors gracefully with fallback messages
- Support for error notifications
"""

import requests
from typing import List, Dict
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import Settings
from src.analysis.prompts import get_sentiment_emoji, get_sentiment_label
from src.utils.logger import setup_logger, log_api_call

logger = setup_logger(__name__)


class TelegramClient:
    """Client for sending messages via Telegram Bot API."""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Initialize Telegram client.

        Args:
            bot_token: Telegram bot token (defaults to Settings.TELEGRAM_BOT_TOKEN)
            chat_id: Telegram chat ID (defaults to Settings.TELEGRAM_CHAT_ID)
        """
        self.bot_token = bot_token or Settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or Settings.TELEGRAM_CHAT_ID
        self.base_url = f"{Settings.TELEGRAM_BASE_URL}/bot{self.bot_token}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def send_message(self, text: str, parse_mode: str = None) -> bool:
        """
        Send a message to Telegram.

        Args:
            text: Message text (max 4096 characters)
            parse_mode: Parse mode (HTML, Markdown, or None)

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": text
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                log_api_call(logger, "Telegram", "sendMessage", "SUCCESS")
                logger.info("Message sent to Telegram successfully")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                log_api_call(logger, "Telegram", "sendMessage", "FAILURE")
                return False

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            log_api_call(logger, "Telegram", "sendMessage", "FAILURE")
            return False

    def format_report(
        self,
        analysis_results: List[dict],
        total_articles: int = 0,
        errors: List[dict] = None,
        runtime_seconds: float = 0,
        no_news_tickers: List[str] = None
    ) -> str:
        """
        Format analysis results into a readable report.

        Args:
            analysis_results: List of analysis result dicts
            total_articles: Total number of articles analyzed
            errors: List of error dicts (optional)
            runtime_seconds: Total runtime in seconds
            no_news_tickers: List of tickers with no news (optional)

        Returns:
            Formatted message string
        """
        # Header
        date_str = datetime.now().strftime('%b %d, %Y')
        message = f"📊 Daily Analysis - {date_str}\n\n"

        # Analysis results
        for result in analysis_results:
            ticker = result.get('ticker', 'Unknown')
            score = result.get('sentiment_score', 0)
            insights = result.get('top_insights', [])
            emoji = get_sentiment_emoji(score)
            label = get_sentiment_label(score)

            # Ticker header
            
            
            if :
                message += f"{emoji} {ticker} | Score: {score}/10 ({label})\n"

            # Insights (bullet points)
            for insight in insights[:3]:  # Max 3 insights
                message += f"• {insight}\n"

            message += "\n"

        # Footer with statistics
        message += "---\n"
        message += f"📊 Articles analyzed: {total_articles}\n"

        if runtime_seconds > 0:
            runtime_str = f"{int(runtime_seconds // 60)}m {int(runtime_seconds % 60)}s"
            message += f"⏱️ Runtime: {runtime_str}\n"

        # No news section (informational)
        if no_news_tickers:
            message += f"\nNo news today: {', '.join(no_news_tickers)}\n"

        # Error summary with details
        if errors:
            message += f"\n⚠️ {len(errors)} error(s) occurred:\n"
            for error in errors:
                ticker = error.get('ticker', 'Unknown')
                error_detail = error.get('error', 'Unknown error')
                message += f"• {ticker}: {error_detail}\n"
            message += "Check logs for full details\n"
        else:
            # Success indicator (only if no errors)
            message += "\n✅ All analyses successful\n"

        return message.strip()

    def format_error_report(
        self,
        errors: List[dict],
        partial_results: List[dict] = None,
        no_news_tickers: List[str] = None
    ) -> str:
        """
        Format error report for failed analyses.

        Args:
            errors: List of error dicts
            partial_results: Partial results that succeeded (optional)
            no_news_tickers: List of tickers with no news (optional)

        Returns:
            Formatted error message
        """
        date_str = datetime.now().strftime('%b %d, %Y')
        message = f"⚠️ Daily Analysis - {date_str}\n\n"

        # Show partial results if available
        if partial_results:
            message += "Partial results:\n\n"
            for result in partial_results:
                ticker = result.get('ticker', 'Unknown')
                score = result.get('sentiment_score', 0)
                emoji = get_sentiment_emoji(score)
                message += f"{emoji} {ticker} | Score: {score}/10\n"
                for insight in result.get('top_insights', [])[:2]:
                    message += f"• {insight}\n"
                message += "\n"

        # Error summary
        message += "---\n"

        # No news section (informational)
        if no_news_tickers:
            message += f"\nNo news today: {', '.join(no_news_tickers)}\n"

        # Error details
        message += f"\n❌ Errors ({len(errors)}):\n"
        for error in errors:
            ticker = error.get('ticker', 'Unknown')
            error_msg = error.get('error', 'Unknown error')
            message += f"• {ticker}: {error_msg}\n"

        message += "\n⚠️ Check logs for details\n"

        return message.strip()

    def send_daily_report(
        self,
        analysis_results: List[dict],
        total_articles: int = 0,
        errors: List[dict] = None,
        runtime_seconds: float = 0,
        no_news_tickers: List[str] = None
    ) -> bool:
        """
        Send formatted daily report to Telegram.

        Args:
            analysis_results: List of analysis result dicts
            total_articles: Total number of articles analyzed
            errors: List of error dicts (optional)
            runtime_seconds: Total runtime in seconds
            no_news_tickers: List of tickers with no news (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Format report
            if analysis_results and len(analysis_results) > 0:
                message = self.format_report(
                    analysis_results=analysis_results,
                    total_articles=total_articles,
                    errors=errors,
                    runtime_seconds=runtime_seconds,
                    no_news_tickers=no_news_tickers
                )
            else:
                # No results - send error report
                message = self.format_error_report(
                    errors=errors or [],
                    no_news_tickers=no_news_tickers
                )

            # Send message
            return self.send_message(message)

        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
            # Try to send simple error notification
            try:
                self.send_message(f"❌ Failed to generate daily report: {str(e)}")
            except:
                pass
            return False

    def send_market_quiet_notification(self) -> bool:
        """
        Send notification when market is quiet (no news).

        Returns:
            True if successful, False otherwise
        """
        date_str = datetime.now().strftime('%b %d, %Y')
        message = f"📊 Daily Analysis - {date_str}\n\n"
        message += "🔇 Market Quiet\n\n"
        message += "No new news articles found today.\n"
        message += "This is likely a weekend or market holiday.\n\n"
        message += "Analysis will resume on next trading day."

        return self.send_message(message)

    def send_error_notification(self, error_message: str) -> bool:
        """
        Send error notification to Telegram.

        Args:
            error_message: Error message to send

        Returns:
            True if successful, False otherwise
        """
        date_str = datetime.now().strftime('%b %d, %Y')
        message = f"❌ Error - {date_str}\n\n"
        message += f"{error_message}\n\n"
        message += "Check logs for details."

        return self.send_message(message)

    def send_test_message(self) -> bool:
        """
        Send test message to verify Telegram setup.

        Returns:
            True if successful, False otherwise
        """
        message = "✅ Telegram Bot Test\n\n"
        message += "Your bot is configured correctly!\n"
        message += f"Chat ID: {self.chat_id}\n"
        message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return self.send_message(message)


# Convenience functions
def send_report(
    results: List[dict],
    total_articles: int = 0,
    errors: List[dict] = None,
    runtime: float = 0
) -> bool:
    """
    Send daily report (convenience function).

    Args:
        results: Analysis results
        total_articles: Total articles analyzed
        errors: List of errors
        runtime: Runtime in seconds

    Returns:
        True if successful, False otherwise
    """
    client = TelegramClient()
    return client.send_daily_report(
        analysis_results=results,
        total_articles=total_articles,
        errors=errors,
        runtime_seconds=runtime
    )


def send_market_quiet() -> bool:
    """Send market quiet notification (convenience function)."""
    client = TelegramClient()
    return client.send_market_quiet_notification()


def send_error(error_message: str) -> bool:
    """Send error notification (convenience function)."""
    client = TelegramClient()
    return client.send_error_notification(error_message)
