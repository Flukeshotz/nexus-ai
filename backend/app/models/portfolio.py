"""
SQLAlchemy ORM models for the `portfolios`, `portfolio_assets`,
and `audit_logs` tables.
"""

import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    String, Integer, DateTime, Enum, ForeignKey, Text, Float,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


# ── Portfolio Status ──────────────────────────────────────────

class PortfolioStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    REBALANCED = "rebalanced"


# ── Portfolio Model ───────────────────────────────────────────

class Portfolio(Base):
    """Stores generated portfolio snapshots for a user."""
    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[PortfolioStatus] = mapped_column(
        Enum(PortfolioStatus),
        default=PortfolioStatus.ACTIVE,
    )
    # ── Aggregated Metrics ────────────────────────────────────
    expected_cagr: Mapped[float] = mapped_column(Float, nullable=True)
    expected_volatility: Mapped[float] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=True)
    diversification_score: Mapped[float] = mapped_column(Float, nullable=True)

    # ── AI Reasoning ──────────────────────────────────────────
    ai_rationale: Mapped[str] = mapped_column(Text, nullable=True)
    market_signals_used: Mapped[dict] = mapped_column(JSON, default=dict)

    # ── Timestamps ────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="portfolios")
    assets: Mapped[list["PortfolioAsset"]] = relationship(
        "PortfolioAsset",
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Portfolio {self.id} status={self.status}>"


# ── Portfolio Asset Model ─────────────────────────────────────

class PortfolioAsset(Base):
    """Individual asset allocations within a portfolio snapshot."""
    __tablename__ = "portfolio_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_class: Mapped[str] = mapped_column(String(100), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=True)
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    allocation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="assets")

    def __repr__(self) -> str:
        return f"<PortfolioAsset {self.asset_name} {self.allocation_pct}%>"


# ── Audit Log Model ──────────────────────────────────────────

class AuditLog(Base):
    """Immutable log of every recommendation and rebalance event."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} at {self.created_at}>"


# ── Portfolio Snapshot Model (History) ─────────────────────────

class PortfolioSnapshot(Base):
    """Daily snapshot of a user's vault dashboard for performance history."""
    __tablename__ = "portfolio_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    net_worth: Mapped[float] = mapped_column(Float, nullable=False)
    total_invested: Mapped[float] = mapped_column(Float, nullable=False)
    day_change: Mapped[float] = mapped_column(Float, nullable=False)
    health_score: Mapped[int] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<PortfolioSnapshot {self.snapshot_date.date()} NetWorth={self.net_worth}>"


# ── AI Advice History Model ───────────────────────────────────

class AIAdviceHistory(Base):
    """Persisted actionable advice generated by the AI for the user."""
    __tablename__ = "ai_advice_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    advice_type: Mapped[str] = mapped_column(String(50), nullable=False) # RISK, OPPORTUNITY, REBALANCE
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="NEW") # NEW, ACTED, DISMISSED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<AIAdviceHistory {self.advice_type} {self.title}>"

# ── Smart Alerts Model ───────────────────────────────────────

class SmartAlert(Base):
    """Proactive alerts (Risk Drift, Concentration, Unusual Movement)"""
    __tablename__ = "smart_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False) # DRIFT, CONCENTRATION, MOVEMENT
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="INFO") # INFO, WARNING, CRITICAL
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<SmartAlert {self.alert_type} {self.severity}>"
