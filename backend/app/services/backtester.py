import pandas as pd
from .data_collector import DataCollector

class Backtester:
    @staticmethod
    async def run_backtest(ticker: str, initial_capital: float = 10000.0, period: str = "1y", strategy: str = "SMA", parameters: dict = None):
        """
        Runs a backtest based on the selected strategy.
        Strategies:
        - SMA: Simple Moving Average Crossover (Price vs SMA). Params: {'window': 20}
        - RSI: Relative Strength Index (Reversal). Params: {'period': 14, 'overbought': 70, 'oversold': 30}
        """
        if parameters is None:
            parameters = {}

        # Fetch data
        data = await DataCollector.fetch_stock_data(ticker, period=period)
        if not data:
            return {"error": "No data found"}
            
        df = pd.DataFrame(data)
        df['close'] = df['close'].astype(float)
        
        # Calculate Indicators & Signals
        if strategy == "SMA":
            window = int(parameters.get("window", 20))
            df['sma'] = df['close'].rolling(window=window).mean()
            # Buy when Price > SMA, Sell when Price < SMA
            df['signal'] = 0
            df.loc[df['close'] > df['sma'], 'signal'] = 1 # Buy Signal/Hold
            df.loc[df['close'] < df['sma'], 'signal'] = -1 # Sell Signal
            
        elif strategy == "RSI":
            period_len = int(parameters.get("period", 14))
            overbought = int(parameters.get("overbought", 70))
            oversold = int(parameters.get("oversold", 30))
            
            # RSI Calculation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period_len).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period_len).mean()
            
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Logic: Buy when RSI crosses below Oversold (Reversal Buy), Sell when RSI crosses above Overbought
            # Simplification for backtest:
            # - Buy if RSI < Oversold
            # - Sell if RSI > Overbought
            # - Hold otherwise (or close on neutral? Let's stick to simple bands)
            
            df['signal'] = 0
            # Note: This is a mean-reversion strategy
            df.loc[df['rsi'] < oversold, 'signal'] = 1 # Buy zone
            df.loc[df['rsi'] > overbought, 'signal'] = -1 # Sell zone
            # 0 is Hold current position
            
        else:
            return {"error": f"Unknown strategy: {strategy}"}

        # Simulation Loop
        balance = initial_capital
        position = 0 # Shares held
        trades = []
        equity_curve = []
        
        # We need to iterate to handle state (buy/sell execution)
        # Shift signal to avoid lookhead bias? 
        # For simplicity in this demo, we act on Close price signal of CURRENT day (assuming we trade at close) 
        # OR we trade next day open.
        # Let's trade SAME DAY CLOSE for simplicity, but acknowledge lookahead if not careful.
        # Actually, standard simple backtests often use current close.
        
        current_signal = 0 # 0: None, 1: Long, -1: Short/Cash
        
        for i, row in df.iterrows():
            # Skip if indicator is NaN (start of data)
            if strategy == "SMA" and pd.isna(row.get('sma')): continue
            if strategy == "RSI" and pd.isna(row.get('rsi')): continue
            
            price = row['close']
            date = row['timestamp']
            row_signal = row.get('signal', 0)
            
            # Signal Logic Handling
            # SMA: State based (Always in market if signal is active)
            # RSI: Event based (Buy/Sell zones) -> State maintenance needed
            
            if strategy == "SMA":
                # State Based: 1 = Long, -1 = Cash
                 if row_signal == 1 and position == 0:
                    # Buy
                    shares = balance // price
                    cost = shares * price
                    balance -= cost
                    position += shares
                    trades.append({"type": "buy", "date": date, "price": price, "shares": shares, "balance_after": balance})
                    
                 elif row_signal == -1 and position > 0:
                    # Sell
                    revenue = position * price
                    balance += revenue
                    trades.append({"type": "sell", "date": date, "price": price, "shares": position, "balance_after": balance})
                    position = 0
            
            elif strategy == "RSI":
                # Mean Reversion
                if row_signal == 1 and position == 0: # Buy Zone
                    shares = balance // price
                    cost = shares * price
                    balance -= cost
                    position += shares
                    trades.append({"type": "buy", "date": date, "price": price, "shares": shares, "balance_after": balance})
                
                elif row_signal == -1 and position > 0: # Sell Zone
                    revenue = position * price
                    balance += revenue
                    trades.append({"type": "sell", "date": date, "price": price, "shares": position, "balance_after": balance})
                    position = 0
            
            # Track Equity
            current_equity = balance + (position * price)
            equity_curve.append({"date": date, "equity": current_equity})

        # Final Sell
        if position > 0:
            final_price = df.iloc[-1]['close']
            balance += position * final_price
            
        total_return = ((balance - initial_capital) / initial_capital) * 100
        
        # Advanced Metrics
        if not equity_curve:
            sharpe_ratio = 0
            max_drawdown = 0
        else:
            equity_series = pd.Series([e['equity'] for e in equity_curve])
            rolling_max = equity_series.cummax()
            drawdown = (equity_series - rolling_max) / rolling_max
            max_drawdown = drawdown.min() * 100
            returns = equity_series.pct_change().dropna()
            sharpe_ratio = (returns.mean() / returns.std()) * (252 ** 0.5) if returns.std() != 0 else 0

        return {
            "ticker": ticker,
            "initial_capital": initial_capital,
            "final_balance": round(balance, 2),
            "total_return_percent": round(total_return, 2),
            "max_drawdown_percent": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "total_trades": len(trades),
            "trades": trades, 
            "equity_curve": equity_curve,
            "price_history": df[['timestamp', 'close', 'sma' if 'sma' in df else 'rsi' if 'rsi' in df else 'close']].fillna(0).to_dict(orient='records')
        }
