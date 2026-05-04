"""
Normalized Exchange Models

All exchange adapters MUST return data in these formats.
This ensures UI and other services don't care about exchange specifics.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class AccountInfo(BaseModel):
    """Normalized account info"""
    account_id: str
    exchange: str  # "paper", "binance_testnet", "bybit_demo"
    account_type: str  # "SPOT", "FUTURES", "MARGIN"
    status: str  # "ACTIVE", "SUSPENDED"
    can_trade: bool
    can_withdraw: bool
    can_deposit: bool
    created_at: Optional[datetime] = None


class Balance(BaseModel):
    """Normalized balance"""
    asset: str  # "USDT", "BTC", etc.
    free: float  # available balance
    locked: float  # locked in orders
    total: float  # total = free + locked
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 8)
        }


class Position(BaseModel):
    """Normalized position"""
    symbol: str  # "BTCUSDT"
    side: Literal["LONG", "SHORT"]  # position side
    qty: float  # position quantity
    entry_price: float  # average entry price
    mark_price: float  # current mark price
    unrealized_pnl: float  # unrealized P&L
    unrealized_pnl_pct: float  # unrealized P&L %
    realized_pnl: float  # realized P&L (from this position)
    leverage: Optional[float] = 1.0  # leverage (1.0 for spot)
    status: Literal["OPEN", "CLOSED"]
    liquidation_price: Optional[float] = None  # for futures
    opened_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 8),
            datetime: lambda v: v.isoformat()
        }


class Order(BaseModel):
    """Normalized order"""
    order_id: str  # exchange order ID
    client_order_id: Optional[str] = None  # client-provided ID
    symbol: str  # "BTCUSDT"
    side: Literal["BUY", "SELL"]
    type: Literal["MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"]
    price: float  # limit price (0 for MARKET)
    stop_price: Optional[float] = None  # stop price (for STOP orders)
    qty: float  # order quantity
    filled_qty: float  # filled quantity
    remaining_qty: float  # remaining quantity
    status: Literal["NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"]
    time_in_force: Optional[str] = "GTC"  # "GTC", "IOC", "FOK"
    reduce_only: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 8),
            datetime: lambda v: v.isoformat()
        }


class Fill(BaseModel):
    """Normalized fill/trade"""
    fill_id: str  # exchange fill/trade ID
    order_id: str  # parent order ID
    symbol: str  # "BTCUSDT"
    side: Literal["BUY", "SELL"]
    price: float  # execution price
    qty: float  # filled quantity
    quote_qty: float  # filled quote quantity (price * qty)
    fee: float  # trading fee
    fee_asset: str  # fee currency ("USDT", "BNB", etc.)
    is_maker: bool  # True if maker, False if taker
    timestamp: datetime  # execution timestamp
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 8),
            datetime: lambda v: v.isoformat()
        }


class OrderRequest(BaseModel):
    """Normalized order request"""
    symbol: str
    side: Literal["BUY", "SELL"]
    type: Literal["MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"]
    quantity: float
    price: Optional[float] = None  # required for LIMIT
    stop_price: Optional[float] = None  # required for STOP orders
    time_in_force: Optional[str] = "GTC"
    reduce_only: bool = False
    client_order_id: Optional[str] = None


# Legacy model for backward compatibility
class OrderResponse(BaseModel):
    """Legacy order response model (for backward compat with old paper_adapter)."""
    order_id: str
    client_order_id: Optional[str] = None
    symbol: str
    side: str
    type: str
    price: float
    qty: float
    filled_qty: float = 0.0
    status: str
    timestamp: datetime
    
    # Execution quality metrics (legacy)
    expected_fill_price: Optional[float] = None
    actual_fill_price: Optional[float] = None
    slippage_bps: Optional[float] = None
    fill_quality_score: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

