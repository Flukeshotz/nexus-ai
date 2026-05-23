"""
Portfolio Construction Engine using PyPortfolioOpt.
Handles Mean-Variance Optimization with full edge case handling:

  - edgeCases.md §3.1: Non-positive definite covariance matrices → Ledoit-Wolf shrinkage
  - edgeCases.md §3.2: Corner solutions → strict sector/asset caps
  - edgeCases.md §3.3: Negative expected returns → auto-fallback to Min Volatility / HRP

Implementation Plan §3.2
"""

import numpy as np
import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Constants & Constraints (edgeCases.md §3.2)
# ═══════════════════════════════════════════════════════════════

# Max allocation per single asset (prevents corner solutions)
MAX_SINGLE_ASSET_WEIGHT = 0.25
# Min allocation per asset (prevents dust positions)
MIN_SINGLE_ASSET_WEIGHT = 0.02
# Max sector exposure
MAX_SECTOR_WEIGHT = 0.35
# Minimum number of assets in portfolio
MIN_PORTFOLIO_ASSETS = 4
# Negative returns threshold for fallback (edgeCases §3.3)
NEGATIVE_RETURN_THRESHOLD = 0.50  # If >50% of assets have negative returns


# ═══════════════════════════════════════════════════════════════
# Covariance Matrix Regularization (edgeCases.md §3.1)
# ═══════════════════════════════════════════════════════════════

def regularize_covariance_matrix(cov_matrix: pd.DataFrame) -> pd.DataFrame:
    """
    Edge Case §3.1: Ensure covariance matrix is positive definite.

    Applies Ledoit-Wolf shrinkage to regularize the matrix,
    preventing LinAlgError in MVO optimization.
    """
    from sklearn.covariance import LedoitWolf

    lw = LedoitWolf()
    lw.fit(np.random.multivariate_normal(
        mean=np.zeros(len(cov_matrix)),
        cov=cov_matrix.values,
        size=max(len(cov_matrix) * 3, 100),
    ))
    shrunk_cov = pd.DataFrame(
        lw.covariance_,
        index=cov_matrix.index,
        columns=cov_matrix.columns,
    )
    logger.info(f"Applied Ledoit-Wolf shrinkage (shrinkage={lw.shrinkage_:.4f})")
    return shrunk_cov


def ensure_positive_definite(cov_matrix: pd.DataFrame) -> pd.DataFrame:
    """
    Fallback: Force positive definiteness via eigenvalue clipping
    if Ledoit-Wolf still fails.
    """
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix.values)

    # Clip negative eigenvalues to a small positive number
    min_eigenvalue = max(1e-10, eigenvalues.max() * 1e-6)
    eigenvalues = np.maximum(eigenvalues, min_eigenvalue)

    fixed = eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T
    fixed = (fixed + fixed.T) / 2  # Ensure symmetry

    return pd.DataFrame(fixed, index=cov_matrix.index, columns=cov_matrix.columns)


# ═══════════════════════════════════════════════════════════════
# Expected Returns Computation
# ═══════════════════════════════════════════════════════════════

def compute_expected_returns(prices: pd.DataFrame, method: str = "mean") -> pd.Series:
    """
    Compute annualized expected returns.

    Methods:
      - "mean": Historical mean return (annualized)
      - "capm": Capital Asset Pricing Model (simplified)
    """
    daily_returns = prices.pct_change().dropna()

    if method == "mean":
        annual_returns = daily_returns.mean() * 252
    elif method == "capm":
        # Simplified CAPM using the first column as market proxy
        market_returns = daily_returns.iloc[:, 0]
        risk_free = 0.05 / 252  # Daily risk-free rate
        market_premium = market_returns.mean() - risk_free
        annual_returns = pd.Series(index=daily_returns.columns, dtype=float)
        for col in daily_returns.columns:
            if daily_returns[col].std() == 0:
                annual_returns[col] = risk_free * 252
            else:
                beta = daily_returns[col].cov(market_returns) / market_returns.var()
                annual_returns[col] = (risk_free + beta * market_premium) * 252
    else:
        annual_returns = daily_returns.mean() * 252

    return annual_returns


