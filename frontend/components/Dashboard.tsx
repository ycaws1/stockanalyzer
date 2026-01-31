'use client';

import React, { useEffect, useState } from 'react';
import StockCard from './StockCard';
import styles from './Dashboard.module.css';
import { usePushNotifications } from '../hooks/usePushNotifications';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Dashboard() {
    const [stocks, setStocks] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [newTicker, setNewTicker] = useState('');
    const [adding, setAdding] = useState(false);
    const [sortMethod, setSortMethod] = useState<'default' | 'marketCap' | 'change' | 'sentiment' | 'composite'>('change');
    const [trendView, setTrendView] = useState<'1H' | '1D'>('1D');
    const [allExpanded, setAllExpanded] = useState<boolean | undefined>(undefined);
    const pushNotifications = usePushNotifications();

    const fetchWatchlist = async () => {
        try {
            const res = await fetch(`${API_BASE}/stocks/`);
            if (!res.ok) throw new Error('Failed to fetch watchlist');
            const watchlist = await res.json();
            return watchlist.map((item: any) => item.ticker);
        } catch (e) {
            console.error(e);
            return [];
        }
    };

    const fetchStockData = async (tickers: string[]) => {
        if (tickers.length === 0) {
            setStocks([]);
            setLoading(false);
            return;
        }
        setLoading(true);

        const intervalParam = trendView === '1H' ? '1h' : '1d';

        try {
            // Try fetching all cached stocks at once
            const overviewRes = await fetch(`${API_BASE}/stocks/overview?interval=${intervalParam}`);
            if (overviewRes.ok) {
                const overviewData = await overviewRes.json();

                // Map to frontend format
                const mappedStocks = overviewData.map((data: any) => ({
                    ticker: data.ticker,
                    name: data.company_info?.name || data.ticker,
                    price: data.price || 0,
                    changePercent: data.change_percent || 0,
                    sentiment: data.sentiment_label || 'Neutral',
                    score: data.score || 0,
                    scoreBreakdown: data.score_breakdown || null,
                    scoreDetails: data.score_details || null,
                    volume: data.company_info?.volume ? (data.company_info.volume / 1000000).toFixed(1) + 'M' : 'N/A',
                    marketCap: data.company_info?.market_cap ? (data.company_info.market_cap / 1e9).toFixed(1) + 'B' : 'N/A',
                    news: data.news || []
                }));

                // Check if we have all tickers. If not, fetch missing ones individually.
                const foundTickers = new Set(mappedStocks.map((s: any) => s.ticker));
                const missingTickers = tickers.filter(t => !foundTickers.has(t));

                if (missingTickers.length > 0) {
                    console.log(`Fetching ${missingTickers.length} missing stocks individually`);
                    const missingPromises = missingTickers.map(async (ticker) => {
                        try {
                            const res = await fetch(`${API_BASE}/stocks/${ticker}/analysis?interval=${intervalParam}`);
                            if (!res.ok) return null;
                            const data = await res.json();
                            return {
                                ticker: data.ticker,
                                name: data.company_info?.name || data.ticker,
                                price: data.price || 0,
                                changePercent: data.change_percent || 0,
                                sentiment: data.sentiment_label || 'Neutral',
                                score: data.score || 0,
                                scoreBreakdown: data.score_breakdown || null,
                                scoreDetails: data.score_details || null,
                                volume: data.company_info?.volume ? (data.company_info.volume / 1000000).toFixed(1) + 'M' : 'N/A',
                                marketCap: data.company_info?.market_cap ? (data.company_info.market_cap / 1e9).toFixed(1) + 'B' : 'N/A',
                                news: data.news || []
                            };
                        } catch (e) {
                            return null;
                        }
                    });
                    const missingResults = await Promise.all(missingPromises);
                    const successfulMissing = missingResults.filter(s => s !== null);
                    setStocks([...mappedStocks, ...successfulMissing]);
                } else {
                    setStocks(mappedStocks);
                }
            } else {
                throw new Error('Failed to fetch overview');
            }
        } catch (e) {
            console.error('Error fetching stock data:', e);
            // Fallback to empty or old behavior if needed, but for now just clear
            setStocks([]);
        } finally {
            setLoading(false);
        }
    };

    const loadData = async () => {
        setLoading(true);
        const watchlist = await fetchWatchlist();
        if (watchlist.length === 0) {
            setStocks([]);
            setLoading(false);
        } else {
            await fetchStockData(watchlist);
        }
    };

    useEffect(() => {
        loadData();
    }, [trendView]);

    const handleAddStock = async () => {
        if (!newTicker) return;
        setAdding(true);
        try {
            const url = `${API_BASE}/stocks/?ticker=${encodeURIComponent(newTicker.trim().toUpperCase())}`;
            const res = await fetch(url, { method: 'POST' });

            if (res.ok) {
                setNewTicker('');
                loadData(); // Reload all
            } else {
                const errorData = await res.json().catch(() => ({}));
                console.error('Server returned error:', res.status, errorData);
                alert(`Failed to add stock: ${errorData.detail || 'Check ticker symbol'}`);
            }
        } catch (e: any) {
            console.error('Network or CORS error adding stock:', e);
            alert(`Error adding stock: ${e.message || 'Check connection/CORS'}`);
        } finally {
            setAdding(false);
        }
    };

    const handleRemoveStock = async (ticker: string) => {
        if (!confirm(`Remove ${ticker} from watchlist?`)) return;
        try {
            await fetch(`${API_BASE}/stocks/${ticker}`, { method: 'DELETE' });
            setStocks(prev => prev.filter(s => s.ticker !== ticker));
        } catch (e) {
            alert('Failed to remove stock');
        }
    };

    const getSortedStocks = () => {
        const sorted = [...stocks];
        switch (sortMethod) {
            case 'marketCap':
                return sorted.sort((a, b) => {
                    const getCap = (s: any) => {
                        if (s.marketCap === 'N/A') return 0;
                        const val = parseFloat(s.marketCap);
                        return s.marketCap.includes('T') ? val * 1000 : val;
                    };
                    return getCap(b) - getCap(a);
                });
            case 'change':
                return sorted.sort((a, b) => b.changePercent - a.changePercent);
            case 'sentiment':
                return sorted.sort((a, b) => (b.scoreBreakdown?.sentiment || 0) - (a.scoreBreakdown?.sentiment || 0));
            case 'composite':
                return sorted.sort((a, b) => b.score - a.score);
            default:
                return sorted;
        }
    };

    return (
        <div className={`container ${styles.dashboard}`}>
            {/* Permission Prompt Banner for PWA/iOS */}
            {pushNotifications.needsPermissionPrompt && (
                <div style={{
                    background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
                    borderRadius: '12px',
                    padding: '1rem 1.5rem',
                    marginBottom: '1.5rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '1rem',
                    boxShadow: '0 4px 20px rgba(59, 130, 246, 0.3)'
                }}>
                    <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: '1.1rem', marginBottom: '0.25rem' }}>
                            🔔 Enable Stock Alerts
                        </div>
                        <div style={{ opacity: 0.9, fontSize: '0.9rem' }}>
                            Get notified when stocks move &gt;{pushNotifications.thresholds?.threshold_1h || 2}% (1H) or &gt;{pushNotifications.thresholds?.threshold_1d || 3.5}% (1D)
                        </div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                            onClick={() => pushNotifications.subscribe()}
                            disabled={pushNotifications.isLoading}
                            style={{
                                background: 'white',
                                color: '#667eea',
                                border: 'none',
                                borderRadius: '8px',
                                padding: '0.6rem 1.2rem',
                                fontWeight: 600,
                                cursor: 'pointer',
                                opacity: pushNotifications.isLoading ? 0.7 : 1
                            }}
                        >
                            {pushNotifications.isLoading ? '...' : 'Enable'}
                        </button>
                        <button
                            onClick={() => pushNotifications.dismissPermissionPrompt()}
                            style={{
                                background: 'rgba(255,255,255,0.2)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                padding: '0.6rem 1rem',
                                cursor: 'pointer'
                            }}
                        >
                            ✕
                        </button>
                    </div>
                </div>
            )}

            <header className={styles.section}>
                <h1>Stock Analyzer</h1>
                <p>Real-time AI-powered market insights and trade simulation.</p>
            </header>

            <section className={styles.section}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                    <h2>Market Overview</h2>

                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        {/* Push Notification Toggle */}
                        {pushNotifications.isSupported && (
                            <button
                                onClick={() => pushNotifications.isSubscribed ? pushNotifications.unsubscribe() : pushNotifications.subscribe()}
                                disabled={pushNotifications.isLoading}
                                style={{
                                    background: pushNotifications.isSubscribed ? 'var(--primary)' : 'transparent',
                                    border: '1px solid rgba(255,255,255,0.1)',
                                    borderRadius: '6px',
                                    color: pushNotifications.isSubscribed ? 'white' : 'var(--text-muted)',
                                    padding: '0.5rem 0.8rem',
                                    cursor: 'pointer',
                                    fontSize: '0.85rem',
                                    whiteSpace: 'nowrap',
                                    opacity: pushNotifications.isLoading ? 0.6 : 1
                                }}
                                title={pushNotifications.isSubscribed ? 'Disable alerts' : `Enable alerts (1H >${pushNotifications.thresholds?.threshold_1h || 2}%, 1D >${pushNotifications.thresholds?.threshold_1d || 3.5}%)`}
                            >
                                {pushNotifications.isLoading ? '...' : (pushNotifications.isSubscribed ? '🔔 Alerts On' : '🔕 Alerts Off')}
                            </button>
                        )}

                        <button
                            onClick={() => setAllExpanded(prev => prev === true ? false : true)}
                            style={{
                                background: 'transparent',
                                border: '1px solid rgba(255,255,255,0.1)',
                                borderRadius: '6px',
                                color: 'var(--text-muted)',
                                padding: '0.5rem 0.8rem',
                                cursor: 'pointer',
                                fontSize: '0.85rem',
                                whiteSpace: 'nowrap'
                            }}
                            title={allExpanded === true ? "Collapse all cards" : "Expand all cards"}
                        >
                            {allExpanded === true ? 'Collapse All' : 'Expand All'}
                        </button>

                        {/* Trend Controls */}
                        <select
                            value={trendView}
                            onChange={(e) => setTrendView(e.target.value as '1H' | '1D')}
                            style={{
                                background: 'rgba(255,255,255,0.05)',
                                color: 'var(--text-muted)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                padding: '0.5rem',
                                borderRadius: '6px',
                                outline: 'none'
                            }}
                        >
                            <option value="1H">Hourly Trend (1H)</option>
                            <option value="1D">Daily Trend (1D)</option>
                        </select>

                        {/* Sort Controls */}
                        <select
                            value={sortMethod}
                            onChange={(e) => setSortMethod(e.target.value as any)}
                            style={{
                                background: 'rgba(255,255,255,0.05)',
                                color: 'var(--text-muted)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                padding: '0.5rem',
                                borderRadius: '6px',
                                outline: 'none'
                            }}
                        >
                            <option value="default">Sort by...</option>
                            <option value="marketCap">Market Cap</option>
                            <option value="change">Change %</option>
                            <option value="sentiment">Sentiment Score</option>
                            <option value="composite">Composite Score</option>
                        </select>

                        {/* Add Stock */}
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <input
                                value={newTicker}
                                onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                                placeholder="Add Ticker"
                                style={{
                                    background: 'rgba(255,255,255,0.05)',
                                    border: '1px solid rgba(255,255,255,0.1)',
                                    padding: '0.5rem',
                                    borderRadius: '6px',
                                    color: 'white',
                                    width: '100px'
                                }}
                            />
                            <button
                                onClick={handleAddStock}
                                disabled={adding}
                                style={{
                                    background: 'var(--primary)',
                                    border: 'none',
                                    borderRadius: '6px',
                                    color: 'white',
                                    padding: '0 1rem',
                                    cursor: 'pointer',
                                    opacity: adding ? 0.7 : 1
                                }}
                            >
                                {adding ? '...' : '+'}
                            </button>
                        </div>
                    </div>
                </div>
                {loading ? (
                    <p>Loading market data...</p>
                ) : stocks.length === 0 ? (
                    <div className={styles.emptyState} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                        <p>Your watchlist is empty.</p>
                        <p style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>Add a ticker symbol above to get started.</p>
                    </div>
                ) : (
                    <div className={styles.grid}>
                        {getSortedStocks().map((stock) => (
                            <div key={stock.ticker} style={{ position: 'relative', width: '100%', maxWidth: '350px', margin: '0 auto' }}>
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        handleRemoveStock(stock.ticker);
                                    }}
                                    style={{
                                        position: 'absolute',
                                        top: '10px',
                                        right: '12px',
                                        background: 'rgba(0,0,0,0.3)',
                                        border: 'none',
                                        color: '#888',
                                        width: '24px',
                                        height: '24px',
                                        borderRadius: '50%',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        cursor: 'pointer',
                                        zIndex: 10,
                                        fontSize: '1rem',
                                        lineHeight: 1
                                    }}
                                    title="Remove from watchlist"
                                >
                                    &times;
                                </button>
                                <StockCard
                                    data={stock}
                                    forceExpanded={allExpanded}
                                    trendPeriod={trendView === '1H' ? '5d' : '1mo'}
                                    trendInterval={trendView === '1H' ? '1h' : '1d'}
                                />
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div >
    );
}
