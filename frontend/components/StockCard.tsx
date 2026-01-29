import React, { useState } from 'react';
import styles from './StockCard.module.css';
import {
    LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip
} from 'recharts';

interface StockData {
    ticker: string;
    name: string;
    price: number;
    changePercent: number;
    sentiment: 'Bullish' | 'Bearish' | 'Neutral';
    score: number;
    scoreBreakdown?: {
        technical: number;
        sentiment: number;
        financial: number;
    };
    scoreDetails?: any;
    volume: string;
    marketCap: string;
    news: any[];
}

interface StockCardProps {
    data: StockData;
    forceExpanded?: boolean;
}

export default function StockCard({ data, forceExpanded }: StockCardProps) {
    const isPositive = data.changePercent >= 0;
    const [expanded, setExpanded] = useState(false);

    // Sync with forceExpanded prop from parent
    React.useEffect(() => {
        if (forceExpanded !== undefined) {
            if (forceExpanded && !expanded) {
                handleExpand();
            } else if (!forceExpanded && expanded) {
                setExpanded(false);
            }
        }
    }, [forceExpanded]);
    const [history, setHistory] = useState<any[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(false);

    const handleExpand = async () => {
        if (!expanded && history.length === 0) {
            setLoadingHistory(true);
            try {
                // Fetch 5d hourly data
                const res = await fetch(`http://localhost:8000/stocks/${data.ticker}/history?period=5d&interval=1h`);
                if (res.ok) {
                    const histData = await res.json();
                    setHistory(histData);
                }
            } catch (e) {
                console.error("Failed to load history", e);
            } finally {
                setLoadingHistory(false);
            }
        }
        setExpanded(!expanded);
    };

    const getScoreColor = (score: number) => {
        if (score >= 65) return '#4ade80'; // Green
        if (score >= 50) return '#fbbf24'; // Yellow
        return '#ef4444'; // Red
    };

    const getScoreLabel = (score: number) => {
        if (score >= 65) return 'Good';
        if (score >= 50) return 'Neutral';
        return 'Poor';
    };

    return (
        <div
            className={`glass-card ${styles.card} ${expanded ? styles.expanded : ''}`}
            onClick={handleExpand}
        >
            <div className={styles.header}>
                <span className={styles.ticker}>{data.ticker}</span>
                <span className={`${styles.sentiment} ${styles[data.sentiment.toLowerCase()]}`}>
                    {data.sentiment}
                </span>
            </div>

            <div className={styles.companyName}>{data.name}</div>

            <div className={styles.priceRow}>
                <span className={styles.price}>${data.price.toFixed(2)}</span>
                <span className={`${styles.change} ${isPositive ? 'text-green' : 'text-red'}`}>
                    {isPositive ? '+' : ''}{data.changePercent.toFixed(2)}%
                </span>
            </div>

            <div className={styles.details}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    Score: <span className={styles.score} style={{ color: getScoreColor(data.score) }}>{data.score}/100</span>
                    <span
                        title={
                            data.scoreBreakdown
                                ? `Composite Score (${data.score}/100) - ${getScoreLabel(data.score)}\n\n📈 Technical: ${data.scoreBreakdown.technical}/100 (${getScoreLabel(data.scoreBreakdown.technical)})\n💰 Financial: ${data.scoreBreakdown.financial}/100 (${getScoreLabel(data.scoreBreakdown.financial)})\n💭 Sentiment: ${data.scoreBreakdown.sentiment}/100 (${getScoreLabel(data.scoreBreakdown.sentiment)})\n\nClick card for details`
                                : `Composite Score: ${data.score}/100\n\nFetching latest scores...\n(Technical: 40%, Financial: 30%, Sentiment: 30%)\n\nPlease wait a moment for analysis to complete.`
                        }
                        style={{
                            cursor: 'help',
                            color: '#888',
                            fontSize: '0.85rem',
                            fontWeight: 'bold',
                            whiteSpace: 'pre-line'
                        }}
                    >
                        ⓘ
                    </span>
                </span>
                <span>Vol: {data.volume}</span>
            </div>
            <div className={styles.details} style={{ border: 'none', paddingTop: 0 }}>
                <span>Cap: {data.marketCap}</span>
            </div>

            {/* Score Breakdown (when available and expanded) */}
            {expanded && data.scoreBreakdown && (
                <div style={{
                    marginTop: '8px',
                    padding: '8px',
                    backgroundColor: 'rgba(0,0,0,0.2)',
                    borderRadius: '4px',
                    fontSize: '0.85rem'
                }}>
                    <div style={{ marginBottom: '4px', fontWeight: 'bold', color: '#888' }}>Score Breakdown:</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                        <span>📈 Technical:</span>
                        <span style={{ color: getScoreColor(data.scoreBreakdown.technical) }}>{data.scoreBreakdown.technical}/100</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                        <span>💰 Financial:</span>
                        <span style={{ color: getScoreColor(data.scoreBreakdown.financial) }}>{data.scoreBreakdown.financial}/100</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>💭 Sentiment:</span>
                        <span style={{ color: getScoreColor(data.scoreBreakdown.sentiment) }}>{data.scoreBreakdown.sentiment}/100</span>
                    </div>
                </div>
            )}

            {expanded && (
                <div className={styles.expandedContent} onClick={(e) => e.stopPropagation()}>
                    <div className={styles.divider} />

                    {/* Hourly Trend Chart */}
                    <div className={styles.chartSection}>
                        <h4>5-Day Hourly Trend</h4>
                        {loadingHistory ? (
                            <div className={styles.loading}>Loading chart...</div>
                        ) : (
                            <div style={{ width: '100%', height: 150 }}>
                                <ResponsiveContainer>
                                    <LineChart data={history}>
                                        <XAxis dataKey="timestamp" hide />
                                        <YAxis domain={['auto', 'auto']} hide />
                                        <Tooltip
                                            contentStyle={{ background: '#111', border: '1px solid #333', fontSize: '12px' }}
                                            labelFormatter={(label) => {
                                                if (!label) return '';
                                                return new Date(label).toLocaleString('en-US', {
                                                    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
                                                });
                                            }}
                                            formatter={(value: any) => [`$${Number(value).toFixed(2)}`, 'Price']}
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="close"
                                            stroke={isPositive ? '#4ade80' : '#ef4444'}
                                            strokeWidth={2}
                                            dot={false}
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        )}
                    </div>

                    {/* News Section */}
                    <div className={styles.newsSection}>
                        <h4>Latest News</h4>
                        {data.news && data.news.length > 0 ? (
                            <ul className={styles.newsList}>
                                {data.news.slice(0, 3).map((item, idx) => {
                                    const sentimentScore = item.sentiment_score || 0;
                                    const getSentimentColor = (score: number) => {
                                        if (score > 0.3) return '#4ade80'; // Positive - green
                                        if (score < -0.3) return '#ef4444'; // Negative - red
                                        return '#fbbf24'; // Neutral - yellow
                                    };
                                    const getSentimentLabel = (score: number) => {
                                        if (score > 0.3) return 'Positive';
                                        if (score < -0.3) return 'Negative';
                                        return 'Neutral';
                                    };

                                    return (
                                        <li key={idx} className={styles.newsItem}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', gap: '8px' }}>
                                                <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ flex: 1 }}>
                                                    {item.headline}
                                                </a>
                                                <span
                                                    style={{
                                                        fontSize: '0.75rem',
                                                        padding: '2px 6px',
                                                        borderRadius: '4px',
                                                        backgroundColor: `${getSentimentColor(sentimentScore)}20`,
                                                        color: getSentimentColor(sentimentScore),
                                                        fontWeight: 'bold',
                                                        whiteSpace: 'nowrap'
                                                    }}
                                                    title={`Sentiment Score: ${sentimentScore.toFixed(2)}`}
                                                >
                                                    {getSentimentLabel(sentimentScore)}
                                                </span>
                                            </div>
                                            <span className={styles.newsMeta}>
                                                {new Date(item.published_at).toLocaleDateString()} - {item.publisher}
                                            </span>
                                        </li>
                                    );
                                })}
                            </ul>
                        ) : (
                            <p className={styles.noNews}>No recent news</p>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
