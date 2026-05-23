import uuid
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.holding import Holding
from app.schemas.holdings import (
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    HoldingSnapshotResponse,
    VaultDashboardResponse
)

router = APIRouter()

# In-memory price cache to avoid hitting yfinance limits
# Format: { "TICKER": {"price": float, "prev_close": float, "timestamp": datetime} }
PRICE_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_MINUTES = 15

def get_live_price(ticker: str, fallback_price: float) -> tuple[float, float]:
    """Fetch live price from yfinance or cache. Returns (current_price, previous_close)."""
    now = datetime.now()
    if ticker in PRICE_CACHE:
        cached = PRICE_CACHE[ticker]
        if now - cached["timestamp"] < timedelta(minutes=CACHE_TTL_MINUTES):
            return cached["price"], cached["prev_close"]
    
    try:
        t = yf.Ticker(ticker)
        data = t.history(period="5d")
        if not data.empty:
            current_price = data["Close"].iloc[-1]
            prev_close = data["Close"].iloc[-2] if len(data) > 1 else current_price
            
            # Save to cache
            PRICE_CACHE[ticker] = {
                "price": current_price,
                "prev_close": prev_close,
                "timestamp": now
            }
            return current_price, prev_close
    except Exception as e:
        print(f"yfinance error for {ticker}: {e}")
        
    return fallback_price, fallback_price


from app.models.portfolio import AuditLog

@router.post("/", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
async def create_holding(
    holding_in: HoldingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a new holding manually. If ticker exists, update quantity and avg price."""
    
    # 1. Deduplication Check
    stmt = select(Holding).where(
        Holding.user_id == current_user.id,
        Holding.asset_ticker == holding_in.asset_ticker
    )
    result = await db.execute(stmt)
    existing_holding = result.scalar_one_or_none()
    
    if existing_holding:
        # Calculate new weighted average price
        total_value = (existing_holding.quantity * existing_holding.average_buy_price) + (holding_in.quantity * holding_in.average_buy_price)
        new_quantity = existing_holding.quantity + holding_in.quantity
        new_avg_price = total_value / new_quantity
        
        existing_holding.quantity = new_quantity
        existing_holding.average_buy_price = new_avg_price
        
        holding_to_return = existing_holding
        action_desc = "HOLDING_UPDATED"
    else:
        new_holding = Holding(
            user_id=current_user.id,
            **holding_in.model_dump()
        )
        db.add(new_holding)
        holding_to_return = new_holding
        action_desc = "HOLDING_ADDED"
        
    # 2. Audit Logging
    audit = AuditLog(
        user_id=current_user.id,
        action=action_desc,
        details={"ticker": holding_in.asset_ticker, "quantity": holding_in.quantity, "price": holding_in.average_buy_price}
    )
    db.add(audit)
    
    await db.commit()
    await db.refresh(holding_to_return)
    return holding_to_return


@router.get("/dashboard", response_model=VaultDashboardResponse)
async def get_vault_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch all holdings and calculate live portfolio P&L."""
    stmt = select(Holding).where(Holding.user_id == current_user.id)
    result = await db.execute(stmt)
    holdings = result.scalars().all()
    
    snapshot_holdings = []
    total_net_worth = 0.0
    total_invested = 0.0
    total_prev_value = 0.0
    
    for h in holdings:
        current_price, prev_close = get_live_price(h.asset_ticker, h.average_buy_price)
        
        current_val = current_price * h.quantity
        invested_val = h.average_buy_price * h.quantity
        prev_val = prev_close * h.quantity
        
        unrealised_pnl = current_val - invested_val
        unrealised_pnl_pct = (unrealised_pnl / invested_val) * 100 if invested_val > 0 else 0
        
        day_change = current_val - prev_val
        day_change_pct = (day_change / prev_val) * 100 if prev_val > 0 else 0
        
        total_net_worth += current_val
        total_invested += invested_val
        total_prev_value += prev_val
        
        snap = HoldingSnapshotResponse(
            **h.__dict__,
            current_price=current_price,
            current_value=current_val,
            unrealised_pnl=unrealised_pnl,
            unrealised_pnl_pct=unrealised_pnl_pct,
            day_change=day_change,
            day_change_pct=day_change_pct
        )
        snapshot_holdings.append(snap)
        
    tot_unrealised_pnl = total_net_worth - total_invested
    tot_unrealised_pnl_pct = (tot_unrealised_pnl / total_invested) * 100 if total_invested > 0 else 0
    tot_day_change = total_net_worth - total_prev_value
    tot_day_change_pct = (tot_day_change / total_prev_value) * 100 if total_prev_value > 0 else 0
    
    return VaultDashboardResponse(
        net_worth=total_net_worth,
        total_invested=total_invested,
        total_unrealised_pnl=tot_unrealised_pnl,
        total_unrealised_pnl_pct=tot_unrealised_pnl_pct,
        day_change=tot_day_change,
        day_change_pct=tot_day_change_pct,
        holdings=snapshot_holdings
    )


@router.delete("/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
    holding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a holding."""
    stmt = select(Holding).where(Holding.id == holding_id, Holding.user_id == current_user.id)
    result = await db.execute(stmt)
    holding = result.scalar_one_or_none()
    
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
        
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="HOLDING_DELETED",
        details={"ticker": holding.asset_ticker}
    )
    db.add(audit)
        
    await db.delete(holding)
    await db.commit()
    return None

from app.models.portfolio import PortfolioSnapshot
import random
from datetime import timedelta

@router.get("/snapshots", response_model=List[Dict[str, Any]])
async def get_portfolio_snapshots(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch 30-day historical snapshots for timeline. Seeds mock data if none exists."""
    stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == current_user.id).order_by(PortfolioSnapshot.snapshot_date.asc())
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    
    # 3. Retention Schedulers & Mock Data
    if not snapshots:
        # Fetch current dashboard to get base Net Worth
        vault = await get_vault_dashboard(db, current_user)
        base_nw = vault.net_worth
        if base_nw > 0:
            now = datetime.now(timezone.utc)
            simulated_snapshots = []
            
            # Start 30 days ago, add random walk
            current_sim_nw = base_nw * 0.95 # Assume 5% gain over 30 days
            for i in range(30, 0, -1):
                snap_date = now - timedelta(days=i)
                # Random daily movement between -1.5% and 2.0%
                daily_pct = random.uniform(-0.015, 0.02)
                current_sim_nw = current_sim_nw * (1 + daily_pct)
                
                snap = PortfolioSnapshot(
                    user_id=current_user.id,
                    snapshot_date=snap_date,
                    net_worth=current_sim_nw,
                    total_invested=vault.total_invested,
                    day_change=current_sim_nw * daily_pct,
                    health_score=random.randint(65, 85)
                )
                db.add(snap)
                simulated_snapshots.append(snap)
                
            await db.commit()
            
            stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == current_user.id).order_by(PortfolioSnapshot.snapshot_date.asc())
            result = await db.execute(stmt)
            snapshots = result.scalars().all()
            
    return [
        {
            "id": str(s.id),
            "date": s.snapshot_date.isoformat(),
            "net_worth": s.net_worth,
            "total_invested": s.total_invested,
            "day_change": s.day_change,
            "health_score": s.health_score
        } for s in snapshots
    ]
