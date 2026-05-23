"""
SQLAlchemy ORM model for the `investor_profiles` table.
Captures the complete financial profile of an investor as defined
in the problem statement: demographics, financials, preferences,
goals, risk appetite, and investment horizon.
"""

import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    String, Integer, Numeric, Boolean, DateTime, Enum, ForeignKey,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


# ── Enum Definitions ──────────────────────────────────────────

class RiskAppetite(str, enum.Enum):
    CONSERVATIVE = "conservative"
    MODERATELY_CONSERVATIVE = "moderately_conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    VERY_AGGRESSIVE = "very_aggressive"


class InvestmentHorizon(str, enum.Enum):
    SHORT_TERM = "short_term"       # < 3 years
    MEDIUM_TERM = "medium_term"     # 3–7 years
    LONG_TERM = "long_term"         # > 7 years


class DomesticInternational(str, enum.Enum):
    DOMESTIC = "domestic"
    INTERNATIONAL = "international"
    BOTH = "both"


# ── ORM Model ────────────────────────────────────────────────

class InvestorProfile(Base):
    __tablename__ = "investor_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # ── Demographics ──────────────────────────────────────────
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    occupation: Mapped[str] = mapped_column(String(255), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    tax_bracket: Mapped[str] = mapped_column(String(50), nullable=True)

    # ── Financial Information ─────────────────────────────────
    monthly_income: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    monthly_expenses: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    emergency_savings: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    existing_investments: Mapped[dict] = mapped_column(JSON, default=dict)
    debt_obligations: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    net_worth: Mapped[float] = mapped_column(Numeric(15, 2), default=0)

    # ── Investment Preferences ────────────────────────────────
    monthly_investment_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    lump_sum_capability: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    preferred_sectors: Mapped[list] = mapped_column(JSON, default=list)
    ethical_investing: Mapped[bool] = mapped_column(Boolean, default=False)
    domestic_vs_international: Mapped[DomesticInternational] = mapped_column(
        Enum(DomesticInternational),
        default=DomesticInternational.BOTH,
    )

    # ── Financial Goals ───────────────────────────────────────
    financial_goals: Mapped[list] = mapped_column(JSON, default=list)

    # ── Risk & Horizon ────────────────────────────────────────
    risk_appetite: Mapped[RiskAppetite] = mapped_column(
        Enum(RiskAppetite),
        nullable=False,
    )
    investment_horizon: Mapped[InvestmentHorizon] = mapped_column(
        Enum(InvestmentHorizon),
        nullable=False,
    )

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<InvestorProfile user_id={self.user_id} risk={self.risk_appetite}>"
