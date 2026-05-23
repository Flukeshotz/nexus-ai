from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Dict, Literal

class SectorMomentum(BaseModel):
    Technology: float = Field(ge=0.0, le=1.0, description="Relative strength of Tech sector vs benchmark")
    Bonds: float = Field(ge=0.0, le=1.0, description="Relative strength of Bonds vs benchmark")

class AssetSignal(BaseModel):
    rsi: float = Field(ge=0.0, le=100.0)
    trend: Literal["Bullish", "Bearish", "Neutral"]

class MarketSnapshotSchema(BaseModel):
    timestamp: str
    market_regime: Literal["Bullish", "Bearish", "Neutral"]
    inflation_trend: Literal["Rising", "Falling", "Stable"]
    interest_rate_trend: Literal["Rising", "Falling", "Stable"]
    volatility_level: Literal["High", "Low", "Moderate"]
    fear_greed_score: int = Field(ge=0, le=100)
    sector_momentum: SectorMomentum
    asset_signals: Dict[str, AssetSignal]

    @field_validator("timestamp")
    def validate_timestamp(cls, v):
        try:
            # Enforce ISO format validation
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("Timestamp must be a valid ISO-8601 string.")
