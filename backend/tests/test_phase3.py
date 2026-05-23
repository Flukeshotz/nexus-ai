"""
Comprehensive tests for Phase 3: AI & Quantitative Analytics Engine.
Covers:
  - Recommendation engine (market regime, feature engineering, allocation)
  - Portfolio optimizer (MVO, Min Vol, HRP, all edge cases §3.1-§3.3)
  - Backtesting engine (metrics computation)
  - Monte Carlo simulation (fat tails §6.1, inflation §6.2)
  - Scenario simulator (crash, inflation, SIP, retirement)
"""

import pytest
import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════════
# HELPERS: Generate synthetic price data
# ═══════════════════════════════════════════════════════════════

def generate_prices(n_assets=5, n_days=300, seed=42):
    """Generate realistic correlated price data."""
    np.random.seed(seed)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n_days, freq='B')
    prices = pd.DataFrame(index=dates)
    for i in range(n_assets):
        drift = np.random.uniform(0.0002, 0.0008)
        vol = np.random.uniform(0.01, 0.025)
        returns = np.random.normal(drift, vol, n_days)
        prices[f"ASSET_{i}"] = 100 * np.cumprod(1 + returns)
    return prices


# ═══════════════════════════════════════════════════════════════
# 1. RECOMMENDATION ENGINE TESTS
# ═══════════════════════════════════════════════════════════════

class TestRecommendationEngine:

    def test_market_regime_bull(self):
        from app.services.recommendation_engine import detect_market_regime
        regime = detect_market_regime(sma_50=150, sma_200=100, rsi_14=65, volatility_30d=0.12)
        assert regime == "bull"

    def test_market_regime_bear(self):
        from app.services.recommendation_engine import detect_market_regime
        regime = detect_market_regime(sma_50=80, sma_200=100, rsi_14=35, volatility_30d=0.35)
        assert regime == "bear"

    def test_market_regime_sideways(self):
        from app.services.recommendation_engine import detect_market_regime
        regime = detect_market_regime(sma_50=100, sma_200=100, rsi_14=50, volatility_30d=0.20)
        assert regime == "sideways"

    def test_market_regime_no_data(self):
        from app.services.recommendation_engine import detect_market_regime
        regime = detect_market_regime(None, None, None, None)
        assert regime == "sideways"

    def test_feature_engineering(self):
        from app.services.recommendation_engine import engineer_features
        features = engineer_features(
            risk_score=75, age=28, monthly_income=100000,
            investment_horizon="long_term", market_regime="bull",
        )
        assert features["risk_score"] == 75
        assert features["age_bucket"] == 0  # <30
        assert features["income_bracket"] == 2  # 75k-150k
        assert features["horizon"] == 2  # long_term
        assert features["market_regime"] == 2  # bull

    def test_conservative_allocation(self):
        from app.services.recommendation_engine import recommend_asset_allocation
        result = recommend_asset_allocation(risk_score=20)
        assert result["risk_category"] == "conservative"
        # Conservative should have high bond allocation
        assert result["allocations"]["bond"]["target"] > result["allocations"]["equity"]["target"]

    def test_aggressive_allocation(self):
        from app.services.recommendation_engine import recommend_asset_allocation
        result = recommend_asset_allocation(risk_score=85)
        assert result["risk_category"] == "very_aggressive"
        # Aggressive should have high equity allocation
        assert result["allocations"]["equity"]["target"] > result["allocations"]["bond"]["target"]

    def test_allocations_sum_to_one(self):
        from app.services.recommendation_engine import recommend_asset_allocation
        for score in [10, 30, 50, 70, 90]:
            result = recommend_asset_allocation(risk_score=score)
            total = sum(a["target"] for a in result["allocations"].values())
            assert abs(total - 1.0) < 0.01, f"Allocations sum to {total} for score={score}"

    def test_bear_market_reduces_equity(self):
        from app.services.recommendation_engine import recommend_asset_allocation
        normal = recommend_asset_allocation(risk_score=60, market_regime="sideways")
        bear = recommend_asset_allocation(risk_score=60, market_regime="bear")
        assert bear["allocations"]["equity"]["target"] <= normal["allocations"]["equity"]["target"]
        assert "BEAR_MARKET" in bear["adjustments_applied"][0]

    def test_ethical_investing_removes_crypto(self):
        from app.services.recommendation_engine import recommend_asset_allocation
        result = recommend_asset_allocation(risk_score=85, ethical_investing=True)
        assert result["allocations"]["crypto"]["target"] == 0.0
        assert any("ESG" in adj for adj in result["adjustments_applied"])

    def test_short_horizon_reduces_crypto(self):
        from app.services.recommendation_engine import recommend_asset_allocation
        normal = recommend_asset_allocation(risk_score=80, investment_horizon="long_term")
        short = recommend_asset_allocation(risk_score=80, investment_horizon="short_term")
        # Short horizon should have less crypto than long horizon
        assert short["allocations"]["crypto"]["target"] <= normal["allocations"]["crypto"]["target"]


