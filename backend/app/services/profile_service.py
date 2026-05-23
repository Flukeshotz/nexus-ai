"""
Investor Profile service: handles CRUD operations and
risk score quantification as specified in the implementation plan.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import uuid

from app.models.investor_profile import InvestorProfile
from app.schemas.profile import (
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ProfileResponse,
    RiskScoreResponse,
)


class ProfileService:
    """Encapsulates investor profile business logic."""

    @staticmethod
    async def create_profile(
        db: AsyncSession, user_id: uuid.UUID, data: ProfileCreateRequest
    ) -> ProfileResponse:
        """Create a new investor profile for the authenticated user."""
        # Check if profile already exists
        stmt = select(InvestorProfile).where(InvestorProfile.user_id == user_id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Investor profile already exists. Use PUT to update.",
            )

        profile = InvestorProfile(
            user_id=user_id,
            **data.model_dump(),
        )
        db.add(profile)
        await db.flush()

        return ProfileService._to_response(profile)

    @staticmethod
    async def get_profile(db: AsyncSession, user_id: uuid.UUID) -> ProfileResponse:
        """Retrieve the investor profile for the authenticated user."""
        stmt = select(InvestorProfile).where(InvestorProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investor profile not found. Please create one first.",
            )

        return ProfileService._to_response(profile)

    @staticmethod
    async def update_profile(
        db: AsyncSession, user_id: uuid.UUID, data: ProfileUpdateRequest
    ) -> ProfileResponse:
        """Partially update the investor profile."""
        stmt = select(InvestorProfile).where(InvestorProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investor profile not found.",
            )

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(profile, key, value)

        await db.flush()
        return ProfileService._to_response(profile)

    @staticmethod
    async def compute_risk_score(db: AsyncSession, user_id: uuid.UUID) -> RiskScoreResponse:
        """
        Compute a quantitative risk score (0-100) from the investor's profile
        using weighted factors as defined in the implementation plan:

        - Age weight: younger → higher score (weight: 0.15)
        - Income-to-debt ratio: higher → higher score (weight: 0.20)
        - Investment horizon: longer → higher score (weight: 0.25)
        - Explicit risk appetite: direct mapping (weight: 0.40)
        """
        stmt = select(InvestorProfile).where(InvestorProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investor profile not found.",
            )

        anomaly_flags = []

        # ── Factor 1: Age Score (0-100) ───────────────────────
        # Age 18 → 100, Age 70+ → 10 (linear interpolation, clamped)
        clamped_age = max(18, min(profile.age, 70))
        age_score = max(10, min(100, 100 - ((clamped_age - 18) * (90 / 52))))
        if profile.age > 70:
            anomaly_flags.append("AGE_CAPPED: Age clamped at 70 for risk calculation.")

        # ── Factor 2: Income-to-Debt Ratio Score (0-100) ─────
        # Edge case: zero income with positive debt → score = 0 (not a crash)
        # Edge case: zero debt → score = 100
        # Edge case: extreme debt → capped at 0
        monthly_income = float(profile.monthly_income)
        debt = float(profile.debt_obligations)

        if debt == 0:
            income_debt_score = 100.0
        elif monthly_income == 0:
            income_debt_score = 0.0
            anomaly_flags.append(
                "ZERO_INCOME_WITH_DEBT: No income reported but debt exists. "
                "Risk score heavily penalized."
            )
        else:
            ratio = monthly_income / debt
            income_debt_score = min(100, ratio * 20)  # ratio of 5+ → 100

        # Flag extreme debt-to-income
        if monthly_income > 0 and debt > monthly_income * 120:
            anomaly_flags.append(
                "EXTREME_DEBT_RATIO: Debt exceeds 10 years of gross income."
            )
            income_debt_score = max(income_debt_score, 5)  # floor at 5, not 0

        # ── Factor 3: Investment Horizon Score (0-100) ────────
        horizon_map = {
            "short_term": 25,
            "medium_term": 55,
            "long_term": 90,
        }
        horizon_score = horizon_map.get(profile.investment_horizon.value, 50)

        # ── Factor 4: Risk Appetite Score (0-100) ─────────────
        appetite_map = {
            "conservative": 20,
            "moderately_conservative": 35,
            "moderate": 50,
            "aggressive": 80,
            "very_aggressive": 95,
        }
        appetite_score = appetite_map.get(profile.risk_appetite.value, 50)

        # ── Weighted Composite ────────────────────────────────
        weights = {
            "age": 0.15,
            "income_to_debt": 0.20,
            "investment_horizon": 0.25,
            "risk_appetite": 0.40,
        }
        composite = (
            age_score * weights["age"]
            + income_debt_score * weights["income_to_debt"]
            + horizon_score * weights["investment_horizon"]
            + appetite_score * weights["risk_appetite"]
        )
        composite = round(max(0, min(100, composite)), 2)  # clamp to 0-100

        # ── Classify ──────────────────────────────────────────
        if composite < 30:
            category = "Conservative"
        elif composite < 50:
            category = "Moderately Conservative"
        elif composite < 65:
            category = "Moderate"
        elif composite < 80:
            category = "Aggressive"
        else:
            category = "Very Aggressive"

        return RiskScoreResponse(
            risk_score=composite,
            risk_category=category,
            breakdown={
                "age_score": round(age_score, 2),
                "age_weight": weights["age"],
                "income_debt_score": round(income_debt_score, 2),
                "income_debt_weight": weights["income_to_debt"],
                "horizon_score": horizon_score,
                "horizon_weight": weights["investment_horizon"],
                "appetite_score": appetite_score,
                "appetite_weight": weights["risk_appetite"],
                "anomaly_flags": anomaly_flags,
            },
        )

    @staticmethod
    def _to_response(profile: InvestorProfile) -> ProfileResponse:
        """Convert an ORM model to a Pydantic response."""
        return ProfileResponse(
            id=str(profile.id),
            user_id=str(profile.user_id),
            age=profile.age,
            occupation=profile.occupation,
            country=profile.country,
            tax_bracket=profile.tax_bracket,
            monthly_income=float(profile.monthly_income),
            monthly_expenses=float(profile.monthly_expenses),
            emergency_savings=float(profile.emergency_savings),
            existing_investments=profile.existing_investments or {},
            debt_obligations=float(profile.debt_obligations),
            net_worth=float(profile.net_worth),
            monthly_investment_amount=float(profile.monthly_investment_amount),
            lump_sum_capability=float(profile.lump_sum_capability),
            preferred_sectors=profile.preferred_sectors or [],
            ethical_investing=profile.ethical_investing,
            domestic_vs_international=profile.domestic_vs_international.value if profile.domestic_vs_international else "both",
            financial_goals=profile.financial_goals or [],
            risk_appetite=profile.risk_appetite.value if profile.risk_appetite else "moderate",
            investment_horizon=profile.investment_horizon.value if profile.investment_horizon else "medium_term",
        )
