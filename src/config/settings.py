"""
Central configuration hub for all environment variables and system parameters.

This module loads configuration from .env files (local development) or
environment variables (production/GitHub Actions) and validates all required settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
# This is for local development - GitHub Actions uses Secrets
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings and configuration."""

    # ============================================================================
    # API Configuration
    # ============================================================================

    # Finnhub API
    FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
    FINNHUB_BASE_URL = 'https://finnhub.io/api/v1'
    FINNHUB_RATE_LIMIT = int(os.getenv('FINNHUB_RATE_LIMIT', '60'))  # calls per minute

    # Financial Modeling Prep API (Removed)

    # FMP_BASE_URL = 'https://financialmodelingprep.com/api/v3'

    # Groq API
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
    GROQ_TEMPERATURE = float(os.getenv('GROQ_TEMPERATURE', '0.3'))
    GROQ_MAX_TOKENS = int(os.getenv('GROQ_MAX_TOKENS', '1024'))

    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    TELEGRAM_BASE_URL = 'https://api.telegram.org'

    # ============================================================================
    # Rate Limiting Configuration
    # ============================================================================

    # Number of articles to fetch per ticker (1 is optimal for daily analysis)
    MAX_ARTICLES_PER_TICKER = int(os.getenv('MAX_ARTICLES_PER_TICKER', '2'))

    # Delay between API calls (seconds) - prevents hitting 30/sec limit
    # 1.1 seconds ensures 51 calls take ~56 seconds (under 60/min)
    API_CALL_DELAY = float(os.getenv('API_CALL_DELAY', '1.1'))

    # Retry configuration for rate limiting
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '5'))
    RETRY_MIN_WAIT = int(os.getenv('RETRY_MIN_WAIT', '2'))  # seconds
    RETRY_MAX_WAIT = int(os.getenv('RETRY_MAX_WAIT', '30'))  # seconds

    # ============================================================================
    # Data Configuration
    # ============================================================================

    # Lookback period for news fetching
    DEFAULT_LOOKBACK_HOURS = int(os.getenv('DEFAULT_LOOKBACK_HOURS', '24'))
    WEEKEND_LOOKBACK_HOURS = int(os.getenv('WEEKEND_LOOKBACK_HOURS', '72'))

    # Article summary truncation length (prevents context overflow)
    MAX_SUMMARY_LENGTH = int(os.getenv('MAX_SUMMARY_LENGTH', '200'))

    # Holdings Configuration
    TOP_HOLDINGS_COUNT = int(os.getenv('TOP_HOLDINGS_COUNT', '50'))  # Top N holdings to analyze
    HOLDINGS_UPDATE_INTERVAL_DAYS = int(os.getenv('HOLDINGS_UPDATE_INTERVAL_DAYS', '90'))  # Quarterly rebalancing

    # ============================================================================
    # File Paths
    # ============================================================================

    # Base directory
    BASE_DIR = Path(__file__).parent.parent.parent

    # Data directories
    DATA_DIR = BASE_DIR / 'data'
    LOGS_DIR = BASE_DIR / 'logs'

    # CSV file for sentiment history
    SENTIMENT_CSV_PATH = DATA_DIR / 'sentiment_history.csv'

    # Holdings cache file
    HOLDINGS_CACHE_FILE = DATA_DIR / 'holdings_cache.json'

    # Log file
    LOG_FILE_PATH = LOGS_DIR / 'analysis.log'

    # ============================================================================
    # Logging Configuration
    # ============================================================================

    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # ============================================================================
    # Validation
    # ============================================================================

    @classmethod
    def validate(cls):
        """
        Validate that all required environment variables are set.

        Raises:
            ValueError: If any required environment variable is missing.
        """
        required_vars = {
            'FINNHUB_API_KEY': cls.FINNHUB_API_KEY,

            'GROQ_API_KEY': cls.GROQ_API_KEY,
            'TELEGRAM_BOT_TOKEN': cls.TELEGRAM_BOT_TOKEN,
            'TELEGRAM_CHAT_ID': cls.TELEGRAM_CHAT_ID,
        }

        missing = [name for name, value in required_vars.items() if not value]

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please set them in your .env file (local) or GitHub Secrets (production).\n"
                f"See .env.example for reference."
            )

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_summary(cls):
        """Get a summary of current settings (for logging/debugging)."""
        return {
            'finnhub_rate_limit': cls.FINNHUB_RATE_LIMIT,
            'max_articles_per_ticker': cls.MAX_ARTICLES_PER_TICKER,
            'api_call_delay': cls.API_CALL_DELAY,
            'groq_model': cls.GROQ_MODEL,
            'groq_temperature': cls.GROQ_TEMPERATURE,
            'default_lookback_hours': cls.DEFAULT_LOOKBACK_HOURS,
            'weekend_lookback_hours': cls.WEEKEND_LOOKBACK_HOURS,
            'max_summary_length': cls.MAX_SUMMARY_LENGTH,
            'top_holdings_count': cls.TOP_HOLDINGS_COUNT,
            'holdings_update_interval_days': cls.HOLDINGS_UPDATE_INTERVAL_DAYS,
        }


# Initialize settings on module import
try:
    Settings.validate()
    Settings.ensure_directories()
except ValueError as e:
    # Don't fail import - just warn
    # This allows importing the module for testing without all vars set
    print(f"Warning: {e}")


# Export settings instance
settings = Settings()
