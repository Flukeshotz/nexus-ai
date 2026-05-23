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

    logger.info("🎉 Seeding Complete! The platform is now fully populated and ready for demo.")

if __name__ == "__main__":
    asyncio.run(seed_data())
