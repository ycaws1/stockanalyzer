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

    useEffect(() => {
        fetchHistory();
    }, []);

    const fetchHistory = async () => {
        try {
            setLoading(true);
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await fetch(`${apiUrl}/push/history?limit=50`);
            if (!response.ok) throw new Error('Failed to fetch history');
            const data = await response.json();
            setHistory(data);
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

    return (
        <div className={styles.container}>
            <h1 className={styles.title}>
                <span>🔔</span> Notification History
            </h1>

            {history.length === 0 ? (
                <div className={styles.empty}>
                    No notifications sent yet.
                </div>
            ) : (
                <div className={styles.list}>
                    {history.map((item) => (
                        <div key={item.id} className={styles.card}>
                            <div className={styles.cardHeader}>
                                <span className={styles.ticker}>{item.ticker}</span>
                                <span className={styles.timestamp}>{formatTimestamp(item.timestamp)}</span>
                            </div>
                            <div className={styles.body}>
                                <strong>{item.title}</strong>
                                <p>{item.body}</p>
                            </div>
                            <div className={styles.tag}>{item.tag}</div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