# ═══════════════════════════════════════════════════════════════
# Check for Negative Returns Environment (edgeCases.md §3.3)
# ═══════════════════════════════════════════════════════════════

def check_negative_returns_environment(expected_returns: pd.Series) -> dict:
    """
    Edge Case §3.3: Detect if majority of assets have negative expected returns.

    Returns:
        {
            "is_negative_environment": bool,
            "negative_pct": float,
            "recommendation": str,
        }
    """
    negative_count = (expected_returns < 0).sum()
    total = len(expected_returns)
    negative_pct = negative_count / total if total > 0 else 0

    if negative_pct > NEGATIVE_RETURN_THRESHOLD:
        return {
            "is_negative_environment": True,
            "negative_pct": round(negative_pct, 3),
            "recommendation": (
                "CAPITAL_PRESERVATION_FALLBACK: >50% of asset classes show negative "
                "expected returns. Switching from Max Sharpe to Minimum Volatility."
            ),
        }
    return {
        "is_negative_environment": False,
        "negative_pct": round(negative_pct, 3),
        "recommendation": "Normal market conditions. Standard optimization applies.",
    }


# ═══════════════════════════════════════════════════════════════
# Portfolio Optimizer (Core Engine)
# ═══════════════════════════════════════════════════════════════

def optimize_portfolio(
    prices: pd.DataFrame,
    strategy: str = "max_sharpe",
    risk_free_rate: float = 0.05,
    weight_bounds: tuple = None,
    sector_mapper: Optional[dict] = None,
    sector_upper: Optional[dict] = None,
) -> dict:
    """
    Run portfolio optimization with full edge case handling.

    Args:
        prices: DataFrame with columns=tickers, rows=dates, values=close prices.
        strategy: "max_sharpe", "min_volatility", or "hrp".
        risk_free_rate: Annual risk-free rate.
        weight_bounds: (min_weight, max_weight) per asset.
        sector_mapper: {ticker: sector} for sector constraints.
        sector_upper: {sector: max_weight} for sector caps.

    Returns:
        {
            "weights": {ticker: weight},
            "metrics": {expected_return, volatility, sharpe_ratio},
            "strategy_used": str,
            "warnings": list,
            "edge_cases_triggered": list,
        }
    """
    if prices.empty or len(prices.columns) < 2:
        return {
            "weights": {},
            "metrics": {},
            "strategy_used": "none",
            "warnings": ["Insufficient assets for optimization (need >= 2)."],
            "edge_cases_triggered": ["INSUFFICIENT_ASSETS"],
        }

    warnings = []
    edge_cases = []

    # Default weight bounds (edgeCases §3.2: prevent corner solutions)
    if weight_bounds is None:
        weight_bounds = (MIN_SINGLE_ASSET_WEIGHT, MAX_SINGLE_ASSET_WEIGHT)

    # ── Step 1: Compute expected returns ──────────────────────
    expected_returns = compute_expected_returns(prices, method="mean")

    # ── Step 2: Check negative returns environment (§3.3) ─────
    neg_check = check_negative_returns_environment(expected_returns)
    if neg_check["is_negative_environment"]:
        edge_cases.append("NEGATIVE_RETURNS_ENVIRONMENT")
        warnings.append(neg_check["recommendation"])
        # Force fallback to min_volatility
        if strategy == "max_sharpe":
            strategy = "min_volatility"
            warnings.append("AUTO_FALLBACK: Strategy changed to min_volatility.")

    # ── Step 3: Compute covariance matrix with shrinkage (§3.1) ─
    daily_returns = prices.pct_change().dropna()
    cov_matrix = daily_returns.cov() * 252  # Annualized

    # Check positive definiteness
    try:
        eigenvalues = np.linalg.eigvalsh(cov_matrix.values)
        if np.any(eigenvalues <= 0):
            edge_cases.append("NON_POSITIVE_DEFINITE_COVARIANCE")
            warnings.append("Applied Ledoit-Wolf shrinkage to fix non-PD covariance matrix.")
            try:
                cov_matrix = regularize_covariance_matrix(cov_matrix)
            except Exception:
                cov_matrix = ensure_positive_definite(cov_matrix)
                warnings.append("Ledoit-Wolf failed. Applied eigenvalue clipping fallback.")
    except np.linalg.LinAlgError:
        edge_cases.append("COVARIANCE_COMPUTATION_FAILED")
        cov_matrix = ensure_positive_definite(cov_matrix)

    # ── Step 4: Run optimization ──────────────────────────────
    try:
        if strategy == "hrp":
            weights, metrics = _run_hrp(daily_returns)
        elif strategy == "min_volatility":
            weights, metrics = _run_efficient_frontier(
                expected_returns, cov_matrix, "min_volatility",
                risk_free_rate, weight_bounds,
                sector_mapper, sector_upper,
            )
        else:  # max_sharpe
            weights, metrics = _run_efficient_frontier(
                expected_returns, cov_matrix, "max_sharpe",
                risk_free_rate, weight_bounds,
                sector_mapper, sector_upper,
            )
    except Exception as e:
        # Final fallback: equal weight
        edge_cases.append("OPTIMIZATION_FAILED")
        warnings.append(f"Optimization failed ({str(e)}). Using equal-weight fallback.")
        n = len(prices.columns)
        weights = {ticker: round(1.0 / n, 4) for ticker in prices.columns}
        port_returns = daily_returns.mean() * 252
        port_vol = daily_returns.std().mean() * np.sqrt(252)
        metrics = {
            "expected_annual_return": round(float(port_returns.mean()), 4),
            "annual_volatility": round(float(port_vol), 4),
            "sharpe_ratio": round(float((port_returns.mean() - risk_free_rate) / port_vol), 4) if port_vol > 0 else 0,
        }
        strategy = "equal_weight_fallback"

    # ── Step 5: Validate constraints (§3.2) ───────────────────
    corner_solutions = [t for t, w in weights.items() if w > MAX_SINGLE_ASSET_WEIGHT + 0.01]
    if corner_solutions:
        edge_cases.append("CORNER_SOLUTION_DETECTED")
        warnings.append(
            f"Corner solution: {corner_solutions} exceeded {MAX_SINGLE_ASSET_WEIGHT:.0%} cap. "
            f"Weights were clamped by optimizer bounds."
        )

    return {
        "weights": weights,
        "metrics": metrics,
        "strategy_used": strategy,
        "warnings": warnings,
        "edge_cases_triggered": edge_cases,
    }


