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

    # Start Background Tasks
    interval_minutes = os.getenv('CACHE_INTERVAL_MINUTES', 5)
    cache_task = asyncio.create_task(CacheManager.start_scheduler(interval_minutes=interval_minutes))
    
    from .services.simulation_manager import SimulationManager
    sim_task = asyncio.create_task(SimulationManager.start_scheduler(interval_minutes=1)) # Check simulations every minute
    
    yield
    
    # Shutdown
    cache_task.cancel()
    sim_task.cancel()

app = FastAPI(title="Stock Analyzer API", lifespan=lifespan)

# Configure CORS
cors_origins_raw = os.getenv('CORS_ORIGINS', "*")
cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
