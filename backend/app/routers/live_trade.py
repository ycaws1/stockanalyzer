from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..database import get_db
from ..models import Base
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..services.data_collector import DataCollector
from ..services.analyzer import Analyzer
import pandas as pd

router = APIRouter(
    prefix="/live_trade",
    tags=["live_trade"]
)

class LiveTradeRequest(BaseModel):
    ticker: str
    strategy: str = "SMA"
    parameters: Optional[dict] = {}

class TradeActionRequest(BaseModel):
    ticker: str
    action: str  # 'buy' or 'sell'
    shares: int
    price: float

@router.post("/start")
async def start_live_simulation(request: LiveTradeRequest):
    """
    Start a live trading simulation based on the selected strategy.
    Returns the current signal and recommendation.
    """
    try:
        # Fetch recent data (last 30 days for indicators)
        data = await DataCollector.fetch_stock_data(request.ticker, period="1mo", interval="1d")
        if not data:
            return {"error": "No data found"}
            
        df = pd.DataFrame(data)
        df['close'] = df['close'].astype(float)
        
        # Calculate indicators based on strategy
        signal = None
        indicator_value = None
        current_price = df.iloc[-1]['close']
        
        if request.strategy == "SMA":
            window = int(request.parameters.get("window", 20))
            df['sma'] = df['close'].rolling(window=window).mean()
            sma_value = df.iloc[-1]['sma']
            
            if current_price > sma_value:
                signal = "BUY"
            elif current_price < sma_value:
                signal = "SELL"
            else:
                signal = "HOLD"
                
            indicator_value = sma_value
            
        elif request.strategy == "RSI":
            period_len = int(request.parameters.get("period", 14))
            overbought = int(request.parameters.get("overbought", 70))
            oversold = int(request.parameters.get("oversold", 30))
            
            # RSI Calculation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period_len).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period_len).mean()
            
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            rsi_value = df.iloc[-1]['rsi']
            
            if rsi_value < oversold:
                signal = "BUY"
            elif rsi_value > overbought:
                signal = "SELL"
            else:
                signal = "HOLD"
                
            indicator_value = rsi_value
        
        return {
            "ticker": request.ticker,
            "strategy": request.strategy,
            "current_price": float(current_price),
            "indicator_value": float(indicator_value) if indicator_value and not pd.isna(indicator_value) else None,
            "signal": signal,
            "timestamp": datetime.now().isoformat(),
            "parameters": request.parameters
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{ticker}")
async def get_live_status(ticker: str):
    """
    Get the current live market status for a ticker.
    Returns current price and basic info.
    """
    try:
        # Fetch latest price
        data = await DataCollector.fetch_stock_data(ticker, period="1d", interval="1m")
        if not data:
            return {"error": "No data found"}
        
        current_price = data[-1]['close'] if data else None
        
        # Fetch company info
        info = await DataCollector.fetch_company_info(ticker)
        
        return {
            "ticker": ticker,
            "current_price": current_price,
            "company_name": info.get('name', ticker),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
