'use client';

import React, { useEffect, useState } from 'react';
import styles from './NotificationHistory.module.css';

interface NotificationLog {
    id: number;
    ticker: string;
    title: string;
    body: string;
    tag: string;
    value: number;
    timestamp: string;
}

export default function NotificationHistory() {
    const [history, setHistory] = useState<NotificationLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filterTicker, setFilterTicker] = useState('');
    const [appliedTicker, setAppliedTicker] = useState('');

    useEffect(() => {
        fetchHistory('');
    }, []);

    const fetchHistory = async (ticker: string) => {
        try {
            setLoading(true);
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const query = ticker ? `&ticker=${encodeURIComponent(ticker)}` : '';
            const response = await fetch(`${apiUrl}/push/history?limit=50${query}`);
            if (!response.ok) throw new Error('Failed to fetch history');
            const data = await response.json();
            setHistory(data);
            setAppliedTicker(ticker);
            setError(null);
        } catch (err) {
            console.error('Error fetching notification history:', err);
            setError('Could not load notification history.');
        } finally {
            setLoading(false);
        }
    };

    const formatTimestamp = (isoString: string) => {
        const date = new Date(isoString);
        return date.toLocaleString();
    };

    if (loading) {
        return (
            <div className={styles.loading}>
                <div className={styles.spinner}></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className={styles.container}>
                <div className={styles.empty}>{error}</div>
            </div>
        );
    }

    const handleApplyFilter = (e: React.FormEvent) => {
        e.preventDefault();
        fetchHistory(filterTicker.trim().toUpperCase());
    };

    const handleClearFilter = () => {
        setFilterTicker('');
        fetchHistory('');
    };

    return (
        <div className={styles.container}>
            <h1 className={styles.title}>
                <span>🔔</span> Notification History
            </h1>

            <form className={styles.filterBar} onSubmit={handleApplyFilter}>
                <label className={styles.filterLabel} htmlFor="ticker-filter">Filter by ticker</label>
                <input
                    id="ticker-filter"
                    className={styles.filterInput}
                    type="text"
                    placeholder="e.g. AAPL"
                    value={filterTicker}
                    onChange={(e) => setFilterTicker(e.target.value)}
                    autoComplete="off"
                />
                <button className={styles.filterButton} type="submit" disabled={loading}>
                    Apply
                </button>
                <button className={styles.clearButton} type="button" onClick={handleClearFilter} disabled={loading || !appliedTicker}>
                    Clear
                </button>
                {appliedTicker ? (
                    <div className={styles.appliedNote}>Showing: {appliedTicker}</div>
                ) : (
                    <div className={styles.appliedNote}>Showing: All tickers</div>
                )}
            </form>

            {history.length === 0 ? (
                <div className={styles.empty}>
                    No notifications sent yet.
                </div>
            ) : (
                <div className={styles.tableWrap}>
                    <table className={styles.table}>
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Ticker</th>
                                <th>Title</th>
                                <th>Message</th>
                                <th>Tag</th>
                                <th>Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {history.map((item) => (
                                <tr key={item.id}>
                                    <td className={styles.timestamp}>{formatTimestamp(item.timestamp)}</td>
                                    <td className={styles.ticker}>{item.ticker}</td>
                                    <td className={styles.titleCell}>{item.title}</td>
                                    <td className={styles.bodyCell}>{item.body}</td>
                                    <td className={styles.tagCell}>{item.tag}</td>
                                    <td className={styles.valueCell}>{item.value.toFixed(2)}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
