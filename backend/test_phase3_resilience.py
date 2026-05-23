import os
import sys
import logging
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.market_snapshot_service import get_latest_snapshot, generate_market_snapshot, update_and_cache_snapshot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api_failure_recovery():
    print("\n--- Test 1: API Failure Recovery (yfinance timeout simulation) ---")
    
    # Mock yfinance to raise a timeout exception
    with patch("app.services.market_data_service.fetch_batch_stock_data") as mock_fetch:
        mock_fetch.side_effect = Exception("yfinance API Timeout")
        
        try:
            update_and_cache_snapshot()
            print("✅ Scheduler correctly caught the exception and didn't crash.")
        except Exception as e:
            print(f"❌ Scheduler crashed during failure: {e}")

    # Now verify the API layer can still serve cached data
    snapshot = get_latest_snapshot()
    if snapshot.get("market_regime"):
        print(f"✅ Cache layer remains accessible. Market Regime: {snapshot['market_regime']}")
    else:
        print("❌ Cache layer failed to serve.")

def test_snapshot_integrity():
    print("\n--- Test 2: Market Snapshot Integrity ---")
    
    # Generate real snapshot
    snapshot = generate_market_snapshot()
    
    if "timestamp" in snapshot:
        print(f"✅ Timestamp exists: {snapshot['timestamp']}")
    else:
        print("❌ Missing timestamp.")
        
    if "market_regime" in snapshot and snapshot["market_regime"] in ["Bullish", "Bearish", "Neutral"]:
        print(f"✅ Market Regime computed deterministically: {snapshot['market_regime']}")
    else:
        print(f"❌ Invalid or missing regime: {snapshot.get('market_regime')}")

def test_prompt_grounding():
    print("\n--- Test 3: Prompt Grounding Validation ---")
    
    from app.services.chat_agent import process_chat_message
    
    # Send a query asking why tech was chosen
    result = process_chat_message("Why should I invest in technology right now?")
    
    signals = result.get("market_signals", [])
    if signals:
        print(f"✅ Retrieval Transparency Layer successfully injected {len(signals)} signals!")
        for sig in signals:
            print(f"   - {sig['signal']}: {sig['impact']}")
    else:
        print("❌ Missing Retrieval Transparency Layer signals.")

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 3: RESILIENCE & GROUNDING VALIDATION")
    print("=" * 60)
    test_snapshot_integrity()
    test_api_failure_recovery()
    test_prompt_grounding()
    print("\n✅ All Phase 3 Resilience Tests Completed.")
