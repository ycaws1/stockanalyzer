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

@router.get("/overview")
async def get_stocks_overview(interval: str = "1h", db: AsyncSession = Depends(get_db)):
    """Get all cached analysis for all stocks in watchlist based on interval (1d or 1h)"""
    import json
    result = await db.execute(select(Stock))
    stocks = result.scalars().all()
    
    overview = []
    for s in stocks:
        if s.cached_analysis:
            try:
                data = json.loads(s.cached_analysis)
                # Check if data is in new format (dict with keys '1d', '1h')
                if isinstance(data, dict):
                    if interval in data and isinstance(data[interval], dict):
                        overview.append(data[interval])
                    elif "1d" not in data and "1h" not in data and interval == "1d":
                        # Legacy format (flat object), assume it's 1d data
                        overview.append(data)
            except:
                continue
    return overview

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
        if not info:
             info = {}
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
async def get_stock_analysis(ticker: str, interval: str = "1h", db: AsyncSession = Depends(get_db)):
    try:
        # Determine fetch parameters based on requested interval
        if interval == "1h":
            fetch_period = "5d"
            fetch_interval = "1h"
        else:
            fetch_period = "1mo"
            fetch_interval = "1d"

        # Check Cache First
        stmt = select(Stock).where(Stock.ticker == ticker)
        result = await db.execute(stmt)
        stock = result.scalars().first()
        
        # Check if we have valid cached data for this interval
        import json
        cached_registry = {}
        if stock and stock.cached_analysis:
            try:
                cached_registry = json.loads(stock.cached_analysis)
                # If registry is old flat format, wrap it in '1d' to migrate structure eventually
                if "1d" not in cached_registry and "1h" not in cached_registry:
                     cached_registry = {"1d": cached_registry}
                
                # Check if specific interval data is present
                if interval in cached_registry:
                    return cached_registry[interval]
            except:
                cached_registry = {}

        # Fetch data concurrently (Fallback) - We fetch BOTH 1h and 1d to populate cache fully
        news, history_1h, history_1d, info = await asyncio.gather(
            DataCollector.fetch_news(ticker),
            DataCollector.fetch_stock_data(ticker, period="5d", interval="1h"),
            DataCollector.fetch_stock_data(ticker, period="1mo", interval="1d"),
            DataCollector.fetch_company_info(ticker)
        )
        
        # Helper to generate analysis for a specific history dataset
        def generate_analysis(hist, interval_label):
            # Analyze Technicals
            technicals = Analyzer.calculate_technicals(hist)
            
            # Analyze Sentiment (common for both)
            sentiment_scores = []
            for item in news:
                # Use cached sentiment if available to avoid re-analyzing? 
                # Analyzer is fast enough, let's just re-run or better yet, run once outside.
                pass
                
            # ...
            return {}

        # Analyze Sentiment ONCE (Shared)
        sentiment_scores = []
        for item in news:
            score = Analyzer.analyze_sentiment(item['headline'])
            item['sentiment_score'] = score
            sentiment_scores.append(score)
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        sentiment_data = Analyzer.calculate_sentiment_score(avg_sentiment) # We can reuse this too if we want

        # Prepare Serializable News ONCE
        serializable_news = []
        for item in news:
            news_item = dict(item)
            if 'published_at' in news_item and hasattr(news_item['published_at'], 'isoformat'):
                news_item['published_at'] = news_item['published_at'].isoformat()
            serializable_news.append(news_item)

        # Function to build analysis object
        def build_analysis_response(hist, intv):
            # Technicals
            technicals = Analyzer.calculate_technicals(hist)
            # Composite
            comp_score = Analyzer.calculate_composite_score(hist, avg_sentiment, info)
            
            # Price & Change
            current_price = info.get("current_price")
            change_percent = 0
            
            if intv == "1h":
                 if hist and len(hist) >= 2:
                    latest = hist[-1]["close"]
                    prev = hist[-2]["close"]
                    if prev and prev != 0:
                        change_percent = ((latest - prev) / prev) * 100
                    current_price = latest
            else: # 1d
                prev_close = info.get("previous_close")
                if current_price and prev_close:
                    change_percent = ((current_price - prev_close) / prev_close) * 100
                elif hist and len(hist) >= 2:
                    latest = hist[-1]["close"]
                    prev = hist[-2]["close"]
                    change_percent = ((latest - prev) / prev) * 100
                    if not current_price:
                        current_price = latest
            
            return {
                "ticker": ticker,
                "period": intv,
                "price": current_price or 0,
                "change_percent": change_percent,
                "average_sentiment": avg_sentiment,
                "sentiment_label": "Bullish" if change_percent > 0.1 else "Bearish" if change_percent < -0.1 else "Neutral",
                "technicals": technicals,
                "company_info": info,
                "news": serializable_news,
                "score": comp_score["composite_score"],
                "score_breakdown": {
                    "technical": comp_score["technical"]["score"],
                    "sentiment": comp_score["sentiment"]["score"],
                    "financial": comp_score["financial"]["score"]
                },
                "score_details": comp_score
            }

        # Build both responses
        response_1h = build_analysis_response(history_1h, "1h")
        response_1d = build_analysis_response(history_1d, "1d")
        
        # Update Cache Registry
        cached_registry["1h"] = response_1h
        cached_registry["1d"] = response_1d
        
        if stock:
            import json
            from datetime import datetime
            stock.cached_analysis = json.dumps(cached_registry)
            stock.last_updated = datetime.now()
            await db.commit()

        # Return the one requested
        return cached_registry.get(interval, response_1d)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
