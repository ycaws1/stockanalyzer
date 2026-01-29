import asyncio
import json
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import AsyncSessionLocal
from ..models import Stock
from .data_collector import DataCollector
from .analyzer import Analyzer

class CacheManager:
    @staticmethod
    async def update_stock_cache(stock_ticker: str, db: AsyncSession):
        try:
            # Re-use the data fetching logic from routers/stocks.py
            news, history, info = await asyncio.gather(
                DataCollector.fetch_news(stock_ticker),
                DataCollector.fetch_stock_data(stock_ticker, period="1mo"),
                DataCollector.fetch_company_info(stock_ticker)
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
            
            # Prepare serializable news
            serializable_news = []
            for item in news:
                news_item = dict(item)
                if 'published_at' in news_item and hasattr(news_item['published_at'], 'isoformat'):
                    news_item['published_at'] = news_item['published_at'].isoformat()
                serializable_news.append(news_item)
            
            # Construct Analysis Object
            analysis_data = {
                "ticker": stock_ticker,
                "average_sentiment": avg_sentiment,
                "sentiment_label": "Bullish" if avg_sentiment > 0.1 else "Bearish" if avg_sentiment < -0.1 else "Neutral",
                "technicals": technicals,
                "company_info": info,
                "news": serializable_news
            }
            
            # Update DB
            result = await db.execute(select(Stock).where(Stock.ticker == stock_ticker))
            stock = result.scalars().first()
            if stock:
                stock.cached_analysis = json.dumps(analysis_data)
                stock.last_updated = datetime.now()
                await db.commit()
                print(f"Updated cache for {stock_ticker}")
            
        except Exception as e:
            print(f"Error updating cache for {stock_ticker}: {e}")

    @staticmethod
    async def update_all_stocks():
        print("Starting background cache update...")
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Stock))
            stocks = result.scalars().all()
            
            for stock in stocks:
                await CacheManager.update_stock_cache(stock.ticker, db)
                # Sleep briefly to avoid rate limits
                await asyncio.sleep(2) 
        print("Finished background cache update.")

    @staticmethod
    async def start_scheduler(interval_minutes=5):
        while True:
            await CacheManager.update_all_stocks()
            await asyncio.sleep(interval_minutes * 60)
