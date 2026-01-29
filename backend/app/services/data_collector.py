import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

class DataCollector:
    @staticmethod
    async def fetch_stock_data(ticker: str, period="1mo", interval="1d"):
        """
        Fetches historical market data for a given ticker.
        """
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period, interval=interval)
        
        # Convert to list of dicts or standard format
        data = []
        for date, row in hist.iterrows():
            data.append({
                "timestamp": date,
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
                "volume": row["Volume"]
            })
        return data

    @staticmethod
    async def fetch_company_info(ticker: str):
        """
        Fetches company metadata and key financial metrics.
        """
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "name": info.get("shortName") or info.get("longName"),
            "sector": info.get("sector"),
            "market_cap": info.get("marketCap"),
            "summary": info.get("longBusinessSummary"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "previous_close": info.get("regularMarketPreviousClose"),
            "pe_ratio": info.get("forwardPE") or info.get("trailingPE"),
            "profit_margin": info.get("profitMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "bid": info.get("bid"),
            "ask": info.get("ask"),
            "volume": info.get("regularMarketVolume")
        }

    @staticmethod
    async def fetch_news(ticker: str):
        """
        Fetches news for a given ticker.
        Uses yfinance news if available, or mocks it.
        """
        stock = yf.Ticker(ticker)
        news_items = stock.news
        
        formatted_news = []
        if news_items:
            for item in news_items:
                # Handle new yfinance structure (nested in 'content')
                content = item.get('content', {})
                title = item.get("title") or content.get("title")
                
                if not title:
                    continue
                
                # Extract URL
                url = item.get("link")
                if not url:
                    canonical = content.get("canonicalUrl", {})
                    if canonical:
                        url = canonical.get("url")
                    if not url:
                        click_through = content.get("clickThroughUrl", {})
                        if click_through:
                            url = click_through.get("url")

                # Extract Publisher
                publisher = item.get("publisher")
                if not publisher:
                     provider = content.get("provider", {})
                     publisher = provider.get("displayName")
                
                # Extract Time
                pub_time = item.get("providerPublishTime")
                if pub_time:
                    published_at = datetime.fromtimestamp(pub_time)
                else:
                    pub_date_str = content.get("pubDate")
                    if pub_date_str:
                        try:
                            # Handle ISO format '2026-01-28T14:39:47Z'
                            published_at = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                        except ValueError:
                            published_at = datetime.now()
                    else:
                        published_at = datetime.now()

                formatted_news.append({
                    "headline": title,
                    "url": url or "#",
                    "published_at": published_at,
                    "publisher": publisher or "Unknown"
                })
        else:
            # Fallback/Mock for demonstration if yfinance API changes or is empty
            formatted_news = [
                {
                    "headline": f"{ticker} expected to beat earnings estimates",
                    "url": "#",
                    "published_at": datetime.now(),
                    "publisher": "Mock News"
                },
                {
                    "headline": f"Analysts upgrade {ticker} to Buy",
                    "url": "#",
                    "published_at": datetime.now() - timedelta(hours=5),
                    "publisher": "Mock News"
                }
            ]
            
        return formatted_news
