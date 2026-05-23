"""
Backtesting & Scenario Simulation Engine.

  - Historical backtesting with benchmark comparison
  - Monte Carlo simulation with fat-tail handling (edgeCases.md §6.1)
  - Scenario simulator (crash, inflation, SIP changes)
  - Real vs Nominal return display (edgeCases.md §6.2)

Implementation Plan §3.3
"""

import numpy as np
import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Historical Backtesting
# ═══════════════════════════════════════════════════════════════

def backtest_portfolio(
    prices: pd.DataFrame,
    weights: dict,
    initial_investment: float = 1000000,
    risk_free_rate: float = 0.05,
    benchmark_prices: Optional[pd.Series] = None,
) -> dict:
    """
    Simulate historical portfolio performance.

    Args:
        prices: DataFrame of historical close prices (columns = tickers).
        weights: {ticker: weight} allocation dict.
        initial_investment: Starting capital.
        benchmark_prices: Optional benchmark (e.g., S&P 500) for comparison.

    Returns:
        {
            "portfolio_metrics": {...},
            "benchmark_metrics": {...} or None,
            "time_series": {...},
        }
    """
    if prices.empty:
        return {"error": "No price data for backtesting."}

    # Align weights with available tickers
    available = [t for t in weights if t in prices.columns]
    if not available:
        return {"error": "No matching tickers between weights and price data."}

    weight_series = pd.Series({t: weights[t] for t in available})
    weight_series = weight_series / weight_series.sum()  # Renormalize

    # Compute daily returns
    daily_returns = prices[available].pct_change().dropna()
    portfolio_returns = (daily_returns * weight_series).sum(axis=1)

    # Portfolio value time series
    portfolio_value = initial_investment * (1 + portfolio_returns).cumprod()

    # Compute metrics
    portfolio_metrics = _compute_performance_metrics(
        portfolio_returns, portfolio_value, risk_free_rate
    )
    portfolio_metrics["initial_investment"] = initial_investment
    portfolio_metrics["final_value"] = round(float(portfolio_value.iloc[-1]), 2)
    portfolio_metrics["total_return_pct"] = round(
        (float(portfolio_value.iloc[-1]) / initial_investment - 1) * 100, 2
    )

    # Benchmark comparison
    benchmark_metrics = None
    if benchmark_prices is not None and not benchmark_prices.empty:
        bench_returns = benchmark_prices.pct_change().dropna()
        # Align dates
        common_dates = portfolio_returns.index.intersection(bench_returns.index)
        if len(common_dates) > 0:
            bench_returns = bench_returns.loc[common_dates]
            bench_value = initial_investment * (1 + bench_returns).cumprod()
            benchmark_metrics = _compute_performance_metrics(
                bench_returns, bench_value, risk_free_rate
            )
            benchmark_metrics["final_value"] = round(float(bench_value.iloc[-1]), 2)

    return {
        "portfolio_metrics": portfolio_metrics,
        "benchmark_metrics": benchmark_metrics,
        "data_points": len(portfolio_returns),
        "period_years": round(len(portfolio_returns) / 252, 1),
    }


