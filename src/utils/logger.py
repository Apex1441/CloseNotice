"""
Comprehensive logging infrastructure with file and console output.

Provides structured logging for the entire application with:
- File logging for persistence
- Console logging for real-time monitoring
- Configurable log levels
- Formatted output with timestamps
"""

import logging
import sys
from pathlib import Path
from src.config.settings import Settings


def setup_logger(name: str = __name__, level: str = None) -> logging.Logger:
    """
    Configure and return a logger with file and console handlers.

    Args:
        name: Logger name (typically __name__ from calling module)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, uses Settings.LOG_LEVEL

    Returns:
        Configured logger instance
    """
    # Get or create logger
    logger = logging.getLogger(name)

    # Prevent duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    # Set log level
    log_level = level or Settings.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper()))

    # Create formatters
    formatter = logging.Formatter(Settings.LOG_FORMAT)

    # File handler - logs to file
    try:
        Settings.ensure_directories()
        file_handler = logging.FileHandler(Settings.LOG_FILE_PATH, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create file handler: {e}", file=sys.stderr)

    # Console handler - logs to stdout/stderr
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def log_api_call(logger: logging.Logger, service: str, endpoint: str, status: str):
    """
    Log API call with structured format.

    Args:
        logger: Logger instance
        service: Service name (e.g., "Finnhub", "Groq", "Telegram")
        endpoint: API endpoint or action
        status: "SUCCESS", "FAILURE", or "RETRY"
    """
    logger.info(f"API [{service}] {endpoint} - {status}")


def log_ticker_progress(logger: logging.Logger, ticker: str, current: int, total: int):
    """
    Log progress for ticker processing.

    Args:
        logger: Logger instance
        ticker: Ticker symbol
        current: Current ticker number
        total: Total number of tickers
    """
    logger.info(f"Processing ticker {current}/{total}: {ticker}")


def log_analysis_result(logger: logging.Logger, ticker: str, sentiment_score: int, success: bool):
    """
    Log sentiment analysis result.

    Args:
        logger: Logger instance
        ticker: Ticker symbol or fund name
        sentiment_score: Sentiment score (1-10)
        success: Whether analysis succeeded
    """
    status = "SUCCESS" if success else "FAILURE"
    logger.info(f"Analysis [{ticker}] Score: {sentiment_score if success else 'N/A'} - {status}")


def log_error_with_context(logger: logging.Logger, error: Exception, context: dict):
    """
    Log error with contextual information.

    Args:
        logger: Logger instance
        error: Exception object
        context: Dictionary with contextual information (ticker, operation, etc.)
    """
    context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
    logger.error(f"Error [{context_str}]: {type(error).__name__}: {str(error)}")


# Create default application logger
app_logger = setup_logger('stock_analysis')


# Convenience functions using default logger
def info(message: str):
    """Log info message using default logger."""
    app_logger.info(message)


def warning(message: str):
    """Log warning message using default logger."""
    app_logger.warning(message)


def error(message: str):
    """Log error message using default logger."""
    app_logger.error(message)


def debug(message: str):
    """Log debug message using default logger."""
    app_logger.debug(message)


def critical(message: str):
    """Log critical message using default logger."""
    app_logger.critical(message)
