"""
Pytest configuration and fixtures for CloseNotice tests.
"""
import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def fast_retries(monkeypatch):
    """Reduce retry wait times for faster test execution."""
    from src.config import settings
    monkeypatch.setattr(settings.Settings, 'RETRY_MIN_WAIT', 0.1)
    monkeypatch.setattr(settings.Settings, 'RETRY_MAX_WAIT', 0.5)


@pytest.fixture
def mock_telegram_env(monkeypatch):
    """Mock Telegram environment variables for tests."""
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'test_token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', 'test_chat_id')


@pytest.fixture
def mock_api_env(monkeypatch):
    """Mock API environment variables for tests."""
    monkeypatch.setenv('FINNHUB_API_KEY', 'test_finnhub_key')
    monkeypatch.setenv('GROQ_API_KEY', 'test_groq_key')
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'test_token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', 'test_chat_id')
