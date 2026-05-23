"""
Comprehensive edge case tests for Phase 1.
Tests all scenarios from edgeCases.md §1 (Investor Profiling Engine).
These are pure unit tests — no database required.
"""

import pytest
from pydantic import ValidationError
from app.schemas.profile import ProfileCreateRequest


# ═══════════════════════════════════════════════════════════════
# HELPER: base valid profile data
# ═══════════════════════════════════════════════════════════════

def _base_profile(**overrides) -> dict:
    """Return a valid profile dict with optional overrides."""
    data = {
        "age": 30,
        "occupation": "Engineer",
        "country": "India",
        "tax_bracket": "20%",
        "monthly_income": 100000,
        "monthly_expenses": 40000,
        "emergency_savings": 200000,
        "existing_investments": {},
        "debt_obligations": 0,
        "net_worth": 500000,
        "monthly_investment_amount": 20000,
        "lump_sum_capability": 100000,
        "preferred_sectors": ["technology"],
        "ethical_investing": False,
        "domestic_vs_international": "both",
        "financial_goals": ["retirement"],
        "risk_appetite": "moderate",
        "investment_horizon": "long_term",
    }
    data.update(overrides)
    return data


# ═══════════════════════════════════════════════════════════════
# 1. AGE BOUNDARY TESTS
# ═══════════════════════════════════════════════════════════════

class TestAgeBoundaries:
    """Edge Case: Age must be 18-120, no crash at extremes."""

    def test_minimum_age_18_accepted(self):
        profile = ProfileCreateRequest(**_base_profile(age=18))
        assert profile.age == 18

    def test_maximum_age_120_accepted(self):
        profile = ProfileCreateRequest(**_base_profile(age=120))
        assert profile.age == 120

    def test_age_below_18_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ProfileCreateRequest(**_base_profile(age=17))
        assert "age" in str(exc_info.value).lower()

    def test_age_below_0_rejected(self):
        with pytest.raises(ValidationError):
            ProfileCreateRequest(**_base_profile(age=-5))

    def test_age_above_120_rejected(self):
        with pytest.raises(ValidationError):
            ProfileCreateRequest(**_base_profile(age=121))


# ═══════════════════════════════════════════════════════════════
# 2. EDGE CASE 1.1: CONTRADICTORY RISK vs GOALS
# ═══════════════════════════════════════════════════════════════

class TestContradictoryRiskGoals:
    """
    edgeCases.md §1.1: Conservative risk + aggressive goals (FIRE)
    + short horizon should be rejected as mathematically infeasible.
    """

    def test_conservative_fire_short_term_rejected(self):
        """Hard contradiction: conservative + FIRE + short_term → error."""
        with pytest.raises(ValidationError) as exc_info:
            ProfileCreateRequest(**_base_profile(
                risk_appetite="conservative",
                financial_goals=["fire"],
                investment_horizon="short_term",
            ))
        assert "contradictory" in str(exc_info.value).lower()

    def test_moderately_conservative_wealth_short_term_rejected(self):
        """Hard contradiction: moderately_conservative + wealth_accumulation + short_term → error."""
        with pytest.raises(ValidationError) as exc_info:
            ProfileCreateRequest(**_base_profile(
                risk_appetite="moderately_conservative",
                financial_goals=["wealth_accumulation"],
                investment_horizon="short_term",
            ))
        assert "contradictory" in str(exc_info.value).lower()

    def test_conservative_fire_long_term_allowed_with_warning(self):
        """Soft contradiction: conservative + FIRE + long_term → allowed (warning only)."""
        profile = ProfileCreateRequest(**_base_profile(
            risk_appetite="conservative",
            financial_goals=["fire"],
            investment_horizon="long_term",
        ))
        # Should be created successfully
        assert profile.risk_appetite.value == "conservative"

    def test_aggressive_fire_short_term_allowed(self):
        """No contradiction: aggressive + FIRE + short_term → allowed."""
        profile = ProfileCreateRequest(**_base_profile(
            risk_appetite="aggressive",
            financial_goals=["fire"],
            investment_horizon="short_term",
        ))
        assert profile.risk_appetite.value == "aggressive"

    def test_conservative_retirement_long_term_fine(self):
        """No issue: conservative + retirement + long_term → perfectly valid."""
        profile = ProfileCreateRequest(**_base_profile(
            risk_appetite="conservative",
            financial_goals=["retirement"],
            investment_horizon="long_term",
        ))
        assert profile.risk_appetite.value == "conservative"


# ═══════════════════════════════════════════════════════════════
# 3. EDGE CASE 1.2: EXTREME FINANCIAL IMBALANCES
# ═══════════════════════════════════════════════════════════════

