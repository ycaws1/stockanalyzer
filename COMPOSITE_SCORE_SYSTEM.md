# Composite Score System Documentation

## Overview

The stock analyzer now uses a **Composite Score** system that combines multiple data sources to provide a more comprehensive assessment of each stock. Instead of relying solely on sentiment analysis, the score now integrates:

1. **Technical Analysis** (40% weight)
2. **Financial Metrics** (40% weight)
3. **Sentiment Analysis** (20% weight)

```
Composite Score = (0.40 × Technical) + (0.40 × Financial) + (0.20 × Sentiment)
```

---

## Component Breakdowns

### 1. Technical Score (40% weight)

Analyzes price action and momentum using technical indicators.

**Components:**
- **RSI (Relative Strength Index)** - 40% of technical score
- **SMA (Simple Moving Average)** - 40% of technical score
- **5-Day Momentum** - 20% of technical score

**RSI Scoring:**
- RSI < 30 (Oversold): 70-100 points (bullish - stock may bounce)
- RSI 30-70 (Normal): 30-70 points (proportional)
- RSI > 70 (Overbought): 0-30 points (bearish - stock may correct)

**SMA Scoring:**
- Price > SMA: 60-100 points (bullish trend)
- Price = SMA: 50 points (neutral)
- Price < SMA: 0-40 points (bearish trend)

**Momentum Scoring:**
- +10% or more in 5 days: 100 points
- 0% to +10%: 50-100 points
- -10% to 0%: 0-50 points
- Below -10%: 0 points

---

### 2. Sentiment Score (20% weight)

Analyzes news sentiment using AI (TextBlob NLP).

**Process:**
1. Fetch recent news headlines
2. Analyze each with AI sentiment analysis
3. Average all sentiment scores
4. Convert from -1/+1 scale to 0-100

**Scoring:**
```python
score = (average_sentiment + 1) * 50
```

**Interpretation:**
- 70-100: Very positive news coverage
- 60-70: Positive news coverage
- 40-60: Neutral or mixed coverage
- 30-40: Negative news coverage
- 0-30: Very negative news coverage

---

### 3. Financial Score (40% weight)

Analyzes fundamental business metrics.

**Components (averaged):**

#### P/E Ratio (Price-to-Earnings)
Lower is generally better (value investing principle)
- P/E < 15: 100 points (great value)
- P/E 15-25: 70-100 points (good value)
- P/E 25-35: 50-70 points (fair value)
- P/E > 35: 30-50 points (expensive)

#### Market Cap (Company Size)
Larger = more stable
- > $200B (Mega Cap): 90 points
- > $10B (Large Cap): 75 points
- > $2B (Mid Cap): 60 points
- < $2B (Small Cap): 45 points

#### Profit Margin
Higher = more efficient
- > 20%: 100 points (excellent)
- 10-20%: 70-100 points (good)
- 5-10%: 50-70 points (fair)
- < 5%: 20-50 points (poor)

#### Revenue Growth (YoY)
Higher = faster growing
- > 20%: 100 points (hypergrowth)
- 10-20%: 75-100 points (strong growth)
- 0-10%: 50-75 points (moderate growth)
- < 0%: 10-50 points (declining)

**Note:** If any metric is unavailable, it's excluded from the average.

---

## Example Calculation

### Stock: AAPL (Apple Inc.)

#### Technical Analysis:
- RSI: 45 → RSI Score: 36
- Price vs SMA: +3% above → SMA Score: 65
- 5-Day Momentum: +2% → Momentum Score: 60
- **Technical Score = (36 × 0.4) + (65 × 0.4)+(60 × 0.2) = 52.4**

#### Sentiment Analysis:
- Average Sentiment: +0.32
- **Sentiment Score = (0.32 + 1) × 50 = 66**

#### Financial Metrics:
- P/E Ratio: 28 → 60 points
- Market Cap: $2.8T → 90 points
- Profit Margin: 25% → 95 points
- Revenue Growth: 8% → 70 points
- **Financial Score = (60 + 90 + 95 + 70) / 4 = 78.75**

#### Final Composite Score:
```
= (52.4 × 0.40) + (78.75 × 0.40) + (66 × 0.20)
= 20.96 + 31.50 + 13.20
= 65.66 ≈ 66/100
```

**Interpretation:** Moderately bullish - strong financials, positive sentiment, but neutral technical indicators.

---

## UI Display

### Collapsed View
- Shows composite score with **ⓘ** tooltip
- Tooltip explains: "Composite Score: Technical Analysis (40%), Financial Metrics (40%), AI Sentiment (20%)"

### Expanded View
Clicking the card shows detailed breakdown:
```
Score Breakdown:
📈 Technical:  52/100
💭 Sentiment:  66/100
💰 Financial:  79/100
```

