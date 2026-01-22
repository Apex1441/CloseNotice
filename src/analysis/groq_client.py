"""
Groq LLM client for sentiment analysis.

Features:
- Aggregate sentiment analysis for FNILX (all holdings combined)
- Individual sentiment analysis for specific stocks
- Robust JSON parsing (handles markdown code blocks)
- Retry logic for API failures
- Article truncation to prevent context overflow
"""

import re
import json
from typing import Dict, List
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import Settings
from src.config.tickers import get_sector, MAGNIFICENT_7
from src.analysis.prompts import (
    format_aggregate_prompt,
    format_individual_prompt
)
from src.utils.logger import setup_logger, log_api_call
from src.utils.error_handler import InsufficientDataError

logger = setup_logger(__name__)


class GroqClient:
    """Client for Groq LLM API."""

    def __init__(self, api_key: str = None):
        """
        Initialize Groq client.

        Args:
            api_key: Groq API key (defaults to Settings.GROQ_API_KEY)
        """
        self.api_key = api_key or Settings.GROQ_API_KEY
        self.client = Groq(api_key=self.api_key)
        self.model = Settings.GROQ_MODEL
        self.temperature = Settings.GROQ_TEMPERATURE
        self.max_tokens = Settings.GROQ_MAX_TOKENS

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call_llm(self, prompt: str) -> str:
        """
        Call Groq LLM API with retry logic.

        Args:
            prompt: Prompt text

        Returns:
            LLM response text

        Raises:
            Exception: If all retries fail
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst providing sentiment analysis in JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            response_text = response.choices[0].message.content
            log_api_call(logger, "Groq", f"{self.model}", "SUCCESS")

            return response_text

        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            log_api_call(logger, "Groq", f"{self.model}", "FAILURE")
            raise

    def parse_llm_response(self, response_text: str) -> dict:
        """
        Extract JSON from LLM response, handling markdown code blocks.

        LLMs sometimes wrap JSON in ```json ... ``` which breaks json.loads().
        This method extracts the JSON content regardless of formatting.

        Args:
            response_text: Raw LLM response

        Returns:
            Parsed JSON dict

        Raises:
            ValueError: If no valid JSON found
        """
        # Try direct parsing first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        # Pattern: ```json ... ``` or ``` ... ```
        code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(code_block_pattern, response_text, re.DOTALL)

        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Fallback: Extract content between first { and last }
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from: {response_text[:200]}")
                raise ValueError("No valid JSON found in LLM response")

        logger.error(f"No JSON found in response: {response_text[:200]}")
        raise ValueError("No valid JSON found in LLM response")

    def _validate_result(self, result: dict) -> dict:
        """
        Validate LLM response structure and data types.
        """
        # 1. Field presence
        required_fields = ['ticker', 'sentiment_score', 'top_insights', 'rationale']
        missing = [f for f in required_fields if f not in result]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # 2. Sentiment Score (integer 1-10)
        try:
            score = int(result['sentiment_score'])
            if not 1 <= score <= 10:
                raise ValueError(f"Score out of range: {score}")
            result['sentiment_score'] = score
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid sentiment_score: {result.get('sentiment_score')}")

        # 3. Top Insights (non-empty list, 2-3 items)
        insights = result.get('top_insights', [])
        if not isinstance(insights, list) or len(insights) == 0:
            raise ValueError("top_insights must be a non-empty list")
        if len(insights) < 2:
            logger.warning(f"LLM returned only {len(insights)} insights")
        result['top_insights'] = insights[:3]  # Enforce max 3 items

        # 4. Rationale (string, min 20 chars)
        rationale = result.get('rationale', '')
        if not isinstance(rationale, str) or len(rationale) < 20:
            raise ValueError("Rationale too short or not a string")

        return result

    def analyze_aggregate_sentiment(
        self,
        fund_name: str,
        ticker_news_dict: Dict[str, List[dict]],
        ticker_sectors: Dict[str, str]
    ) -> dict:
        """
        Aggregate news from all FNILX holdings into single sentiment analysis.

        Includes sector tags and active ticker count for better LLM context.

        Args:
            fund_name: "FNILX"
            ticker_news_dict: {"AAPL": [articles], "NVDA": [articles], ...}
                              (ONLY tickers with news, filtered by finnhub_client)
            ticker_sectors: {"AAPL": "Tech/Hardware", "NVDA": "Tech/AI", ...}

        Returns:
            {"ticker": "FNILX", "sentiment_score": 7, "top_insights": [...], "rationale": "..."}

        Raises:
            InsufficientDataError: If LLM returns "Insufficient Data"
        """
        logger.info(f"Analyzing aggregate sentiment for {fund_name} ({len(ticker_news_dict)} active holdings)")

        # Combine all articles from all holdings with sector context
        all_articles = []
        for ticker, articles in ticker_news_dict.items():
            sector = ticker_sectors.get(ticker, "Unknown")

            for article in articles:
                # CRITICAL: Truncate summary to prevent context overflow
                # 50 tickers × 200 chars ≈ 10,000 chars (safe for Llama 3.1)
                truncated_summary = article.get('summary', '')[:Settings.MAX_SUMMARY_LENGTH]

                all_articles.append({
                    'ticker': ticker,
                    'sector': sector,
                    'headline': article.get('headline', ''),
                    'summary': truncated_summary,
                    'source': article.get('source', '')
                })

        # Calculate active ticker count
        active_count = len(ticker_news_dict)
        # Dynamic holdings count from get_fund_holdings()
        from src.config.tickers import get_fund_holdings
        total_holdings = len(get_fund_holdings(fund_name)) or 50

        logger.debug(f"Prepared {len(all_articles)} articles from {active_count} tickers")

        # Format prompt
        prompt = format_aggregate_prompt(
            fund_name=fund_name,
            articles=all_articles,
            active_count=active_count,
            total_holdings=total_holdings
        )

        # Call LLM
        try:
            response_text = self._call_llm(prompt)
            result = self.parse_llm_response(response_text)

            # Check for insufficient data response
            if "Insufficient Data" in result.get('rationale', ''):
                logger.warning(f"LLM returned 'Insufficient Data' for {fund_name}")
                raise InsufficientDataError(f"Insufficient news data for {fund_name} analysis")

            # Validate result schema and values
            result = self._validate_result(result)
            
            logger.info(f"✓ {fund_name} analysis complete: Score {result['sentiment_score']}/10")

            return result

        except (InsufficientDataError, ValueError) as e:
            logger.error(f"Failed to analyze {fund_name}: {e}")
            raise

    def analyze_individual_sentiment(
        self,
        ticker: str,
        articles: List[dict]
    ) -> dict:
        """
        Individual sentiment analysis for a single stock.

        Args:
            ticker: Stock ticker symbol
            articles: List of news articles

        Returns:
            {"ticker": "UURAF", "sentiment_score": 6, "top_insights": [...], "rationale": "..."}

        Raises:
            InsufficientDataError: If LLM returns "Insufficient Data"
        """
        logger.info(f"Analyzing individual sentiment for {ticker} ({len(articles)} articles)")

        # Get sector for context
        sector = get_sector(ticker)

        # Truncate article summaries
        truncated_articles = []
        for article in articles:
            truncated_articles.append({
                'headline': article.get('headline', ''),
                'summary': article.get('summary', '')[:Settings.MAX_SUMMARY_LENGTH],
                'source': article.get('source', '')
            })

        # Format prompt
        prompt = format_individual_prompt(
            ticker=ticker,
            sector=sector,
            articles=truncated_articles
        )

        # Call LLM
        try:
            response_text = self._call_llm(prompt)
            result = self.parse_llm_response(response_text)

            # Check for insufficient data response
            if "Insufficient Data" in result.get('rationale', ''):
                logger.warning(f"LLM returned 'Insufficient Data' for {ticker}")
                raise InsufficientDataError(f"Insufficient news data for {ticker} analysis")

            # Validate result schema and values
            result = self._validate_result(result)

            logger.info(f"✓ {ticker} analysis complete: Score {result['sentiment_score']}/10")

            return result

        except (InsufficientDataError, ValueError) as e:
            logger.error(f"Failed to analyze {ticker}: {e}")
            raise


# Convenience functions
def analyze_fnilx(ticker_news_dict: Dict[str, List[dict]]) -> dict:
    """
    Convenience function to analyze FNILX aggregate sentiment.

    Args:
        ticker_news_dict: Dict mapping tickers to their news articles

    Returns:
        Analysis result dict
    """
    from src.config.tickers import FNILX_TOP50_WITH_SECTORS

    client = GroqClient()
    return client.analyze_aggregate_sentiment(
        fund_name="FNILX",
        ticker_news_dict=ticker_news_dict,
        ticker_sectors=FNILX_TOP50_WITH_SECTORS
    )


def analyze_stock(ticker: str, articles: List[dict]) -> dict:
    """
    Convenience function to analyze individual stock sentiment.

    Args:
        ticker: Stock ticker symbol
        articles: List of news articles

    Returns:
        Analysis result dict
    """
    client = GroqClient()
    return client.analyze_individual_sentiment(ticker, articles)
