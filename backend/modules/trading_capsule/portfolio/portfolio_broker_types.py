"""
Portfolio Broker Types (S4.2)
=============================

Type definitions for Portfolio Broker and Multi-Strategy Execution.

Includes:
- PortfolioTrade: Trade linked to portfolio slot
- PortfolioPosition: Position per strategy slot
- PortfolioOrder: Order routed through portfolio
- ExecutionEvent: Event for portfolio execution pipeline
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# Enums
# ===========================================

class OrderSide(Enum):
    """Order side"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(Enum):
    """Order status"""
    NEW = "NEW"
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class TradeType(Enum):
    """Trade type"""
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ADD = "ADD"           # Adding to position
    PARTIAL_EXIT = "PARTIAL_EXIT"


class PositionSide(Enum):
    """Position side"""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class ExecutionEventType(Enum):
    """Execution event type"""
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    POSITION_UPDATED = "POSITION_UPDATED"


# ===========================================
# PortfolioOrder (S4.2.1)
# ===========================================

@dataclass
class PortfolioOrder:
    """
    Order routed through portfolio layer.
    
    Links to simulation_id, slot_id, and strategy_id.
    """
    order_id: str = field(default_factory=lambda: f"pord_{uuid.uuid4().hex[:10]}")
    
    # Parent references
    simulation_id: str = ""
    slot_id: str = ""
    strategy_id: str = ""
    
    # Order details
    asset: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    
    quantity: float = 0.0
    price: Optional[float] = None       # For limit orders
    notional_usd: float = 0.0
    
    # Status
    status: OrderStatus = OrderStatus.NEW
    
    # Fill info
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    filled_notional_usd: float = 0.0
    fee_usd: float = 0.0
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None
    
    # Metadata
    trade_type: TradeType = TradeType.ENTRY
    source_signal_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "simulation_id": self.simulation_id,
            "slot_id": self.slot_id,
            "strategy_id": self.strategy_id,
            "asset": self.asset,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": round(self.quantity, 8),
            "price": round(self.price, 8) if self.price else None,
            "notional_usd": round(self.notional_usd, 2),
            "status": self.status.value,
            "fill": {
                "filled_quantity": round(self.filled_quantity, 8),
                "filled_price": round(self.filled_price, 8),
                "filled_notional_usd": round(self.filled_notional_usd, 2),
                "fee_usd": round(self.fee_usd, 4)
            },
            "timestamps": {
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "filled_at": self.filled_at.isoformat() if self.filled_at else None
            },
            "trade_type": self.trade_type.value,
            "source_signal_id": self.source_signal_id
        }


# ===========================================
# PortfolioPosition (S4.2.2)
# ===========================================

@dataclass
class PortfolioPosition:
    """
    Position per strategy slot.
    
    Tracks position state for one strategy in portfolio.
    """
    position_id: str = field(default_factory=lambda: f"ppos_{uuid.uuid4().hex[:10]}")
    
    # Parent references
    simulation_id: str = ""
    slot_id: str = ""
    strategy_id: str = ""
    
    # Position details
    asset: str = ""
    symbol: str = ""
    
    side: PositionSide = PositionSide.FLAT
    size: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    
    # Value calculations
    notional_usd: float = 0.0
    unrealized_pnl_usd: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    # Risk levels
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Timestamps
    opened_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "simulation_id": self.simulation_id,
            "slot_id": self.slot_id,
            "strategy_id": self.strategy_id,
            "asset": self.asset,
            "symbol": self.symbol,
            "side": self.side.value,
            "size": round(self.size, 8),
            "entry_price": round(self.entry_price, 8),
            "current_price": round(self.current_price, 8),
            "value": {
                "notional_usd": round(self.notional_usd, 2),
                "unrealized_pnl_usd": round(self.unrealized_pnl_usd, 2),
                "unrealized_pnl_pct": round(self.unrealized_pnl_pct, 4)
            },
            "risk": {
                "stop_loss": round(self.stop_loss, 8) if self.stop_loss else None,
                "take_profit": round(self.take_profit, 8) if self.take_profit else None
            },
            "timestamps": {
                "opened_at": self.opened_at.isoformat() if self.opened_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None
            }
        }


# ===========================================
# PortfolioTrade (S4.2.3)
# ===========================================

