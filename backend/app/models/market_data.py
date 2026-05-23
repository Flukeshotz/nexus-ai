"""
SQLAlchemy ORM models for Phase 2: Data Intelligence & Market Pipeline.

Tables:
  - market_prices: OHLCV data per ticker per day
  - asset_metadata: Static info (ticker, name, sector, asset class, exchange)
  - economic_indicators: Time-series macro data
  - news_articles: Raw article metadata for unstructured data
  - market_signals: Computed technical indicators per ticker per day
  - sentiment_scores: FinBERT sentiment per ticker/sector per day
"""

import uuid
import enum
from datetime import datetime, timezone, date
from sqlalchemy import (
    String, Integer, Float, Date, DateTime, Enum,
    Text, UniqueConstraint, Index,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


# ═══════════════════════════════════════════════════════════════
# Asset Metadata
# ═══════════════════════════════════════════════════════════════

class AssetClass(str, enum.Enum):
    EQUITY = "equity"
    MUTUAL_FUND = "mutual_fund"
    ETF = "etf"
    BOND = "bond"
    GOLD = "gold"
    CRYPTO = "crypto"
    INDEX = "index"


class AssetMetadata(Base):
    """Static reference data for every trackable asset."""
    __tablename__ = "asset_metadata"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_class: Mapped[AssetClass] = mapped_column(Enum(AssetClass), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=True)
    exchange: Mapped[str] = mapped_column(String(50), nullable=True)
    country: Mapped[str] = mapped_column(String(50), default="US")
    is_active: Mapped[bool] = mapped_column(default=True)
    is_halted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<AssetMetadata {self.ticker} ({self.asset_class.value})>"


# ═══════════════════════════════════════════════════════════════
# Market Prices (OHLCV)
# ═══════════════════════════════════════════════════════════════

class MarketPrice(Base):
    """Daily OHLCV price data per ticker."""
    __tablename__ = "market_prices"
    __table_args__ = (
        UniqueConstraint("ticker", "price_date", name="uq_ticker_date"),
        Index("ix_market_prices_ticker_date", "ticker", "price_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=True)
    high: Mapped[float] = mapped_column(Float, nullable=True)
    low: Mapped[float] = mapped_column(Float, nullable=True)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    adj_close: Mapped[float] = mapped_column(Float, nullable=True)
    volume: Mapped[int] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="yfinance")
    is_anomaly: Mapped[bool] = mapped_column(default=False)
    anomaly_reason: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<MarketPrice {self.ticker} {self.price_date} close={self.close}>"


# ═══════════════════════════════════════════════════════════════
# Economic Indicators
# ═══════════════════════════════════════════════════════════════

class EconomicIndicator(Base):
    """Time-series macroeconomic data (CPI, GDP, interest rates, etc.)."""
    __tablename__ = "economic_indicators"
    __table_args__ = (
        UniqueConstraint("indicator_name", "indicator_date", name="uq_indicator_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    indicator_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    indicator_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="FRED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<EconomicIndicator {self.indicator_name} {self.indicator_date}={self.value}>"


# ═══════════════════════════════════════════════════════════════
# News Articles (Unstructured Data Metadata)
# ═══════════════════════════════════════════════════════════════

class NewsArticle(Base):
    """Metadata for ingested financial news articles."""
    __tablename__ = "news_articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_content: Mapped[str] = mapped_column(Text, nullable=True)
    tickers_mentioned: Mapped[list] = mapped_column(JSON, default=list)
    sectors_mentioned: Mapped[list] = mapped_column(JSON, default=list)
    is_embedded: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<NewsArticle '{self.title[:40]}...'>"


# ═══════════════════════════════════════════════════════════════
# Market Signals (Computed Technical Indicators)
# ═══════════════════════════════════════════════════════════════

class MarketSignal(Base):
    """Computed technical indicators per ticker per day."""
    __tablename__ = "market_signals"
    __table_args__ = (
        UniqueConstraint("ticker", "signal_date", name="uq_signal_ticker_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Technical indicators
    rsi_14: Mapped[float] = mapped_column(Float, nullable=True)
    sma_50: Mapped[float] = mapped_column(Float, nullable=True)
    sma_200: Mapped[float] = mapped_column(Float, nullable=True)
    ema_12: Mapped[float] = mapped_column(Float, nullable=True)
    ema_26: Mapped[float] = mapped_column(Float, nullable=True)
    macd: Mapped[float] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[float] = mapped_column(Float, nullable=True)
    bollinger_upper: Mapped[float] = mapped_column(Float, nullable=True)
    bollinger_lower: Mapped[float] = mapped_column(Float, nullable=True)
    volatility_30d: Mapped[float] = mapped_column(Float, nullable=True)
    beta: Mapped[float] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<MarketSignal {self.ticker} {self.signal_date} RSI={self.rsi_14}>"


# ═══════════════════════════════════════════════════════════════
# Sentiment Scores
# ═══════════════════════════════════════════════════════════════

class SentimentLabel(str, enum.Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SentimentScore(Base):
    """FinBERT sentiment analysis results per ticker/sector."""
    __tablename__ = "sentiment_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=True)
    score_date: Mapped[date] = mapped_column(Date, nullable=False)
    sentiment: Mapped[SentimentLabel] = mapped_column(Enum(SentimentLabel), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source_article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_text_snippet: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<SentimentScore {self.ticker or self.sector} {self.sentiment.value} {self.confidence:.2f}>"
