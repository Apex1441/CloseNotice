"""
LLM prompt templates for sentiment analysis.

Provides structured prompts with:
- Hallucination guardrails (Insufficient Data handling)
- Sector-specific focus
- Magnificent 7 vs breadth detection
- Industry-specific catalysts for individual stocks
"""

# ============================================================================
# Aggregate Analysis Prompt (FNILX Fund-Level)
# ============================================================================

AGGREGATE_PROMPT = """You are a Senior Portfolio Manager at a top-tier hedge fund. Provide a high-conviction analysis of {fund_name}.

Context: Today, {active_count} out of {total_holdings} holdings in {fund_name} had newsworthy developments. The remaining stocks had no significant news.

Sector-Tagged News Articles:
{articles}

Each article is tagged with its sector (e.g., "Tech/AI", "Financials/Banking") to help you identify sector-level trends.

CRITICAL INSTRUCTIONS:
1. **Hallucination Guard**: If the provided news is insufficient, outdated, or sparse, respond with "Insufficient Data" in the rationale. DO NOT attempt to guess current sentiment based on your training data.

2. **Signal Diversification**: This fund is market-cap weighted. Explicitly identify if sentiment is driven by the largest holdings (the "Top Weights") or if there is broader "market breadth" across the mid-sized and smaller holdings in the sample.

3. **Sector Rotation**: Identify any sector rotation themes (e.g., "Tech to Financials rotation", "Risk-on to defensive shift").

4. **Macro Context**: Consider macro themes like industrial trends, interest rates, policy changes, and earnings season relevant to the holdings.

Provide an aggregate fund-level sentiment analysis in JSON format:
{{
  "ticker": "{fund_name}",
  "sentiment_score": <1-10 integer>,
  "top_insights": [
    "Identify if sentiment is top-heavy or broad-based",
    "Sector rotation or dominant sector theme",
    "Key macro risk or opportunity"
  ],
  "rationale": "<fund-level explanation or 'Insufficient Data'>"
}}

Sentiment Scale:
1-3: Bearish (Negative news outweighs positive, downside risks)
4-6: Neutral (Mixed signals, balanced news, or low conviction)
7-10: Bullish (Positive news dominates, upside catalysts)

Focus on: Weight concentration vs breadth, sector rotation, and relevant macro themes.

IMPORTANT: Return ONLY the JSON object, no additional text or markdown formatting.
"""

# ============================================================================
# Individual Analysis Prompt (Single Stock)
# ============================================================================

INDIVIDUAL_PROMPT = """You are a Senior Equity Analyst specializing in {sector}. Analyze the following news for {ticker}:

News Articles:
{articles}

CRITICAL INSTRUCTIONS:
1. **Hallucination Guard**: If news is insufficient or outdated, respond with "Insufficient Data" in rationale. DO NOT guess based on historical knowledge.

2. **Sector-Specific Focus**: For {ticker} ({sector}), focus on industry-specific catalysts:
   - Energy/Uranium: Spot prices, policy (IRA, nuclear renaissance), production, enrichment capacity, supply/demand
   - Tech: Product launches, earnings, competitive dynamics, regulatory
   - Financials: Credit trends, rates, loan growth, capital allocation
   - Healthcare: Drug approvals, clinical trials, reimbursement, M&A
   - Consumer: Sales trends, traffic, pricing power, margin expansion
   - NOT general market sentiment or macro trends (unless directly impacting sector)

3. **Company-Specific**: Focus on company-specific news, not broader sector commentary.

Provide analysis in JSON format:
{{
  "ticker": "{ticker}",
  "sentiment_score": <1-10 integer>,
  "top_insights": [
    "Sector-specific catalyst 1",
    "Sector-specific catalyst 2",
    "Sector-specific catalyst 3"
  ],
  "rationale": "<sector-focused explanation or 'Insufficient Data'>"
}}

Sentiment Scale:
1-3: Bearish (Negative developments, downside risks)
4-6: Neutral (Mixed news, balanced outlook)
7-10: Bullish (Positive catalysts, upside potential)

Focus on: Industry-specific drivers, NOT general market conditions.

IMPORTANT: Return ONLY the JSON object, no additional text or markdown formatting.
"""

# ============================================================================
# Helper Functions
# ============================================================================

def format_aggregate_prompt(
    fund_name: str,
    articles: list,
    active_count: int,
    total_holdings: int
) -> str:
    """
    Format the aggregate analysis prompt with actual data.

    Args:
        fund_name: Fund name (e.g., "FNILX")
        articles: List of article dicts with ticker, sector, headline, summary
        active_count: Number of holdings with news
        total_holdings: Total number of holdings (50)

    Returns:
        Formatted prompt string
    """
    # Format articles as readable text
    articles_text = ""
    for article in articles:
        articles_text += f"\n[{article['ticker']} - {article['sector']}]\n"
        articles_text += f"Headline: {article['headline']}\n"
        articles_text += f"Summary: {article['summary']}\n"
        articles_text += f"Source: {article['source']}\n"

    return AGGREGATE_PROMPT.format(
        fund_name=fund_name,
        articles=articles_text.strip(),
        active_count=active_count,
        total_holdings=total_holdings
    )


def format_individual_prompt(
    ticker: str,
    sector: str,
    articles: list
) -> str:
    """
    Format the individual analysis prompt with actual data.

    Args:
        ticker: Stock ticker symbol
        sector: Sector tag (e.g., "Energy/Uranium")
        articles: List of article dicts with headline, summary

    Returns:
        Formatted prompt string
    """
    # Format articles as readable text
    articles_text = ""
    for article in articles:
        articles_text += f"\nHeadline: {article.get('headline', 'N/A')}\n"
        articles_text += f"Summary: {article.get('summary', 'N/A')}\n"
        articles_text += f"Source: {article.get('source', 'Unknown')}\n"

    return INDIVIDUAL_PROMPT.format(
        ticker=ticker,
        sector=sector,
        articles=articles_text.strip()
    )


def get_sentiment_label(score: int) -> str:
    """
    Get sentiment label from score.

    Args:
        score: Sentiment score (1-10)

    Returns:
        Label string (Bearish, Neutral, or Bullish)
    """
    if score <= 3:
        return "Bearish"
    elif score <= 6:
        return "Neutral"
    else:
        return "Bullish"


def get_sentiment_emoji(score: int) -> str:
    """
    Get emoji for sentiment score.

    Args:
        score: Sentiment score (1-10)

    Returns:
        Emoji string
    """
    if score <= 3:
        return "📉"
    elif score <= 6:
        return "➖"
    else:
        return "📈"