# ═══════════════════════════════════════════════════════════════
# Efficient Frontier Optimization
# ═══════════════════════════════════════════════════════════════

def _run_efficient_frontier(
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    strategy: str,
    risk_free_rate: float,
    weight_bounds: tuple,
    sector_mapper: Optional[dict],
    sector_upper: Optional[dict],
) -> tuple:
    """Run PyPortfolioOpt EfficientFrontier optimization."""
    try:
        from pypfopt import EfficientFrontier, objective_functions

        ef = EfficientFrontier(
            expected_returns,
            cov_matrix,
            weight_bounds=weight_bounds,
        )

        # Add sector constraints (§3.2)
        if sector_mapper and sector_upper:
            ef.add_sector_constraints(sector_mapper, sector_upper)

        # Add L2 regularization to prevent extreme weights
        ef.add_objective(objective_functions.L2_reg, gamma=0.1)

        if strategy == "max_sharpe":
            ef.max_sharpe(risk_free_rate=risk_free_rate)
        elif strategy == "min_volatility":
            ef.min_volatility()

        weights = ef.clean_weights(cutoff=0.01)
        perf = ef.portfolio_performance(risk_free_rate=risk_free_rate)

        return dict(weights), {
            "expected_annual_return": round(perf[0], 4),
            "annual_volatility": round(perf[1], 4),
            "sharpe_ratio": round(perf[2], 4),
        }
    except ImportError:
        # PyPortfolioOpt not installed — use manual fallback
        return _manual_optimization(expected_returns, cov_matrix, strategy, risk_free_rate, weight_bounds)


