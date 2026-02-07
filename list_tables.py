
import asyncio
from backend.app.database import engine
from sqlalchemy import text

async def list_tables():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"))
        tables = res.fetchall()
        print("Tables in database:")
        for t in tables:
            print(f"- {t[0]}")

if __name__ == "__main__":
    asyncio.run(list_tables())