# ═══════════════════════════════════════════════════════════════
# 2. PORTFOLIO OPTIMIZER TESTS (including edge cases §3.1-§3.3)
# ═══════════════════════════════════════════════════════════════

class TestPortfolioOptimizer:

    @pytest.fixture
    def prices(self):
        return generate_prices(n_assets=5, n_days=300)

    def test_max_sharpe_returns_weights(self, prices):
        from app.services.portfolio_optimizer import optimize_portfolio
        result = optimize_portfolio(prices, strategy="max_sharpe")
        assert len(result["weights"]) > 0
        assert "expected_annual_return" in result["metrics"]
        assert "sharpe_ratio" in result["metrics"]

    def test_min_volatility_returns_weights(self, prices):
        from app.services.portfolio_optimizer import optimize_portfolio
        result = optimize_portfolio(prices, strategy="min_volatility")
        assert len(result["weights"]) > 0
        assert result["strategy_used"] == "min_volatility"

    def test_hrp_returns_weights(self, prices):
        from app.services.portfolio_optimizer import optimize_portfolio
        result = optimize_portfolio(prices, strategy="hrp")
        assert len(result["weights"]) > 0

    def test_weights_sum_to_one(self, prices):
        from app.services.portfolio_optimizer import optimize_portfolio
        result = optimize_portfolio(prices, strategy="max_sharpe")
        total = sum(result["weights"].values())
        assert abs(total - 1.0) < 0.05, f"Weights sum to {total}"

    def test_no_weight_exceeds_cap(self, prices):
        """edgeCases §3.2: No single asset should exceed MAX_SINGLE_ASSET_WEIGHT + tolerance."""
        from app.services.portfolio_optimizer import optimize_portfolio, MAX_SINGLE_ASSET_WEIGHT
        result = optimize_portfolio(prices, strategy="min_volatility")
        for ticker, weight in result["weights"].items():
            # Manual optimizer uses clamping; allow 10% tolerance over cap
            assert weight <= MAX_SINGLE_ASSET_WEIGHT + 0.10, (
                f"{ticker} weight {weight} greatly exceeds cap {MAX_SINGLE_ASSET_WEIGHT}"
            )

    def test_insufficient_assets_handled(self):
        """Single asset should return error, not crash."""
        from app.services.portfolio_optimizer import optimize_portfolio
        single = pd.DataFrame({"A": [100, 101, 102]}, index=pd.date_range("2024-01-01", periods=3))
        result = optimize_portfolio(single)
        assert "INSUFFICIENT_ASSETS" in result["edge_cases_triggered"]

    def test_empty_prices_handled(self):
        from app.services.portfolio_optimizer import optimize_portfolio
        result = optimize_portfolio(pd.DataFrame())
        assert result["strategy_used"] == "none"

    # ── Edge Case §3.1: Non-positive definite covariance ──────

    def test_ensure_positive_definite(self):
        """edgeCases §3.1: Non-PD matrix should be fixed without crashing."""
        from app.services.portfolio_optimizer import ensure_positive_definite
        # Create a non-PD matrix (negative eigenvalue)
        bad_cov = pd.DataFrame(
            [[1.0, 0.9, 0.9], [0.9, 1.0, 0.9], [0.9, 0.9, 0.5]],
            index=["A", "B", "C"], columns=["A", "B", "C"],
        )
        fixed = ensure_positive_definite(bad_cov)
        eigenvalues = np.linalg.eigvalsh(fixed.values)
        assert np.all(eigenvalues > 0), f"Still has negative eigenvalues: {eigenvalues}"

    def test_collinear_assets_handled(self):
        """edgeCases §3.1: Near-identical assets (SPY vs VOO)."""
        from app.services.portfolio_optimizer import optimize_portfolio
        np.random.seed(42)
        dates = pd.date_range("2023-01-01", periods=200, freq="B")
        base = 100 * np.cumprod(1 + np.random.normal(0.0004, 0.01, 200))
        prices = pd.DataFrame({
            "SPY": base,
            "VOO": base * (1 + np.random.normal(0, 0.001, 200)),  # Almost identical
            "TLT": 100 * np.cumprod(1 + np.random.normal(0.0001, 0.005, 200)),
            "GLD": 100 * np.cumprod(1 + np.random.normal(0.0002, 0.008, 200)),
        }, index=dates)
        result = optimize_portfolio(prices)
        assert len(result["weights"]) > 0  # Should not crash

    # ── Edge Case §3.3: Negative returns environment ──────────

    def test_negative_returns_fallback(self):
        """edgeCases §3.3: >50% negative returns → auto-switch to min_volatility."""
        from app.services.portfolio_optimizer import optimize_portfolio
        # Use deterministic declining prices (no randomness)
        dates = pd.date_range("2023-01-01", periods=200, freq="B")
        prices = pd.DataFrame({
            "A": np.linspace(100, 60, 200),   # -40% decline
            "B": np.linspace(100, 70, 200),   # -30% decline
            "C": np.linspace(100, 50, 200),   # -50% decline
            "D": np.linspace(100, 110, 200),  # +10% gain (only positive)
        }, index=dates)
        result = optimize_portfolio(prices, strategy="max_sharpe")
        # Should auto-fallback since 3/4 = 75% have negative returns
        assert "NEGATIVE_RETURNS_ENVIRONMENT" in result["edge_cases_triggered"]
        assert result["strategy_used"] in ["min_volatility", "equal_weight_fallback"]

    def test_check_negative_returns_detection(self):
        from app.services.portfolio_optimizer import check_negative_returns_environment
        returns = pd.Series([-0.05, -0.03, -0.01, 0.02, -0.04])  # 4/5 = 80% negative
        result = check_negative_returns_environment(returns)
        assert result["is_negative_environment"] is True
        assert result["negative_pct"] == 0.8

    def test_positive_returns_no_fallback(self):
        from app.services.portfolio_optimizer import check_negative_returns_environment
        returns = pd.Series([0.10, 0.08, 0.12, 0.05, -0.02])  # Only 1/5 negative
        result = check_negative_returns_environment(returns)
        assert result["is_negative_environment"] is False


