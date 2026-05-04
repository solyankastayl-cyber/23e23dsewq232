"""
Trade Types (TR3)
=================

Type definitions for Trade Monitor.

Entities:
- Order: Order record
- Fill: Execution fill
- Trade: Completed trade (entry + exit)
- ExecutionLog: Execution audit log
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# Enums
# ===========================================

class OrderStatus(Enum):
    """Order status"""
    NEW = "NEW"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderType(Enum):
    """Order type"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"


class OrderSide(Enum):
    """Order side"""
    BUY = "BUY"
    SELL = "SELL"


class ExecutionLogType(Enum):
    """Execution log event types"""
    SIGNAL = "SIGNAL"           # Strategy signal
    ORDER_REQUEST = "ORDER_REQUEST"  # Order sent
    ORDER_ACCEPTED = "ORDER_ACCEPTED"  # Broker accepted
    ORDER_REJECTED = "ORDER_REJECTED"  # Broker rejected
    FILL = "FILL"               # Partial/full fill
    CANCEL_REQUEST = "CANCEL_REQUEST"  # Cancel sent
    CANCELLED = "CANCELLED"     # Order cancelled
    ERROR = "ERROR"             # Error occurred
    INFO = "INFO"               # Informational


# ===========================================
# Order
# ===========================================

@dataclass
class Order:
    """
    Order record.
    
    Source of truth for order lifecycle.
    """
    order_id: str = field(default_factory=lambda: f"ord_{uuid.uuid4().hex[:8]}")
    
    # External ID (from exchange)
    exchange_order_id: str = ""
    
    # Context
    exchange: str = ""
    connection_id: str = ""
    symbol: str = ""
    
    # Order details
    side: OrderSide = OrderSide.BUY
    type: OrderType = OrderType.MARKET
    
    # Quantities
    quantity: float = 0.0
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    
    # Prices
    price: float = 0.0          # Limit price
    stop_price: float = 0.0     # Stop trigger price
    avg_fill_price: float = 0.0
    
    # Status
    status: OrderStatus = OrderStatus.NEW
    
    # Fees
    total_fee: float = 0.0
    fee_asset: str = ""
    
    # Strategy context
    strategy_id: str = ""
    signal_id: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "exchange_order_id": self.exchange_order_id,
            "exchange": self.exchange,
            "connection_id": self.connection_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "type": self.type.value,
            "quantity": round(self.quantity, 8),
            "filled_quantity": round(self.filled_quantity, 8),
            "remaining_quantity": round(self.remaining_quantity, 8),
            "price": round(self.price, 8),
            "stop_price": round(self.stop_price, 8),
            "avg_fill_price": round(self.avg_fill_price, 8),
            "status": self.status.value,
            "total_fee": round(self.total_fee, 8),
            "fee_asset": self.fee_asset,
            "strategy_id": self.strategy_id,
            "signal_id": self.signal_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None
        }


# ===========================================
# Fill
# ===========================================

@dataclass
class Fill:
    """
    Single fill execution.
    
    An order can have multiple fills.
    """
    fill_id: str = field(default_factory=lambda: f"fill_{uuid.uuid4().hex[:8]}")
    
    # Reference
    order_id: str = ""
    exchange_fill_id: str = ""
    
    # Context
    exchange: str = ""
    symbol: str = ""
    
    # Fill details
    side: OrderSide = OrderSide.BUY
    quantity: float = 0.0
    price: float = 0.0
    
    # Fee
    fee: float = 0.0
    fee_asset: str = ""
    
    # Value
    notional_value: float = 0.0
    
    # Timestamp
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "fill_id": self.fill_id,
            "order_id": self.order_id,
            "exchange_fill_id": self.exchange_fill_id,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": round(self.quantity, 8),
            "price": round(self.price, 8),
            "fee": round(self.fee, 8),
            "fee_asset": self.fee_asset,
            "notional_value": round(self.notional_value, 4),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ===========================================
# Trade
# ===========================================

@dataclass
class Trade:
    """
    Completed trade (position entry + exit).
    
    This is the final closed trade with PnL.
    """
    trade_id: str = field(default_factory=lambda: f"trade_{uuid.uuid4().hex[:8]}")
    
    # Context
    exchange: str = ""
    symbol: str = ""
    
    # Direction
    side: str = "LONG"  # LONG / SHORT
    
    # Entry
    entry_order_id: str = ""
    entry_price: float = 0.0
    entry_quantity: float = 0.0
    entry_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Exit
    exit_order_id: str = ""
    exit_price: float = 0.0
    exit_quantity: float = 0.0
    exit_time: Optional[datetime] = None
    
    # PnL
    gross_pnl: float = 0.0
    total_fees: float = 0.0
    net_pnl: float = 0.0
    pnl_pct: float = 0.0
    
    # Duration
    duration_minutes: float = 0.0
    
    # Strategy context
    strategy_id: str = ""
    
    # Status
    is_closed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "side": self.side,
            "entry": {
                "order_id": self.entry_order_id,
                "price": round(self.entry_price, 8),
                "quantity": round(self.entry_quantity, 8),
                "time": self.entry_time.isoformat() if self.entry_time else None
            },
            "exit": {
                "order_id": self.exit_order_id,
                "price": round(self.exit_price, 8),
                "quantity": round(self.exit_quantity, 8),
                "time": self.exit_time.isoformat() if self.exit_time else None
            } if self.is_closed else None,
            "pnl": {
                "gross": round(self.gross_pnl, 4),
                "fees": round(self.total_fees, 4),
                "net": round(self.net_pnl, 4),
                "pct": round(self.pnl_pct, 4)
            },
            "duration_minutes": round(self.duration_minutes, 1),
            "strategy_id": self.strategy_id,
            "is_closed": self.is_closed
        }


# ===========================================
# ExecutionLog
# ===========================================

@dataclass
class ExecutionLog:
    """
    Execution audit log entry.
    
    For debugging and audit trail.
    """
    log_id: str = field(default_factory=lambda: f"log_{uuid.uuid4().hex[:8]}")
    
    # Type
    event_type: ExecutionLogType = ExecutionLogType.INFO
    
    # Context
    order_id: str = ""
    strategy_id: str = ""
    symbol: str = ""
    exchange: str = ""
    
    # Content
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Severity
    is_error: bool = False
    
    # Timestamp
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "event_type": self.event_type.value,
            "order_id": self.order_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "message": self.message,
            "details": self.details,
            "is_error": self.is_error,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ===========================================
# TradesSummary
# ===========================================

@dataclass
class TradesSummary:
    """
    Summary of trading activity.
    """
    total_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    
    total_fills: int = 0
    
    closed_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_pnl: float = 0.0
    total_pnl: float = 0.0
    total_fees: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "orders": {
                "total": self.total_orders,
                "filled": self.filled_orders,
                "cancelled": self.cancelled_orders
            },
            "fills": self.total_fills,
            "trades": {
                "closed": self.closed_trades,
                "winning": self.winning_trades,
                "losing": self.losing_trades,
                "win_rate": round(self.win_rate, 4),
                "profit_factor": round(self.profit_factor, 2),
                "avg_pnl": round(self.avg_pnl, 4),
                "total_pnl": round(self.total_pnl, 4),
                "total_fees": round(self.total_fees, 4)
            }
        }