@dataclass
class PortfolioTrade:
    """
    Completed trade in portfolio.
    
    Records a round-trip trade with entry and exit.
    """
    trade_id: str = field(default_factory=lambda: f"ptrd_{uuid.uuid4().hex[:10]}")
    
    # Parent references
    simulation_id: str = ""
    slot_id: str = ""
    strategy_id: str = ""
    
    # Trade details
    asset: str = ""
    symbol: str = ""
    side: str = ""              # LONG, SHORT
    
    # Entry
    entry_price: float = 0.0
    entry_quantity: float = 0.0
    entry_notional_usd: float = 0.0
    entry_timestamp: Optional[datetime] = None
    entry_order_id: str = ""
    
    # Exit
    exit_price: float = 0.0
    exit_quantity: float = 0.0
    exit_notional_usd: float = 0.0
    exit_timestamp: Optional[datetime] = None
    exit_order_id: str = ""
    
    # PnL
    realized_pnl_usd: float = 0.0
    realized_pnl_pct: float = 0.0
    r_multiple: float = 0.0           # Risk-adjusted return
    
    # Fees
    total_fees_usd: float = 0.0
    
    # Duration
    holding_period_seconds: int = 0
    
    # Status
    is_closed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "simulation_id": self.simulation_id,
            "slot_id": self.slot_id,
            "strategy_id": self.strategy_id,
            "asset": self.asset,
            "symbol": self.symbol,
            "side": self.side,
            "entry": {
                "price": round(self.entry_price, 8),
                "quantity": round(self.entry_quantity, 8),
                "notional_usd": round(self.entry_notional_usd, 2),
                "timestamp": self.entry_timestamp.isoformat() if self.entry_timestamp else None,
                "order_id": self.entry_order_id
            },
            "exit": {
                "price": round(self.exit_price, 8),
                "quantity": round(self.exit_quantity, 8),
                "notional_usd": round(self.exit_notional_usd, 2),
                "timestamp": self.exit_timestamp.isoformat() if self.exit_timestamp else None,
                "order_id": self.exit_order_id
            },
            "pnl": {
                "realized_pnl_usd": round(self.realized_pnl_usd, 2),
                "realized_pnl_pct": round(self.realized_pnl_pct, 4),
                "r_multiple": round(self.r_multiple, 2)
            },
            "total_fees_usd": round(self.total_fees_usd, 4),
            "holding_period_seconds": self.holding_period_seconds,
            "is_closed": self.is_closed
        }


# ===========================================
# ExecutionEvent (S4.2.4)
# ===========================================

@dataclass
class ExecutionEvent:
    """
    Event in portfolio execution pipeline.
    
    Used for event-driven execution tracking.
    """
    event_id: str = field(default_factory=lambda: f"pevt_{uuid.uuid4().hex[:8]}")
    
    simulation_id: str = ""
    slot_id: str = ""
    
    event_type: ExecutionEventType = ExecutionEventType.ORDER_SUBMITTED
    
    # Related entities
    order_id: Optional[str] = None
    position_id: Optional[str] = None
    trade_id: Optional[str] = None
    
    # Event data
    data: Dict[str, Any] = field(default_factory=dict)
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "simulation_id": self.simulation_id,
            "slot_id": self.slot_id,
            "event_type": self.event_type.value,
            "order_id": self.order_id,
            "position_id": self.position_id,
            "trade_id": self.trade_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ===========================================
# Slot Execution Summary
# ===========================================

@dataclass
class SlotExecutionSummary:
    """Summary of execution for a slot"""
    slot_id: str = ""
    strategy_id: str = ""
    
    # Orders
    total_orders: int = 0
    filled_orders: int = 0
    rejected_orders: int = 0
    
    # Trades
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Position
    has_open_position: bool = False
    position_side: str = "FLAT"
    position_size: float = 0.0
    
    # PnL
    realized_pnl_usd: float = 0.0
    unrealized_pnl_usd: float = 0.0
    total_fees_usd: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "strategy_id": self.strategy_id,
            "orders": {
                "total": self.total_orders,
                "filled": self.filled_orders,
                "rejected": self.rejected_orders
            },
            "trades": {
                "total": self.total_trades,
                "winning": self.winning_trades,
                "losing": self.losing_trades,
                "win_rate": round(self.winning_trades / self.total_trades, 4) if self.total_trades > 0 else 0.0
            },
            "position": {
                "has_open": self.has_open_position,
                "side": self.position_side,
                "size": round(self.position_size, 8)
            },
            "pnl": {
                "realized_usd": round(self.realized_pnl_usd, 2),
                "unrealized_usd": round(self.unrealized_pnl_usd, 2),
                "total_fees_usd": round(self.total_fees_usd, 4)
            }
        }