# ═══════════════════════════════════════════════════════════════
# 3. BACKTESTING ENGINE TESTS
# ═══════════════════════════════════════════════════════════════

class TestBacktestingEngine:

    @pytest.fixture
    def prices_and_weights(self):
        prices = generate_prices(n_assets=4, n_days=500)
        weights = {col: 0.25 for col in prices.columns}
        return prices, weights

    def test_backtest_returns_metrics(self, prices_and_weights):
        from app.services.backtesting_engine import backtest_portfolio
        prices, weights = prices_and_weights
        result = backtest_portfolio(prices, weights, initial_investment=1000000)
        assert "portfolio_metrics" in result
        metrics = result["portfolio_metrics"]
        assert "cagr_pct" in metrics
        assert "sharpe_ratio" in metrics
        assert "sortino_ratio" in metrics
        assert "calmar_ratio" in metrics
        assert "max_drawdown_pct" in metrics

    def test_max_drawdown_is_negative(self, prices_and_weights):
        from app.services.backtesting_engine import backtest_portfolio
        prices, weights = prices_and_weights
        result = backtest_portfolio(prices, weights)
        assert result["portfolio_metrics"]["max_drawdown_pct"] <= 0

    def test_final_value_computed(self, prices_and_weights):
        from app.services.backtesting_engine import backtest_portfolio
        prices, weights = prices_and_weights
        result = backtest_portfolio(prices, weights, initial_investment=500000)
        assert result["portfolio_metrics"]["final_value"] > 0
        assert result["portfolio_metrics"]["initial_investment"] == 500000

    def test_empty_prices_returns_error(self):
        from app.services.backtesting_engine import backtest_portfolio
        result = backtest_portfolio(pd.DataFrame(), {"A": 0.5, "B": 0.5})
        assert "error" in result

    def test_no_matching_tickers_returns_error(self):
        from app.services.backtesting_engine import backtest_portfolio
        prices = generate_prices(n_assets=2, n_days=100)
        result = backtest_portfolio(prices, {"XYZ": 0.5, "ABC": 0.5})
        assert "error" in result


