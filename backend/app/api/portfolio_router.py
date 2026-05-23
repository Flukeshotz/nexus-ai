"""
Portfolio API Router.
Endpoints for portfolio generation, backtesting, Monte Carlo simulation,
and scenario analysis.

Implementation Plan §3.2, §3.3
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import pandas as pd
import numpy as np
from datetime import date, timedelta

from app.core.rate_limit import limiter
from fastapi import Request

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/portfolio", tags=["Portfolio & Analytics"])


# ── Request/Response Schemas ──────────────────────────────────

class PortfolioGenerateRequest(BaseModel):
    """Request to generate an optimized portfolio."""
    risk_score: float = Field(..., ge=0, le=100)
    investment_horizon: str = Field("medium_term")
    strategy: str = Field("max_sharpe", description="max_sharpe | min_volatility | hrp")
    tickers: Optional[list] = Field(None, description="Custom tickers. Uses defaults if None.")
    initial_investment: float = Field(1000000, ge=1000)
    ethical_investing: bool = Field(False)
    preferred_sectors: Optional[list] = None


class BacktestRequest(BaseModel):
    """Request for historical backtesting."""
    weights: dict = Field(..., description="{ticker: weight}")
    initial_investment: float = Field(1000000, ge=1000)
    years: int = Field(3, ge=1, le=20)


class MonteCarloRequest(BaseModel):
    """Request for Monte Carlo simulation."""
    expected_annual_return: float = Field(0.10, ge=-0.5, le=1.0)
    annual_volatility: float = Field(0.15, ge=0.01, le=1.0)
    initial_investment: float = Field(1000000, ge=1000)
    monthly_contribution: float = Field(0, ge=0)
    years: int = Field(10, ge=1, le=50)
    inflation_rate: float = Field(0.04, ge=0, le=0.5)
    use_fat_tails: bool = Field(True)
    num_simulations: int = Field(10000, ge=100, le=50000)


class ScenarioRequest(BaseModel):
    """Request for scenario simulation."""
    portfolio_value: float = Field(..., ge=0)
    weights: dict = Field(...)
    scenario: str = Field(..., description="market_crash | inflation_spike | sip_increase | early_retirement")
    scenario_params: Optional[dict] = Field(default_factory=dict)


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/generate")
async def generate_portfolio(
    data: PortfolioGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate an optimized portfolio using the full pipeline:
    1. Recommend asset classes (XGBoost interface)
    2. Fetch price data
    3. Run optimization (PyPortfolioOpt)
    """
    from app.services.recommendation_engine import recommend_asset_allocation
    from app.services.portfolio_optimizer import optimize_portfolio
    from app.services.market_data_service import fetch_stock_data

    # Step 1: Get asset class recommendations
    allocation = recommend_asset_allocation(
        risk_score=data.risk_score,
        investment_horizon=data.investment_horizon,
        ethical_investing=data.ethical_investing,
    )

    # Step 2: Build ticker universe
    tickers = data.tickers
    if not tickers:
        # Default diversified Indian tickers
        tickers = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
                    "SBI.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "ASIANPAINT.NS"]

    # Step 3: Fetch price data
    start_date = (date.today() - timedelta(days=730)).isoformat()
    price_data = {}
    fetch_errors = []
    for ticker in tickers:
        result = fetch_stock_data(ticker, start_date)
        if result["data"] and not result["error"]:
            clean = [r for r in result["data"] if not r["is_anomaly"]]
            if len(clean) >= 30:
                price_data[ticker] = {r["price_date"]: r["close"] for r in clean}
        else:
            fetch_errors.append(ticker)

    if len(price_data) < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient price data. Only {len(price_data)} tickers available. Need >= 2.",
        )

    # Build DataFrame
    prices_df = pd.DataFrame(price_data).dropna()
    if len(prices_df) < 30:
        raise HTTPException(status_code=422, detail="Insufficient overlapping price data.")

    # Step 4: Optimize
    result = optimize_portfolio(
        prices=prices_df,
        strategy=data.strategy,
    )

    return {
        "asset_allocation_recommendation": allocation,
        "optimization": result,
        "tickers_used": list(price_data.keys()),
        "tickers_failed": fetch_errors,
        "data_points": len(prices_df),
    }


