# Stock News Analysis System

Automated system that analyzes news for FZROX (Fidelity ZERO Total Market Index Fund) by aggregating news from its top holdings. Generates AI-powered sentiment summaries and delivers daily reports via Telegram at 5:00 PM EST using GitHub Actions.

Tracked funds/stocks are configurable at runtime (see [Updating Holdings](#updating-holdings)) — they are not hardcoded, so the fund(s) described here reflect the current default configuration in `data/config/monitored_items.json`, not a fixed feature of the code.

## Features

- **Automated News Aggregation**: Fetches news from Finnhub API for each tracked fund's holdings
- **AI-Powered Analysis**: Uses Groq LLM (default: `openai/gpt-oss-120b`, configurable via `GROQ_MODEL`) for sentiment analysis
- **Fund-Level Insights**: Aggregates a fund's holdings into a single fund-level sentiment score
- **Individual Stock Tracking**: Optional separate analysis for individual stocks with sector-specific focus
- **Daily Telegram Reports**: Formatted reports delivered at 5 PM EST
- **Historical Tracking**: CSV logging for sentiment trend analysis
- **Production-Ready**: Robust error handling, rate limiting, and monitoring

## System Architecture

**Pipeline Flow:**
1. **Ingestion**: Finnhub API fetches news for every tracked fund's holdings + individual stocks
2. **Aggregation**: Combines each fund's holdings news into a single dataset per fund
3. **Analysis**: Groq LLM generates one sentiment analysis per fund + one per individual stock
4. **Storage**: Logs results to CSV for trend tracking
5. **Delivery**: Sends formatted summary to Telegram

## Prerequisites

- Python 3.11+
- Free API keys:
  - [Finnhub](https://finnhub.io/register) - Stock news data
  - [Groq](https://console.groq.com/keys) - LLM for sentiment analysis
  - [Telegram Bot](https://core.telegram.org/bots#6-botfather) - Message delivery

## Quick Start

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd CloseNotice
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Keys

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your actual API keys:

```env
FINNHUB_API_KEY=your_finnhub_api_key_here
GROQ_API_KEY=your_groq_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

#### Getting API Keys

**Finnhub:**
1. Register at https://finnhub.io/register
2. Copy your API key from the dashboard
3. Free tier: 60 calls/minute, 1000 calls/day (sufficient for 51 tickers)

**Groq:**
1. Sign up at https://console.groq.com
2. Navigate to API Keys section
3. Create new key
4. Generous rate limits on the default model (see https://console.groq.com/docs/models for current models/pricing - availability changes over time)

**Telegram Bot:**
1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow instructions
3. Copy the bot token
4. Send `/start` to your new bot
5. Get your chat ID:
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Send a message to your bot
   - Refresh the URL and find your chat ID in the response

### 4. Test Local Run

```bash
# Run analysis
python -m src.main
```

This will:
- Fetch news for all tracked tickers (see `data/config/monitored_items.json`)
- Analyze sentiment for each tracked fund/stock
- Send report to Telegram
- Log results to `data/sentiment_history.csv`

## GitHub Actions Setup

### 1. Push Code to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Stock News Analysis System"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 2. Configure GitHub Secrets

Go to: **Repository → Settings → Secrets and variables → Actions**

Add the following secrets:
- `FINNHUB_API_KEY`
- `GROQ_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### 3. Enable GitHub Actions

The workflow is already configured in `.github/workflows/daily_analysis.yml`

**Manual Trigger (for testing):**
1. Go to **Actions** tab
2. Select **Daily Stock Analysis**
3. Click **Run workflow**
4. Check Telegram for report

**Scheduled Run:**
- Runs automatically daily at 5:00 PM EST (10:00 PM UTC)
- **Important**: Adjust cron schedule for daylight saving time:
  - EST (Nov-Mar): `0 22 * * *` (currently configured)
  - EDT (Mar-Nov): `0 21 * * *` (uncomment in workflow file)

## Project Structure

```
CloseNotice/
├── .github/workflows/
│   └── daily_analysis.yml          # GitHub Actions cron job
├── src/
│   ├── main.py                      # Orchestration entry point
│   ├── config/
│   │   ├── settings.py              # Environment variables & config
│   │   └── tickers.py               # Loads tracked funds/stocks from data/config
│   ├── data/
│   │   └── finnhub_client.py        # News fetching with rate limiting
│   ├── analysis/
│   │   ├── groq_client.py           # LLM sentiment analysis
│   │   └── prompts.py               # Prompt templates
│   ├── delivery/
│   │   └── telegram_client.py       # Message formatting & sending
│   ├── storage/
│   │   └── csv_logger.py            # Sentiment history tracking
│   └── utils/
│       ├── error_handler.py         # Error handling & alerts
│       └── logger.py                # Logging configuration
├── data/
│   └── sentiment_history.csv        # Persistent sentiment log
├── logs/
│   └── analysis.log                 # Application logs
├── .env.example                     # Template for API keys
├── .gitignore                       # Git ignore rules
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## Configuration

### Which funds/stocks are tracked

Tracked funds and individual stocks are **not** hardcoded in `tickers.py` — they're loaded at runtime from `data/config/monitored_items.json` (managed via `src/utils/persistence.py`). `src/config/tickers.py` just reads whatever that file lists and populates holdings from `data/cache/<FUND>_holdings.json`.

**To add/remove a tracked fund or stock**, use the CLI:

```bash
python manage_items.py list                  # show current funds/stocks
python manage_items.py add fund FZROX        # track a new fund
python manage_items.py add stock AAPL        # track an individual stock
python manage_items.py remove FZROX          # stop tracking
```

**Updating a fund's holdings:**
- By default, `src/main.py` fetches current holdings for each tracked fund via `HoldingsScraper` (`src/data/holdings_scraper.py`) and caches them to `data/cache/<FUND>_holdings.json`. Cached holdings are reused unless you run with `--refresh`.
- To seed/override holdings manually (e.g. pasted from a fund's official holdings page), write directly to `data/cache/<FUND>_holdings.json` in this format:
  ```json
  {
    "ticker": "FZROX",
    "updated_at": "2026-09-17T00:00:00.000000",
    "holdings": [
      {"ticker": "NVDA", "name": "NVIDIA Corp", "sector": "Technology", "weightPercentage": 6.71}
    ]
  }
  ```
- Run `python -m src.main --refresh` to force a live re-scrape instead of using the cache.

### Adjusting Settings

Modify `src/config/settings.py` or use environment variables:

```env
# Rate limiting
FINNHUB_RATE_LIMIT=60           # Calls per minute
API_CALL_DELAY=1.1              # Seconds between calls

# News fetching
MAX_ARTICLES_PER_TICKER=1       # Articles per ticker
DEFAULT_LOOKBACK_HOURS=24       # Normal lookback period
WEEKEND_LOOKBACK_HOURS=72       # Weekend lookback period

# LLM configuration
GROQ_MODEL=openai/gpt-oss-120b  # Model to use (see console.groq.com/docs/models)
GROQ_TEMPERATURE=0.3            # Temperature (0-1)
MAX_SUMMARY_LENGTH=200          # Chars to truncate summaries
```

## Usage Examples

### Local Testing

```bash
# Full production run
python -m src.main

# Test Telegram connection
python -c "from src.delivery.telegram_client import TelegramClient; TelegramClient().send_test_message()"

# Test Finnhub connection (fetch AAPL news)
python -c "from src.data.finnhub_client import FinnhubClient; print(FinnhubClient().fetch_company_news('AAPL', '2026-01-18', '2026-01-19'))"
```

### Viewing Sentiment History

```python
from src.storage.csv_logger import SentimentLogger

logger = SentimentLogger()

# Get FZROX trend over 30 days
trend = logger.get_sentiment_trend("FZROX", days=30)
print(f"Average sentiment: {trend['mean']:.1f}/10")
print(f"Trend: {'↑' if trend['trend'] > 0 else '↓'}")

# Get latest sentiment
latest = logger.get_latest_sentiment("FZROX")
print(f"Latest FZROX sentiment: {latest['sentiment_score']}/10")
```

## Troubleshooting

### Rate Limit Errors (429)

**Symptom**: Finnhub returns 429 status code

**Solutions:**
1. Increase `API_CALL_DELAY` in `.env`:
   ```env
   API_CALL_DELAY=1.5
   ```
2. The system automatically retries with exponential backoff

### Groq API Timeouts

**Symptom**: LLM analysis fails after retries

**Solutions:**
1. Check [Groq status page](https://status.groq.com/)
2. System will send Telegram alert for extended outages
3. Retry manually: `python -m src.main`

### Telegram Message Not Received

**Symptom**: Analysis succeeds but no Telegram message

**Solutions:**
1. Verify bot token and chat ID:
   ```bash
   python -c "from src.delivery.telegram_client import TelegramClient; TelegramClient().send_test_message()"
   ```
2. Check bot permissions (must be able to send messages)
3. Ensure you've sent `/start` to the bot

### CSV Not Persisting in GitHub Actions

**Symptom**: CSV history not updated after workflow runs

**Solutions:**
1. Check workflow logs for git errors
2. Ensure repository permissions allow Actions to push
3. Verify `GITHUB_TOKEN` has write permissions (Settings → Actions → General → Workflow permissions)

### Weekend/Holiday No News

**Symptom**: "Market Quiet" notification on trading days

**Solutions:**
- This is expected on weekends/holidays
- System automatically uses 72-hour lookback on Monday/Sunday
- If occurring on trading days, check Finnhub API status

## Performance Metrics

**Typical Run** (scales with number of tracked tickers, currently 25 for FZROX):
- News fetching: ~(ticker count × `API_CALL_DELAY` seconds), e.g. ~28s for 25 tickers at the default 1.1s delay
- LLM analysis: ~5-10 seconds (one call per tracked fund/stock)
- CSV logging + Telegram: ~2 seconds
- **Total runtime**: roughly 35-45 seconds for the current FZROX-only configuration

**API Usage:**
- Finnhub: 1 call per tracked ticker per day (well within the 1000/day free tier for any reasonable watchlist size)
- Groq: 1 call per tracked fund/stock per day (minimal usage, free tier sufficient)
- Telegram: 1-2 messages/day (unlimited free)

**Cost**: $0/month (all free tier APIs)

## Advanced Features

### Sentiment Trend Analysis

The CSV logger tracks sentiment over time. Access historical data:

```python
import pandas as pd

# Load CSV
df = pd.read_csv('data/sentiment_history.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Plot FZROX sentiment over time
fzrox = df[df['ticker'] == 'FZROX']
fzrox.plot(x='timestamp', y='sentiment_score', title='FZROX Sentiment Trend')
```

### Custom Alerts

Modify `src/delivery/telegram_client.py` to add custom alerts:

```python
# Alert on significant sentiment change
def check_sentiment_shift(current_score, historical_mean):
    if abs(current_score - historical_mean) > 3:
        send_alert(f"⚠️ Significant sentiment shift detected!")
```

### Multi-Fund Support

Track multiple funds at once with the CLI (see [Configuration](#configuration)):

```bash
python manage_items.py add fund FNILX
python manage_items.py add fund FZROX
```

## Contributing

Contributions welcome! Please:
1. Fork repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Test locally: `python -m src.main`
4. Submit pull request

## License

MIT License - feel free to use and modify.

## Acknowledgments

- **Finnhub**: Stock news API
- **Groq**: Fast LLM inference
- **Fidelity**: Fund holdings data

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review logs: `logs/analysis.log`
3. Open GitHub issue with logs and error details

---

**Note**: This system is for informational purposes only. Not financial advice. Always do your own research before making investment decisions.
