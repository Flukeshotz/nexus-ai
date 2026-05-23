"""
Market Data API Router.
Exposes endpoints for fetching market data, computing indicators,
and running sentiment analysis.
"""

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/market", tags=["Market Data & Intelligence"])


@router.get("/prices/{ticker}")
async def get_stock_prices(
    ticker: str,
    days: int = Query(default=365, ge=1, le=3650),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch historical OHLCV data for a ticker.
    Includes anomaly detection (fat-finger, halted securities).
    """
    from app.services.market_data_service import fetch_stock_data
    from datetime import date, timedelta

    start_date = (date.today() - timedelta(days=days)).isoformat()
    result = fetch_stock_data(ticker.upper(), start_date)

    if result["error"]:
        raise HTTPException(status_code=502, detail=result["error"])

    return {
        "ticker": result["ticker"],
        "records": len(result["data"]),
        "anomalies_detected": len(result["anomalies"]),
        "anomalies": result["anomalies"],
        "source": result["source"],
        "data": result["data"][-30:],  # Return last 30 days by default
    }


@router.get("/indicators/{ticker}")
async def get_technical_indicators(
    ticker: str,
    days: int = Query(default=365, ge=30, le=3650),
    current_user: User = Depends(get_current_user),
):
    """
    Compute all technical indicators for a ticker.
    Returns RSI, SMA, EMA, MACD, Bollinger, Volatility, Sharpe, Max Drawdown.
    """
    import pandas as pd
    from datetime import date, timedelta
    from app.services.market_data_service import fetch_stock_data
    from app.services.technical_indicators import TechnicalIndicators

    start_date = (date.today() - timedelta(days=days)).isoformat()
    result = fetch_stock_data(ticker.upper(), start_date)

    if result["error"]:
        raise HTTPException(status_code=502, detail=result["error"])

    if not result["data"]:
        raise HTTPException(status_code=404, detail=f"No price data for {ticker}")

    # Build price series (exclude anomalies for indicator computation)
    clean_data = [r for r in result["data"] if not r["is_anomaly"]]
    if len(clean_data) < 30:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient clean data ({len(clean_data)} days). Need at least 30.",
        )

    prices = pd.Series(
        [r["close"] for r in clean_data],
        index=pd.to_datetime([r["price_date"] for r in clean_data]),
    )

    indicators = TechnicalIndicators(prices)
    computed = indicators.compute_all()

    return {
        "ticker": ticker.upper(),
        "data_points": len(clean_data),
        "anomalies_excluded": len(result["data"]) - len(clean_data),
        "indicators": computed,
    }


@router.post("/sentiment/analyze")
async def analyze_sentiment(
    texts: list,
    current_user: User = Depends(get_current_user),
):
    """
    Analyze sentiment of provided financial texts.
    Also detects sentiment divergence (edgeCases.md §2.4).
    """
    from app.services.sentiment_service import (
        analyze_sentiment_keywords,
        detect_sentiment_divergence,
    )

    if not texts:
        raise HTTPException(status_code=422, detail="No texts provided.")

    # Analyze each text
    results = []
    for text in texts:
        if isinstance(text, str):
            results.append(analyze_sentiment_keywords(text))
        elif isinstance(text, dict):
            content = text.get("title", "") + " " + text.get("content", "")
            sentiment = analyze_sentiment_keywords(content)
            sentiment["source"] = text.get("source", "unknown")
            results.append(sentiment)

    # Detect divergence
    divergence = detect_sentiment_divergence(results)

    return {
        "results": results,
        "aggregate": divergence,
    }


@router.get("/staleness-check")
async def check_staleness(
    current_user: User = Depends(get_current_user),
):
    """
    Check if market data is stale (edgeCases.md §2.1).
    Returns staleness status for the circuit breaker.
    """
    from datetime import datetime, timezone
    from app.services.market_data_service import check_data_staleness

    # In production, this would query the latest data timestamp from the DB.
    # For now, simulate with current time (not stale).
    last_update = datetime.now(timezone.utc)
    result = check_data_staleness(last_update, market_is_open=True)

    return {
        "status": "stale" if result["is_stale"] else "fresh",
        "minutes_since_update": result["minutes_since_update"],
        "warning": result["warning"],
        "circuit_breaker_active": result["is_stale"],
    }
