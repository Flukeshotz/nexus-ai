"""
Sentiment Analysis Service.
Provides financial text sentiment scoring using a lightweight
rule-based approach (FinBERT can be swapped in as a drop-in).

Handles edgeCases.md §2.4: Contradictory sentiment detection.
"""

import re
import logging
from typing import Optional
from datetime import date

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Keyword-based Sentiment (lightweight fallback for FinBERT)
# ═══════════════════════════════════════════════════════════════

BULLISH_KEYWORDS = {
    "surge", "rally", "bullish", "growth", "outperform", "upgrade",
    "beat", "strong", "profit", "record", "soar", "boom", "upside",
    "breakthrough", "momentum", "optimistic", "exceeded", "positive",
    "higher", "gain", "recovery", "innovative", "expansion",
}

BEARISH_KEYWORDS = {
    "crash", "bearish", "decline", "downgrade", "miss", "loss",
    "weak", "risk", "recession", "fall", "plunge", "sink", "fear",
    "default", "bankrupt", "layoff", "sell-off", "warning", "lower",
    "negative", "contraction", "debt", "overvalued", "bubble",
}


def analyze_sentiment_keywords(text: str) -> dict:
    """
    Lightweight keyword-based sentiment analysis.

    Returns:
        {
            "sentiment": "bullish" | "bearish" | "neutral",
            "confidence": float (0-1),
            "bullish_count": int,
            "bearish_count": int,
        }
    """
    if not text or not text.strip():
        return {
            "sentiment": "neutral",
            "confidence": 0.0,
            "bullish_count": 0,
            "bearish_count": 0,
        }

    words = set(re.findall(r'\b\w+\b', text.lower()))

    bullish_hits = words & BULLISH_KEYWORDS
    bearish_hits = words & BEARISH_KEYWORDS
    bullish_count = len(bullish_hits)
    bearish_count = len(bearish_hits)
    total = bullish_count + bearish_count

    if total == 0:
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "bullish_count": 0,
            "bearish_count": 0,
        }

    if bullish_count > bearish_count:
        sentiment = "bullish"
        confidence = bullish_count / total
    elif bearish_count > bullish_count:
        sentiment = "bearish"
        confidence = bearish_count / total
    else:
        sentiment = "neutral"
        confidence = 0.5

    return {
        "sentiment": sentiment,
        "confidence": round(confidence, 3),
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
    }


# ═══════════════════════════════════════════════════════════════
# Sentiment Divergence Detection (edgeCases.md §2.4)
# ═══════════════════════════════════════════════════════════════

def detect_sentiment_divergence(
    sentiment_scores: list,
    divergence_threshold: float = 0.4,
) -> dict:
    """
    Edge Case §2.4: Detect contradictory sentiment across multiple articles
    for the same ticker/sector.

    Args:
        sentiment_scores: list of dicts with "sentiment" and "confidence" keys.
        divergence_threshold: If both bullish and bearish each represent >threshold
                             of total articles, flag as divergent.

    Returns:
        {
            "is_divergent": bool,
            "bullish_pct": float,
            "bearish_pct": float,
            "neutral_pct": float,
            "recommendation": str,
        }
    """
    if not sentiment_scores:
        return {
            "is_divergent": False,
            "bullish_pct": 0,
            "bearish_pct": 0,
            "neutral_pct": 0,
            "recommendation": "No sentiment data available.",
        }

    total = len(sentiment_scores)
    bullish = sum(1 for s in sentiment_scores if s.get("sentiment") == "bullish")
    bearish = sum(1 for s in sentiment_scores if s.get("sentiment") == "bearish")
    neutral = total - bullish - bearish

    bullish_pct = bullish / total
    bearish_pct = bearish / total
    neutral_pct = neutral / total

    is_divergent = (bullish_pct >= divergence_threshold and bearish_pct >= divergence_threshold)

    if is_divergent:
        recommendation = (
            "SENTIMENT_DIVERGENCE: Market consensus is currently fractured. "
            f"Analysts are divided — {bullish_pct:.0%} bullish vs {bearish_pct:.0%} bearish. "
            "Recommend maintaining current position weight until consensus forms."
        )
    elif bullish_pct > 0.6:
        recommendation = f"Strong bullish consensus ({bullish_pct:.0%}). Favorable outlook."
    elif bearish_pct > 0.6:
        recommendation = f"Strong bearish consensus ({bearish_pct:.0%}). Caution advised."
    else:
        recommendation = "Mixed/neutral sentiment. No strong directional signal."

    return {
        "is_divergent": is_divergent,
        "bullish_pct": round(bullish_pct, 3),
        "bearish_pct": round(bearish_pct, 3),
        "neutral_pct": round(neutral_pct, 3),
        "recommendation": recommendation,
    }


# ═══════════════════════════════════════════════════════════════
# Batch Sentiment Analysis
# ═══════════════════════════════════════════════════════════════

def analyze_articles_batch(articles: list) -> list:
    """
    Run sentiment analysis on a batch of articles.

    Args:
        articles: list of dicts with at least "title" and optionally "content" keys.

    Returns:
        list of sentiment result dicts.
    """
    results = []
    for article in articles:
        text = article.get("title", "") + " " + article.get("content", "")
        sentiment = analyze_sentiment_keywords(text)
        sentiment["article_title"] = article.get("title", "")
        sentiment["source"] = article.get("source", "unknown")
        results.append(sentiment)
    return results
