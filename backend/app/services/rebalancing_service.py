"""
Phase 6: Dynamic Portfolio Rebalancing Module
Handles portfolio drift, wash sale prevention, and friction cost optimization.

Edge Cases Addressed:
- §5.1 Intraday Flash Crashes: Time-Delayed Triggers (End of Day only)
- §5.2 Wash Sales: 31-day cooldown on substantially identical assets
- §5.3 Rebalancing Friction: Requires Sharpe improvement > Friction cost
"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Mocked 30-day transaction history to demonstrate Wash Sale prevention
MOCK_TRANSACTION_HISTORY = [
    {"ticker": "SPY", "action": "SELL", "date": datetime.now() - timedelta(days=15), "reason": "tax_loss_harvesting"},
    {"ticker": "AAPL", "action": "BUY", "date": datetime.now() - timedelta(days=5), "reason": "rebalance"}
]

class RebalancingService:
    def __init__(self):
        self.drift_threshold = 0.05  # 5% drift threshold
        self.friction_cost_estimate = 0.005  # 0.5% estimated transaction + tax cost
        self.wash_sale_cooldown_days = 31

    def check_portfolio_drift(
        self, 
        target_weights: Dict[str, float], 
        current_weights: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Check if any asset class deviates > 5% from target weight.
        Returns a dict of assets that have drifted beyond the threshold.
        """
        drifted_assets = {}
        for asset, target in target_weights.items():
            current = current_weights.get(asset, 0.0)
            drift = abs(current - target)
            if drift > self.drift_threshold:
                drifted_assets[asset] = {"target": target, "current": current, "drift": drift}
        return drifted_assets

    def is_intraday_flash_crash(self, is_end_of_day: bool, market_drop_pct: float) -> bool:
        """
        Edge Case §5.1: Prevent rebalancing during intraday flash crashes.
        Must be End-of-Day or sustained breach.
        """
        if market_drop_pct > 0.05 and not is_end_of_day:
            logger.warning("Intraday flash crash detected. Suppressing rebalance trigger.")
            return True
        return False

    def check_wash_sale_violation(self, proposed_buys: List[str], transaction_history: List[dict]) -> List[str]:
        """
        Edge Case §5.2: Prevent buying substantially identical assets sold for a loss within 30 days.
        """
        violations = []
        cutoff_date = datetime.now() - timedelta(days=self.wash_sale_cooldown_days)
        
        recent_sells = [
            tx["ticker"] for tx in transaction_history 
            if tx["action"] == "SELL" and tx["date"] >= cutoff_date
        ]
        
        # In a real system, we'd check "substantially identical" mappings (e.g. SPY vs VOO)
        substantially_identical_map = {
            "VOO": ["SPY", "IVV"],
            "SPY": ["VOO", "IVV"]
        }
        
        for buy in proposed_buys:
            if buy in recent_sells:
                violations.append(buy)
            elif buy in substantially_identical_map:
                for identical in substantially_identical_map[buy]:
                    if identical in recent_sells:
                        violations.append(buy)
                        break
                        
        return violations

    def evaluate_rebalance_friction(
        self, 
        current_sharpe: float, 
        expected_new_sharpe: float
    ) -> bool:
        """
        Edge Case §5.3: High Rebalancing Friction.
        Only trigger if Expected Sharpe Improvement > Estimated Friction Cost + Tax Impact.
        """
        sharpe_improvement = expected_new_sharpe - current_sharpe
        
        if sharpe_improvement > self.friction_cost_estimate:
            return True
        else:
            logger.info(f"Rebalance rejected: Sharpe improvement ({sharpe_improvement:.4f}) < Friction cost ({self.friction_cost_estimate}).")
            return False

    def generate_rebalance_proposal(
        self,
        target_weights: Dict[str, float],
        current_weights: Dict[str, float],
        current_sharpe: float,
        expected_new_sharpe: float,
        is_end_of_day: bool = True,
        market_drop_pct: float = 0.0
    ) -> dict:
        """
        Full workflow evaluating all edge cases before proposing a rebalance.
        """
        # 1. Check Intraday Flash Crash (§5.1)
        if self.is_intraday_flash_crash(is_end_of_day, market_drop_pct):
            return {"status": "rejected", "reason": "intraday_flash_crash_protection"}
            
        # 2. Check Drift
        drifts = self.check_portfolio_drift(target_weights, current_weights)
        if not drifts:
            return {"status": "no_action", "reason": "drift_within_thresholds"}
            
        # 3. Check Friction Cost (§5.3)
        if not self.evaluate_rebalance_friction(current_sharpe, expected_new_sharpe):
            return {"status": "rejected", "reason": "friction_cost_exceeds_benefit"}
            
        # Determine proposed buys (assets where current < target)
        proposed_buys = [asset for asset, data in drifts.items() if data["current"] < data["target"]]
        
        # 4. Check Wash Sales (§5.2)
        wash_violations = self.check_wash_sale_violation(proposed_buys, MOCK_TRANSACTION_HISTORY)
        if wash_violations:
            return {
                "status": "rejected", 
                "reason": "wash_sale_violation", 
                "violating_assets": wash_violations
            }
            
        # All checks passed
        return {
            "status": "approved",
            "reason": "optimization_criteria_met",
            "drifts": drifts,
            "expected_sharpe_improvement": expected_new_sharpe - current_sharpe
        }

rebalancing_service = RebalancingService()