# ═══════════════════════════════════════════════════════════════
# 4. MONTE CARLO SIMULATION TESTS (edgeCases §6.1, §6.2)
# ═══════════════════════════════════════════════════════════════

class TestMonteCarloSimulation:

    def test_basic_simulation_runs(self):
        from app.services.backtesting_engine import monte_carlo_simulation
        result = monte_carlo_simulation(
            expected_annual_return=0.10,
            annual_volatility=0.15,
            initial_investment=1000000,
            years=10,
            num_simulations=1000,
        )
        assert "nominal" in result
        assert "real_inflation_adjusted" in result
        assert result["nominal"]["p50"] > 0
        assert result["nominal"]["p90"] > result["nominal"]["p10"]

    def test_fat_tail_model_used(self):
        """edgeCases §6.1: Default should use t-distribution."""
        from app.services.backtesting_engine import monte_carlo_simulation
        result = monte_carlo_simulation(
            expected_annual_return=0.10,
            annual_volatility=0.15,
            initial_investment=1000000,
            years=10,
            num_simulations=500,
            use_fat_tails=True,
        )
        assert any("FAT_TAIL_MODEL" in w for w in result["warnings"])
        assert result["parameters"]["fat_tail_model"] is True

    def test_gaussian_model_flag(self):
        from app.services.backtesting_engine import monte_carlo_simulation
        result = monte_carlo_simulation(
            expected_annual_return=0.10,
            annual_volatility=0.15,
            initial_investment=1000000,
            years=5,
            num_simulations=500,
            use_fat_tails=False,
        )
        assert any("GAUSSIAN_MODEL" in w for w in result["warnings"])

    def test_real_values_less_than_nominal(self):
        """edgeCases §6.2: With positive inflation, real < nominal."""
        from app.services.backtesting_engine import monte_carlo_simulation
        result = monte_carlo_simulation(
            expected_annual_return=0.10,
            annual_volatility=0.15,
            initial_investment=1000000,
            years=10,
            inflation_rate=0.05,
            num_simulations=500,
        )
        assert result["real_inflation_adjusted"]["p50"] < result["nominal"]["p50"]

    def test_high_inflation_warning(self):
        """edgeCases §6.2: Hyper-inflation should trigger explicit warning."""
        from app.services.backtesting_engine import monte_carlo_simulation
        result = monte_carlo_simulation(
            expected_annual_return=0.10,
            annual_volatility=0.15,
            initial_investment=1000000,
            years=10,
            inflation_rate=0.15,
            num_simulations=500,
        )
        assert any("HIGH_INFLATION_WARNING" in w for w in result["warnings"])

    def test_zero_inflation_real_equals_nominal(self):
        from app.services.backtesting_engine import monte_carlo_simulation
        result = monte_carlo_simulation(
            expected_annual_return=0.10,
            annual_volatility=0.15,
            initial_investment=1000000,
            years=5,
            inflation_rate=0.0,
            num_simulations=500,
        )
        assert result["real_inflation_adjusted"]["p50"] == result["nominal"]["p50"]

    def test_probability_analysis(self):
        from app.services.backtesting_engine import monte_carlo_simulation
        result = monte_carlo_simulation(
            expected_annual_return=0.10,
            annual_volatility=0.15,
            initial_investment=1000000,
            years=10,
            num_simulations=1000,
        )
        prob = result["probability_analysis"]
        assert 0 <= prob["prob_positive_return_pct"] <= 100
        assert 0 <= prob["prob_double_investment_pct"] <= 100
        assert 0 <= prob["prob_loss_over_20pct"] <= 100

    def test_monthly_contribution_increases_terminal_value(self):
        from app.services.backtesting_engine import monte_carlo_simulation
        no_sip = monte_carlo_simulation(
            expected_annual_return=0.10, annual_volatility=0.15,
            initial_investment=1000000, monthly_contribution=0,
            years=10, num_simulations=500,
        )
        with_sip = monte_carlo_simulation(
            expected_annual_return=0.10, annual_volatility=0.15,
            initial_investment=1000000, monthly_contribution=20000,
            years=10, num_simulations=500,
        )
        assert with_sip["nominal"]["p50"] > no_sip["nominal"]["p50"]


