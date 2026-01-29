# Score Calculation Explanation

## Overview

The **Sentiment Score** displayed on each stock card is calculated using AI-powered sentiment analysis of recent news headlines. The score ranges from **0 to 100**, where:

- **0-40**: Bearish sentiment (negative news)
- **40-60**: Neutral sentiment (mixed or no strong signals)
- **60-100**: Bullish sentiment (positive news)

---

## How It Works

### 1. **News Collection**
The system fetches recent news articles for each stock ticker from various financial news sources using the Yahoo Finance API.

### 2. **Sentiment Analysis**
Each news headline is analyzed using **TextBlob**, a Natural Language Processing (NLP) library that performs sentiment analysis. TextBlob returns a polarity score:

- **-1.0**: Extremely negative sentiment
- **0.0**: Neutral sentiment
- **+1.0**: Extremely positive sentiment

**Example:**
```python
from textblob import TextBlob

headline = "Apple reports record-breaking quarterly earnings"
sentiment = TextBlob(headline).sentiment.polarity
# Returns: ~0.7 (positive)

headline = "Tesla stock plummets on production concerns"
sentiment = TextBlob(headline).sentiment.polarity
# Returns: ~-0.6 (negative)
```

### 3. **Average Sentiment Calculation**
All news headlines for a stock are analyzed, and the sentiment scores are averaged:

```python
sentiment_scores = [sentiment1, sentiment2, sentiment3, ...]
average_sentiment = sum(sentiment_scores) / len(sentiment_scores)
```

**Result:** A value between -1.0 and +1.0

### 4. **Conversion to 0-100 Scale**
The average sentiment is converted to a user-friendly 0-100 scale:

```python
score = round((average_sentiment + 1) * 50)
```

**Math:**
- If `average_sentiment = -1.0`: `score = (-1 + 1) * 50 = 0`
- If `average_sentiment = 0.0`: `score = (0 + 1) * 50 = 50`
- If `average_sentiment = +1.0`: `score = (1 + 1) * 50 = 100`

---

## Interpretation

### Score Ranges:
| Score Range | Label | Interpretation |
|-------------|-------|----------------|
| 0-30 | **Very Bearish** | Strongly negative news sentiment |
| 30-40 | **Bearish** | Moderately negative news sentiment |
| 40-60 | **Neutral** | Mixed or no strong signals |
| 60-70 | **Bullish** | Moderately positive news sentiment |
| 70-100 | **Very Bullish** | Strongly positive news sentiment |

### Sentiment Labels:
The system also assigns a simple label based on the average sentiment:
- **Bullish**: `average_sentiment > 0.1`
- **Bearish**: `average_sentiment < -0.1`
- **Neutral**: `-0.1 ≤ average_sentiment ≤ 0.1`

---

## Technical Implementation

### Backend (Python)

**File:** `/backend/app/services/analyzer.py`
```python
from textblob import TextBlob

class Analyzer:
    @staticmethod
    def analyze_sentiment(text: str) -> float:
        """
        Returns a sentiment polarity score between -1.0 and 1.0
        """
        blob = TextBlob(text)
        return blob.sentiment.polarity
```

**File:** `/backend/app/routers/stocks.py`
```python
# Analyze Sentiment for each news item
sentiment_scores = []
for item in news:
    score = Analyzer.analyze_sentiment(item['headline'])
    item['sentiment_score'] = score
    sentiment_scores.append(score)

# Calculate average
avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

# Determine label
sentiment_label = "Bullish" if avg_sentiment > 0.1 else "Bearish" if avg_sentiment < -0.1 else "Neutral"

response_data = {
    "average_sentiment": avg_sentiment,
    "sentiment_label": sentiment_label,
    ...
}
```

### Frontend (TypeScript)

**File:** `/frontend/components/Dashboard.tsx`
```typescript
// Convert to 0-100 scale
score: Math.round((data.average_sentiment + 1) * 50)
```

**File:** `/frontend/components/StockCard.tsx`
```tsx
{/* Display score with tooltip */}
<span>Score: <span className={styles.score}>{data.score}/100</span></span>
```

---

## Example Calculation

### Real Example:

**Stock:** AAPL (Apple Inc.)

**Recent Headlines:**
1. "Apple unveils groundbreaking new AI features" → Sentiment: +0.8
2. "iPhone sales exceed expectations in Q4" → Sentiment: +0.6
3. "Concerns over supply chain delays" → Sentiment: -0.4
4. "Apple stock reaches new all-time high" → Sentiment: +0.9
5. "Regulatory challenges in Europe" → Sentiment: -0.3

**Step 1:** Average Sentiment
```
average = (0.8 + 0.6 - 0.4 + 0.9 - 0.3) / 5 = 1.6 / 5 = 0.32
```

**Step 2:** Convert to 0-100 Scale
```
score = (0.32 + 1) * 50 = 1.32 * 50 = 66
```

**Step 3:** Label Determination
```
0.32 > 0.1 → Label: "Bullish"
```

**Result:**
- **Score:** 66/100
- **Label:** Bullish (displayed in green)

---

## Limitations & Considerations

### 1. **News Recency**
- The score is only as current as the latest news articles
- Older news may not reflect current market conditions

### 2. **NLP Accuracy**
- TextBlob provides basic sentiment analysis
- May not capture nuanced financial terminology or sarcasm
- More advanced models (FinBERT, Bloomberg GPT) could improve accuracy

### 3. **News Source Coverage**
- Limited to news available from the data provider
- May miss breaking news or niche sources

### 4. **Not Financial Advice**
- The score is purely sentiment-based
- Does not include fundamental analysis (P/E, revenue, etc.)
- Should be used alongside technical analysis and due diligence

---

## Future Enhancements

### Potential Improvements:
1. **Weighted Scoring**: Give more weight to recent news
2. **Source Credibility**: Weight articles from reputable sources higher
3. **Technical Integration**: Combine with RSI, SMA, MACD indicators
4. **Machine Learning**: Train custom models on financial news
5. **Real-time Updates**: Stream news and update scores live
6. **Historical Tracking**: Track sentiment score changes over time

### Combined Score Formula (Future):
```
Final Score = (0.5 × Sentiment Score) + (0.3 × Technical Score) + (0.2 × Momentum Score)
```

This would provide a more holistic view combining:
- **Sentiment Analysis** (news-based)
- **Technical Indicators** (price patterns)
- **Momentum** (volume and trend strength)

---

## Summary

The **Sentiment Score** is a simple, effective indicator that:
- ✅ Analyzes recent news headlines using AI
- ✅ Provides an easy-to-understand 0-100 scale
- ✅ Updates when new news articles are published
- ✅ Helps identify market sentiment at a glance

**Remember:** This is one tool among many. Always combine sentiment analysis with technical analysis, fundamental research, and your own judgment when making investment decisions.

---

## Code References

### Key Files:
- **Backend Analysis**: `/backend/app/services/analyzer.py`
- **API Endpoint**: `/backend/app/routers/stocks.py` (line 113-125)
- **Frontend Display**: `/frontend/components/Dashboard.tsx` (line 55)
- **Card Component**: `/frontend/components/StockCard.tsx` (line 70)

### Dependencies:
- **TextBlob**: Python NLP library for sentiment analysis
- **pandas**: Data manipulation for technical indicators
- **yfinance**: Stock data and news fetching
