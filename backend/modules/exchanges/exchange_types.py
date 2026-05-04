"""
Exchange Types - PHASE 5.1
==========================

Unified types for exchange interactions.
These types abstract away exchange-specific formats.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ExchangeId(str, Enum):
    """Supported exchanges"""
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"
    OKX = "OKX"


class OrderSide(str, Enum):
    """Order side"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"


class TimeInForce(str, Enum):
    """Time in force"""
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate Or Cancel
    FOK = "FOK"  # Fill Or Kill
    GTX = "GTX"  # Post Only


class OrderStatus(str, Enum):
    """Order status"""
    NEW = "NEW"
    PENDING = "PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class PositionSide(str, Enum):
    """Position side"""
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"  # Hedge mode


class MarginMode(str, Enum):
    """Margin mode"""
    CROSS = "CROSS"
    ISOLATED = "ISOLATED"


class StreamType(str, Enum):
    """WebSocket stream types"""
    TICKER = "TICKER"
    ORDERBOOK = "ORDERBOOK"
    TRADES = "TRADES"
    KLINE = "KLINE"
    USER_ORDERS = "USER_ORDERS"
    USER_POSITIONS = "USER_POSITIONS"
    USER_BALANCE = "USER_BALANCE"


class StreamStatus(str, Enum):
    """Stream status"""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


# ============================================
# Order Types
# ============================================

class ExchangeOrderRequest(BaseModel):
    """Unified order request"""
    exchange: ExchangeId = ExchangeId.BINANCE
    symbol: str = Field(..., description="Trading pair, e.g., BTCUSDT")
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    size: float = Field(..., gt=0, description="Order size in base currency")
    price: Optional[float] = Field(default=None, description="Limit price")
    stop_price: Optional[float] = Field(default=None, description="Stop/trigger price")
    time_in_force: TimeInForce = TimeInForce.GTC
    reduce_only: bool = False
    position_side: PositionSide = PositionSide.BOTH
    client_order_id: Optional[str] = None
    leverage: Optional[int] = None
    
    # Extra params for specific exchanges
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class ExchangeOrderResponse(BaseModel):
    """Unified order response"""
    exchange: ExchangeId
    exchange_order_id: str
    client_order_id: Optional[str] = None
    symbol: str
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    
    # Quantities
    original_size: float
    filled_size: float = 0.0
    remaining_size: float = 0.0
    
    # Prices
    price: Optional[float] = None
    avg_fill_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Fees
    fees: float = 0.0
    fee_asset: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Raw exchange response
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


# ============================================
# Position Types
# ============================================

class ExchangePosition(BaseModel):
    """Unified position"""
    exchange: ExchangeId
    symbol: str
    side: PositionSide
    size: float
    entry_price: float
    mark_price: float
    liquidation_price: Optional[float] = None
    
    # PnL
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    pnl_percentage: float = 0.0
    
    # Margin
    leverage: int = 1
    margin_mode: MarginMode = MarginMode.CROSS
    margin: float = 0.0
    maintenance_margin: float = 0.0
    
    # Timestamps
    opened_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


# ============================================
# Balance Types
# ============================================

class ExchangeBalance(BaseModel):
    """Unified balance"""
    exchange: ExchangeId
    asset: str
    free: float = 0.0
    locked: float = 0.0
    total: float = 0.0
    
    # USD value
    usd_value: Optional[float] = None
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AccountSummary(BaseModel):
    """Account summary"""
    exchange: ExchangeId
    total_balance_usd: float = 0.0
    available_balance_usd: float = 0.0
    margin_balance_usd: float = 0.0
    unrealized_pnl_usd: float = 0.0
    
    balances: List[ExchangeBalance] = Field(default_factory=list)
    positions: List[ExchangePosition] = Field(default_factory=list)
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Market Data Types
# ============================================

class ExchangeTicker(BaseModel):
    """Unified ticker"""
    exchange: ExchangeId
    symbol: str
    last_price: float
    bid_price: float
    ask_price: float
    bid_size: float = 0.0
    ask_size: float = 0.0
    
    # 24h stats
    high_24h: float = 0.0
    low_24h: float = 0.0
    volume_24h: float = 0.0
    quote_volume_24h: float = 0.0
    price_change_24h: float = 0.0
    price_change_pct_24h: float = 0.0
    
    # Funding (for perpetuals)
    funding_rate: Optional[float] = None
    next_funding_time: Optional[datetime] = None
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderbookLevel(BaseModel):
    """Orderbook level"""
    price: float
    size: float


class ExchangeOrderbook(BaseModel):
    """Unified orderbook"""
    exchange: ExchangeId
    symbol: str
    bids: List[OrderbookLevel] = Field(default_factory=list)
    asks: List[OrderbookLevel] = Field(default_factory=list)
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sequence: Optional[int] = None
    
    @property
    def best_bid(self) -> Optional[float]:
        return self.bids[0].price if self.bids else None
    
    @property
    def best_ask(self) -> Optional[float]:
        return self.asks[0].price if self.asks else None
    
    @property
    def spread(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return None
    
    @property
    def spread_bps(self) -> Optional[float]:
        if self.spread and self.best_bid:
            return (self.spread / self.best_bid) * 10000
        return None


# ============================================
# Connection Types
# ============================================

class ExchangeConnectionStatus(BaseModel):
    """Connection status"""
    exchange: ExchangeId
    connected: bool = False
    authenticated: bool = False
    
    # REST API status
    rest_available: bool = True
    rest_latency_ms: float = 0.0
    
    # WebSocket status
    ws_connected: bool = False
    ws_authenticated: bool = False
    
    # Rate limits
    rate_limit_remaining: int = 1000
    rate_limit_reset_at: Optional[datetime] = None
    
    # Error tracking
    last_error: Optional[str] = None
    error_count: int = 0
    
    connected_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StreamConfig(BaseModel):
    """Stream configuration"""
    exchange: ExchangeId
    stream_type: StreamType
    symbols: List[str] = Field(default_factory=list)
    interval: Optional[str] = None  # For klines: 1m, 5m, 1h, etc.


class ExchangeCredentials(BaseModel):
    """Exchange credentials reference (actual secrets in SEC2 Vault)"""
    exchange: ExchangeId
    api_key_ref: str  # Reference to SEC2 Vault
    api_secret_ref: str
    passphrase_ref: Optional[str] = None  # For OKX
    testnet: bool = False
    label: str = "default"


# ============================================
# Request/Response Models for API
# ============================================

class ConnectRequest(BaseModel):
    """Connect to exchange request"""
    exchange: ExchangeId
    testnet: bool = False
    credentials_label: str = "default"


class CreateOrderRequest(BaseModel):
    """Create order API request"""
    exchange: ExchangeId
    symbol: str
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    size: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    reduce_only: bool = False
    client_order_id: Optional[str] = None


class CancelOrderRequest(BaseModel):
    """Cancel order request"""
    exchange: ExchangeId
    order_id: str
    symbol: Optional[str] = None  # Some exchanges require symbol


class StreamRequest(BaseModel):
    """Stream control request"""
    exchange: ExchangeId
    stream_type: StreamType
    symbols: List[str] = Field(default_factory=list)
    action: str = Field(default="start", description="start/stop")
