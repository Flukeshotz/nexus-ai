from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
import uuid

class HoldingBase(BaseModel):
    asset_ticker: str = Field(..., max_length=50)
    asset_name: str = Field(..., max_length=255)
    asset_class: str = Field(..., max_length=50)
    quantity: float = Field(..., gt=0)
    average_buy_price: float = Field(..., gt=0)
    buy_date: Optional[datetime] = None
    source: str = "MANUAL"
    notes: Optional[str] = None

    @field_validator('asset_ticker')
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        # If it doesn't end in .NS or .BO and doesn't contain a dot, assume Indian Equity (.NS)
        # We can keep it simple: just strip and upper.
        if not '.' in v:
            v = f"{v}.NS"
        return v

class HoldingCreate(HoldingBase):
    pass

class HoldingUpdate(BaseModel):
    quantity: Optional[float] = Field(None, gt=0)
    average_buy_price: Optional[float] = Field(None, gt=0)
    buy_date: Optional[datetime] = None
    notes: Optional[str] = None

class HoldingResponse(HoldingBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class HoldingSnapshotResponse(HoldingResponse):
    current_price: float
    current_value: float
    unrealised_pnl: float
    unrealised_pnl_pct: float
    day_change: float
    day_change_pct: float

class VaultDashboardResponse(BaseModel):
    net_worth: float
    total_invested: float
    total_unrealised_pnl: float
    total_unrealised_pnl_pct: float
    day_change: float
    day_change_pct: float
    holdings: List[HoldingSnapshotResponse]
