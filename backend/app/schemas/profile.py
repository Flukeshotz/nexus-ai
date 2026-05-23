"""
Pydantic schemas for the Investor Profile endpoints.
Covers create, update, read, and risk score output.
"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional
from enum import Enum
import warnings


# ── Enum Mirrors (for Pydantic) ───────────────────────────────

class RiskAppetiteEnum(str, Enum):
    conservative = "conservative"
    moderately_conservative = "moderately_conservative"
    moderate = "moderate"
    aggressive = "aggressive"
    very_aggressive = "very_aggressive"


class InvestmentHorizonEnum(str, Enum):
    short_term = "short_term"
    medium_term = "medium_term"
    long_term = "long_term"


class DomesticInternationalEnum(str, Enum):
    domestic = "domestic"
    international = "international"
    both = "both"


# ── Request Schemas ───────────────────────────────────────────

# ── Valid Financial Goals ─────────────────────────────────────
VALID_GOALS = {
    "retirement", "wealth_accumulation", "passive_income",
    "house_purchase", "education", "tax_optimization", "fire",
}

# ── Aggressive goals that conflict with conservative risk ─────
AGGRESSIVE_GOALS = {"fire", "wealth_accumulation"}
CONSERVATIVE_RISK_LEVELS = {"conservative", "moderately_conservative"}


class ProfileCreateRequest(BaseModel):
    """Schema for creating an investor profile."""
    # Demographics
    age: int = Field(..., ge=18, le=120, description="User's age")
    occupation: Optional[str] = Field(None, max_length=255)
    country: str = Field("India", max_length=100)
    tax_bracket: Optional[str] = Field(None, max_length=50)

    # Financial Information
    monthly_income: float = Field(..., ge=0, description="Gross monthly income")
    monthly_expenses: float = Field(..., ge=0, description="Average monthly expenses")
    emergency_savings: float = Field(0, ge=0)
    existing_investments: dict = Field(default_factory=dict, description="Breakdown of current holdings")
    debt_obligations: float = Field(0, ge=0)
    net_worth: float = Field(0)

    # Investment Preferences
    monthly_investment_amount: float = Field(..., ge=0)
    lump_sum_capability: float = Field(0, ge=0)
    preferred_sectors: list[str] = Field(default_factory=list)
    ethical_investing: bool = Field(False)
    domestic_vs_international: DomesticInternationalEnum = Field(DomesticInternationalEnum.both)

    # Goals
    financial_goals: list[str] = Field(
        default_factory=list,
        description="e.g., retirement, wealth_accumulation, passive_income, house_purchase, education, tax_optimization, fire",
    )

    # Risk & Horizon
    risk_appetite: RiskAppetiteEnum
    investment_horizon: InvestmentHorizonEnum

    # ── Warnings (populated by validators, returned in response) ──
    _warnings: list[str] = []

    @model_validator(mode="after")
    def validate_financial_consistency(self):
        """Edge Case 1.2: Detect extreme financial imbalances."""
        warns = []

        # Investment exceeds disposable income
        disposable = self.monthly_income - self.monthly_expenses
        if self.monthly_investment_amount > 0 and disposable <= 0:
            raise ValueError(
                "Monthly investment amount cannot exceed disposable income "
                f"(income={self.monthly_income}, expenses={self.monthly_expenses})."
            )
        if disposable > 0 and self.monthly_investment_amount > disposable:
            raise ValueError(
                f"Monthly investment (₹{self.monthly_investment_amount}) exceeds "
                f"disposable income (₹{disposable})."
            )

        # Extreme debt-to-income ratio (> 10x)
        if self.monthly_income > 0 and self.debt_obligations > self.monthly_income * 120:
            warns.append(
                "EXTREME_DEBT: Debt obligations exceed 10 years of gross income. "
                "Recommendations will be adjusted for capital preservation."
            )

        # Zero income with significant assets (High Net Worth edge case)
        if self.monthly_income == 0 and self.net_worth > 5_000_000:
            warns.append(
                "HIGH_NET_WORTH_ANOMALY: Zero income reported with high net worth. "
                "Profile flagged for specialized advisory flow."
            )

        self._warnings = warns
        return self

    @model_validator(mode="after")
    def validate_goal_risk_consistency(self):
        """Edge Case 1.1: Detect contradictory risk appetite vs financial goals."""
        if self.risk_appetite in CONSERVATIVE_RISK_LEVELS:
            conflicting = set(self.financial_goals) & AGGRESSIVE_GOALS
            if conflicting and self.investment_horizon == InvestmentHorizonEnum.short_term:
                raise ValueError(
                    f"Contradictory profile: Conservative risk appetite with aggressive "
                    f"goals ({', '.join(conflicting)}) and a short-term horizon is "
                    f"mathematically infeasible. Please adjust your risk appetite, "
                    f"goals, or investment horizon."
                )
            elif conflicting:
                # Warn but allow — long horizons can partially offset
                self._warnings.append(
                    f"GOAL_RISK_MISMATCH: Goals {list(conflicting)} typically require "
                    f"higher risk tolerance than '{self.risk_appetite.value}'. "
                    f"Expected returns may be lower than needed."
                )
        return self


class ProfileUpdateRequest(BaseModel):
    """Schema for partially updating an investor profile."""
    age: Optional[int] = Field(None, ge=18, le=120)
    occupation: Optional[str] = None
    country: Optional[str] = None
    tax_bracket: Optional[str] = None
    monthly_income: Optional[float] = Field(None, ge=0)
    monthly_expenses: Optional[float] = Field(None, ge=0)
    emergency_savings: Optional[float] = Field(None, ge=0)
    existing_investments: Optional[dict] = None
    debt_obligations: Optional[float] = Field(None, ge=0)
    net_worth: Optional[float] = None
    monthly_investment_amount: Optional[float] = Field(None, ge=0)
    lump_sum_capability: Optional[float] = Field(None, ge=0)
    preferred_sectors: Optional[list[str]] = None
    ethical_investing: Optional[bool] = None
    domestic_vs_international: Optional[DomesticInternationalEnum] = None
    financial_goals: Optional[list[str]] = None
    risk_appetite: Optional[RiskAppetiteEnum] = None
    investment_horizon: Optional[InvestmentHorizonEnum] = None


# ── Response Schemas ──────────────────────────────────────────

class ProfileResponse(BaseModel):
    """Full investor profile response."""
    id: str
    user_id: str
    age: int
    occupation: Optional[str]
    country: str
    tax_bracket: Optional[str]
    monthly_income: float
    monthly_expenses: float
    emergency_savings: float
    existing_investments: dict
    debt_obligations: float
    net_worth: float
    monthly_investment_amount: float
    lump_sum_capability: float
    preferred_sectors: list[str]
    ethical_investing: bool
    domestic_vs_international: str
    financial_goals: list[str]
    risk_appetite: str
    investment_horizon: str

    class Config:
        from_attributes = True


class RiskScoreResponse(BaseModel):
    """Computed quantitative risk score."""
    risk_score: float = Field(..., ge=0, le=100, description="Numerical risk score 0-100")
    risk_category: str
    breakdown: dict = Field(
        ...,
        description="Weighted factor breakdown showing how the score was computed",
    )
