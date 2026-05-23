import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path to allow app module imports
sys.path.append(str(Path(__file__).parent))

from app.core.database import engine, Base
from app.models import *

async def init_db():
    print("Initializing SQLite Database...")
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialization complete! Created nexus.db")

if __name__ == "__main__":
    asyncio.run(init_db())
