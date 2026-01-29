import json
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..database import get_db
from ..models import Simulation, SimulationTrade
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..services.data_collector import DataCollector
import pandas as pd

router = APIRouter(
    prefix="/live_trade",
    tags=["live_trade"]
)

class LiveTradeRequest(BaseModel):
    ticker: str
    strategy: str = "SMA"
    parameters: Optional[dict] = {}

class SimulationTradeSchema(BaseModel):
    type: str
    shares: int
    price: float
    timestamp: datetime
    balance_after: float

    class Config:
        from_attributes = True

@router.post("/start")
async def start_live_simulation(request: LiveTradeRequest, db: AsyncSession = Depends(get_db)):
    """
    Start/Reset a persistent background simulation for a ticker.
    """
    try:
        # Check for existing active simulation
        stmt = select(Simulation).where(Simulation.ticker == request.ticker, Simulation.is_active == True)
        result = await db.execute(stmt)
        sim = result.scalars().first()
        
        if not sim:
            sim = Simulation(
                ticker=request.ticker,
                strategy=request.strategy,
                parameters=json.dumps(request.parameters),
                balance=10000.0,
                initial_capital=10000.0,
                is_active=True
            )
            db.add(sim)
        else:
            # Re-initialize existing simulation
            sim.strategy = request.strategy
            sim.parameters = json.dumps(request.parameters)
            sim.balance = 10000.0
            sim.position = 0
            sim.start_time = datetime.utcnow()
            
        await db.commit()
        await db.refresh(sim)
        
        return {
            "message": "Simulation started",
            "simulation_id": sim.id,
            "ticker": sim.ticker,
            "balance": sim.balance
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop/{ticker}")
async def stop_live_simulation(ticker: str, db: AsyncSession = Depends(get_db)):
    """
    Deactivate a running simulation.
    """
    stmt = select(Simulation).where(Simulation.ticker == ticker, Simulation.is_active == True)
    result = await db.execute(stmt)
    sim = result.scalars().first()
    
    if not sim:
        raise HTTPException(status_code=404, detail="Active simulation not found")
        
    sim.is_active = False
    await db.commit()
    print(f"Simulation STOPPED for {ticker}")
    return {"message": "Simulation stopped", "ticker": ticker}

@router.get("/status/{ticker}")
async def get_live_status(ticker: str, db: AsyncSession = Depends(get_db)):
    """
    Get the current status of the persistent simulation including latest market data.
    """
    try:
        # Get simulation state
        stmt = select(Simulation).where(Simulation.ticker == ticker, Simulation.is_active == True)
        result = await db.execute(stmt)
        sim = result.scalars().first()
        
        if not sim:
            return {"active": False}

        # Fetch latest price
        data = await DataCollector.fetch_stock_data(ticker, period="1d", interval="1m")
        current_price = data[-1]['close'] if data else 0
        
        return {
            "active": True,
            "ticker": sim.ticker,
            "balance": sim.balance,
            "position": sim.position,
            "strategy": sim.strategy,
            "current_price": float(current_price),
            "total_value": float(sim.balance + (sim.position * current_price)),
            "last_updated": sim.last_run_time.isoformat() + ("Z" if not sim.last_run_time.tzinfo else "") if sim.last_run_time else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades/{ticker}", response_model=List[SimulationTradeSchema])
async def get_simulation_trades(ticker: str, db: AsyncSession = Depends(get_db)):
    """
    Get transaction history for the active simulation.
    """
    stmt = select(SimulationTrade).join(Simulation).where(
        Simulation.ticker == ticker, 
        Simulation.is_active == True
    ).order_by(SimulationTrade.timestamp.desc())
    
    result = await db.execute(stmt)
    return result.scalars().all()
