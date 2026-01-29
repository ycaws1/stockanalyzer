from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import stocks, backtest, live_trade

from contextlib import asynccontextmanager
import asyncio
from .services.cache_manager import CacheManager
from .database import engine
from sqlalchemy import text
from .models import Base
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