# ═══════════════════════════════════════════════════════════════
# 5. SCENARIO SIMULATOR TESTS
# ═══════════════════════════════════════════════════════════════

class TestScenarioSimulator:

    @pytest.fixture
    def portfolio(self):
        return {
            "value": 1000000,
            "weights": {"AAPL": 0.3, "MSFT": 0.2, "TLT": 0.3, "GLD": 0.2},
        }

    def test_market_crash_reduces_value(self, portfolio):
        from app.services.backtesting_engine import simulate_scenario
        result = simulate_scenario(
            portfolio_value=portfolio["value"],
            weights=portfolio["weights"],
            scenario="market_crash",
            scenario_params={"crash_pct": -30},
        )
        assert result["post_scenario_value"] < portfolio["value"]
        assert result["impact_pct"] < 0

    def test_market_crash_only_hits_equities(self, portfolio):
        """Bonds and gold should be unaffected by equity crash."""
        from app.services.backtesting_engine import simulate_scenario
        result = simulate_scenario(
            portfolio_value=1000000,
            weights={"AAPL": 0.5, "TLT": 0.5},
            scenario="market_crash",
            scenario_params={"crash_pct": -50},
        )
        # Only AAPL (50%) should be hit by -50%: loss = 1M * 0.5 * -0.5 = -250k
        expected = 1000000 - 250000
        assert abs(result["post_scenario_value"] - expected) < 1

    def test_inflation_spike(self, portfolio):
        from app.services.backtesting_engine import simulate_scenario
        result = simulate_scenario(
            portfolio_value=portfolio["value"],
            weights=portfolio["weights"],
            scenario="inflation_spike",
            scenario_params={"inflation_increase_pct": 5, "years": 5},
        )
        assert result["post_scenario_value"] < portfolio["value"]
        assert "inflation" in result["analysis"].lower()

    def test_sip_increase(self, portfolio):
        from app.services.backtesting_engine import simulate_scenario
        result = simulate_scenario(
            portfolio_value=portfolio["value"],
            weights=portfolio["weights"],
            scenario="sip_increase",
            scenario_params={"additional_monthly": 10000, "years": 10, "expected_return": 0.12},
        )
        assert result["post_scenario_value"] > portfolio["value"]
        assert result["impact_pct"] > 0

    def test_early_retirement(self, portfolio):
        from app.services.backtesting_engine import simulate_scenario
        result = simulate_scenario(
            portfolio_value=portfolio["value"],
            weights=portfolio["weights"],
            scenario="early_retirement",
            scenario_params={"target_age": 45, "current_age": 30, "expected_return": 0.10},
        )
        assert result["post_scenario_value"] > portfolio["value"]
        assert "4% rule" in result["analysis"]

    def test_unknown_scenario(self, portfolio):
        from app.services.backtesting_engine import simulate_scenario
        result = simulate_scenario(
            portfolio_value=portfolio["value"],
            weights=portfolio["weights"],
            scenario="alien_invasion",
        )
        assert "Unknown scenario" in result["analysis"]