def _compute_performance_metrics(
    returns: pd.Series,
    values: pd.Series,
    risk_free_rate: float,
) -> dict:
    """Compute standard performance metrics from a returns series."""
    trading_days = len(returns)
    years = trading_days / 252

    # CAGR
    if years > 0 and values.iloc[0] > 0:
        cagr = (values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1
    else:
        cagr = 0.0

    # Volatility (annualized)
    volatility = returns.std() * np.sqrt(252)

    # Sharpe Ratio
    excess_returns = returns - risk_free_rate / 252
    sharpe = (excess_returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0

    # Sortino Ratio (downside deviation only)
    downside = returns[returns < 0]
    downside_std = downside.std() * np.sqrt(252) if len(downside) > 0 else 0
    sortino = (returns.mean() * 252 - risk_free_rate) / downside_std if downside_std > 0 else 0

    # Max Drawdown
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = float(drawdown.min()) * 100

    # Calmar Ratio
    calmar = cagr / abs(max_drawdown / 100) if max_drawdown != 0 else 0

    return {
        "cagr_pct": round(float(cagr) * 100, 2),
        "annual_volatility_pct": round(float(volatility) * 100, 2),
        "sharpe_ratio": round(float(sharpe), 4),
        "sortino_ratio": round(float(sortino), 4),
        "calmar_ratio": round(float(calmar), 4),
        "max_drawdown_pct": round(max_drawdown, 2),
        "trading_days": trading_days,
    }


# ═══════════════════════════════════════════════════════════════
# Monte Carlo Simulation (edgeCases.md §6.1)
# ═══════════════════════════════════════════════════════════════

def monte_carlo_simulation(
    expected_annual_return: float,
    annual_volatility: float,
    initial_investment: float,
    monthly_contribution: float = 0,
    years: int = 10,
    num_simulations: int = 10000,
    inflation_rate: float = 0.04,
    use_fat_tails: bool = True,
) -> dict:
    """
    Run Monte Carlo simulation for portfolio projections.

    Edge Case §6.1: Uses t-distribution (fat tails) by default instead of
    Gaussian to avoid underestimating black swan risks.

    Edge Case §6.2: Returns both nominal AND real (inflation-adjusted) values.

    Args:
        expected_annual_return: Annual expected return (decimal).
        annual_volatility: Annual volatility (decimal).
        initial_investment: Starting capital.
        monthly_contribution: Monthly SIP amount.
        years: Investment horizon in years.
        num_simulations: Number of simulated paths.
        inflation_rate: Annual inflation rate.
        use_fat_tails: If True, use t-distribution (df=5) for fat tails (§6.1).

    Returns:
        {
            "nominal": {p10, p25, p50, p75, p90, mean, std},
            "real": {p10, p25, p50, p75, p90, mean, std},
            "probability_analysis": {...},
            "warnings": list,
        }
    """
    warnings = []
    trading_days = years * 252
    daily_return = expected_annual_return / 252
    daily_vol = annual_volatility / np.sqrt(252)

    # ── Generate random returns ───────────────────────────────
    if use_fat_tails:
        # edgeCases §6.1: t-distribution with df=5 for fat tails
        # This captures black swan events more realistically
        df_t = 5  # Degrees of freedom (lower = fatter tails)
        random_returns = np.random.standard_t(df_t, size=(num_simulations, trading_days))
        # Scale to match desired mean and volatility
        # t-distribution with df=5 has variance = df/(df-2) = 5/3
        scale_factor = daily_vol / np.sqrt(df_t / (df_t - 2))
        random_returns = random_returns * scale_factor + daily_return
        warnings.append(
            "FAT_TAIL_MODEL: Using t-distribution (df=5) to model black swan events. "
            "Tail risks are more accurately captured than Gaussian models."
        )
    else:
        random_returns = np.random.normal(daily_return, daily_vol, (num_simulations, trading_days))
        warnings.append(
            "GAUSSIAN_MODEL: Using normal distribution. May underestimate tail risks."
        )

    # ── Simulate portfolio growth ─────────────────────────────
    # Compound daily returns
    cumulative = np.cumprod(1 + random_returns, axis=1)
    terminal_values = initial_investment * cumulative[:, -1]

    # Add monthly contributions (approximate: add at each month-end)
    if monthly_contribution > 0:
        months = years * 12
        for m in range(1, months + 1):
            day_index = min(int(m * 21) - 1, trading_days - 1)  # ~21 trading days per month
            remaining_growth = cumulative[:, -1] / cumulative[:, day_index]
            terminal_values += monthly_contribution * remaining_growth

    # ── Compute percentiles (nominal) ─────────────────────────
    nominal = {
        "p10": round(float(np.percentile(terminal_values, 10)), 2),
        "p25": round(float(np.percentile(terminal_values, 25)), 2),
        "p50": round(float(np.percentile(terminal_values, 50)), 2),
        "p75": round(float(np.percentile(terminal_values, 75)), 2),
        "p90": round(float(np.percentile(terminal_values, 90)), 2),
        "mean": round(float(np.mean(terminal_values)), 2),
        "std": round(float(np.std(terminal_values)), 2),
    }

    # ── Edge Case §6.2: Real (inflation-adjusted) values ─────
    inflation_factor = (1 + inflation_rate) ** years
    real = {
        "p10": round(nominal["p10"] / inflation_factor, 2),
        "p25": round(nominal["p25"] / inflation_factor, 2),
        "p50": round(nominal["p50"] / inflation_factor, 2),
        "p75": round(nominal["p75"] / inflation_factor, 2),
        "p90": round(nominal["p90"] / inflation_factor, 2),
        "mean": round(nominal["mean"] / inflation_factor, 2),
        "std": round(nominal["std"] / inflation_factor, 2),
    }

    if inflation_rate > 0.10:
        warnings.append(
            f"HIGH_INFLATION_WARNING: At {inflation_rate:.0%} inflation over {years} years, "
            f"nominal values are misleading. Real purchasing power is {1/inflation_factor:.1%} "
            f"of nominal value. Always refer to real (inflation-adjusted) figures."
        )

    # ── Probability analysis ──────────────────────────────────
    prob_positive = float((terminal_values > initial_investment).mean() * 100)
    prob_double = float((terminal_values > initial_investment * 2).mean() * 100)
    prob_loss_20pct = float((terminal_values < initial_investment * 0.80).mean() * 100)

    return {
        "nominal": nominal,
        "real_inflation_adjusted": real,
        "probability_analysis": {
            "prob_positive_return_pct": round(prob_positive, 1),
            "prob_double_investment_pct": round(prob_double, 1),
            "prob_loss_over_20pct": round(prob_loss_20pct, 1),
        },
        "parameters": {
            "initial_investment": initial_investment,
            "monthly_contribution": monthly_contribution,
            "years": years,
            "expected_return": expected_annual_return,
            "volatility": annual_volatility,
            "inflation_rate": inflation_rate,
            "num_simulations": num_simulations,
            "fat_tail_model": use_fat_tails,
        },
        "warnings": warnings,
    }


# ═══════════════════════════════════════════════════════════════
# Scenario Simulator
# ═══════════════════════════════════════════════════════════════

def simulate_scenario(
    portfolio_value: float,
    weights: dict,
    scenario: str,
    scenario_params: Optional[dict] = None,
) -> dict:
    """
    Apply a specific market scenario and compute impact.

    Scenarios:
      - "market_crash": Apply -30% shock to equities
      - "inflation_spike": Adjust returns for higher inflation
      - "sip_increase": Reproject with higher monthly contributions
      - "early_retirement": Shorten horizon and recompute
    """
    if scenario_params is None:
        scenario_params = {}

    # Classify assets
    equity_tickers = [t for t in weights if not any(
        x in t.upper() for x in ["TLT", "BND", "AGG", "GLD", "SLV", "BTC", "ETH"]
    )]
    bond_tickers = [t for t in weights if any(x in t.upper() for x in ["TLT", "BND", "AGG"])]
    gold_tickers = [t for t in weights if any(x in t.upper() for x in ["GLD", "SLV"])]

    result = {
        "scenario": scenario,
        "original_value": portfolio_value,
        "post_scenario_value": portfolio_value,
        "impact_pct": 0.0,
        "analysis": "",
        "recommended_action": "",
    }

    if scenario == "market_crash":
        crash_pct = scenario_params.get("crash_pct", -30) / 100
        equity_weight = sum(weights.get(t, 0) for t in equity_tickers)
        impact = portfolio_value * equity_weight * crash_pct
        new_value = portfolio_value + impact
        result["post_scenario_value"] = round(new_value, 2)
        result["impact_pct"] = round((new_value / portfolio_value - 1) * 100, 2)
        result["analysis"] = (
            f"A {crash_pct*100:.0f}% equity crash affects {equity_weight:.0%} of your portfolio. "
            f"Portfolio drops from ₹{portfolio_value:,.0f} to ₹{new_value:,.0f}."
        )
        result["recommended_action"] = (
            "Maintain current allocation. Historical data shows markets recover within 2-3 years. "
            "Consider increasing bond allocation by 5-10% if risk tolerance has changed."
        )

    elif scenario == "inflation_spike":
        inflation_increase = scenario_params.get("inflation_increase_pct", 3) / 100
        years = scenario_params.get("years", 5)
        inflation_erosion = (1 + inflation_increase) ** years
        real_value = portfolio_value / inflation_erosion
        bond_weight = sum(weights.get(t, 0) for t in bond_tickers)
        gold_weight = sum(weights.get(t, 0) for t in gold_tickers)
        result["post_scenario_value"] = round(real_value, 2)
        result["impact_pct"] = round((real_value / portfolio_value - 1) * 100, 2)
        result["analysis"] = (
            f"A {inflation_increase*100:.0f}% inflation spike over {years} years erodes "
            f"real purchasing power by {(1 - 1/inflation_erosion)*100:.1f}%. "
            f"Bond allocation ({bond_weight:.0%}) loses real value. "
            f"Gold allocation ({gold_weight:.0%}) provides partial hedge."
        )
        result["recommended_action"] = (
            "Consider increasing gold/commodity exposure and inflation-linked bonds (TIPS). "
            "Reduce nominal bond duration."
        )

    elif scenario == "sip_increase":
        additional_sip = scenario_params.get("additional_monthly", 5000)
        years = scenario_params.get("years", 10)
        annual_return = scenario_params.get("expected_return", 0.12)
        monthly_return = annual_return / 12
        # Future value of additional SIP
        months = years * 12
        if monthly_return > 0:
            fv_additional = additional_sip * (((1 + monthly_return) ** months - 1) / monthly_return)
        else:
            fv_additional = additional_sip * months
        result["post_scenario_value"] = round(portfolio_value + fv_additional, 2)
        result["impact_pct"] = round(fv_additional / portfolio_value * 100, 2)
        result["analysis"] = (
            f"Increasing SIP by ₹{additional_sip:,.0f}/month for {years} years at "
            f"{annual_return*100:.0f}% CAGR adds ₹{fv_additional:,.0f} to your portfolio."
        )
        result["recommended_action"] = "Strongly recommended. Compounding significantly amplifies returns over time."

    elif scenario == "early_retirement":
        target_age = scenario_params.get("target_age", 45)
        current_age = scenario_params.get("current_age", 30)
        years_to_retire = max(1, target_age - current_age)
        annual_return = scenario_params.get("expected_return", 0.10)
        projected_value = portfolio_value * (1 + annual_return) ** years_to_retire
        # Safe withdrawal rate: 4% rule
        annual_withdrawal = projected_value * 0.04
        result["post_scenario_value"] = round(projected_value, 2)
        result["impact_pct"] = round((projected_value / portfolio_value - 1) * 100, 2)
        result["analysis"] = (
            f"Retiring at age {target_age} ({years_to_retire} years away): "
            f"Projected corpus ₹{projected_value:,.0f}. "
            f"Safe annual withdrawal (4% rule): ₹{annual_withdrawal:,.0f}/year "
            f"(₹{annual_withdrawal/12:,.0f}/month)."
        )
        result["recommended_action"] = (
            f"{'Feasible' if annual_withdrawal > 500000 else 'Requires aggressive saving'}. "
            f"Consider increasing SIP to build a larger corpus."
        )

    elif scenario == "tech_rally":
        rally_pct = scenario_params.get("rally_pct", 15) / 100
        equity_weight = sum(weights.get(t, 0) for t in equity_tickers)
        impact = portfolio_value * equity_weight * rally_pct
        new_value = portfolio_value + impact
        result["post_scenario_value"] = round(new_value, 2)
        result["impact_pct"] = round((new_value / portfolio_value - 1) * 100, 2)
        result["analysis"] = (
            f"A {rally_pct*100:.0f}% tech-led equity rally pushes your portfolio up to ₹{new_value:,.0f}."
        )
        result["recommended_action"] = "Consider rebalancing if equity concentration exceeds your target risk profile."

    elif scenario == "rate_hike":
        hike_pct = scenario_params.get("hike_pct", 2) / 100
        bond_weight = sum(weights.get(t, 0) for t in bond_tickers)
        # simplistic bond math: -1% for every 1% rate hike (duration approx 1)
        bond_impact = portfolio_value * bond_weight * -hike_pct * 5 # assuming avg duration 5
        equity_weight = sum(weights.get(t, 0) for t in equity_tickers)
        equity_impact = portfolio_value * equity_weight * -0.05 # slight equity hit
        impact = bond_impact + equity_impact
        new_value = portfolio_value + impact
        result["post_scenario_value"] = round(new_value, 2)
        result["impact_pct"] = round((new_value / portfolio_value - 1) * 100, 2)
        result["analysis"] = (
            f"A {hike_pct*100:.0f}% unexpected rate hike hurts both equities and long-duration bonds. "
            f"Portfolio drops to ₹{new_value:,.0f}."
        )
        result["recommended_action"] = "Ensure sufficient cash reserves and consider short-duration bonds to limit interest rate risk."

    elif scenario == "recession":
        drop_pct = scenario_params.get("drop_pct", -20) / 100
        equity_weight = sum(weights.get(t, 0) for t in equity_tickers)
        bond_weight = sum(weights.get(t, 0) for t in bond_tickers)
        equity_impact = portfolio_value * equity_weight * drop_pct
        bond_impact = portfolio_value * bond_weight * 0.05 # flight to safety
        impact = equity_impact + bond_impact
        new_value = portfolio_value + impact
        result["post_scenario_value"] = round(new_value, 2)
        result["impact_pct"] = round((new_value / portfolio_value - 1) * 100, 2)
        result["analysis"] = (
            f"A global recession scenario drops equities by {abs(drop_pct)*100:.0f}%. "
            f"Bonds provide a slight cushion. Portfolio value becomes ₹{new_value:,.0f}."
        )
        result["recommended_action"] = "Stay invested. Do not crystallize losses. Maintain SIPs to buy assets at a discount."

    else:
        result["analysis"] = f"Unknown scenario: {scenario}"

    return result