@router.post("/backtest")
async def backtest(
    data: BacktestRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Backtest a portfolio over historical data.
    Returns CAGR, Sharpe, Sortino, Calmar, Max Drawdown.
    """
    from app.services.backtesting_engine import backtest_portfolio
    from app.services.market_data_service import fetch_stock_data

    tickers = list(data.weights.keys())
    start_date = (date.today() - timedelta(days=data.years * 365)).isoformat()

    price_data = {}
    for ticker in tickers:
        result = fetch_stock_data(ticker, start_date)
        if result["data"]:
            clean = [r for r in result["data"] if not r["is_anomaly"]]
            if clean:
                price_data[ticker] = {r["price_date"]: r["close"] for r in clean}

    if not price_data:
        raise HTTPException(status_code=422, detail="No price data available for backtesting.")

    prices_df = pd.DataFrame(price_data).dropna()

    result = backtest_portfolio(
        prices=prices_df,
        weights=data.weights,
        initial_investment=data.initial_investment,
    )

    return result


@router.post("/simulate")
async def monte_carlo(
    data: MonteCarloRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Run Monte Carlo simulation with fat-tail distribution.
    Returns P10/P50/P90 for both nominal and real values.
    """
    from app.services.backtesting_engine import monte_carlo_simulation

    result = monte_carlo_simulation(
        expected_annual_return=data.expected_annual_return,
        annual_volatility=data.annual_volatility,
        initial_investment=data.initial_investment,
        monthly_contribution=data.monthly_contribution,
        years=data.years,
        num_simulations=data.num_simulations,
        inflation_rate=data.inflation_rate,
        use_fat_tails=data.use_fat_tails,
    )

    return result


@router.post("/scenario")
async def scenario_analysis(
    data: ScenarioRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Simulate a specific market scenario and return impact analysis.
    Scenarios: market_crash, inflation_spike, sip_increase, early_retirement.
    """
    from app.services.backtesting_engine import simulate_scenario

    valid_scenarios = {"market_crash", "inflation_spike", "sip_increase", "early_retirement"}
    if data.scenario not in valid_scenarios:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid scenario. Must be one of: {valid_scenarios}",
        )

    result = simulate_scenario(
        portfolio_value=data.portfolio_value,
        weights=data.weights,
        scenario=data.scenario,
        scenario_params=data.scenario_params,
    )

    return result

@router.get("/scenario")
@limiter.limit("5/minute")
async def scenario_analysis_get(
    request: Request,
    scenario_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Simulate a specific market scenario for the user's Vault.
    Returns impact and AI analysis.
    """
    from app.services.backtesting_engine import simulate_scenario
    from app.api.holdings_router import get_vault_dashboard
    
    vault = await get_vault_dashboard(db, current_user)
    if vault.net_worth == 0 or not vault.holdings:
        raise HTTPException(status_code=400, detail="Add holdings to run scenario simulations.")
        
    weights = {}
    for h in vault.holdings:
        weights[h.ticker] = weights.get(h.ticker, 0) + (h.current_value / vault.net_worth)
        
    # Map frontend scenario to backend scenario names
    scenario_map = {
        "MARKET_CRASH": "market_crash",
        "TECH_RALLY": "tech_rally",
        "RATE_HIKE": "rate_hike",
        "RECESSION": "recession"
    }
    mapped_scenario = scenario_map.get(scenario_type, "market_crash")

    # Call the simulator
    result = simulate_scenario(
        portfolio_value=vault.net_worth,
        weights=weights,
        scenario=mapped_scenario,
    )
    
    # Structure the response to match the frontend expectations
    return {
        "portfolio_impact_pct": result.get("impact_pct", 0) / 100,
        "new_net_worth": result.get("post_scenario_value", vault.net_worth),
        "ai_analysis": result.get("analysis", "") + " " + result.get("recommended_action", "")
    }
