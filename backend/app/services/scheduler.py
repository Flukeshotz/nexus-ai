import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from tenacity import retry, wait_exponential, stop_after_attempt

from app.services.market_data_service import fetch_batch_stock_data, fetch_amfi_navs
from app.services.news_service import fetch_news_from_feeds
from app.services.rebalancing_service import RebalancingService
from app.core.database import SessionLocal
from app.models.portfolio import SmartAlert
from app.models.user import User
from app.models.investor_profile import InvestorProfile
from app.api.holdings_router import get_vault_dashboard
from sqlalchemy import select

logger = logging.getLogger(__name__)

job_defaults = {
    'coalesce': True,
    'max_instances': 1,
    'misfire_grace_time': 3600
}
scheduler = AsyncIOScheduler(job_defaults=job_defaults)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def daily_market_data_sync():
    """Daily job: Fetches closing prices for Nifty50 and NAVs for AMFI."""
    logger.info("Starting daily market data sync...")
    try:
        # Fetch Nifty50 and ETFs
        stock_data = fetch_batch_stock_data()
        logger.info(f"Fetched {stock_data['total_tickers']} tickers. Anomalies: {stock_data['total_anomalies']}")
        
        # Fetch AMFI NAVs
        nav_data = fetch_amfi_navs()
        logger.info(f"Fetched {nav_data.get('total_funds', 0)} mutual fund NAVs.")
        
    except Exception as e:
        logger.error(f"Error in daily_market_data_sync: {e}")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def daily_news_sync():
    """Daily job: Fetches news and indexes into FAISS."""
    logger.info("Starting daily news sync...")
    try:
        from app.services.rag_service import get_vector_store
        news_data = await fetch_news_from_feeds()
        articles = news_data.get("articles", [])
        if articles:
            texts = [a["title"] + ". " + a.get("content", "") for a in articles]
            metadatas = [{"url": a.get("url", ""), "source": a.get("source", "")} for a in articles]
            store = get_vector_store()
            store.add_documents(texts, metadatas)
    except Exception as e:
        logger.error(f"Error in daily_news_sync: {e}")

async def hourly_portfolio_drift_check():
    """Hourly job: Checks portfolio drift for all users and triggers rebalancing alerts."""
    logger.info("Starting hourly portfolio drift check...")
    try:
        async with SessionLocal() as db:
            stmt = select(User)
            result = await db.execute(stmt)
            users = result.scalars().all()
            
            rebalancer = RebalancingService()
            for user in users:
                prof_stmt = select(InvestorProfile).where(InvestorProfile.user_id == user.id)
                profile = (await db.execute(prof_stmt)).scalar_one_or_none()
                if not profile:
                    continue
                
                # Simplified Target Weights mapping based on risk profile
                # E.g. Aggressive -> 80% Equity, 20% Debt
                target_weights = {"EQUITY": 0.8, "DEBT": 0.2} if profile.risk_appetite == "Aggressive" else {"EQUITY": 0.6, "DEBT": 0.4}
                
                vault = await get_vault_dashboard(db, user)
                if vault.net_worth == 0:
                    continue
                    
                current_weights = {}
                for h in vault.holdings:
                    current_weights[h.asset_class] = current_weights.get(h.asset_class, 0) + (h.current_value / vault.net_worth)
                    
                drifts = rebalancer.check_portfolio_drift(target_weights, current_weights)
                if drifts:
                    for asset_class, data in drifts.items():
                        alert_msg = f"{asset_class} drifted to {data['current']*100:.1f}%. Target is {data['target']*100:.1f}%."
                        
                        # Check if alert already exists today to prevent spam
                        alert_stmt = select(SmartAlert).where(
                            SmartAlert.user_id == user.id,
                            SmartAlert.alert_type == "DRIFT",
                            SmartAlert.is_read == False
                        )
                        existing_alert = (await db.execute(alert_stmt)).first()
                        if not existing_alert:
                            new_alert = SmartAlert(
                                user_id=user.id,
                                alert_type="DRIFT",
                                message=alert_msg,
                                severity="WARNING"
                            )
                            db.add(new_alert)
            await db.commit()
            logger.info("Drift check completed.")
    except Exception as e:
        logger.error(f"Error in hourly_portfolio_drift_check: {e}")

import os
from app.services.market_snapshot_service import update_and_cache_snapshot

def start_scheduler():
    """Initializes and starts the APScheduler with configured jobs."""
    if not scheduler.running:
        # Run daily at 6:30 AM IST (which is 1:00 AM UTC, but let's use timezone)
        scheduler.add_job(
            daily_market_data_sync,
            CronTrigger(hour=6, minute=30, timezone="Asia/Kolkata"),
            id="daily_market_data_sync",
            replace_existing=True
        )
        
        scheduler.add_job(
            daily_news_sync,
            CronTrigger(hour=7, minute=0, timezone="Asia/Kolkata"),
            id="daily_news_sync",
            replace_existing=True
        )
        
        scheduler.add_job(
            hourly_portfolio_drift_check,
            IntervalTrigger(hours=1),
            id="hourly_portfolio_drift_check",
            replace_existing=True
        )
        
        # Phase 3: 15-minute live market data polling loop
        scheduler.add_job(
            update_and_cache_snapshot,
            IntervalTrigger(minutes=15),
            id="update_and_cache_snapshot",
            name="Fetch live market snapshot and inject to RAG",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("APScheduler started with daily, hourly, and 15-minute jobs.")
