'use client';

import React, { useEffect, useState } from 'react';
import StockCard from './StockCard';
import styles from './Dashboard.module.css';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Dashboard() {
    const [stocks, setStocks] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [newTicker, setNewTicker] = useState('');
    const [adding, setAdding] = useState(false);
    const [sortMethod, setSortMethod] = useState<'default' | 'marketCap' | 'change' | 'sentiment' | 'composite'>('change');
    const [allExpanded, setAllExpanded] = useState<boolean | undefined>(undefined);

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
            setStocks([]); // Clear stocks if no tickers
            setLoading(false);
            return;
        }
        setLoading(true);

        const promises = tickers.map(async (ticker) => {
            try {
                const res = await fetch(`${API_BASE}/stocks/${ticker}/analysis`);
                if (!res.ok) throw new Error(`Failed to fetch ${ticker}`);
                const data = await res.json();

                // Map backend response to frontend format
                // Fetch history for sparkline/price
                const historyRes = await fetch(`${API_BASE}/stocks/${ticker}/history?period=5d`);
                const history = await historyRes.ok ? await historyRes.json() : [];
                const latest = history.length > 0 ? history[history.length - 1] : { close: 0, volume: 0 };
                const prev = history.length > 1 ? history[history.length - 2] : null;

                const changePercent = prev ? ((latest.close - prev.close) / prev.close) * 100 : 0;

                return {
                    ticker: data.ticker,
                    name: data.company_info?.name || data.ticker,
                    price: latest.close,
                    changePercent: changePercent,
                    sentiment: changePercent > 0.1 ? 'Bullish' : changePercent < -0.1 ? 'Bearish' : 'Neutral',
                    score: data.score || Math.round((data.average_sentiment + 1) * 50), // Use composite score or fallback
                    scoreBreakdown: data.score_breakdown || null,
                    scoreDetails: data.score_details || null,
                    volume: (latest.volume / 1000000).toFixed(1) + 'M',
                    marketCap: data.company_info?.market_cap ? (data.company_info.market_cap / 1e9).toFixed(1) + 'B' : 'N/A',
                    news: data.news || []
                };
            } catch (e) {
                console.error(`Error fetching data for ${ticker}:`, e);
                return null;
            }
        });

        const results = await Promise.allSettled(promises);
        const successfulStocks = results
            .filter(result => result.status === 'fulfilled' && result.value !== null)
            .map(result => (result as PromiseFulfilledResult<any>).value);
        setStocks(successfulStocks);
        setLoading(false);
    };

    const loadData = async () => {
        setLoading(true); // Ensure loading is true when starting to load data
        const watchlist = await fetchWatchlist();
        // Fallback to default if empty (first run)
        if (watchlist.length === 0) {
            // Seed defaults? Or just show empty.
            // Let's seed defaults via backend ideally, but for now we fallback logic in frontend or show empty state.
            // Let's show empty state to encourage adding.
            setStocks([]); // Ensure stocks are empty if watchlist is empty
            setLoading(false);
        } else {
            await fetchStockData(watchlist);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

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
            <header className={styles.section}>
                <h1>Stock Analyzer</h1>
                <p>Real-time AI-powered market insights and trade simulation.</p>
            </header>

            <section className={styles.section}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                    <h2>Market Overview</h2>

                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
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
                            <option value="change">Daily Change %</option>
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
                                <StockCard data={stock} forceExpanded={allExpanded} />
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div >
    );
}
