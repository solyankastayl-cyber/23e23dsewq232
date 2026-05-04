"""
Market Data Types - PHASE 5.2
=============================

Unified types for live market data streaming.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Timeframe(str, Enum):
    """Supported timeframes"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class MarketDataSource(str, Enum):
    """Data source type"""
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"
    OKX = "OKX"
    AGGREGATED = "AGGREGATED"


# ============================================
# Core Market Data Types
# ============================================

class MarketTick(BaseModel):
    """Single market tick/trade"""
    exchange: str
    symbol: str
    price: float
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    volume: float = 0.0
    side: Optional[str] = None  # BUY/SELL
    trade_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def mid_price(self) -> float:
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return self.price


class MarketCandle(BaseModel):
    """OHLCV candle"""
    exchange: str
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float = 0.0
    trades_count: int = 0
    start_time: datetime
    end_time: datetime
    is_closed: bool = False
    
    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def wick_upper(self) -> float:
        return self.high - max(self.open, self.close)
    
    @property
    def wick_lower(self) -> float:
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def range_pct(self) -> float:
        if self.low > 0:
            return ((self.high - self.low) / self.low) * 100
        return 0.0


class OrderbookLevel(BaseModel):
    """Single orderbook level"""
    price: float
    size: float
    orders_count: int = 0


class MarketOrderbook(BaseModel):
    """Live orderbook snapshot"""
    exchange: str
    symbol: str
    bids: List[OrderbookLevel] = Field(default_factory=list)
    asks: List[OrderbookLevel] = Field(default_factory=list)
    best_bid: float = 0.0
    best_ask: float = 0.0
    spread: float = 0.0
    spread_bps: float = 0.0
    mid_price: float = 0.0
    bid_depth: float = 0.0  # Total bid volume
    ask_depth: float = 0.0  # Total ask volume
    imbalance: float = 0.0  # Bid/Ask imbalance ratio
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sequence: Optional[int] = None
    
    def calculate_metrics(self):
        """Calculate derived metrics"""
        if self.bids:
            self.best_bid = self.bids[0].price
            self.bid_depth = sum(b.size for b in self.bids)
        if self.asks:
            self.best_ask = self.asks[0].price
            self.ask_depth = sum(a.size for a in self.asks)
        
        if self.best_bid > 0 and self.best_ask > 0:
            self.spread = self.best_ask - self.best_bid
            self.spread_bps = (self.spread / self.best_bid) * 10000
            self.mid_price = (self.best_bid + self.best_ask) / 2
        
        total_depth = self.bid_depth + self.ask_depth
        if total_depth > 0:
            self.imbalance = (self.bid_depth - self.ask_depth) / total_depth


class MarketSnapshot(BaseModel):
    """Aggregated market snapshot for a symbol"""
    symbol: str
    last_price: float
    price_change_24h: float = 0.0
    price_change_pct_24h: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    spread_bps: float = 0.0
    volume_24h: float = 0.0
    quote_volume_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    vwap: float = 0.0  # Volume-weighted average price
    volatility: float = 0.0  # Recent volatility
    trades_count: int = 0
    active_exchanges: List[str] = Field(default_factory=list)
    primary_exchange: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional metrics
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class VolumeMetrics(BaseModel):
    """Volume analysis metrics"""
    symbol: str
    exchange: str
    timeframe: str
    
    # Basic volume
    current_volume: float = 0.0
    avg_volume: float = 0.0
    volume_ratio: float = 0.0  # current / avg
    
    # Buy/Sell breakdown
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    buy_sell_ratio: float = 0.0
    
    # Volume patterns
    is_volume_spike: bool = False
    spike_magnitude: float = 0.0
    
    # Rolling metrics
    rolling_volume_1h: float = 0.0
    rolling_volume_24h: float = 0.0
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MarketFeedConfig(BaseModel):
    """Configuration for market data feed"""
    exchange: str
    symbols: List[str]
    subscribe_ticker: bool = True
    subscribe_orderbook: bool = True
    subscribe_trades: bool = False
    subscribe_candles: bool = True
    candle_timeframes: List[str] = Field(default_factory=lambda: ["1m", "5m", "1h"])
    orderbook_depth: int = 10
    snapshot_interval_ms: int = 1000


class MarketFeedStatus(BaseModel):
    """Status of a market data feed"""
    exchange: str
    symbols: List[str]
    is_active: bool = False
    connected_at: Optional[datetime] = None
    last_update: Optional[datetime] = None
    tick_count: int = 0
    candle_count: int = 0
    orderbook_updates: int = 0
    errors: int = 0
    latency_ms: float = 0.0
    
    # Subscription status
    ticker_subscribed: bool = False
    orderbook_subscribed: bool = False
    trades_subscribed: bool = False
    candles_subscribed: bool = False


# ============================================
# API Request/Response Models
# ============================================

class StartFeedRequest(BaseModel):
    """Request to start market data feed"""
    exchange: str = "BINANCE"
    symbols: List[str] = Field(default_factory=lambda: ["BTCUSDT"])
    subscribe_ticker: bool = True
    subscribe_orderbook: bool = True
    subscribe_candles: bool = True
    candle_timeframes: List[str] = Field(default_factory=lambda: ["1m", "5m"])


class StopFeedRequest(BaseModel):
    """Request to stop market data feed"""
    exchange: str = "BINANCE"
    symbols: List[str] = Field(default_factory=list)


class CandleHistoryRequest(BaseModel):
    """Request for candle history"""
    symbol: str
    timeframe: str = "1h"
    exchange: Optional[str] = None
    limit: int = 100
