from fastapi import APIRouter, HTTPException
from ..services.backtester import Backtester

from pydantic import BaseModel
from typing import Optional

router = APIRouter(
    prefix="/backtest",
    tags=["backtest"]
)

class BacktestRequest(BaseModel):
    ticker: str
    initial_capital: float = 10000.0
    period: str = "1y"
    strategy: str = "SMA"
    parameters: Optional[dict] = {}

@router.post("/")
async def backtest_stock(request: BacktestRequest):
    try:
        result = await Backtester.run_backtest(
            ticker=request.ticker, 
            initial_capital=request.initial_capital, 
            period=request.period,
            strategy=request.strategy,
            parameters=request.parameters
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
