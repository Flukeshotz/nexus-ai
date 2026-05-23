import asyncio
import logging
import os
import sys

# Add backend directory to path so imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, Base
from app.services.market_data_service import fetch_batch_stock_data, fetch_amfi_navs
from app.services.news_service import fetch_news_from_feeds
from app.services.rag_service import get_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_data():
    logger.info("🌱 Starting Database Seed Process...")
    
    # 1. Initialize Tables
    logger.info("1. Creating database tables if they don't exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables ready.")

    # 2. Fetch Market Data (6 months history for demo)
    logger.info("2. Fetching 6 months of historical NSE/BSE market data...")
    # fetch_batch_stock_data defaults to 365 days if period is not specified
    # but we can pass period_days=180
    stock_data = fetch_batch_stock_data(period_days=180)
    logger.info(f"✅ Fetched {stock_data['total_tickers']} tickers. Anomalies: {stock_data['total_anomalies']}")

    # 3. Fetch AMFI NAVs
    logger.info("3. Fetching Mutual Fund NAVs from AMFI...")
    nav_data = fetch_amfi_navs()
    logger.info(f"✅ Fetched {nav_data.get('total_funds', 0)} mutual fund NAVs.")

    # 4. Fetch News & Vectorize (FAISS RAG)
    logger.info("4. Fetching financial news and embedding into FAISS Vector DB...")
    try:
        news_data = await fetch_news_from_feeds()
        articles = news_data.get("articles", [])
        if articles:
            texts = [a["title"] + ". " + a.get("content", "") for a in articles]
            metadatas = [{"url": a.get("url", ""), "source": a.get("source", ""), "published_at": a.get("published_at", "")} for a in articles]
            store = get_vector_store()
            store.add_documents(texts, metadatas)
            logger.info(f"✅ FAISS RAG Index populated with {len(articles)} articles.")
        else:
            logger.warning("No news articles fetched.")
    except Exception as e:
        logger.error(f"Failed to populate FAISS: {e}")

    # 5. Create Deterministic Demo Portfolio
    logger.info("5. Creating deterministic Demo User and Portfolio...")
    from app.models.user import User
    from app.models.investor_profile import InvestorProfile, RiskAppetite, InvestmentHorizon, DomesticInternational
    from app.models.holding import Holding
    from sqlalchemy import select
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async with engine.begin() as conn:
        from sqlalchemy.ext.asyncio import AsyncSession
        async with AsyncSession(engine) as session:
            # Check if user exists
            stmt = select(User).where(User.email == "demo@nexusai.com")
            result = await session.execute(stmt)
            demo_user = result.scalar_one_or_none()

            if not demo_user:
                logger.info("   Creating 'demo@nexusai.com'...")
                demo_user = User(
                    email="demo@nexusai.com",
                    password_hash=pwd_context.hash("demo123"),
                    full_name="Demo Investor"
                )
                session.add(demo_user)
                await session.flush()

                logger.info("   Creating Investor Profile...")
                profile = InvestorProfile(
                    user_id=demo_user.id,
                    age=32,
                    occupation="Product Manager",
                    monthly_income=250000,
                    monthly_expenses=100000,
                    monthly_investment_amount=50000,
                    risk_appetite=RiskAppetite.AGGRESSIVE,
                    investment_horizon=InvestmentHorizon.LONG_TERM,
                    financial_goals=["wealth_accumulation", "fire"],
                    domestic_vs_international=DomesticInternational.BOTH
                )
                session.add(profile)

                logger.info("   Creating Stable Portfolio Holdings...")
                # Tech Heavy, some Gold, some Bonds
                holdings = [
                    Holding(user_id=demo_user.id, asset_ticker="RELIANCE.NS", asset_name="Reliance Ind", asset_class="Equity", quantity=50, average_buy_price=2400.0),
                    Holding(user_id=demo_user.id, asset_ticker="TCS.NS", asset_name="TCS", asset_class="Equity", quantity=20, average_buy_price=3800.0),
                    Holding(user_id=demo_user.id, asset_ticker="INFY.NS", asset_name="Infosys", asset_class="Equity", quantity=100, average_buy_price=1400.0),
                    Holding(user_id=demo_user.id, asset_ticker="GLD", asset_name="SPDR Gold Trust", asset_class="Commodity", quantity=10, average_buy_price=180.0),
                    Holding(user_id=demo_user.id, asset_ticker="TLT", asset_name="20+ Year Treasury", asset_class="Debt", quantity=25, average_buy_price=95.0)
                ]
                session.add_all(holdings)
                await session.commit()
                logger.info("✅ Demo User and Portfolio successfully injected.")
            else:
                logger.info("✅ Demo User already exists. Skipping user seed.")

    logger.info("🎉 Seeding Complete! The platform is now fully populated and ready for demo.")

if __name__ == "__main__":
    asyncio.run(seed_data())
