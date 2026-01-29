from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True)
    company_name = Column(String)
    sector = Column(String, nullable=True)
    
    prices = relationship("MarketData", back_populates="stock")
    news = relationship("News", back_populates="stock")

    # Caching fields
    cached_analysis = Column(Text, nullable=True) # Storing JSON as text for simplicity
    last_updated = Column(DateTime, nullable=True)

class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Integer)

    stock = relationship("Stock", back_populates="prices")

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    headline = Column(Text)
    url = Column(String)
    published_at = Column(DateTime)
    sentiment_score = Column(Float, nullable=True)
    
    stock = relationship("Stock", back_populates="news")

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True) # Placeholder for auth user id
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    quantity = Column(Integer, default=0)
    average_buy_price = Column(Float)

class Simulation(Base):
    __tablename__ = "simulations"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    strategy = Column(String) # 'SMA' or 'RSI'
    parameters = Column(Text) # JSON string of params
    balance = Column(Float, default=10000.0)
    position = Column(Integer, default=0) # Number of shares held
    is_active = Column(Boolean, default=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    last_run_time = Column(DateTime, nullable=True)
    initial_capital = Column(Float, default=10000.0)

class SimulationTrade(Base):
    __tablename__ = "simulation_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"))
    type = Column(String) # 'BUY' or 'SELL'
    shares = Column(Integer)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    balance_after = Column(Float)
    
    simulation = relationship("Simulation", backref="trades")
