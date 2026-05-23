import os
import json
import logging
from datetime import datetime, timezone
import pandas as pd
import requests

from app.services.market_data_service import fetch_batch_stock_data
from app.services.market_signal_engine import (
    compute_rsi, compute_sma_trend, compute_volatility, 
    compute_inflation_delta, compute_bond_yield_trend, compute_sector_relative_strength
)

logger = logging.getLogger(__name__)

CORE_UNIVERSE = ["SPY", "QQQ", "NIFTYBEES.NS", "GLD", "TLT", "VXUS"]
SNAPSHOT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "market_snapshot.json")

def _fetch_fred_inflation() -> str:
    """Fetch inflation delta from FRED, fallback gracefully."""
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return "Stable"
    
    try:
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=CPIAUCSL&api_key={api_key}&file_type=json&sort_order=desc&limit=2"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()["observations"]
        current_cpi = float(data[0]["value"])
        prev_cpi = float(data[1]["value"])
        return compute_inflation_delta(current_cpi, prev_cpi)
    except Exception as e:
        logger.warning(f"FRED fetch failed, defaulting to Stable: {e}")
        return "Stable"

def generate_market_snapshot() -> dict:
    """
    Single source of truth for market state.
    Fetches raw data, computes deterministic signals, and returns strict JSON.
    """
    logger.info("Generating market snapshot...")
    
    # 1. Fetch raw data
    raw_results = fetch_batch_stock_data(tickers=CORE_UNIVERSE, period_days=250)
    market_data = {}
    for res in raw_results.get("results", []):
        if not res.get("error") and res.get("data"):
            market_data[res["ticker"]] = pd.DataFrame(res["data"])["close"]
            
    # 2. Extract specific asset prices
    spy = market_data.get("SPY", pd.Series(dtype=float))
    qqq = market_data.get("QQQ", pd.Series(dtype=float))
    tlt = market_data.get("TLT", pd.Series(dtype=float))
    
    # 3. Compute top-level regime and signals
    market_regime = compute_sma_trend(spy) if not spy.empty else "Neutral"
    volatility_level = compute_volatility(spy) if not spy.empty else "Moderate"
    interest_rate_trend = compute_bond_yield_trend(tlt) if not tlt.empty else "Stable"
    inflation_trend = _fetch_fred_inflation()
    
    # Compute Fear/Greed Proxy (inverse of VIX/Volatility proxy mapped to 0-100)
    fear_greed_score = 50
    if volatility_level == "High":
        fear_greed_score = 25
    elif volatility_level == "Low":
        fear_greed_score = 75
    
    # Sector Momentum mapping
    tech_mom = compute_sector_relative_strength(qqq, spy) if not qqq.empty else 0.5
    
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_regime": market_regime,
        "inflation_trend": inflation_trend,
        "interest_rate_trend": interest_rate_trend,
        "volatility_level": volatility_level,
        "fear_greed_score": fear_greed_score,
        "sector_momentum": {
            "Technology": round(tech_mom, 2),
            "Bonds": round(compute_sector_relative_strength(tlt, spy) if not tlt.empty else 0.5, 2)
        },
        "asset_signals": {}
    }
    
    # Populate individual asset signals for RAG text generation
    for ticker, prices in market_data.items():
        snapshot["asset_signals"][ticker] = {
            "rsi": compute_rsi(prices),
            "trend": compute_sma_trend(prices)
        }
        
    return snapshot

def update_and_cache_snapshot():
    """Scheduled task function to build, validate, and save the snapshot to disk."""
    snapshot = generate_market_snapshot()
    
    # Enforce strict Pydantic schema validation
    from app.schemas.market_snapshot_schema import MarketSnapshotSchema
    from pydantic import ValidationError
    import shutil
    
    try:
        validated_snapshot = MarketSnapshotSchema(**snapshot)
        snapshot_dict = validated_snapshot.model_dump()
        
        # Save previous snapshot for Delta Reasoning
        PREV_SNAPSHOT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "previous_market_snapshot.json")
        if os.path.exists(SNAPSHOT_FILE):
            shutil.copy(SNAPSHOT_FILE, PREV_SNAPSHOT_FILE)
            
        with open(SNAPSHOT_FILE, "w") as f:
            json.dump(snapshot_dict, f, indent=2)
        logger.info("Snapshot validated and cached successfully.")
        
        # Inject RAG context
        _inject_snapshot_to_rag(snapshot_dict)
    except ValidationError as e:
        logger.error(f"Snapshot Validation Failed. Rejecting state update: {e}")
    except Exception as e:
        logger.error(f"Failed to cache snapshot: {e}")

def _inject_snapshot_to_rag(snapshot: dict):
    from app.services.rag_service import get_vector_store
    
    # Construct grounded semantic context for the LLM
    rag_texts = [
        f"LIVE MACRO STATE ({snapshot['timestamp']}): Market Regime is {snapshot['market_regime']}. "
        f"Inflation trend is {snapshot['inflation_trend']}. "
        f"Interest rates are {snapshot['interest_rate_trend']}. "
        f"Overall volatility is {snapshot['volatility_level']} (Fear/Greed Score: {snapshot['fear_greed_score']}/100)."
    ]
    
    for ticker, signals in snapshot.get("asset_signals", {}).items():
        rag_texts.append(
            f"LIVE ASSET STATE ({snapshot['timestamp']}): {ticker} is in a {signals['trend']} trend with RSI at {signals['rsi']:.1f}."
        )
        
    store = get_vector_store()
    store.add_documents(rag_texts, [{"type": "live_market_data"}] * len(rag_texts))

def get_latest_snapshot() -> dict:
    """API Layer calls this to retrieve the snapshot without blocking."""
    if os.path.exists(SNAPSHOT_FILE):
        with open(SNAPSHOT_FILE, "r") as f:
            return json.load(f)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_regime": "Unknown",
        "error": "Snapshot cache not generated yet."
    }

def get_previous_snapshot() -> dict:
    """Retrieves the previous snapshot for portfolio delta reasoning."""
    PREV_SNAPSHOT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "previous_market_snapshot.json")
    if os.path.exists(PREV_SNAPSHOT_FILE):
        with open(PREV_SNAPSHOT_FILE, "r") as f:
            return json.load(f)
    return {}
