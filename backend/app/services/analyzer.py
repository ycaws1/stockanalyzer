from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd

class Analyzer:
    _vader_analyzer = None
    
    # Financial sentiment keywords
    POSITIVE_KEYWORDS = {
        'beat', 'beats', 'surge', 'surges', 'gain', 'gains', 'rise', 'rises', 'rising',
        'growth', 'profit', 'profits', 'up', 'high', 'higher', 'bullish', 'buy',
        'upgrade', 'upgrades', 'outperform', 'record', 'strong', 'positive',
        'boost', 'boosts', 'rally', 'rallies', 'soar', 'soars', 'jump', 'jumps',
        'exceed', 'exceeds', 'exceeded', 'breakout', 'momentum'
    }
    
    NEGATIVE_KEYWORDS = {
        'miss', 'misses', 'fall', 'falls', 'drop', 'drops', 'decline', 'declines',
        'loss', 'losses', 'down', 'low', 'lower', 'bearish', 'sell',
        'downgrade', 'downgrades', 'underperform', 'weak', 'negative',
        'crash', 'crashes', 'plunge', 'plunges', 'sink', 'sinks', 'slump',
        'warning', 'warns', 'cut', 'cuts', 'layoff', 'layoffs', 'bankruptcy'
    }

    @classmethod
    def get_analyzer(cls):
        """
        Lazy-loads the VADER sentiment analyzer.
        """
        if cls._vader_analyzer is None:
            cls._vader_analyzer = SentimentIntensityAnalyzer()
        return cls._vader_analyzer

    @staticmethod
    def analyze_sentiment(text: str) -> float:
        """
        Returns a sentiment polarity score between -1.0 (negative) and 1.0 (positive).
        Combines VADER sentiment with financial keyword matching.
        """
        if not text or len(text.strip()) == 0:
            return 0.0
            
        try:
            analyzer = Analyzer.get_analyzer()
            # Get VADER compound score (-1 to 1)
            scores = analyzer.polarity_scores(text)
            vader_score = float(scores['compound'])
            
            # Keyword-based adjustment for financial context
            text_lower = text.lower()
            words = set(text_lower.split())
            
            keyword_score = 0.0
            pos_matches = words.intersection(Analyzer.POSITIVE_KEYWORDS)
            neg_matches = words.intersection(Analyzer.NEGATIVE_KEYWORDS)
            
            # Each keyword contributes a small bonus/penalty
            keyword_score += len(pos_matches) * 0.15
            keyword_score -= len(neg_matches) * 0.15
            
            # Combine: VADER (70%) + Keywords (30%)
            combined_score = (vader_score * 0.7) + (keyword_score * 0.3)
            
            # Clamp to valid range
            return max(-1.0, min(1.0, combined_score))
            
        except Exception as e:
            print(f"Sentiment analysis error: {e}")
            return 0.0

    @staticmethod
    def calculate_technicals(prices_data: list):
        """
        Calculates basic technical indicators: SMA, RSI.
        Expects a list of dicts with 'close' price.
        """
        if not prices_data:
            return {}
            
        df = pd.DataFrame(prices_data)
        
        # Ensure close is float
        df['close'] = df['close'].astype(float)
        
        # Simple Moving Average (SMA)
        df['sma_20'] = df['close'].rolling(window=20).mean()
        
        # RSI Calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Get latest values (handle NaN)
        latest = df.iloc[-1]
        
        return {
            "sma_20": None if pd.isna(latest['sma_20']) else latest['sma_20'],
            "rsi": None if pd.isna(latest['rsi']) else latest['rsi']
        }

    @staticmethod
    def calculate_technical_score(prices_data: list) -> dict:
        """
        Calculate technical score (0-100) based on RSI, SMA, and momentum.
        Returns dict with score and breakdown.
        """
        if not prices_data or len(prices_data) < 20:
            return {"score": 50, "breakdown": {}, "signals": []}
        
        df = pd.DataFrame(prices_data)
        df['close'] = df['close'].astype(float)
        
        # Calculate indicators
        df['sma_20'] = df['close'].rolling(window=20).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        latest = df.iloc[-1]
        current_price = latest['close']
        sma_20 = latest['sma_20']
        rsi = latest['rsi']
        
        # RSI Score (0-100)
        # RSI < 30 = oversold (bullish) = high score
        # RSI > 70 = overbought (bearish) = low score
        # RSI 50 = neutral = 50
        if pd.isna(rsi):
            rsi_score = 50
        elif rsi < 30:
            # Oversold (Potential Bounce) - Score 70-100
            rsi_score = 70 + (30 - rsi)
        elif rsi > 70:
            # Overbought (Strong Trend but Risky) - Score 50-70
            # Previously was 0-30, now we gently taper down from 70
            rsi_score = max(0, 70 - (rsi - 70)) 
        else:
            # Neutral/Trend (30-70) - Score matches RSI
            rsi_score = rsi
        
        # SMA Score (0-100)
        # Price above SMA = bullish = 60-100
        # Price below SMA = bearish = 0-40
        if pd.isna(sma_20):
            sma_score = 50
        else:
            price_distance = ((current_price - sma_20) / sma_20) * 100
            if price_distance > 0:
                # Above SMA - bullish
                sma_score = 50 + min(price_distance * 5, 50)  # Cap at 100
            else:
                # Below SMA - bearish
                sma_score = 50 + max(price_distance * 5, -50)  # Floor at 0
        
        # Momentum Score (0-100) - based on recent price change
        if len(df) >= 5:
            price_5d_ago = df.iloc[-6]['close']
            momentum_change = ((current_price - price_5d_ago) / price_5d_ago) * 100
            # -10% to +10% change maps to 0-100
            momentum_score = 50 + (momentum_change * 5)
            momentum_score = max(0, min(100, momentum_score))
        else:
            momentum_score = 50
        
        # Weighted average: RSI 40%, SMA 40%, Momentum 20%
        technical_score = (rsi_score * 0.4) + (sma_score * 0.4) + (momentum_score * 0.2)
        technical_score = max(0, min(100, round(technical_score)))
        
        return {
            "score": technical_score,
            "breakdown": {
                "rsi_score": round(rsi_score, 1),
                "sma_score": round(sma_score, 1),
                "momentum_score": round(momentum_score, 1)
            },
            "signals": {
                "rsi": round(rsi, 1) if not pd.isna(rsi) else None,
                "price_vs_sma": round(((current_price - sma_20) / sma_20) * 100, 2) if not pd.isna(sma_20) else None,
                "momentum_5d": round(momentum_change, 2) if len(df) >= 5 else None
            }
        }

    @staticmethod
    def calculate_sentiment_score(avg_sentiment: float) -> dict:
        """
        Convert sentiment (-1 to +1) to 0-100 score with breakdown.
        """
        score = round((avg_sentiment + 1) * 50)
        
        return {
            "score": score,
            "breakdown": {
                "raw_sentiment": round(avg_sentiment, 3)
            },
            "signals": {
                "label": "Bullish" if avg_sentiment > 0.1 else "Bearish" if avg_sentiment < -0.1 else "Neutral"
            }
        }

    @staticmethod
    def calculate_financial_score(company_info: dict) -> dict:
        """
        Calculate financial score (0-100) based on fundamental metrics.
        """
        if not company_info:
            return {"score": 50, "breakdown": {}, "signals": {}}
        
        scores = []
        breakdown = {}
        signals = {}
        
        # P/E Ratio Score (if available)
        pe_ratio = company_info.get('pe_ratio')
        if pe_ratio and pe_ratio > 0:
            # Lower P/E is better (value stock)
            # 0-15 = great (100), 15-25 = good (70), 25-35 = fair (50), 35+ = expensive (30)
            if pe_ratio < 15:
                pe_score = 100
            elif pe_ratio < 25:
                pe_score = 70 + (15 - pe_ratio) * 3
            elif pe_ratio < 35:
                pe_score = 50 + (25 - pe_ratio) * 2
            else:
                pe_score = max(30, 50 - (pe_ratio - 35))
            scores.append(pe_score)
            breakdown['pe_score'] = round(pe_score, 1)
            signals['pe_ratio'] = round(pe_ratio, 2)
        
        # Market Cap Score (stability indicator)
        market_cap = company_info.get('market_cap')
        if market_cap:
            # Larger cap = more stable = higher score
            if market_cap > 200e9:  # > $200B = mega cap
                cap_score = 90
            elif market_cap > 10e9:  # > $10B = large cap
                cap_score = 75
            elif market_cap > 2e9:  # > $2B = mid cap
                cap_score = 60
            else:  # < $2B = small cap
                cap_score = 45
            scores.append(cap_score)
            breakdown['market_cap_score'] = round(cap_score, 1)
            signals['market_cap_billion'] = round(market_cap / 1e9, 2)
        
        # Profit Margin Score
        profit_margin = company_info.get('profit_margin')
        if profit_margin:
            # Higher margin = better
            # 0.20+ = excellent (100), 0.10-0.20 = good (70), 0.05-0.10 = fair (50), <0.05 = poor (30)
            if profit_margin > 0.20:
                margin_score = 100
            elif profit_margin > 0.10:
                margin_score = 70 + (profit_margin - 0.10) * 300
            elif profit_margin > 0.05:
                margin_score = 50 + (profit_margin - 0.05) * 400
            else:
                margin_score = max(20, 50 + profit_margin * 600)
            scores.append(margin_score)
            breakdown['profit_margin_score'] = round(margin_score, 1)
            signals['profit_margin_pct'] = round(profit_margin * 100, 2)
        
        # Revenue Growth Score
        revenue_growth = company_info.get('revenue_growth')
        if revenue_growth:
            # Higher growth = better
            # 20%+ = excellent (100), 10-20% = good (75), 0-10% = fair (50), negative = poor (25)
            if revenue_growth > 0.20:
                growth_score = 100
            elif revenue_growth > 0.10:
                growth_score = 75 + (revenue_growth - 0.10) * 250
            elif revenue_growth > 0:
                growth_score = 50 + revenue_growth * 250
            else:
                growth_score = max(10, 50 + revenue_growth * 200)
            scores.append(growth_score)
            breakdown['revenue_growth_score'] = round(growth_score, 1)
            signals['revenue_growth_pct'] = round(revenue_growth * 100, 2)
        
        # Calculate average of available scores
        if scores:
            financial_score = round(sum(scores) / len(scores))
        else:
            financial_score = 50  # Neutral if no data
        
        return {
            "score": financial_score,
            "breakdown": breakdown,
            "signals": signals
        }

    @staticmethod
    def calculate_composite_score(prices_data: list, avg_sentiment: float, company_info: dict) -> dict:
        """
        Calculate composite score combining technical, sentiment, and financial factors.
        Weights: Technical 40%, Financial 40%, Sentiment 20%
        """
        technical = Analyzer.calculate_technical_score(prices_data)
        sentiment = Analyzer.calculate_sentiment_score(avg_sentiment)
        financial = Analyzer.calculate_financial_score(company_info)
        
        # Weighted composite score
        composite_score = round(
            (technical['score'] * 0.40) +
            (financial['score'] * 0.40) +
            (sentiment['score'] * 0.20)
        )
        
        return {
            "composite_score": composite_score,
            "technical": technical,
            "sentiment": sentiment,
            "financial": financial,
            "weights": {
                "technical": 0.40,
                "financial": 0.40,
                "sentiment": 0.20
            }
        }
