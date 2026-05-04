"""
Order Types
===========

Core types for PHASE 4.1 Order State Engine
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time
import uuid


class OrderState(str, Enum):
    """Order lifecycle states"""
    NEW = "NEW"                   # Order created, not yet submitted
    SUBMITTED = "SUBMITTED"       # Sent to exchange
    ACCEPTED = "ACCEPTED"         # Accepted by exchange
    PARTIAL_FILL = "PARTIAL_FILL" # Partially executed
    FILLED = "FILLED"             # Fully executed
    CANCELLED = "CANCELLED"       # Cancelled by user/system
    REJECTED = "REJECTED"         # Rejected by exchange
    FAILED = "FAILED"             # System failure
    EXPIRED = "EXPIRED"           # Time-based expiration


class OrderType(str, Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"


class OrderSide(str, Enum):
    """Order side"""
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(str, Enum):
    """Time in force"""
    GTC = "GTC"       # Good till cancelled
    IOC = "IOC"       # Immediate or cancel
    FOK = "FOK"       # Fill or kill
    GTD = "GTD"       # Good till date


class ExecutionEventType(str, Enum):
    """Execution event types"""
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_PARTIAL_FILL = "ORDER_PARTIAL_FILL"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_FAILED = "ORDER_FAILED"
    ORDER_EXPIRED = "ORDER_EXPIRED"
    ORDER_AMENDED = "ORDER_AMENDED"


# ===========================================
# Order Fill
# ===========================================

@dataclass
class OrderFill:
    """Single fill/execution"""
    fill_id: str = ""
    order_id: str = ""
    
    # Fill details
    filled_qty: float = 0.0
    fill_price: float = 0.0
    
    # Costs
    commission: float = 0.0
    commission_asset: str = "USDT"
    
    # Timing
    filled_at: int = 0
    
    # Exchange info
    exchange_fill_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "fillId": self.fill_id,
            "orderId": self.order_id,
            "filledQty": round(self.filled_qty, 8),
            "fillPrice": round(self.fill_price, 8),
            "commission": round(self.commission, 8),
            "commissionAsset": self.commission_asset,
            "filledAt": self.filled_at,
            "exchangeFillId": self.exchange_fill_id
        }


# ===========================================
# Order
# ===========================================

@dataclass
class Order:
    """Complete order representation"""
    order_id: str = ""
    client_order_id: str = ""
    
    # Identity
    symbol: str = ""
    exchange: str = ""
    strategy_id: str = ""
    position_id: str = ""
    
    # Order params
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.GTC
    
    # Quantities
    quantity: float = 0.0
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    
    # Prices
    price: float = 0.0            # Limit price
    stop_price: float = 0.0       # Stop trigger price
    avg_fill_price: float = 0.0   # Average execution price
    
    # State
    state: OrderState = OrderState.NEW
    previous_state: OrderState = OrderState.NEW
    
    # Fills
    fills: List[OrderFill] = field(default_factory=list)
    fill_count: int = 0
    
    # Costs
    total_commission: float = 0.0
    
    # Slippage
    expected_price: float = 0.0
    slippage_pct: float = 0.0
    
    # Error handling
    error_code: str = ""
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3
    
    # Exchange info
    exchange_order_id: str = ""
    
    # Timestamps
    created_at: int = 0
    submitted_at: int = 0
    accepted_at: int = 0
    filled_at: int = 0
    cancelled_at: int = 0
    updated_at: int = 0
    expires_at: int = 0
    
    # Metadata
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "orderId": self.order_id,
            "clientOrderId": self.client_order_id,
            "identity": {
                "symbol": self.symbol,
                "exchange": self.exchange,
                "strategyId": self.strategy_id,
                "positionId": self.position_id
            },
            "params": {
                "side": self.side.value,
                "type": self.order_type.value,
                "timeInForce": self.time_in_force.value
            },
            "quantity": {
                "total": round(self.quantity, 8),
                "filled": round(self.filled_quantity, 8),
                "remaining": round(self.remaining_quantity, 8),
                "fillPct": round(self.filled_quantity / self.quantity * 100, 1) if self.quantity > 0 else 0
            },
            "price": {
                "limit": round(self.price, 8) if self.price else None,
                "stop": round(self.stop_price, 8) if self.stop_price else None,
                "avgFill": round(self.avg_fill_price, 8) if self.avg_fill_price else None,
                "expected": round(self.expected_price, 8) if self.expected_price else None
            },
            "state": {
                "current": self.state.value,
                "previous": self.previous_state.value
            },
            "fills": {
                "count": self.fill_count,
                "items": [f.to_dict() for f in self.fills[-5:]]  # Last 5 fills
            },
            "costs": {
                "commission": round(self.total_commission, 8),
                "slippagePct": round(self.slippage_pct, 4)
            },
            "error": {
                "code": self.error_code,
                "message": self.error_message,
                "retryCount": self.retry_count
            } if self.error_code else None,
            "exchange": {
                "orderId": self.exchange_order_id
            },
            "timestamps": {
                "createdAt": self.created_at,
                "submittedAt": self.submitted_at,
                "acceptedAt": self.accepted_at,
                "filledAt": self.filled_at,
                "cancelledAt": self.cancelled_at,
                "updatedAt": self.updated_at,
                "expiresAt": self.expires_at
            },
            "tags": self.tags
        }
    
    def is_active(self) -> bool:
        """Check if order is still active"""
        return self.state in [
            OrderState.NEW, 
            OrderState.SUBMITTED, 
            OrderState.ACCEPTED,
            OrderState.PARTIAL_FILL
        ]
    
    def is_terminal(self) -> bool:
        """Check if order is in terminal state"""
        return self.state in [
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.REJECTED,
            OrderState.FAILED,
            OrderState.EXPIRED
        ]


# ===========================================
# Execution Event
# ===========================================

@dataclass
class ExecutionEvent:
    """Execution event for audit trail"""
    event_id: str = ""
    event_type: ExecutionEventType = ExecutionEventType.ORDER_CREATED
    
    # Order reference
    order_id: str = ""
    client_order_id: str = ""
    
    # State transition
    from_state: OrderState = OrderState.NEW
    to_state: OrderState = OrderState.NEW
    
    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Fill info (if applicable)
    fill: Optional[OrderFill] = None
    
    # Timing
    timestamp: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventId": self.event_id,
            "eventType": self.event_type.value,
            "orderId": self.order_id,
            "clientOrderId": self.client_order_id,
            "transition": {
                "from": self.from_state.value,
                "to": self.to_state.value
            },
            "details": self.details,
            "fill": self.fill.to_dict() if self.fill else None,
            "timestamp": self.timestamp
        }


# ===========================================
# State Transition
# ===========================================

@dataclass
class StateTransition:
    """Valid state transition"""
    from_state: OrderState
    to_state: OrderState
    event_type: ExecutionEventType
    requires_fill: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_state.value,
            "to": self.to_state.value,
            "event": self.event_type.value,
            "requiresFill": self.requires_fill
        }


# ===========================================
# Order Summary
# ===========================================

@dataclass
class OrderSummary:
    """Summary of orders"""
    total_orders: int = 0
    active_orders: int = 0
    filled_orders: int = 0
    cancelled_orders: int = 0
    failed_orders: int = 0
    
    total_volume: float = 0.0
    total_commission: float = 0.0
    avg_fill_time_ms: float = 0.0
    avg_slippage_pct: float = 0.0
    
    by_state: Dict[str, int] = field(default_factory=dict)
    by_symbol: Dict[str, int] = field(default_factory=dict)
    by_strategy: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "orders": {
                "total": self.total_orders,
                "active": self.active_orders,
                "filled": self.filled_orders,
                "cancelled": self.cancelled_orders,
                "failed": self.failed_orders
            },
            "metrics": {
                "totalVolume": round(self.total_volume, 2),
                "totalCommission": round(self.total_commission, 4),
                "avgFillTimeMs": round(self.avg_fill_time_ms, 1),
                "avgSlippagePct": round(self.avg_slippage_pct, 4)
            },
            "breakdown": {
                "byState": self.by_state,
                "bySymbol": self.by_symbol,
                "byStrategy": self.by_strategy
            }
        }
