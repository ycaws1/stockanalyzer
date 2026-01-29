from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import stocks, backtest, live_trade

from contextlib import asynccontextmanager
import asyncio
from .services.cache_manager import CacheManager
from .database import engine
from sqlalchemy import text
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Check DB & Start Scheduler
    
    # Simple migration check (Add columns if missing for SQLite/PG)
    # Note: In production, use Alembic. This is a quick fix for local usage.
    async with engine.begin() as conn:
        try:
            # Attempt to query the new column to see if it exists
            await conn.execute(text("SELECT cached_analysis FROM stocks LIMIT 1"))
        except Exception:
            # Column likely missing, add it
            print("Adding missing columns to 'stocks' table...")
            try:
                await conn.execute(text("ALTER TABLE stocks ADD COLUMN cached_analysis TEXT"))
                await conn.execute(text("ALTER TABLE stocks ADD COLUMN last_updated TIMESTAMP"))
            except Exception as e:
                print(f"Migration warning: {e}")

    # Start Background Task
    interval_minutes = os.getenv('CACHE_INTERVAL_MINUTES', 5)
    task = asyncio.create_task(CacheManager.start_scheduler(interval_minutes=interval_minutes))
    
    yield
    
    # Shutdown
    task.cancel()

app = FastAPI(title="Stock Analyzer API", lifespan=lifespan)

# Configure CORS
cors_origins = os.getenv('CORS_ORIGINS', "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router)
app.include_router(backtest.router)
app.include_router(live_trade.router)

@app.get("/")
async def root():
    return {"message": "Stock Analyzer API is running"}