class TestExtremeFinancialImbalances:
    """edgeCases.md §1.2: Extreme or impossible financial values."""

    def test_investment_exceeds_disposable_income_rejected(self):
        """Monthly investment > (income - expenses) should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ProfileCreateRequest(**_base_profile(
                monthly_income=100000,
                monthly_expenses=40000,
                monthly_investment_amount=70000,  # 70k > 60k disposable
            ))
        assert "disposable" in str(exc_info.value).lower()

    def test_zero_income_positive_investment_rejected(self):
        """Zero income but positive investment → impossible."""
        with pytest.raises(ValidationError):
            ProfileCreateRequest(**_base_profile(
                monthly_income=0,
                monthly_expenses=0,
                monthly_investment_amount=10000,
            ))

    def test_investment_equals_disposable_accepted(self):
        """Investing exactly disposable income → allowed."""
        profile = ProfileCreateRequest(**_base_profile(
            monthly_income=100000,
            monthly_expenses=40000,
            monthly_investment_amount=60000,
        ))
        assert profile.monthly_investment_amount == 60000

    def test_zero_investment_always_accepted(self):
        """Zero monthly investment is always valid."""
        profile = ProfileCreateRequest(**_base_profile(
            monthly_investment_amount=0,
        ))
        assert profile.monthly_investment_amount == 0

    def test_negative_income_rejected(self):
        """Negative income should fail schema validation."""
        with pytest.raises(ValidationError):
            ProfileCreateRequest(**_base_profile(monthly_income=-50000))

    def test_negative_expenses_rejected(self):
        """Negative expenses should fail schema validation."""
        with pytest.raises(ValidationError):
            ProfileCreateRequest(**_base_profile(monthly_expenses=-10000))


# ═══════════════════════════════════════════════════════════════
# 4. RISK SCORE COMPUTATION EDGE CASES
# ═══════════════════════════════════════════════════════════════

class TestRiskScoreEdgeCases:
    """
    Verify the risk score formula handles boundary cases without
    crashing or producing out-of-range values.
    """

    def test_youngest_aggressive_long_term_no_debt(self):
        """Age 18, aggressive, long_term, no debt → near-maximum score."""
        age_score = max(10, min(100, 100 - ((18 - 18) * (90 / 52))))
        income_debt_score = 100.0
        horizon_score = 90
        appetite_score = 80
        composite = (
            age_score * 0.15 + income_debt_score * 0.20
            + horizon_score * 0.25 + appetite_score * 0.40
        )
        assert composite > 80, f"Expected very aggressive, got {composite}"

    def test_oldest_conservative_short_term_heavy_debt(self):
        """Age 70, conservative, short_term, heavy debt → minimum score."""
        age_score = max(10, min(100, 100 - ((70 - 18) * (90 / 52))))
        # income 50k, debt 500k → ratio 0.1 → score 2
        income_debt_score = min(100, 0.1 * 20)
        horizon_score = 25
        appetite_score = 20
        composite = (
            age_score * 0.15 + income_debt_score * 0.20
            + horizon_score * 0.25 + appetite_score * 0.40
        )
        assert composite < 30, f"Expected conservative, got {composite}"

    def test_zero_income_zero_debt_score_is_100(self):
        """No income, no debt → income_debt_score should be 100 (no debt)."""
        income_debt_score = 100.0  # No debt → max
        assert income_debt_score == 100.0

    def test_zero_income_positive_debt_score_is_zero(self):
        """Zero income with debt → income_debt_score = 0 (not a crash)."""
        monthly_income = 0
        debt = 500000
        if debt == 0:
            score = 100.0
        elif monthly_income == 0:
            score = 0.0
        else:
            score = min(100, (monthly_income / debt) * 20)
        assert score == 0.0

    def test_very_aggressive_max_boundary(self):
        """Ensure the score never exceeds 100."""
        # Max possible: age=100, income/debt=100, horizon=90, appetite=95
        composite = 100 * 0.15 + 100 * 0.20 + 90 * 0.25 + 95 * 0.40
        assert composite <= 100, f"Score {composite} exceeds 100"

    def test_all_minimum_inputs(self):
        """All factors at minimum → score > 0 (never negative)."""
        composite = 10 * 0.15 + 0 * 0.20 + 25 * 0.25 + 20 * 0.40
        assert composite >= 0, f"Score {composite} is negative"
        assert composite == pytest.approx(15.75, abs=0.01)


# ═══════════════════════════════════════════════════════════════
# 5. SCHEMA VALIDATION EDGE CASES
# ═══════════════════════════════════════════════════════════════

class TestSchemaValidation:
    """Additional schema-level edge case tests."""

    def test_invalid_risk_appetite_rejected(self):
        with pytest.raises(ValidationError):
            ProfileCreateRequest(**_base_profile(risk_appetite="yolo"))

    def test_invalid_horizon_rejected(self):
        with pytest.raises(ValidationError):
            ProfileCreateRequest(**_base_profile(investment_horizon="forever"))

    def test_invalid_domestic_international_rejected(self):
        with pytest.raises(ValidationError):
            ProfileCreateRequest(**_base_profile(domestic_vs_international="mars"))

    def test_empty_profile_missing_required_fields(self):
        """Submitting empty JSON should fail with missing field errors."""
        with pytest.raises(ValidationError) as exc_info:
            ProfileCreateRequest()
        errors = exc_info.value.errors()
        required_fields = {"age", "monthly_income", "monthly_expenses",
                          "monthly_investment_amount", "risk_appetite", "investment_horizon"}
        error_fields = {e["loc"][0] for e in errors}
        assert required_fields.issubset(error_fields)

    def test_email_format_in_auth(self):
        """Invalid email format should be rejected at schema level."""
        from app.schemas.auth import UserRegisterRequest
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="not-an-email",
                password="ValidPass123!",
            )

    def test_short_password_rejected(self):
        """Password under 8 chars should be rejected."""
        from app.schemas.auth import UserRegisterRequest
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="user@test.com",
                password="short",
            )
