from fastapi import APIRouter, HTTPException, Depends
import asyncio
from ..services.data_collector import DataCollector
from ..services.analyzer import Analyzer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..database import get_db
from ..models import Stock

router = APIRouter(
    prefix="/stocks",
    tags=["stocks"]
)

@router.get("/", response_model=list[dict])
async def list_stocks(db: AsyncSession = Depends(get_db)):
    """List all stocks in the watchlist"""
    result = await db.execute(select(Stock))
    stocks = result.scalars().all()
    return [{"ticker": s.ticker, "company_name": s.company_name, "sector": s.sector} for s in stocks]

@router.post("/", status_code=201)
async def add_stock(ticker: str, db: AsyncSession = Depends(get_db)):
    """Add a new stock to the watchlist"""
    ticker = ticker.upper()
    
    # Check if exists
    result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    existing = result.scalars().first()
    if existing:
        return {"message": f"Stock {ticker} already in watchlist"}
        
    # Fetch info
    try:
        info = await DataCollector.fetch_company_info(ticker)
        # Check if info is valid (some tickers might return None/Empty)
        if not info or not info.get('name'):
             # Fallback or allow minimal add
             pass
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {e}")

    new_stock = Stock(
        ticker=ticker,
        company_name=info.get('name', ticker),
        sector=info.get('sector', 'Unknown')
    )
    db.add(new_stock)
    await db.commit()
    await db.refresh(new_stock)
    return {"ticker": new_stock.ticker, "company_name": new_stock.company_name}

@router.delete("/{ticker}", status_code=204)
async def remove_stock(ticker: str, db: AsyncSession = Depends(get_db)):
    """Remove a stock from the watchlist"""
    ticker = ticker.upper()
    result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    stock = result.scalars().first()
    
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found in watchlist")
        
    await db.delete(stock)
    await db.commit()
    return None

@router.get("/{ticker}")
async def get_stock_info(ticker: str):
    try:
        info = await DataCollector.fetch_company_info(ticker)
        return info
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{ticker}/history")
async def get_stock_history(ticker: str, period: str = "1mo", interval: str = "1d"):
    try:
        data = await DataCollector.fetch_stock_data(ticker, period, interval)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/analysis")
async def get_stock_analysis(ticker: str, db: AsyncSession = Depends(get_db)):
    try:
        # Check Cache First
        stmt = select(Stock).where(Stock.ticker == ticker)
        result = await db.execute(stmt)
        stock = result.scalars().first()
        
        # If cached data exists, return it if it has the new composite score fields
        if stock and stock.cached_analysis:
             import json
             cached_data = json.loads(stock.cached_analysis)
             if "score_breakdown" in cached_data:
                 return cached_data
             # Otherwise, continue to re-analyze to generate the breakdown

        # Fetch data concurrently (Fallback)
        news, history, info = await asyncio.gather(
            DataCollector.fetch_news(ticker),
            DataCollector.fetch_stock_data(ticker, period="1mo"),
            DataCollector.fetch_company_info(ticker)
        )
        
        # Analyze Sentiment
        sentiment_scores = []
        for item in news:
            score = Analyzer.analyze_sentiment(item['headline'])
            item['sentiment_score'] = score
            sentiment_scores.append(score)
            
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        # Analyze Technicals
        technicals = Analyzer.calculate_technicals(history)
        
        # Calculate Composite Score
        composite_score_data = Analyzer.calculate_composite_score(history, avg_sentiment, info)
        
        # Prepare response data with serializable dates
        serializable_news = []
        for item in news:
            news_item = dict(item)
            if 'published_at' in news_item and hasattr(news_item['published_at'], 'isoformat'):
                news_item['published_at'] = news_item['published_at'].isoformat()
            serializable_news.append(news_item)
        
        response_data = {
            "ticker": ticker,
            "average_sentiment": avg_sentiment,
            "sentiment_label": "Bullish" if composite_score_data["technical"]["score"] > 60 else "Bearish" if composite_score_data["technical"]["score"] < 40 else "Neutral",
            "technicals": technicals,
            "company_info": info,
            "news": serializable_news,
            # New composite score data
            "score": composite_score_data["composite_score"],
            "score_breakdown": {
                "technical": composite_score_data["technical"]["score"],
                "sentiment": composite_score_data["sentiment"]["score"],
                "financial": composite_score_data["financial"]["score"]
            },
            "score_details": composite_score_data
        }

        # Save to Cache (if stock exists in DB)
        if stock:
            import json
            from datetime import datetime
            stock.cached_analysis = json.dumps(response_data)
            stock.last_updated = datetime.now()
            await db.commit()

        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