---

## API Response Structure

```json
{
  "ticker": "AAPL",
  "score": 64,
  "score_breakdown": {
    "technical": 52,
    "sentiment": 66,
    "financial": 79
  },
  "score_details": {
    "composite_score": 64,
    "weights": {
      "technical": 0.40,
      "financial": 0.40,
      "sentiment": 0.20
    },
    "technical": {
      "score": 52,
      "breakdown": {
        "rsi_score": 36,
        "sma_score": 65,
        "momentum_score": 60
      },
      "signals": {
        "rsi": 45,
        "price_vs_sma": 3.2,
        "momentum_5d": 2.1
      }
    },
    "sentiment": {
      "score": 66,
      "breakdown": {
        "raw_sentiment": 0.32
      },
      "signals": {
        "label": "Bullish"
      }
    },
    "financial": {
      "score": 79,
      "breakdown": {
        "pe_score": 60,
        "market_cap_score": 90,
        "profit_margin_score": 95,
        "revenue_growth_score": 70
      },
      "signals": {
        "pe_ratio": 28,
        "market_cap_billion": 2800,
        "profit_margin_pct": 25,
        "revenue_growth_pct": 8
      }
    }
  }
}
```

---

## Code Architecture

### Backend (`/backend/app/services/analyzer.py`)

**Main Functions:**
```python
Analyzer.calculate_composite_score(prices_data, avg_sentiment, company_info)
    ├── calculate_technical_score(prices_data)
    ├── calculate_sentiment_score(avg_sentiment)
    └── calculate_financial_score(company_info)
```

### API Endpoint (`/backend/app/routers/stocks.py`)
```python
GET /stocks/{ticker}/analysis
```
Calls `Analyzer.calculate_composite_score()` and returns full breakdown.

### Frontend (`/frontend/components/`)
- **Dashboard.tsx**: Fetches and displays scores
- **StockCard.tsx**: Shows score with expandable breakdown

---

## Interpretation Guide

| Score Range | Rating | Interpretation |
|-------------|--------|----------------|
| 80-100 | **Excellent** | Strong across all metrics - buy signal |
| 60-79 | **Good** | Positive overall - consider buying |
| 40-59 | **Neutral** | Mixed signals - hold or research more |
| 20-39 | **Poor** | Negative indicators - consider selling |
| 0-19 | **Very Poor** | Strong sell signals |

---

## Advantages Over Sentiment-Only Score

### Old System (Sentiment Only):
- ❌ Ignored price trends
- ❌ Ignored company fundamentals
- ❌ Could be manipulated by news hype
- ❌ No context on valuation

### New System (Composite):
- ✅ Balanced view across multiple dimensions
- ✅ Catches divergences (e.g., positive news but weak technicals)
- ✅ Includes valuation metrics
- ✅ More robust against manipulation
- ✅ Provides actionable breakdown

---

## Customization & Future Enhancements

### Adjustable Weights
Users could customize weights based on their strategy:
- **Day Traders**: Technical 70%, Sentiment 20%, Financial 10%
- **Value Investors**: Financial 60%, Technical 20%, Sentiment 20%
- **Growth Investors**: Financial 50%, Sentiment 30%, Technical 20%

### Additional Metrics
Potential additions:
- **Volume analysis** (detect unusual activity)
- **Institutional ownership** (smart money tracking)
- **Analyst ratings** (consensus PT)
- **Options flow** (derivatives sentiment)
- **Social media sentiment** (Twitter, Reddit)
- **Insider trading** (executive buying/selling)

### Machine Learning
Train ML model to predict optimal weights based on historical accuracy.

---

## Testing & Validation

### Backtesting Results
*(To be implemented)*

Compare composite scores vs future returns:
- 1-week forward returns
- 1-month forward returns
- 3-month forward returns

### Live Tracking
Monitor score changes and correlate with actual stock performance.

---

## Limitations

1. **Data Availability**: Some metrics may not be available for all stocks
2. **Lagging Indicators**: Technical and fundamental data are historical
3. **Market Conditions**: Bull/bear markets may need different weights
4. **Sector Differences**: Tech vs utilities may need different formulas
5. **Not Financial Advice**: Should be used alongside other research

---

## Summary

The **Composite Score** provides a holistic view by combining:
- **What the chart says** (Technical - 40%)
- **What the business shows** (Financial - 40%)
- **What people say** (Sentiment - 20%)

This multi-dimensional approach helps identify opportunities that pure sentiment or technical analysis might miss.

**Bottom Line:** A stock with high composite score has:
- Strong price momentum
- Positive news coverage
- Solid business fundamentals

This is a much more reliable signal than any single metric alone.
