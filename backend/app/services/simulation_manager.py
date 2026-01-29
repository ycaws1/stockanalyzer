import asyncio
import json
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import AsyncSessionLocal
from ..models import Simulation, SimulationTrade
from .data_collector import DataCollector
import pandas as pd

class SimulationManager:
    @staticmethod
    async def evaluate_simulation(sim: Simulation, db: AsyncSession):
        """
        Calculates signal for a single simulation and executes trades if needed.
        """
        try:
            # Fetch recent data
            data = await DataCollector.fetch_stock_data(sim.ticker, period="1mo", interval="1d")
            if not data:
                return

            df = pd.DataFrame(data)
            df['close'] = df['close'].astype(float)
            current_price = df.iloc[-1]['close']
            
            # Parse parameters if string
            params = sim.parameters
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except:
                    params = {}
            
            signal = "HOLD"
            
            # Strategy Logic
            if sim.strategy == "SMA":
                window = int(params.get("window", 20))
                df['sma'] = df['close'].rolling(window=window).mean()
                sma_value = df.iloc[-1]['sma']
                if not pd.isna(sma_value):
                    if current_price > sma_value: signal = "BUY"
                    elif current_price < sma_value: signal = "SELL"
                
            elif sim.strategy == "RSI":
                period_len = int(params.get("period", 14))
                overbought = int(params.get("overbought", 70))
                oversold = int(params.get("oversold", 30))
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period_len).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period_len).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                rsi_value = rsi.iloc[-1]
                if not pd.isna(rsi_value):
                    if rsi_value < oversold: signal = "BUY"
                    elif rsi_value > overbought: signal = "SELL"

            # Execute Trade
            if signal == "BUY" and sim.position == 0:
                shares = int(sim.balance // current_price)
                if shares > 0:
                    cost = shares * current_price
                    sim.balance -= cost
                    sim.position = shares
                    trade = SimulationTrade(
                        simulation_id=sim.id,
                        type='BUY',
                        shares=shares,
                        price=current_price,
                        balance_after=sim.balance,
                        timestamp=datetime.utcnow()
                    )
                    db.add(trade)
                    print(f"Simulation {sim.id} ({sim.ticker}): Auto-BUY {shares} @ ${current_price:.2f}")
                    
            elif signal == "SELL" and sim.position > 0:
                revenue = sim.position * current_price
                sim.balance += revenue
                trade = SimulationTrade(
                    simulation_id=sim.id,
                    type='SELL',
                    shares=sim.position,
                    price=current_price,
                    balance_after=sim.balance,
                    timestamp=datetime.utcnow()
                )
                db.add(trade)
                print(f"Simulation {sim.id} ({sim.ticker}): Auto-SELL {sim.position} @ ${current_price:.2f}")
                sim.position = 0
                
            sim.last_run_time = datetime.utcnow()
            await db.commit()
            
        except Exception as e:
            print(f"Error evaluating simulation {sim.id}: {e}")

    @staticmethod
    async def process_active_simulations():
        """
        Loops through all active simulations and checks signals.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Simulation).where(Simulation.is_active == True))
            simulations = result.scalars().all()
            
            if not simulations:
                return

            print(f"Running background updates for {len(simulations)} active simulations...")
            for sim in simulations:
                await SimulationManager.evaluate_simulation(sim, db)
                await asyncio.sleep(1) # Tiny throttle

    @staticmethod
    async def start_scheduler(interval_minutes=5):
        """
        Main loop for the background simulation thread.
        """
        # Initial delay to give the API time to breathe on startup
        await asyncio.sleep(5)
        while True:
            try:
                await SimulationManager.process_active_simulations()
            except Exception as e:
                print(f"Simulation Scheduler Error: {e}")
            await asyncio.sleep(interval_minutes * 60)
