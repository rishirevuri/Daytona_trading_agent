"""
Earnings call transcript analysis.

Analyzes earnings call transcripts for sentiment, key phrases,
and correlates with post-earnings stock price movements.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import numpy as np


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""

    score: float  # -1 to 1
    positive_count: int
    negative_count: int
    neutral_count: int
    confidence: float
    key_phrases: list[str]


@dataclass
class EarningsAnalysis:
    """Complete earnings analysis result."""

    ticker: str
    earnings_date: datetime
    sentiment: SentimentResult
    price_reaction: dict
    guidance_summary: str
    risk_factors: list[str]


class EarningsAnalyzer:
    """Analyze earnings call transcripts and correlate with price movements."""

    # Positive sentiment words for financial context
    POSITIVE_WORDS = {
        "growth", "increase", "improved", "strong", "exceeded", "beat",
        "momentum", "robust", "solid", "accelerated", "outperformed",
        "profitable", "expanding", "positive", "optimistic", "confident",
        "record", "best", "highest", "success", "achievement", "upside",
        "opportunity", "innovation", "efficiency", "synergy", "tailwind",
    }

    # Negative sentiment words for financial context
    NEGATIVE_WORDS = {
        "decline", "decrease", "weak", "missed", "below", "challenging",
        "headwind", "uncertain", "difficult", "pressure", "concern",
        "risk", "loss", "slower", "softness", "disappointing", "impact",
        "delayed", "reduced", "lower", "downturn", "volatility", "caution",
        "restructuring", "impairment", "write-off", "litigation",
    }

    # Key guidance phrases to extract
    GUIDANCE_PATTERNS = [
        r"(?:we expect|we anticipate|guidance|outlook|forecast)[^.]*\d+[^.]*",
        r"(?:full[- ]year|quarterly|annual) (?:revenue|earnings|eps)[^.]*\d+[^.]*",
        r"(?:raising|lowering|maintaining|reaffirming) (?:our )?(?:guidance|outlook)[^.]*",
    ]

    # Risk indicator phrases
    RISK_PATTERNS = [
        r"(?:supply chain|inflation|foreign exchange|currency)[^.]*(?:impact|pressure|headwind)[^.]*",
        r"(?:regulatory|compliance|legal)[^.]*(?:risk|issue|challenge)[^.]*",
        r"(?:competitive|market)[^.]*(?:pressure|threat|challenge)[^.]*",
    ]

    def __init__(self):
        """Initialize analyzer."""
        pass

    def analyze_sentiment(self, text: str) -> SentimentResult:
        """Analyze sentiment of earnings call transcript.

        Args:
            text: Full transcript text

        Returns:
            SentimentResult with scores and key phrases
        """
        # Normalize text
        text_lower = text.lower()
        words = re.findall(r'\b[a-z]+\b', text_lower)

        # Count sentiment words
        positive_count = sum(1 for w in words if w in self.POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in self.NEGATIVE_WORDS)
        total_sentiment_words = positive_count + negative_count

        # Calculate score
        if total_sentiment_words > 0:
            score = (positive_count - negative_count) / total_sentiment_words
        else:
            score = 0.0

        # Extract key phrases (sentences with strong sentiment)
        sentences = re.split(r'[.!?]', text)
        key_phrases = []

        for sentence in sentences:
            sentence_lower = sentence.lower()
            sentence_words = set(re.findall(r'\b[a-z]+\b', sentence_lower))

            pos_matches = sentence_words.intersection(self.POSITIVE_WORDS)
            neg_matches = sentence_words.intersection(self.NEGATIVE_WORDS)

            # Strong positive or negative sentence
            if len(pos_matches) >= 2 or len(neg_matches) >= 2:
                key_phrases.append(sentence.strip())

        # Calculate confidence based on sample size
        confidence = min(1.0, total_sentiment_words / 100)

        return SentimentResult(
            score=score,
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=len(words) - total_sentiment_words,
            confidence=confidence,
            key_phrases=key_phrases[:10],  # Top 10 key phrases
        )

    def extract_guidance(self, text: str) -> list[str]:
        """Extract guidance statements from transcript.

        Args:
            text: Full transcript text

        Returns:
            List of guidance statements
        """
        guidance_statements = []

        for pattern in self.GUIDANCE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            guidance_statements.extend(matches)

        # Deduplicate and clean
        seen = set()
        unique_guidance = []
        for stmt in guidance_statements:
            cleaned = stmt.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                unique_guidance.append(cleaned)

        return unique_guidance

    def extract_risk_factors(self, text: str) -> list[str]:
        """Extract risk factor mentions from transcript.

        Args:
            text: Full transcript text

        Returns:
            List of risk factor statements
        """
        risk_statements = []

        for pattern in self.RISK_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            risk_statements.extend(matches)

        # Deduplicate
        return list(set(stmt.strip() for stmt in risk_statements if stmt.strip()))

    def calculate_price_reaction(
        self,
        prices: pd.DataFrame,
        earnings_date: datetime,
        window_days: int = 5,
    ) -> dict:
        """Calculate price reaction around earnings date.

        Args:
            prices: DataFrame with OHLCV data indexed by date
            earnings_date: Date of earnings announcement
            window_days: Days to analyze before/after

        Returns:
            Dictionary with price reaction metrics
        """
        # Find the earnings date in the price data
        earnings_dt = pd.Timestamp(earnings_date)

        # Get pre-earnings prices
        pre_start = earnings_dt - timedelta(days=window_days + 5)
        pre_prices = prices.loc[pre_start:earnings_dt - timedelta(days=1)]

        # Get post-earnings prices
        post_end = earnings_dt + timedelta(days=window_days + 5)
        post_prices = prices.loc[earnings_dt:post_end]

        if len(pre_prices) == 0 or len(post_prices) == 0:
            return {
                "error": "Insufficient price data around earnings date",
            }

        # Calculate metrics
        pre_close = pre_prices["close"].iloc[-1]
        post_open = post_prices["open"].iloc[0] if len(post_prices) > 0 else pre_close
        post_close = post_prices["close"].iloc[-1] if len(post_prices) > 0 else pre_close

        overnight_gap = (post_open - pre_close) / pre_close
        day_1_return = (post_prices["close"].iloc[0] - pre_close) / pre_close if len(post_prices) > 0 else 0
        day_5_return = (post_close - pre_close) / pre_close

        # Volatility comparison
        pre_volatility = pre_prices["close"].pct_change().std()
        post_volatility = post_prices["close"].pct_change().std()

        return {
            "pre_close": float(pre_close),
            "post_open": float(post_open),
            "overnight_gap": float(overnight_gap),
            "day_1_return": float(day_1_return),
            "day_5_return": float(day_5_return),
            "pre_volatility": float(pre_volatility),
            "post_volatility": float(post_volatility),
            "volatility_change": float((post_volatility - pre_volatility) / pre_volatility)
            if pre_volatility > 0
            else 0,
        }

    def analyze_earnings(
        self,
        ticker: str,
        transcript: str,
        prices: pd.DataFrame,
        earnings_date: datetime,
    ) -> EarningsAnalysis:
        """Perform complete earnings analysis.

        Args:
            ticker: Stock ticker symbol
            transcript: Earnings call transcript
            prices: Historical price data
            earnings_date: Date of earnings announcement

        Returns:
            EarningsAnalysis with all results
        """
        # Sentiment analysis
        sentiment = self.analyze_sentiment(transcript)

        # Extract guidance
        guidance_statements = self.extract_guidance(transcript)
        guidance_summary = "; ".join(guidance_statements[:5]) if guidance_statements else "No specific guidance extracted"

        # Extract risk factors
        risk_factors = self.extract_risk_factors(transcript)

        # Price reaction
        price_reaction = self.calculate_price_reaction(prices, earnings_date)

        return EarningsAnalysis(
            ticker=ticker,
            earnings_date=earnings_date,
            sentiment=sentiment,
            price_reaction=price_reaction,
            guidance_summary=guidance_summary,
            risk_factors=risk_factors,
        )

    def sentiment_vs_returns_correlation(
        self,
        analyses: list[EarningsAnalysis],
    ) -> dict:
        """Calculate correlation between sentiment and returns.

        Args:
            analyses: List of EarningsAnalysis results

        Returns:
            Correlation statistics
        """
        sentiments = []
        returns_1d = []
        returns_5d = []

        for analysis in analyses:
            if "error" not in analysis.price_reaction:
                sentiments.append(analysis.sentiment.score)
                returns_1d.append(analysis.price_reaction.get("day_1_return", 0))
                returns_5d.append(analysis.price_reaction.get("day_5_return", 0))

        if len(sentiments) < 2:
            return {"error": "Insufficient data for correlation"}

        sentiments = np.array(sentiments)
        returns_1d = np.array(returns_1d)
        returns_5d = np.array(returns_5d)

        corr_1d = np.corrcoef(sentiments, returns_1d)[0, 1]
        corr_5d = np.corrcoef(sentiments, returns_5d)[0, 1]

        return {
            "sentiment_return_1d_correlation": float(corr_1d),
            "sentiment_return_5d_correlation": float(corr_5d),
            "sample_size": len(sentiments),
            "avg_sentiment": float(np.mean(sentiments)),
            "avg_return_1d": float(np.mean(returns_1d)),
            "avg_return_5d": float(np.mean(returns_5d)),
        }
