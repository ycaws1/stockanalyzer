import React, { useState, useEffect } from 'react';
import styles from './TradeSimulator.module.css';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot
} from 'recharts';
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function TradeSimulator() {
    const [ticker, setTicker] = useState('NVDA');
    const [backtestResult, setBacktestResult] = useState<any>(null);
    const [loadingBacktest, setLoadingBacktest] = useState(false);

    const [strategy, setStrategy] = useState<'SMA' | 'RSI'>('SMA');
    const [params, setParams] = useState<any>({ window: 20, period: 14, overbought: 70, oversold: 30 });

    // Live Simulation State
    const [liveMode, setLiveMode] = useState(false);
    const [liveSignal, setLiveSignal] = useState<any>(null);
    const [liveBalance, setLiveBalance] = useState(10000);
    const [livePosition, setLivePosition] = useState(0);
    const [liveTransactions, setLiveTransactions] = useState<any[]>([]);
    const [loadingLiveSignal, setLoadingLiveSignal] = useState(false);
    const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
    const [timeAgo, setTimeAgo] = useState<string>('');
    const [liveStartTime, setLiveStartTime] = useState<Date | null>(null);
    const [liveInitialCapital] = useState(10000);
    const [livePerformance, setLivePerformance] = useState<any>(null);
    const [isLoaded, setIsLoaded] = useState(false);

    // Load state from localStorage on mount (Client-side only)
    useEffect(() => {
        const loadSaved = () => {
            try {
                const savedTicker = localStorage.getItem('trade_ticker');
                if (savedTicker) setTicker(JSON.parse(savedTicker));

                const savedStrategy = localStorage.getItem('trade_strategy');
                if (savedStrategy) setStrategy(JSON.parse(savedStrategy) as any);

                const savedParams = localStorage.getItem('trade_params');
                if (savedParams) setParams(JSON.parse(savedParams));

                const savedLiveMode = localStorage.getItem('live_mode');
                if (savedLiveMode) setLiveMode(JSON.parse(savedLiveMode));

                const savedLiveSignal = localStorage.getItem('live_signal');
                if (savedLiveSignal) setLiveSignal(JSON.parse(savedLiveSignal));

                const savedLiveBalance = localStorage.getItem('live_balance');
                if (savedLiveBalance) setLiveBalance(JSON.parse(savedLiveBalance));

                const savedLivePosition = localStorage.getItem('live_position');
                if (savedLivePosition) setLivePosition(JSON.parse(savedLivePosition));

                const savedLiveTransactions = localStorage.getItem('live_transactions');
                if (savedLiveTransactions) setLiveTransactions(JSON.parse(savedLiveTransactions));

                const savedLastUpdate = localStorage.getItem('live_last_update');
                if (savedLastUpdate) {
                    const parsed = JSON.parse(savedLastUpdate);
                    if (parsed) setLastUpdateTime(new Date(parsed));
                }

                const savedStartTime = localStorage.getItem('live_start_time');
                if (savedStartTime) {
                    const parsed = JSON.parse(savedStartTime);
                    if (parsed) setLiveStartTime(new Date(parsed));
                }

                const savedPerformance = localStorage.getItem('live_performance');
                if (savedPerformance) setLivePerformance(JSON.parse(savedPerformance));

                console.log("Persistence: State restored from localStorage");
            } catch (e) {
                console.error("Persistence: Error loading state", e);
            } finally {
                setIsLoaded(true);
            }
        };

        if (typeof window !== 'undefined') {
            loadSaved();
        }
    }, []);

    // Save state to localStorage whenever it changes (only after initial load to avoid overwriting)
    useEffect(() => {
        if (!isLoaded) return;

        localStorage.setItem('trade_ticker', JSON.stringify(ticker));
        localStorage.setItem('trade_strategy', JSON.stringify(strategy));
        localStorage.setItem('trade_params', JSON.stringify(params));
        localStorage.setItem('live_mode', JSON.stringify(liveMode));
        localStorage.setItem('live_signal', JSON.stringify(liveSignal));
        localStorage.setItem('live_balance', JSON.stringify(liveBalance));
        localStorage.setItem('live_position', JSON.stringify(livePosition));
        localStorage.setItem('live_transactions', JSON.stringify(liveTransactions));
        localStorage.setItem('live_last_update', JSON.stringify(lastUpdateTime));
        localStorage.setItem('live_start_time', JSON.stringify(liveStartTime));
        localStorage.setItem('live_performance', JSON.stringify(livePerformance));
    }, [isLoaded, ticker, strategy, params, liveMode, liveSignal, liveBalance, livePosition, liveTransactions, lastUpdateTime, liveStartTime, livePerformance]);

    // Calculate time ago string
    const calculateTimeAgo = (date: Date | null): string => {
        if (!date) return '';

        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);

        if (diffSecs < 60) {
            return `${diffSecs} second${diffSecs !== 1 ? 's' : ''} ago`;
        } else if (diffMins < 60) {
            return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        } else {
            const diffHours = Math.floor(diffMins / 60);
            return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        }
    };

    // Update time ago display every second
    useEffect(() => {
        if (!liveMode || !lastUpdateTime) return;

        const interval = setInterval(() => {
            setTimeAgo(calculateTimeAgo(lastUpdateTime));
        }, 1000);

        return () => clearInterval(interval);
    }, [liveMode, lastUpdateTime]);

    // Auto-refresh signal every 2 minutes
    useEffect(() => {
        if (!liveMode) return;

        const interval = setInterval(() => {
            refreshLiveSignal();
        }, 120000); // 2 minutes

        return () => clearInterval(interval);
    }, [liveMode]);

    // Automatic trade execution based on signals
    useEffect(() => {
        if (!liveMode || !liveSignal) return;

        const signal = liveSignal.signal;
        const price = liveSignal.current_price;

        // Auto-execute BUY signal
        if (signal === 'BUY' && livePosition === 0) {
            const sharesToBuy = Math.floor(liveBalance / price);
            if (sharesToBuy > 0) {
                const cost = sharesToBuy * price;
                setLiveBalance((prev: number) => prev - cost);
                setLivePosition((prev: number) => prev + sharesToBuy);
                setLiveTransactions((prev: any[]) => [{
                    type: 'buy',
                    shares: sharesToBuy,
                    price,
                    timestamp: new Date().toISOString(),
                    balance_after: liveBalance - cost
                }, ...prev]);
            }
        }
        // Auto-execute SELL signal
        else if (signal === 'SELL' && livePosition > 0) {
            const revenue = livePosition * price;
            setLiveBalance((prev: number) => prev + revenue);
            setLiveTransactions((prev: any[]) => [{
                type: 'sell',
                shares: livePosition,
                price,
                timestamp: new Date().toISOString(),
                balance_after: liveBalance + revenue
            }, ...prev]);
            setLivePosition(0);
        }
    }, [liveSignal, liveMode]); // Trigger when signal changes



    const runBacktest = async () => {
        setLoadingBacktest(true);
        try {
            const res = await fetch(`${API_BASE}/backtest/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ticker,
                    initial_capital: 10000,
                    period: '1y',
                    strategy,
                    parameters: params
                })
            });
            const data = await res.json();
            setBacktestResult(data);
        } catch (e) {
            console.error(e);
            alert("Backtest failed");
        } finally {
            setLoadingBacktest(false);
        }
    };

    const startLiveSimulation = async () => {
        setLoadingLiveSignal(true);
        try {
            const res = await fetch(`${API_BASE}/live_trade/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ticker,
                    strategy,
                    parameters: params
                })
            });
            const data = await res.json();
            setLiveSignal(data);
            setLiveMode(true);
            const now = new Date();
            setLastUpdateTime(now);
            setTimeAgo(calculateTimeAgo(now));
            setLiveStartTime(now);
            setLivePerformance(null); // Clear previous performance
        } catch (e) {
            console.error(e);
            alert("Failed to start live simulation");
        } finally {
            setLoadingLiveSignal(false);
        }
    };

    const refreshLiveSignal = async () => {
        if (!liveMode) return;
        setLoadingLiveSignal(true);
        try {
            const res = await fetch(`${API_BASE}/live_trade/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ticker,
                    strategy,
                    parameters: params
                })
            });
            const data = await res.json();
            setLiveSignal(data);
            const now = new Date();
            setLastUpdateTime(now);
            setTimeAgo(calculateTimeAgo(now));
        } catch (e) {
            console.error(e);
        } finally {
            setLoadingLiveSignal(false);
        }
    };


    const stopLiveSimulation = () => {
        // Calculate final performance before stopping
        const finalValue = liveBalance + (livePosition * (liveSignal?.current_price || 0));
        const totalReturn = ((finalValue - liveInitialCapital) / liveInitialCapital) * 100;

        // Calculate equity curve from transactions
        const equityCurve = [];
        let runningBalance = liveInitialCapital;
        let runningPosition = 0;

        // Add initial point
        equityCurve.push({ value: liveInitialCapital, timestamp: liveStartTime?.toISOString() || '' });

        // Process transactions in reverse (they're stored newest first)
        [...liveTransactions].reverse().forEach(tx => {
            if (tx.type === 'buy') {
                runningBalance -= tx.shares * tx.price;
                runningPosition += tx.shares;
            } else {
                runningBalance += tx.shares * tx.price;
                runningPosition = 0;
            }
            equityCurve.push({
                value: tx.balance_after + (runningPosition * tx.price),
                timestamp: tx.timestamp
            });
        });

        // Calculate max drawdown
        let maxDrawdown = 0;
        let peak = liveInitialCapital;
        equityCurve.forEach(point => {
            if (point.value > peak) peak = point.value;
            const drawdown = ((point.value - peak) / peak) * 100;
            if (drawdown < maxDrawdown) maxDrawdown = drawdown;
        });

        // Calculate Sharpe ratio (simplified)
        const returns = [];
        for (let i = 1; i < equityCurve.length; i++) {
            const ret = (equityCurve[i].value - equityCurve[i - 1].value) / equityCurve[i - 1].value;
            returns.push(ret);
        }
        const avgReturn = returns.length > 0 ? returns.reduce((a, b) => a + b, 0) / returns.length : 0;
        const stdDev = returns.length > 0
            ? Math.sqrt(returns.reduce((sq, n) => sq + Math.pow(n - avgReturn, 2), 0) / returns.length)
            : 0;
        const sharpeRatio = stdDev !== 0 ? (avgReturn / stdDev) * Math.sqrt(252) : 0;

        const duration = liveStartTime
            ? Math.floor((new Date().getTime() - liveStartTime.getTime()) / 1000)
            : 0;

        const performance = {
            initial_capital: liveInitialCapital,
            final_balance: finalValue,
            total_return_percent: totalReturn,
            max_drawdown_percent: maxDrawdown,
            sharpe_ratio: sharpeRatio,
            total_trades: liveTransactions.length,
            duration_seconds: duration,
            trades: [...liveTransactions].reverse()
        };

        setLivePerformance(performance);

        // Reset state
        setLiveMode(false);
        setLiveSignal(null);
        setLiveBalance(10000);
        setLivePosition(0);
        setLiveTransactions([]);
        setLastUpdateTime(null);
        setTimeAgo('');
    };

    return (
        <div className={styles.simulator}>
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem', fontWeight: '600' }}>Backtest Strategy</h2>

            <div className={styles.backtestContainer}>
                <div className={styles.tradeForm}>
                    {/* Strategy Config */}
                    <div className={styles.formGroup}>
                        <label>Ticker to Backtest</label>
                        <input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
                    </div>

                    <div className={styles.configGrid}>
                        <div className={styles.formGroup}>
                            <label>Strategy</label>
                            <select
                                value={strategy}
                                onChange={(e) => setStrategy(e.target.value as 'SMA' | 'RSI')}
                                className={styles.select}
                            >
                                <option value="SMA">SMA Crossover</option>
                                <option value="RSI">RSI Reversal</option>
                            </select>
                        </div>

                        {strategy === 'SMA' ? (
                            <div className={styles.formGroup}>
                                <label>SMA Window</label>
                                <input
                                    type="number"
                                    value={params.window}
                                    onChange={(e) => setParams({ ...params, window: Number(e.target.value) })}
                                />
                            </div>
                        ) : (
                            <>
                                <div className={styles.formGroup}>
                                    <label>RSI Period</label>
                                    <input
                                        type="number"
                                        value={params.period}
                                        onChange={(e) => setParams({ ...params, period: Number(e.target.value) })}
                                    />
                                </div>
                                <div className={styles.formGroup}>
                                    <label>Overbought</label>
                                    <input
                                        type="number"
                                        value={params.overbought}
                                        onChange={(e) => setParams({ ...params, overbought: Number(e.target.value) })}
                                    />
                                </div>
                                <div className={styles.formGroup}>
                                    <label>Oversold</label>
                                    <input
                                        type="number"
                                        value={params.oversold}
                                        onChange={(e) => setParams({ ...params, oversold: Number(e.target.value) })}
                                    />
                                </div>
                            </>
                        )}
                    </div>

                    <button className={styles.btnExecute} onClick={runBacktest} disabled={loadingBacktest}>
                        {loadingBacktest ? 'Running...' : 'Run Backtest'}
                    </button>
                </div>

                {backtestResult && (
                    <div className={styles.results}>
                        <div className={styles.metricsGrid}>
                            <div className={styles.metric}>
                                <span>Total Return</span>
                                <span style={{ color: backtestResult.total_return_percent >= 0 ? '#4ade80' : '#ef4444' }}>
                                    {backtestResult.total_return_percent}%
                                </span>
                            </div>
                            <div className={styles.metric}>
                                <span>Sharpe Ratio</span>
                                <span>{backtestResult.sharpe_ratio}</span>
                            </div>
                            <div className={styles.metric}>
                                <span>Max Drawdown</span>
                                <span style={{ color: '#ef4444' }}>{backtestResult.max_drawdown_percent}%</span>
                            </div>
                            <div className={styles.metric}>
                                <span>Final Balance</span>
                                <span>${backtestResult.final_balance.toLocaleString()}</span>
                            </div>
                        </div>

                        {/* Equity Curve */}
                        <div className={styles.chartContainer}>
                            <h4>Equity Curve</h4>
                            <ResponsiveContainer width="100%" height={250}>
                                <LineChart data={backtestResult.equity_curve}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                    <XAxis dataKey="date" hide />
                                    <YAxis domain={['auto', 'auto']} tick={{ fill: '#888' }} />
                                    <Tooltip contentStyle={{ backgroundColor: '#111', border: '1px solid #333' }} />
                                    <Line type="monotone" dataKey="equity" stroke="#0070f3" dot={false} strokeWidth={2} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Price & Signals Chart */}
                        <div className={styles.chartContainer}>
                            <h4>Price Trend & Signals</h4>
                            <ResponsiveContainer width="100%" height={300}>
                                <LineChart data={backtestResult.price_history}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                    <XAxis dataKey="timestamp" hide />
                                    <YAxis domain={['auto', 'auto']} tick={{ fill: '#888' }} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#111', border: '1px solid #333' }}
                                        content={(props) => {
                                            if (!props.active || !props.payload || props.payload.length === 0) return null;

                                            const data = props.payload[0].payload;
                                            const timestamp = data.timestamp;

                                            // Find if there's a trade at this timestamp
                                            const trade = backtestResult.trades.find((t: any) => t.date === timestamp);

                                            return (
                                                <div style={{
                                                    backgroundColor: '#111',
                                                    border: '1px solid #333',
                                                    padding: '10px',
                                                    borderRadius: '4px'
                                                }}>
                                                    <p style={{ margin: '0 0 5px 0', color: '#888', fontSize: '0.85rem' }}>
                                                        {timestamp}
                                                    </p>
                                                    <p style={{ margin: '5px 0', color: '#fff' }}>
                                                        Price: <strong>${data.close?.toFixed(2)}</strong>
                                                    </p>
                                                    {strategy === 'SMA' && data.sma && (
                                                        <p style={{ margin: '5px 0', color: '#fbbf24' }}>
                                                            SMA: <strong>${data.sma?.toFixed(2)}</strong>
                                                        </p>
                                                    )}
                                                    {trade && (
                                                        <div style={{
                                                            marginTop: '8px',
                                                            paddingTop: '8px',
                                                            borderTop: '1px solid #333'
                                                        }}>
                                                            <p style={{
                                                                margin: '5px 0',
                                                                color: trade.type === 'buy' ? '#4ade80' : '#ef4444',
                                                                fontWeight: 'bold',
                                                                textTransform: 'uppercase'
                                                            }}>
                                                                {trade.type} SIGNAL
                                                            </p>
                                                            <p style={{ margin: '5px 0', color: '#fff' }}>
                                                                Shares: <strong>{trade.shares}</strong>
                                                            </p>
                                                            <p style={{ margin: '5px 0', color: '#fff' }}>
                                                                {trade.type === 'buy' ? 'Buy' : 'Sell'} Price: <strong>${trade.price?.toFixed(2)}</strong>
                                                            </p>
                                                            <p style={{ margin: '5px 0', color: '#888', fontSize: '0.85rem' }}>
                                                                Balance After: ${trade.balance_after?.toFixed(2)}
                                                            </p>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        }}
                                    />
                                    <Line type="monotone" dataKey="close" stroke="#fff" dot={false} strokeWidth={1} />
                                    {strategy === 'SMA' && (
                                        <Line type="monotone" dataKey="sma" stroke="#fbbf24" dot={false} strokeWidth={1} strokeDasharray="5 5" />
                                    )}
                                    {/* Visualize Trades */}
                                    {backtestResult.trades.map((trade: any, index: number) => {
                                        // Find matching data point to access x/y coordinates implicitly via ReferenceDot
                                        // ReferenceDot needs x (category) and y (value)
                                        return (
                                            <ReferenceDot
                                                key={index}
                                                x={trade.date}
                                                y={trade.price}
                                                r={4}
                                                fill={trade.type === 'buy' ? '#4ade80' : '#ef4444'}
                                                stroke="none"
                                            />
                                        );
                                    })}
                                </LineChart>
                            </ResponsiveContainer>
                            <div style={{ fontSize: '0.8rem', color: '#888', marginTop: '5px' }}>
                                * Visualization of indicators coming next turn if requested. (Trades: {backtestResult.total_trades})
                            </div>
                        </div>
                    </div>
                )}

                {/* Live Simulation Section */}
                <div style={{ marginTop: '3rem', paddingTop: '2rem', borderTop: '2px solid #333' }}>
                    <h3 style={{ marginBottom: '1rem', fontSize: '1.3rem', fontWeight: '600' }}>
                        Live Simulation {liveMode && <span style={{ color: '#4ade80', fontSize: '0.9rem' }}>● ACTIVE</span>}
                    </h3>
                    <p style={{ color: '#888', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                        Use the backtest strategy above to run a live simulated trade. The system will provide real-time buy/sell signals.
                    </p>

                    {!liveMode ? (
                        <div>
                            <button
                                className={styles.btnExecute}
                                onClick={startLiveSimulation}
                                disabled={loadingLiveSignal || !backtestResult}
                                style={{ opacity: !backtestResult ? 0.5 : 1 }}
                            >
                                {loadingLiveSignal ? 'Starting...' : 'Start Live Simulation'}
                            </button>
                            {!backtestResult && (
                                <p style={{ color: '#fbbf24', marginTop: '10px', fontSize: '0.85rem' }}>
                                    ⚠️ Please run a backtest first to configure your strategy
                                </p>
                            )}
                        </div>
                    ) : (
                        <div>
                            {/* Portfolio Status */}
                            <div className={styles.metricsGrid} style={{ marginBottom: '1.5rem' }}>
                                <div className={styles.metric}>
                                    <span>Balance</span>
                                    <span style={{ color: '#4ade80' }}>${liveBalance.toFixed(2)}</span>
                                </div>
                                <div className={styles.metric}>
                                    <span>Position</span>
                                    <span>{livePosition} shares</span>
                                </div>
                                <div className={styles.metric}>
                                    <span>Current Value</span>
                                    <span>${liveSignal ? (liveBalance + (livePosition * liveSignal.current_price)).toFixed(2) : '0.00'}</span>
                                </div>
                                <div className={styles.metric}>
                                    <span>P&L</span>
                                    <span style={{
                                        color: liveSignal && (liveBalance + (livePosition * liveSignal.current_price) - 10000) >= 0 ? '#4ade80' : '#ef4444'
                                    }}>
                                        ${liveSignal ? (liveBalance + (livePosition * liveSignal.current_price) - 10000).toFixed(2) : '0.00'}
                                    </span>
                                </div>
                            </div>

                            {/* Live Signal */}
                            {liveSignal && (
                                <div style={{
                                    backgroundColor: '#1a1a1a',
                                    padding: '1.5rem',
                                    borderRadius: '8px',
                                    marginBottom: '1.5rem',
                                    border: `2px solid ${liveSignal.signal === 'BUY' ? '#4ade80' : liveSignal.signal === 'SELL' ? '#ef4444' : '#888'}`
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <div>
                                            <h4 style={{ margin: '0 0 10px 0', fontSize: '1.1rem' }}>
                                                Current Signal:
                                                <span style={{
                                                    marginLeft: '10px',
                                                    color: liveSignal.signal === 'BUY' ? '#4ade80' : liveSignal.signal === 'SELL' ? '#ef4444' : '#888',
                                                    fontWeight: 'bold'
                                                }}>
                                                    {liveSignal.signal}
                                                </span>
                                            </h4>
                                            <p style={{ margin: '5px 0', color: '#ccc' }}>
                                                Current Price: <strong>${liveSignal.current_price?.toFixed(2)}</strong>
                                            </p>
                                            {liveSignal.indicator_value && (
                                                <p style={{ margin: '5px 0', color: '#888', fontSize: '0.9rem' }}>
                                                    {strategy} Value: {liveSignal.indicator_value.toFixed(2)}
                                                </p>
                                            )}
                                            <p style={{ margin: '5px 0', color: '#666', fontSize: '0.8rem' }}>
                                                Last Updated: {timeAgo || 'Just now'}
                                            </p>
                                            <p style={{ margin: '5px 0', color: '#888', fontSize: '0.75rem' }}>
                                                Auto-refresh in: {lastUpdateTime ? Math.max(0, 120 - Math.floor((new Date().getTime() - lastUpdateTime.getTime()) / 1000)) : 120}s
                                            </p>
                                        </div>
                                        <button
                                            onClick={refreshLiveSignal}
                                            disabled={loadingLiveSignal}
                                            style={{
                                                padding: '8px 16px',
                                                backgroundColor: '#333',
                                                border: '1px solid #555',
                                                borderRadius: '4px',
                                                color: '#fff',
                                                cursor: 'pointer',
                                                fontSize: '0.9rem'
                                            }}
                                        >
                                            {loadingLiveSignal ? 'Refreshing...' : '🔄 Refresh'}
                                        </button>
                                    </div>

                                    {/* Auto-Execution Info */}
                                    <div style={{
                                        marginTop: '15px',
                                        padding: '12px',
                                        backgroundColor: '#0a0a0a',
                                        borderRadius: '4px',
                                        border: '1px solid #333'
                                    }}>
                                        <p style={{ margin: 0, color: '#888', fontSize: '0.9rem' }}>
                                            ✨ <strong style={{ color: '#4ade80' }}>Auto-Execution Mode</strong>: Trades will execute automatically when signals change.
                                            The system refreshes every 2 minutes or when you click Refresh.
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Transaction History */}
                            {liveTransactions.length > 0 && (
                                <div style={{ marginBottom: '1.5rem' }}>
                                    <h4 style={{ marginBottom: '10px' }}>Transaction History</h4>
                                    <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                                        {liveTransactions.map((tx, i) => (
                                            <div
                                                key={i}
                                                style={{
                                                    padding: '10px',
                                                    backgroundColor: '#1a1a1a',
                                                    marginBottom: '8px',
                                                    borderRadius: '4px',
                                                    borderLeft: `3px solid ${tx.type === 'buy' ? '#4ade80' : '#ef4444'}`
                                                }}
                                            >
                                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                                    <span style={{
                                                        color: tx.type === 'buy' ? '#4ade80' : '#ef4444',
                                                        fontWeight: 'bold',
                                                        textTransform: 'uppercase'
                                                    }}>
                                                        {tx.type}
                                                    </span>
                                                    <span style={{ color: '#888', fontSize: '0.85rem' }}>
                                                        {new Date(tx.timestamp).toLocaleString()}
                                                    </span>
                                                </div>
                                                <div style={{ fontSize: '0.9rem', marginTop: '5px' }}>
                                                    {tx.shares} shares @ ${tx.price.toFixed(2)} = ${(tx.shares * tx.price).toFixed(2)}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Stop Button */}
                            <button
                                onClick={stopLiveSimulation}
                                style={{
                                    padding: '10px 20px',
                                    backgroundColor: '#333',
                                    border: '1px solid #555',
                                    borderRadius: '4px',
                                    color: '#fff',
                                    cursor: 'pointer'
                                }}
                            >
                                Stop Simulation
                            </button>
                        </div>
                    )}

                    {/* Live Performance Summary (after stopping) */}
                    {livePerformance && (
                        <div style={{ marginTop: '2rem' }}>
                            <h3 style={{ marginBottom: '1rem', fontSize: '1.2rem', fontWeight: '600', color: '#4ade80' }}>
                                Live Simulation Results
                            </h3>
                            <div className={styles.metricsGrid} style={{ marginBottom: '1.5rem' }}>
                                <div className={styles.metric}>
                                    <span>Total Return</span>
                                    <span style={{ color: livePerformance.total_return_percent >= 0 ? '#4ade80' : '#ef4444' }}>
                                        {livePerformance.total_return_percent.toFixed(2)}%
                                    </span>
                                </div>
                                <div className={styles.metric}>
                                    <span>Sharpe Ratio</span>
                                    <span>{livePerformance.sharpe_ratio.toFixed(2)}</span>
                                </div>
                                <div className={styles.metric}>
                                    <span>Max Drawdown</span>
                                    <span style={{ color: '#ef4444' }}>{livePerformance.max_drawdown_percent.toFixed(2)}%</span>
                                </div>
                                <div className={styles.metric}>
                                    <span>Final Balance</span>
                                    <span>${livePerformance.final_balance.toFixed(2)}</span>
                                </div>
                            </div>

                            <div style={{
                                backgroundColor: '#1a1a1a',
                                padding: '1rem',
                                borderRadius: '8px',
                                marginBottom: '1rem'
                            }}>
                                <p style={{ margin: '5px 0', color: '#888' }}>
                                    Duration: {Math.floor(livePerformance.duration_seconds / 60)}m {livePerformance.duration_seconds % 60}s
                                </p>
                                <p style={{ margin: '5px 0', color: '#888' }}>
                                    Total Trades: {livePerformance.total_trades}
                                </p>
                                <p style={{ margin: '5px 0', color: '#888' }}>
                                    Initial Capital: ${livePerformance.initial_capital.toFixed(2)}
                                </p>
                            </div>

                            {/* Trade List */}
                            {livePerformance.trades && livePerformance.trades.length > 0 && (
                                <div>
                                    <h4 style={{ marginBottom: '10px' }}>Trade History</h4>
                                    <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                                        {livePerformance.trades.map((tx: any, i: number) => (
                                            <div
                                                key={i}
                                                style={{
                                                    padding: '10px',
                                                    backgroundColor: '#1a1a1a',
                                                    marginBottom: '8px',
                                                    borderRadius: '4px',
                                                    borderLeft: `3px solid ${tx.type === 'buy' ? '#4ade80' : '#ef4444'}`
                                                }}
                                            >
                                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                                    <span style={{
                                                        color: tx.type === 'buy' ? '#4ade80' : '#ef4444',
                                                        fontWeight: 'bold',
                                                        textTransform: 'uppercase'
                                                    }}>
                                                        {tx.type}
                                                    </span>
                                                    <span style={{ color: '#888', fontSize: '0.85rem' }}>
                                                        {new Date(tx.timestamp).toLocaleString()}
                                                    </span>
                                                </div>
                                                <div style={{ fontSize: '0.9rem', marginTop: '5px' }}>
                                                    {tx.shares} shares @ ${tx.price.toFixed(2)} = ${(tx.shares * tx.price).toFixed(2)}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <button
                                onClick={() => setLivePerformance(null)}
                                style={{
                                    marginTop: '1rem',
                                    padding: '8px 16px',
                                    backgroundColor: '#333',
                                    border: '1px solid #555',
                                    borderRadius: '4px',
                                    color: '#fff',
                                    cursor: 'pointer',
                                    fontSize: '0.9rem'
                                }}
                            >
                                Clear Results
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
