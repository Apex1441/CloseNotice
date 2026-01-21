"""
Error handling utilities with Telegram alerting for critical failures.

Provides:
- Decorator for automatic error alerting
- Critical failure notification to Telegram
- Graceful error handling patterns
"""

import functools
import traceback
import requests
from typing import Callable, Any
from src.config.settings import Settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def send_critical_alert(error_type: str, error_message: str, additional_info: str = ""):
    """
    Send Telegram alert for critical system failures.

    Use cases:
    - Finnhub API key expired
    - Groq API down for extended period
    - GitHub Actions workflow crash
    - Zero news fetched for all tickers

    Args:
        error_type: Type of error (e.g., "Finnhub API Failure")
        error_message: Detailed error message
        additional_info: Additional context (optional)
    """
    alert_message = f"""
🚨 CRITICAL SYSTEM ERROR

Type: {error_type}
Message: {error_message}

{additional_info}

Check GitHub Actions logs or local logs for details.
Time: {_get_timestamp()}
"""

    try:
        url = f"{Settings.TELEGRAM_BASE_URL}/bot{Settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(
            url,
            json={
                "chat_id": Settings.TELEGRAM_CHAT_ID,
                "text": alert_message.strip()
            },
            timeout=10
        )

        if response.status_code == 200:
            logger.info(f"Critical alert sent: {error_type}")
        else:
            logger.warning(f"Failed to send critical alert: {response.status_code}")

    except Exception as e:
        # Silent fail - don't crash on alert failure
        logger.warning(f"Could not send critical alert: {e}")


def alert_on_failure(error_type: str):
    """
    Decorator to send Telegram alert if function fails after retries.

    Usage:
        @alert_on_failure("Finnhub API Failure")
        def fetch_all_news(tickers):
            # ... fetch logic
            pass

    Args:
        error_type: Type of error for alert message
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log full traceback
                tb = traceback.format_exc()
                logger.error(f"Function {func.__name__} failed: {tb}")

                # Send alert
                send_critical_alert(
                    error_type=error_type,
                    error_message=str(e),
                    additional_info=f"Function: {func.__name__}\nTraceback available in logs"
                )

                # Re-raise to let caller handle
                raise

        return wrapper
    return decorator


class ErrorContext:
    """
    Context manager for graceful error handling with logging.

    Usage:
        with ErrorContext("Fetching AAPL news", ticker="AAPL"):
            # ... operation
            pass
    """

    def __init__(self, operation: str, **context):
        """
        Initialize error context.

        Args:
            operation: Description of operation
            **context: Additional context (ticker, endpoint, etc.)
        """
        self.operation = operation
        self.context = context
        self.logger = setup_logger(__name__)

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context and log error if occurred.

        Returns:
            False to propagate exception, True to suppress it
        """
        if exc_type is not None:
            context_str = ", ".join([f"{k}={v}" for k, v in self.context.items()])
            self.logger.error(
                f"Error during {self.operation} [{context_str}]: "
                f"{exc_type.__name__}: {str(exc_val)}"
            )
            # Don't suppress exception - let caller handle
            return False
        return True


def handle_api_error(error: Exception, service: str, operation: str) -> dict:
    """
    Standardized API error handling.

    Args:
        error: Exception that occurred
        service: Service name (Finnhub, Groq, Telegram)
        operation: Operation being performed

    Returns:
        Error info dictionary
    """
    error_info = {
        'service': service,
        'operation': operation,
        'error_type': type(error).__name__,
        'error_message': str(error),
        'success': False
    }

    logger.error(f"API Error [{service}] {operation}: {error_info['error_type']} - {error_info['error_message']}")

    return error_info


def should_send_critical_alert(error_type: str, error: Exception) -> bool:
    """
    Determine if error warrants a critical alert.

    Critical scenarios:
    - Authentication failures (expired API keys)
    - Extended API outages (after retries exhausted)
    - Zero data scenarios (no news for any ticker)
    - System-level failures

    Args:
        error_type: Type of error
        error: Exception object

    Returns:
        True if critical alert should be sent
    """
    critical_keywords = [
        'authentication',
        'unauthorized',
        'api key',
        'expired',
        'forbidden',
        'zero news',
        'no data',
        'all failed'
    ]

    error_str = str(error).lower()

    return any(keyword in error_str for keyword in critical_keywords)


def _get_timestamp() -> str:
    """Get current timestamp string."""
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class RetryExhaustedError(Exception):
    """Raised when retry attempts are exhausted."""
    pass


class APIAuthenticationError(Exception):
    """Raised when API authentication fails."""
    pass


class InsufficientDataError(Exception):
    """Raised when insufficient data for analysis."""
    pass
