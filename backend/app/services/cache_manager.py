import asyncio
import json
from datetime import datetime, timedelta
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import AsyncSessionLocal
from ..models import Stock
from .data_collector import DataCollector
from .analyzer import Analyzer
from .push_notifications import PushNotificationService

class CacheManager:
    @staticmethod
    async def update_stock_cache(stock_ticker: str, db: AsyncSession):
        try:
            # Fetch both 1h and 1d data for accurate change detection
            news, history_1h, history_1d, info = await asyncio.gather(
                DataCollector.fetch_news(stock_ticker),
                DataCollector.fetch_stock_data(stock_ticker, period="5d", interval="1h"),
                DataCollector.fetch_stock_data(stock_ticker, period="1mo", interval="1d"),
                DataCollector.fetch_company_info(stock_ticker)
            )

            # Analyze Sentiment
            sentiment_scores = []
            for item in news:
                score = Analyzer.analyze_sentiment(item['headline'])
                item['sentiment_score'] = score
                sentiment_scores.append(score)
            
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            # Analyze Technicals (use 1d data for technicals)
            technicals = Analyzer.calculate_technicals(history_1d)
            
            # Calculate Composite Score
            composite_score_data = Analyzer.calculate_composite_score(history_1d, avg_sentiment, info)
            
            # Prepare serializable news
            serializable_news = []
            for item in news:
                news_item = dict(item)
                if 'published_at' in news_item and hasattr(news_item['published_at'], 'isoformat'):
                    news_item['published_at'] = news_item['published_at'].isoformat()
                serializable_news.append(news_item)
            
            # Calculate price and change percent for 1D
            current_price = info.get("current_price")
            prev_close = info.get("previous_close")
            change_percent_1d = 0
            if current_price and prev_close:
                change_percent_1d = ((current_price - prev_close) / prev_close) * 100
            elif history_1d and len(history_1d) >= 2:
                latest = history_1d[-1]["close"]
                prev = history_1d[-2]["close"]
                change_percent_1d = ((latest - prev) / prev) * 100
                if not current_price:
                    current_price = latest
            
            # Calculate 1H change percent
            change_percent_1h = 0
            if history_1h and len(history_1h) >= 2:
                latest_1h = history_1h[-1]["close"]
                prev_1h = history_1h[-2]["close"]
                change_percent_1h = ((latest_1h - prev_1h) / prev_1h) * 100

            # Construct Analysis Object (using 1d change as default)
            analysis_data = {
                "ticker": stock_ticker,
                "price": current_price or 0,
                "change_percent": change_percent_1d,
                "change_percent_1h": change_percent_1h,
                "change_percent_1d": change_percent_1d,
                "average_sentiment": avg_sentiment,
                "sentiment_label": "Bullish" if composite_score_data["technical"]["score"] > 60 else "Bearish" if composite_score_data["technical"]["score"] < 40 else "Neutral",
                "technicals": technicals,
                "company_info": info,
                "news": serializable_news,
                "score": composite_score_data["composite_score"],
                "score_breakdown": {
                    "technical": composite_score_data["technical"]["score"],
                    "sentiment": composite_score_data["sentiment"]["score"],
                    "financial": composite_score_data["financial"]["score"]
                },
                "score_details": composite_score_data
            }
            
            # Get the latest data timestamp for strict deduplication
            latest_ts = None
            if history_1h and len(history_1h) > 0:
                latest_ts = history_1h[-1].get("timestamp")

            # Check for push notification trigger
            await PushNotificationService.check_and_notify(
                ticker=stock_ticker,
                change_1h=change_percent_1h,
                change_1d=change_percent_1d,
                data_timestamp=latest_ts
            )
            
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
        # Convert interval_minutes to int in case it comes from env as string
        interval_minutes = int(interval_minutes)
        while True:
            await CacheManager.update_all_stocks()
            next_update = datetime.now() + timedelta(minutes=interval_minutes)
            print(f"Next cache update scheduled for: {next_update.strftime('%Y-%m-%d %H:%M:%S')}")
            await asyncio.sleep(interval_minutes * 60)
