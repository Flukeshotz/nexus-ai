import pytest
import datetime
from app.services.rebalancing_service import rebalancing_service, MOCK_TRANSACTION_HISTORY

def test_flash_crash_protection():
    # Intraday drop of 10%
    result = rebalancing_service.generate_rebalance_proposal(
        target_weights={"SPY": 0.5, "TLT": 0.5},
        current_weights={"SPY": 0.4, "TLT": 0.6},
        current_sharpe=1.0,
        expected_new_sharpe=1.1,
        is_end_of_day=False,
        market_drop_pct=0.10
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "intraday_flash_crash_protection"

def test_wash_sale_prevention():
    # SPY was sold in MOCK_TRANSACTION_HISTORY within 30 days
    result = rebalancing_service.generate_rebalance_proposal(
        target_weights={"SPY": 0.6, "TLT": 0.4},
        current_weights={"SPY": 0.4, "TLT": 0.6},  # SPY needs buying
        current_sharpe=1.0,
        expected_new_sharpe=1.1,
        is_end_of_day=True,
        market_drop_pct=0.0
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "wash_sale_violation"
    assert "SPY" in result["violating_assets"]

def test_high_rebalancing_friction():
    # Only 0.001 Sharpe improvement, while friction is 0.005
    result = rebalancing_service.generate_rebalance_proposal(
        target_weights={"AAPL": 0.5, "TLT": 0.5},
        current_weights={"AAPL": 0.4, "TLT": 0.6},
        current_sharpe=1.0,
        expected_new_sharpe=1.001,
        is_end_of_day=True,
        market_drop_pct=0.0
    )
    assert result["status"] == "rejected"
    assert result["reason"] == "friction_cost_exceeds_benefit"

def test_successful_rebalance_proposal():
    # High Sharpe improvement, end of day, no wash sales
    result = rebalancing_service.generate_rebalance_proposal(
        target_weights={"TSLA": 0.5, "TLT": 0.5},
        current_weights={"TSLA": 0.4, "TLT": 0.6},
        current_sharpe=1.0,
        expected_new_sharpe=1.5,
        is_end_of_day=True,
        market_drop_pct=0.0
    )
    assert result["status"] == "approved"
    assert result["reason"] == "optimization_criteria_met"
    assert "TSLA" in result["drifts"]
    
def test_no_drift():
    # Weights are exactly target
    result = rebalancing_service.generate_rebalance_proposal(
        target_weights={"TSLA": 0.5, "TLT": 0.5},
        current_weights={"TSLA": 0.5, "TLT": 0.5},
        current_sharpe=1.0,
        expected_new_sharpe=1.0,
        is_end_of_day=True,
        market_drop_pct=0.0
    )
    assert result["status"] == "no_action"
    assert result["reason"] == "drift_within_thresholds"
