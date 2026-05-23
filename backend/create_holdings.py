import asyncio
from app.core.database import engine
from app.models.holding import Holding

async def create_table():
    async with engine.begin() as conn:
        await conn.run_sync(Holding.metadata.create_all)
        
asyncio.run(create_table())
print("Table created")
