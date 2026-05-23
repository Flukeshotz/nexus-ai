"""
Comprehensive tests for Phase 2: Data Intelligence & Market Pipeline.
Covers:
  - Anomaly detection (fat-finger, halted securities)
  - Staleness circuit breaker
  - Technical indicators computation
  - Sentiment analysis & divergence detection
  - Text cleaning and chunking for RAG
  - News ticker extraction
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta


# ═══════════════════════════════════════════════════════════════
# 1. ANOMALY DETECTION TESTS (edgeCases.md §2.2)
# ═══════════════════════════════════════════════════════════════

class TestAnomalyDetection:
    """edgeCases.md §2.2: Fat-finger and unadjusted split detection."""

    def test_normal_price_change_not_flagged(self):
        from app.services.market_data_service import detect_price_anomaly
        is_anomaly, reason = detect_price_anomaly(105, 100)
        assert is_anomaly is False
        assert reason is None

    def test_40pct_drop_flagged_as_anomaly(self):
        """A 50% single-day drop should be flagged (possible split)."""
        from app.services.market_data_service import detect_price_anomaly
        is_anomaly, reason = detect_price_anomaly(50, 100)
        assert is_anomaly is True
        assert "EXTREME_MOVE" in reason
        assert "-50.0%" in reason

    def test_40pct_surge_flagged_as_anomaly(self):
        """A 50% single-day surge should be flagged."""
        from app.services.market_data_service import detect_price_anomaly
        is_anomaly, reason = detect_price_anomaly(150, 100)
        assert is_anomaly is True
        assert "EXTREME_MOVE" in reason

    def test_zero_price_flagged(self):
        """Zero price should always be flagged."""
        from app.services.market_data_service import detect_price_anomaly
        is_anomaly, reason = detect_price_anomaly(0, 100)
        assert is_anomaly is True
        assert "INVALID_PRICE" in reason

    def test_negative_price_flagged(self):
        """Negative price should be flagged."""
        from app.services.market_data_service import detect_price_anomaly
        is_anomaly, reason = detect_price_anomaly(-10, 100)
        assert is_anomaly is True
        assert "INVALID_PRICE" in reason

    def test_zscore_anomaly_with_history(self):
        """A statistically extreme move against calm history should trigger z-score flag."""
        from app.services.market_data_service import detect_price_anomaly
        # Simulate calm history with slight variation (daily returns of ~0.1% ± 0.05%)
        import random
        random.seed(42)
        calm_returns = [0.001 + random.uniform(-0.0005, 0.0005) for _ in range(50)]
        # Then a 20% drop (within 40% hard threshold but extreme z-score)
        is_anomaly, reason = detect_price_anomaly(80, 100, calm_returns)
        assert is_anomaly is True
        assert "ZSCORE_ANOMALY" in reason

    def test_normal_move_in_volatile_history(self):
        """A 10% move in already volatile history should NOT trigger z-score."""
        from app.services.market_data_service import detect_price_anomaly
        # Simulate volatile history (daily returns of ~5%)
        volatile_returns = [0.05, -0.04, 0.06, -0.05, 0.03] * 10
        is_anomaly, reason = detect_price_anomaly(110, 100, volatile_returns)
        assert is_anomaly is False

    def test_exactly_at_threshold_not_flagged(self):
        """39.9% change should NOT be flagged (under 40% threshold)."""
        from app.services.market_data_service import detect_price_anomaly
        price = 100 * (1 - 0.399)  # 60.1
        is_anomaly, _ = detect_price_anomaly(price, 100)
        assert is_anomaly is False


# ═══════════════════════════════════════════════════════════════
# 2. STALENESS CIRCUIT BREAKER TESTS (edgeCases.md §2.1)
# ═══════════════════════════════════════════════════════════════

class TestStalenessCircuitBreaker:
    """edgeCases.md §2.1: Stale data detection during market hours."""

    def test_fresh_data_not_stale(self):
        from app.services.market_data_service import check_data_staleness
        recent = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = check_data_staleness(recent, market_is_open=True)
        assert result["is_stale"] is False
        assert result["warning"] is None

    def test_stale_data_during_market_hours(self):
        from app.services.market_data_service import check_data_staleness
        old = datetime.now(timezone.utc) - timedelta(minutes=30)
        result = check_data_staleness(old, market_is_open=True)
        assert result["is_stale"] is True
        assert "STALE_DATA" in result["warning"]
        assert "HALTED" in result["warning"]

    def test_stale_data_outside_market_hours_ok(self):
        """Data from 2 hours ago is fine if market is closed."""
        from app.services.market_data_service import check_data_staleness
        old = datetime.now(timezone.utc) - timedelta(hours=2)
        result = check_data_staleness(old, market_is_open=False)
        assert result["is_stale"] is False

    def test_exact_threshold_boundary(self):
        """Data exactly at the 15-minute threshold."""
        from app.services.market_data_service import check_data_staleness
        boundary = datetime.now(timezone.utc) - timedelta(minutes=15, seconds=1)
        result = check_data_staleness(boundary, market_is_open=True)
        assert result["is_stale"] is True


# ═══════════════════════════════════════════════════════════════
# 3. TECHNICAL INDICATORS TESTS
# ═══════════════════════════════════════════════════════════════

class TestTechnicalIndicators:
    """Test all technical indicator computations."""

    @pytest.fixture
    def sample_prices(self):
        """Generate 300 days of realistic stock price data."""
        np.random.seed(42)
        dates = pd.date_range(end=pd.Timestamp.today(), periods=300, freq='B')
        # Random walk starting at 100
        returns = np.random.normal(0.0005, 0.015, 300)
        prices = 100 * np.cumprod(1 + returns)
        return pd.Series(prices, index=dates)

    @pytest.fixture
    def indicators(self, sample_prices):
        from app.services.technical_indicators import TechnicalIndicators
        return TechnicalIndicators(sample_prices)

    def test_rsi_in_valid_range(self, indicators):
        rsi = indicators.rsi(14)
        assert rsi is not None
        assert 0 <= rsi <= 100, f"RSI {rsi} out of range"

    def test_sma_50_computed(self, indicators):
        sma = indicators.sma(50)
        assert sma is not None
        assert sma > 0

    def test_sma_200_computed(self, indicators):
        sma = indicators.sma(200)
        assert sma is not None
        assert sma > 0

    def test_sma_returns_none_insufficient_data(self):
        from app.services.technical_indicators import TechnicalIndicators
        short = pd.Series([100, 101, 102], index=pd.date_range("2024-01-01", periods=3))
        ti = TechnicalIndicators(short)
        assert ti.sma(50) is None

    def test_ema_12_computed(self, indicators):
        ema = indicators.ema(12)
        assert ema is not None
        assert ema > 0

    def test_macd_computed(self, indicators):
        macd = indicators.macd()
        assert macd["macd"] is not None
        assert macd["signal"] is not None
        assert macd["histogram"] is not None

    def test_macd_returns_none_insufficient_data(self):
        from app.services.technical_indicators import TechnicalIndicators
        short = pd.Series(range(100, 120), index=pd.date_range("2024-01-01", periods=20))
        ti = TechnicalIndicators(short)
        macd = ti.macd()
        assert macd["macd"] is None

    def test_bollinger_bands(self, indicators):
        bb = indicators.bollinger_bands()
        assert bb["upper"] is not None
        assert bb["lower"] is not None
        assert bb["upper"] > bb["lower"], "Upper band must be above lower band"

    def test_volatility_30d(self, indicators):
        vol = indicators.volatility_30d()
        assert vol is not None
        assert vol > 0, "Volatility must be positive"
        assert vol < 5, "Annualized vol should be realistic (< 500%)"

    def test_sharpe_ratio(self, indicators):
        sharpe = indicators.sharpe_ratio()
        assert sharpe is not None
        assert -10 < sharpe < 10, f"Sharpe {sharpe} seems unrealistic"

    def test_max_drawdown_is_negative(self, indicators):
        mdd = indicators.max_drawdown()
        assert mdd is not None
        assert mdd <= 0, "Max drawdown should be zero or negative"

    def test_beta_with_benchmark(self, indicators, sample_prices):
        # Use the same prices as a "benchmark" → beta should be ~1.0
        benchmark_returns = sample_prices.pct_change().dropna()
        beta = indicators.beta(benchmark_returns)
        assert beta is not None
        assert 0.9 <= beta <= 1.1, f"Self-beta should be ~1.0, got {beta}"

    def test_compute_all_returns_complete_dict(self, indicators):
        result = indicators.compute_all()
        expected_keys = {
            "rsi_14", "sma_50", "sma_200", "ema_12", "ema_26",
            "macd", "macd_signal", "bollinger_upper", "bollinger_lower",
            "volatility_30d", "sharpe_ratio", "max_drawdown", "beta",
        }
        assert expected_keys == set(result.keys())

    def test_empty_prices_raises_error(self):
        from app.services.technical_indicators import TechnicalIndicators
        with pytest.raises(ValueError, match="empty"):
            TechnicalIndicators(pd.Series([], dtype=float))


# ═══════════════════════════════════════════════════════════════
# 4. SENTIMENT ANALYSIS TESTS (edgeCases.md §2.4)
# ═══════════════════════════════════════════════════════════════

class TestSentimentAnalysis:
    """Test sentiment scoring and divergence detection."""

    def test_bullish_text(self):
        from app.services.sentiment_service import analyze_sentiment_keywords
        result = analyze_sentiment_keywords(
            "Apple stock surges to record high on strong earnings, beating analyst expectations"
        )
        assert result["sentiment"] == "bullish"
        assert result["confidence"] > 0.5
        assert result["bullish_count"] > 0

    def test_bearish_text(self):
        from app.services.sentiment_service import analyze_sentiment_keywords
        result = analyze_sentiment_keywords(
            "Stock market crash as recession fears grow, massive sell-off across sectors"
        )
        assert result["sentiment"] == "bearish"
        assert result["confidence"] > 0.5
        assert result["bearish_count"] > 0

    def test_neutral_text(self):
        from app.services.sentiment_service import analyze_sentiment_keywords
        result = analyze_sentiment_keywords(
            "The quarterly report was released today for the company."
        )
        assert result["sentiment"] == "neutral"

    def test_empty_text_returns_neutral(self):
        from app.services.sentiment_service import analyze_sentiment_keywords
        result = analyze_sentiment_keywords("")
        assert result["sentiment"] == "neutral"
        assert result["confidence"] == 0.0

    def test_none_text_returns_neutral(self):
        from app.services.sentiment_service import analyze_sentiment_keywords
        result = analyze_sentiment_keywords(None)
        assert result["sentiment"] == "neutral"

    # ── Divergence Detection ──────────────────────────────────

    def test_divergence_detected(self):
        """edgeCases.md §2.4: 50% bullish + 50% bearish = divergent."""
        from app.services.sentiment_service import detect_sentiment_divergence
        scores = [
            {"sentiment": "bullish", "confidence": 0.8},
            {"sentiment": "bullish", "confidence": 0.7},
            {"sentiment": "bearish", "confidence": 0.9},
            {"sentiment": "bearish", "confidence": 0.85},
        ]
        result = detect_sentiment_divergence(scores)
        assert result["is_divergent"] is True
        assert result["bullish_pct"] == 0.5
        assert result["bearish_pct"] == 0.5
        assert "SENTIMENT_DIVERGENCE" in result["recommendation"]
        assert "fractured" in result["recommendation"]

    def test_no_divergence_strong_bullish(self):
        from app.services.sentiment_service import detect_sentiment_divergence
        scores = [
            {"sentiment": "bullish", "confidence": 0.8},
            {"sentiment": "bullish", "confidence": 0.7},
            {"sentiment": "bullish", "confidence": 0.9},
            {"sentiment": "neutral", "confidence": 0.5},
        ]
        result = detect_sentiment_divergence(scores)
        assert result["is_divergent"] is False
        assert "bullish consensus" in result["recommendation"].lower()

    def test_empty_scores_no_divergence(self):
        from app.services.sentiment_service import detect_sentiment_divergence
        result = detect_sentiment_divergence([])
        assert result["is_divergent"] is False
        assert "No sentiment data" in result["recommendation"]

    def test_single_article_no_divergence(self):
        from app.services.sentiment_service import detect_sentiment_divergence
        result = detect_sentiment_divergence([{"sentiment": "bearish", "confidence": 0.9}])
        assert result["is_divergent"] is False


# ═══════════════════════════════════════════════════════════════
# 5. TEXT PROCESSING TESTS (RAG Pipeline)
# ═══════════════════════════════════════════════════════════════

class TestTextProcessing:
    """Test text cleaning, chunking, and ticker extraction."""

    def test_html_cleaning(self):
        from app.services.news_service import clean_text
        raw = "<p>Apple <b>stock</b> surges &amp; breaks <em>records</em></p>"
        clean = clean_text(raw)
        assert "<" not in clean
        assert ">" not in clean
        assert "Apple" in clean

    def test_empty_string_cleaning(self):
        from app.services.news_service import clean_text
        assert clean_text("") == ""
        assert clean_text(None) == ""

    def test_chunking_short_text(self):
        from app.services.news_service import chunk_text
        short = "This is a short text."
        chunks = chunk_text(short, chunk_size=512)
        assert len(chunks) == 1
        assert chunks[0] == short

    def test_chunking_long_text(self):
        from app.services.news_service import chunk_text
        long_text = "Word " * 500  # ~2500 chars
        chunks = chunk_text(long_text, chunk_size=512, overlap=50)
        assert len(chunks) > 1
        # All chunks should be non-empty
        assert all(len(c.strip()) > 0 for c in chunks)

    def test_chunking_overlap(self):
        from app.services.news_service import chunk_text
        text = "A" * 1100
        chunks = chunk_text(text, chunk_size=512, overlap=50)
        # With overlap, the second chunk should start before the end of the first
        assert len(chunks) >= 2

    def test_chunking_empty_text(self):
        from app.services.news_service import chunk_text
        assert chunk_text("") == []
        assert chunk_text(None) == []

    def test_ticker_extraction(self):
        from app.services.news_service import extract_tickers
        text = "AAPL and MSFT hit record highs while TSLA dipped."
        tickers = extract_tickers(text)
        assert "AAPL" in tickers
        assert "MSFT" in tickers
        assert "TSLA" in tickers

    def test_ticker_extraction_no_tickers(self):
        from app.services.news_service import extract_tickers
        assert extract_tickers("The market was calm today.") == []

    def test_ticker_extraction_empty(self):
        from app.services.news_service import extract_tickers
        assert extract_tickers("") == []
        assert extract_tickers(None) == []


# ═══════════════════════════════════════════════════════════════
# 6. BATCH SENTIMENT ANALYSIS
# ═══════════════════════════════════════════════════════════════

class TestBatchSentiment:

    def test_batch_analysis(self):
        from app.services.sentiment_service import analyze_articles_batch
        articles = [
            {"title": "Stock market rally continues", "content": "Strong growth expected"},
            {"title": "Market crash fears grow", "content": "Recession indicators rising"},
            {"title": "Quarterly results released", "content": "Revenue matched expectations"},
        ]
        results = analyze_articles_batch(articles)
        assert len(results) == 3
        assert results[0]["sentiment"] in ["bullish", "bearish", "neutral"]
        # First article should be bullish
        assert results[0]["sentiment"] == "bullish"
        # Second should be bearish
        assert results[1]["sentiment"] == "bearish"
