"""
AI Recommendation Engine (XGBoost).
Pre-filters which asset classes and sectors are suitable
for a given investor profile + market environment.

Implementation Plan §3.1
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Market Regime Detection
# ═══════════════════════════════════════════════════════════════

def detect_market_regime(
    sma_50: Optional[float],
    sma_200: Optional[float],
    rsi_14: Optional[float],
    volatility_30d: Optional[float],
) -> str:
    """
    Classify the current market as bull/bear/sideways
    using SMA crossover + RSI + volatility signals.

    Returns: "bull", "bear", or "sideways"
    """
    signals = []

    # SMA crossover signal
    if sma_50 is not None and sma_200 is not None:
        if sma_50 > sma_200 * 1.02:
            signals.append("bull")
        elif sma_50 < sma_200 * 0.98:
            signals.append("bear")
        else:
            signals.append("sideways")

    # RSI signal
    if rsi_14 is not None:
        if rsi_14 > 60:
            signals.append("bull")
        elif rsi_14 < 40:
            signals.append("bear")
        else:
            signals.append("sideways")

    # Volatility signal
    if volatility_30d is not None:
        if volatility_30d > 0.30:  # >30% annualized
            signals.append("bear")
        elif volatility_30d < 0.15:
            signals.append("bull")
        else:
            signals.append("sideways")

    if not signals:
        return "sideways"

    # Majority vote
    from collections import Counter
    counts = Counter(signals)
    return counts.most_common(1)[0][0]


# ═══════════════════════════════════════════════════════════════
# Feature Engineering
# ═══════════════════════════════════════════════════════════════

def engineer_features(
    risk_score: float,
    age: int,
    monthly_income: float,
    investment_horizon: str,
    market_regime: str,
    inflation_level: float = 4.0,
    interest_rate_direction: str = "stable",
) -> dict:
    """
    Build feature vector from investor profile + market state.
    Maps categorical variables to numerical representations.

    Returns dict of feature_name → value.
    """
    # Age bucket: 0-3
    if age < 30:
        age_bucket = 0
    elif age < 45:
        age_bucket = 1
    elif age < 60:
        age_bucket = 2
    else:
        age_bucket = 3

    # Income bracket: 0-4
    if monthly_income < 30000:
        income_bracket = 0
    elif monthly_income < 75000:
        income_bracket = 1
    elif monthly_income < 150000:
        income_bracket = 2
    elif monthly_income < 500000:
        income_bracket = 3
    else:
        income_bracket = 4

    # Horizon: 0-2
    horizon_map = {"short_term": 0, "medium_term": 1, "long_term": 2}
    horizon_numeric = horizon_map.get(investment_horizon, 1)

    # Market regime: 0-2
    regime_map = {"bear": 0, "sideways": 1, "bull": 2}
    regime_numeric = regime_map.get(market_regime, 1)

    # Interest rate direction: 0-2
    rate_map = {"falling": 0, "stable": 1, "rising": 2}
    rate_numeric = rate_map.get(interest_rate_direction, 1)

    return {
        "risk_score": risk_score,
        "age_bucket": age_bucket,
        "income_bracket": income_bracket,
        "horizon": horizon_numeric,
        "market_regime": regime_numeric,
        "inflation_level": inflation_level,
        "interest_rate_direction": rate_numeric,
    }


# ═══════════════════════════════════════════════════════════════
# Rule-Based Recommendation Engine
# (Acts as XGBoost stand-in with identical interface)
# ═══════════════════════════════════════════════════════════════

# Asset class recommendations by risk profile
ALLOCATION_TEMPLATES = {
    "conservative": {
        "equity": (0.15, 0.25),
        "bond": (0.35, 0.50),
        "gold": (0.10, 0.20),
        "etf": (0.10, 0.20),
        "crypto": (0.00, 0.02),
        "mutual_fund": (0.05, 0.15),
    },
    "moderately_conservative": {
        "equity": (0.20, 0.35),
        "bond": (0.25, 0.40),
        "gold": (0.05, 0.15),
        "etf": (0.10, 0.20),
        "crypto": (0.00, 0.05),
        "mutual_fund": (0.05, 0.15),
    },
    "moderate": {
        "equity": (0.30, 0.45),
        "bond": (0.15, 0.30),
        "gold": (0.05, 0.10),
        "etf": (0.15, 0.25),
        "crypto": (0.00, 0.05),
        "mutual_fund": (0.05, 0.15),
    },
    "aggressive": {
        "equity": (0.45, 0.65),
        "bond": (0.05, 0.15),
        "gold": (0.02, 0.08),
        "etf": (0.15, 0.25),
        "crypto": (0.02, 0.10),
        "mutual_fund": (0.05, 0.10),
    },
    "very_aggressive": {
        "equity": (0.55, 0.75),
        "bond": (0.00, 0.10),
        "gold": (0.00, 0.05),
        "etf": (0.10, 0.20),
        "crypto": (0.05, 0.15),
        "mutual_fund": (0.02, 0.10),
    },
}


def get_risk_category(risk_score: float) -> str:
    """Map numerical risk score to category."""
    if risk_score < 30:
        return "conservative"
    elif risk_score < 50:
        return "moderately_conservative"
    elif risk_score < 65:
        return "moderate"
    elif risk_score < 80:
        return "aggressive"
    else:
        return "very_aggressive"


def recommend_asset_allocation(
    risk_score: float,
    market_regime: str = "sideways",
    investment_horizon: str = "medium_term",
    ethical_investing: bool = False,
    preferred_sectors: Optional[list] = None,
) -> dict:
    """
    Recommend target asset class allocation ranges based on
    risk profile and market conditions.

    This serves as the XGBoost model interface — identical
    input/output contract so a trained model can be swapped in.

    Returns:
        {
            "risk_category": str,
            "market_regime": str,
            "allocations": {asset_class: {"min": float, "target": float, "max": float}},
            "adjustments_applied": list[str],
        }
    """
    category = get_risk_category(risk_score)
    template = ALLOCATION_TEMPLATES.get(category, ALLOCATION_TEMPLATES["moderate"])
    adjustments = []

    # Deep copy to avoid mutation
    allocations = {}
    for asset_class, (lo, hi) in template.items():
        target = (lo + hi) / 2
        allocations[asset_class] = {"min": lo, "target": round(target, 4), "max": hi}

    # ── Market regime adjustments ─────────────────────────────
    if market_regime == "bear":
        # Shift from equity → bonds + gold (defensive)
        allocations["equity"]["target"] = max(
            allocations["equity"]["min"],
            allocations["equity"]["target"] - 0.10,
        )
        allocations["bond"]["target"] = min(
            allocations["bond"]["max"],
            allocations["bond"]["target"] + 0.05,
        )
        allocations["gold"]["target"] = min(
            allocations["gold"]["max"],
            allocations["gold"]["target"] + 0.05,
        )
        adjustments.append("BEAR_MARKET: Reduced equity, increased bonds/gold.")

    elif market_regime == "bull":
        # Lean into equity + ETFs
        allocations["equity"]["target"] = min(
            allocations["equity"]["max"],
            allocations["equity"]["target"] + 0.05,
        )
        allocations["etf"]["target"] = min(
            allocations["etf"]["max"],
            allocations["etf"]["target"] + 0.03,
        )
        adjustments.append("BULL_MARKET: Increased equity/ETF exposure.")

    # ── Investment horizon adjustments ────────────────────────
    if investment_horizon == "short_term":
        allocations["bond"]["target"] = min(
            allocations["bond"]["max"],
            allocations["bond"]["target"] + 0.05,
        )
        allocations["crypto"]["target"] = allocations["crypto"]["min"]
        adjustments.append("SHORT_HORIZON: Increased bonds, eliminated crypto.")

    elif investment_horizon == "long_term":
        allocations["equity"]["target"] = min(
            allocations["equity"]["max"],
            allocations["equity"]["target"] + 0.05,
        )
        adjustments.append("LONG_HORIZON: Increased equity exposure.")

    # ── Ethical investing ─────────────────────────────────────
    if ethical_investing:
        allocations["crypto"]["target"] = 0.0
        allocations["crypto"]["max"] = 0.0
        adjustments.append("ESG: Crypto excluded for ethical investing.")

    # ── Normalize targets to sum to 1.0 ───────────────────────
    total = sum(a["target"] for a in allocations.values())
    if total > 0:
        for a in allocations.values():
            a["target"] = round(a["target"] / total, 4)

    return {
        "risk_category": category,
        "market_regime": market_regime,
        "allocations": allocations,
        "adjustments_applied": adjustments,
    }