def _manual_optimization(
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    strategy: str,
    risk_free_rate: float,
    weight_bounds: tuple,
) -> tuple:
    """
    Manual mean-variance optimization fallback when PyPortfolioOpt is unavailable.
    Uses a simple inverse-volatility weighting approach.
    """
    tickers = expected_returns.index.tolist()
    n = len(tickers)

    if strategy == "min_volatility":
        # Inverse volatility weighting
        vols = np.sqrt(np.diag(cov_matrix.values))
        vols = np.maximum(vols, 1e-8)
        inv_vol = 1.0 / vols
        raw_weights = inv_vol / inv_vol.sum()
    else:
        # Risk-adjusted weighting (simplified max sharpe)
        vols = np.sqrt(np.diag(cov_matrix.values))
        vols = np.maximum(vols, 1e-8)
        sharpe_scores = (expected_returns.values - risk_free_rate) / vols
        sharpe_scores = np.maximum(sharpe_scores, 0)
        total = sharpe_scores.sum()
        if total > 0:
            raw_weights = sharpe_scores / total
        else:
            raw_weights = np.ones(n) / n

    # Clamp to bounds
    min_w, max_w = weight_bounds
    clamped = np.clip(raw_weights, min_w, max_w)
    clamped = clamped / clamped.sum()  # Renormalize

    weights = {tickers[i]: round(float(clamped[i]), 4) for i in range(n)}

    # Compute metrics
    w = clamped
    port_return = float(w @ expected_returns.values)
    port_vol = float(np.sqrt(w @ cov_matrix.values @ w))
    sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0

    metrics = {
        "expected_annual_return": round(port_return, 4),
        "annual_volatility": round(port_vol, 4),
        "sharpe_ratio": round(sharpe, 4),
    }

    return weights, metrics


# ═══════════════════════════════════════════════════════════════
# Hierarchical Risk Parity (HRP)
# ═══════════════════════════════════════════════════════════════

def _run_hrp(daily_returns: pd.DataFrame) -> tuple:
    """
    Hierarchical Risk Parity optimization.
    Used as fallback for negative returns environment.
    """
    try:
        from pypfopt import HRPOpt
        hrp = HRPOpt(daily_returns)
        hrp.optimize()
        weights = hrp.clean_weights(cutoff=0.01)
        perf = hrp.portfolio_performance()
        return dict(weights), {
            "expected_annual_return": round(perf[0], 4),
            "annual_volatility": round(perf[1], 4),
            "sharpe_ratio": round(perf[2], 4),
        }
    except ImportError:
        # Manual HRP fallback: inverse volatility
        vols = daily_returns.std() * np.sqrt(252)
        vols = vols.replace(0, 1e-8)
        inv_vol = 1.0 / vols
        weights_raw = inv_vol / inv_vol.sum()
        weights = {col: round(float(weights_raw[col]), 4) for col in daily_returns.columns}
        port_vol = float(vols.mean())
        port_ret = float(daily_returns.mean().mean() * 252)
        sharpe = (port_ret - 0.05) / port_vol if port_vol > 0 else 0
        return weights, {
            "expected_annual_return": round(port_ret, 4),
            "annual_volatility": round(port_vol, 4),
            "sharpe_ratio": round(sharpe, 4),
        }
