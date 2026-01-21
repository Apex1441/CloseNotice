# Quick Start Guide

## 5-Minute Setup

### 1. Get API Keys (5 minutes)

**Finnhub (Stock News):**
- Go to: https://finnhub.io/register
- Sign up → Copy API key
- Free tier: 60 calls/min (perfect for our 51 tickers)

**Groq (LLM Analysis):**
- Go to: https://console.groq.com/keys
- Sign up → Create key → Copy it
- Free tier: Generous limits for Llama 3.1

**Telegram Bot:**
- Open Telegram → Search `@BotFather`
- Send: `/newbot` → Follow steps → Copy bot token
- Send `/start` to your new bot
- Get chat ID: Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
- Send a message to your bot → Refresh URL → Copy chat ID from response

### 2. Local Setup (2 minutes)

```bash
# Clone and setup
cd CloseNotice

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Or (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

### 3. Configure API Keys (1 minute)

Edit `.env` file:

```env
FINNHUB_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 4. Test Setup (1 minute)

```bash
# Run setup test
python test_setup.py
```

Should see:
- ✓ All imports successful
- ✓ Configuration validated
- ✓ Telegram message sent successfully

### 5. First Run (2 minutes)

```bash
# Run full analysis
python -m src.main
```

You should receive a Telegram report within ~70 seconds!

## GitHub Actions Setup (10 minutes)

### 1. Configure Git Identity (if needed)

```bash
git config --global user.email "your.email@example.com"
git config --global user.name "Your Name"
```

### 2. Commit and Push

```bash
# Initial commit
git add .
git commit -m "Initial commit: Stock News Analysis System"

# Create GitHub repository (via web UI)
# Then:
git remote add origin https://github.com/YOUR_USERNAME/CloseNotice.git
git branch -M main
git push -u origin main
```

### 3. Add GitHub Secrets

Go to: **Your Repository → Settings → Secrets and variables → Actions → New repository secret**

Add these 4 secrets:
1. `FINNHUB_API_KEY`
2. `GROQ_API_KEY`
3. `TELEGRAM_BOT_TOKEN`
4. `TELEGRAM_CHAT_ID`

### 4. Test Workflow

- Go to **Actions** tab
- Select **Daily Stock Analysis**
- Click **Run workflow**
- Wait ~2 minutes
- Check Telegram for report!

### 5. Enable Daily Runs

Already configured! Runs automatically at 5 PM EST (10 PM UTC).

**Important**: Adjust for daylight saving time:
- Edit `.github/workflows/daily_analysis.yml`
- EST (Nov-Mar): `cron: '0 22 * * *'` (current)
- EDT (Mar-Nov): `cron: '0 21 * * *'` (uncomment line 8, comment line 7)

## What It Does

1. **Fetches news** for 51 tickers (FNILX top 50 + UURAF)
2. **Aggregates** all FNILX holdings into single dataset
3. **Analyzes** with AI:
   - FNILX fund-level sentiment (all 50 holdings combined)
   - UURAF individual sentiment
4. **Logs** to CSV for trend tracking
5. **Sends** formatted report to Telegram

## Sample Output

```
📊 Daily Analysis - Jan 18, 2026

📈 FNILX (Fidelity ZERO Large Cap) | Score: 7/10
Based on 50 holdings
• Tech sector driving bullish momentum with strong earnings
• Mixed signals from financials amid rate uncertainty
• Energy sector showing resilience despite macro headwinds

✅ UURAF | Score: 6/10
• Nuclear energy policy developments favorable
• Uranium spot price showing stability
• Production ramp-up on schedule

---
📊 Articles analyzed: 127
⏱️ Runtime: 2m 15s
✅ All analyses successful
```

## Troubleshooting

**No Telegram message?**
```bash
python test_setup.py
```

**Rate limit errors?**
- Increase delay in `.env`: `API_CALL_DELAY=1.5`

**Weekend quiet?**
- Normal! Market closed on weekends
- System sends "Market Quiet" notification

**GitHub Actions fails?**
- Check Actions logs
- Verify all 4 secrets are set correctly
- Ensure GITHUB_TOKEN has write permissions

## Key Files

- `src/main.py` - Main orchestration
- `src/config/tickers.py` - Update FNILX holdings here
- `data/sentiment_history.csv` - Historical sentiment data
- `logs/analysis.log` - Detailed logs

## Updating FNILX Holdings

```python
# Edit src/config/tickers.py
FNILX_TOP50_WITH_SECTORS = {
    "NVDA": "Tech/AI",
    "AAPL": "Tech/Hardware",
    # ... add/update tickers
}
```

Update quarterly when fund rebalances.

## Cost

**$0/month** - All APIs are free tier!

## Next Steps

1. Run locally: `python -m src.main`
2. Set up GitHub Actions (auto-daily at 5 PM)
3. Monitor sentiment trends in CSV
4. Customize tickers in `src/config/tickers.py`

## Support

- 📖 Full docs: `README.md`
- 🐛 Issues: Check logs in `logs/analysis.log`
- 💬 Questions: Open GitHub issue

---

**Ready to go!** 🚀

Run: `python -m src.main`
