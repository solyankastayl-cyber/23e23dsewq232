"""
Execution Gateway Types

PHASE 39 — Execution Gateway Layer

Types for unified execution pipeline.

Key concepts:
- Execution Request: From Execution Brain
- Safety Gate Result: From Risk Budget Engine
- Execution Order: To Exchange Adapter
- Execution Fill: From Exchange
- Portfolio Update: To Portfolio Manager
"""

from typing import Literal, Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

class ExecutionMode(str, Enum):
    """Execution mode - CRITICAL CONFIG"""
    PAPER = "PAPER"           # Simulated fills
    LIVE = "LIVE"             # Real exchange orders
    APPROVAL = "APPROVAL"     # Requires human approval


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"               # Awaiting safety check
    APPROVED = "APPROVED"             # Passed safety, awaiting execution
    REJECTED = "REJECTED"             # Failed safety check
    AWAITING_APPROVAL = "AWAITING_APPROVAL"  # Needs human approval
    SUBMITTED = "SUBMITTED"           # Sent to exchange
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class SafetyCheckType(str, Enum):
    PORTFOLIO_RISK = "PORTFOLIO_RISK"
    STRATEGY_RISK = "STRATEGY_RISK"
    POSITION_LIMIT = "POSITION_LIMIT"
    LIQUIDITY_IMPACT = "LIQUIDITY_IMPACT"
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    MAX_ORDER_SIZE = "MAX_ORDER_SIZE"


# ══════════════════════════════════════════════════════════════
# Execution Request (from Execution Brain)
# ══════════════════════════════════════════════════════════════

class ExecutionRequest(BaseModel):
    """
    Request from Execution Brain to execute a trade.
    
    This is the entry point to the Execution Gateway.
    """
    request_id: str = Field(default_factory=lambda: f"req_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    # Trade details
    symbol: str
    side: OrderSide
    size_usd: float = Field(gt=0)
    size_base: Optional[float] = None  # In base asset (e.g., BTC)
    
    # Order params
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"
    
    # Strategy context
    strategy: str
    hypothesis_id: Optional[str] = None
    execution_plan_id: Optional[str] = None
    
    # Execution preferences
    preferred_exchange: Optional[str] = None
    urgency: str = "NORMAL"  # LOW, NORMAL, HIGH, IMMEDIATE
    reduce_only: bool = False
    
    # Risk params (from Execution Brain)
    max_slippage_bps: float = 50.0
    expected_price: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Safety Gate Types
# ══════════════════════════════════════════════════════════════

class SafetyCheckResult(BaseModel):
    """Result of a single safety check."""
    check_type: SafetyCheckType
    passed: bool
    reason: str = ""
    value: float = 0.0
    limit: float = 0.0
    severity: str = "NORMAL"  # NORMAL, WARNING, CRITICAL


class SafetyGateResult(BaseModel):
    """
    Result from Safety Gate (Risk Budget + Portfolio + Liquidity checks).
    
    All checks must pass for order to proceed.
    """
    request_id: str
    
    # Overall result
    approved: bool
    blocked_reason: Optional[str] = None
    
    # Individual checks
    checks: List[SafetyCheckResult] = Field(default_factory=list)
    
    # Adjustments (if order was modified)
    original_size_usd: float = 0.0
    approved_size_usd: float = 0.0
    size_adjusted: bool = False
    adjustment_reason: Optional[str] = None
    
    # Risk metrics at time of check
    current_portfolio_risk: float = 0.0
    strategy_risk_used: float = 0.0
    strategy_risk_remaining: float = 0.0
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Execution Order (to Exchange)
# ══════════════════════════════════════════════════════════════

class ExecutionOrder(BaseModel):
    """
    Order to be sent to exchange.
    
    Created after passing Safety Gate.
    """
    order_id: str = Field(default_factory=lambda: f"ord_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    request_id: str  # Link to original request
    
    # Exchange routing
    exchange: str  # BINANCE, BYBIT, OKX, HYPERLIQUID
    
    # Order details
    symbol: str
    exchange_symbol: str  # Exchange-specific format
    side: OrderSide
    order_type: OrderType
    
    # Size
    size_base: float  # In base asset
    size_quote: float  # In quote (usually USDT)
    
    # Pricing
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    expected_price: float = 0.0
    
    # Execution params
    time_in_force: str = "GTC"
    reduce_only: bool = False
    post_only: bool = False
    
    # Strategy context
    strategy: str
    
    # Status
    status: OrderStatus = OrderStatus.PENDING
    
    # Exchange response (filled after submission)
    exchange_order_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ══════════════════════════════════════════════════════════════
# Execution Fill (from Exchange)
# ══════════════════════════════════════════════════════════════

class ExecutionFill(BaseModel):
    """
    Fill received from exchange.
    """
    fill_id: str = Field(default_factory=lambda: f"fill_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    order_id: str
    request_id: str
    exchange_order_id: str
    
    # Exchange
    exchange: str
    symbol: str
    
    # Fill details
    side: OrderSide
    filled_size: float  # In base asset
    filled_value: float  # In quote
    avg_price: float
    
    # Execution quality
    expected_price: float
    slippage_bps: float  # (avg_price - expected) / expected * 10000
    fee: float = 0.0
    fee_asset: str = "USDT"
    
    # Result
    is_complete: bool  # Order fully filled
    remaining_size: float = 0.0
    
    # Strategy
    strategy: str
    
    # Timestamps
    filled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Portfolio Update (to Portfolio Manager)
# ══════════════════════════════════════════════════════════════

class PortfolioUpdateEvent(BaseModel):
    """
    Event to update Portfolio Manager after fill.
    """
    event_id: str = Field(default_factory=lambda: f"evt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    fill_id: str
    order_id: str
    
    # Position change
    symbol: str
    exchange: str
    strategy: str
    
    side: OrderSide
    size_change: float  # Positive for buy, negative for sell
    value_change: float
    avg_price: float
    
    # New position state (after update)
    new_position_size: Optional[float] = None
    new_position_value: Optional[float] = None
    new_avg_entry: Optional[float] = None
    
    # PnL (for closing trades)
    realized_pnl: Optional[float] = None
    
    # Risk update
    risk_contribution_change: float = 0.0
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Approval Request (for APPROVAL mode)
# ══════════════════════════════════════════════════════════════

class ApprovalRequest(BaseModel):
    """
    Request for human approval before execution.
    
    Used in APPROVAL mode (Decision Support).
    """
    approval_id: str = Field(default_factory=lambda: f"apr_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    request_id: str
    order_id: str
    
    # Order details
    symbol: str
    exchange: str
    side: OrderSide
    size_usd: float
    size_base: float
    order_type: OrderType
    
    # Strategy context
    strategy: str
    hypothesis_id: Optional[str] = None
    
    # Risk context
    portfolio_risk: float
    strategy_risk: float
    expected_slippage_bps: float
    liquidity_impact: str  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Recommendation
    system_recommendation: str  # APPROVE, REDUCE, REJECT
    recommendation_reason: str
    suggested_size_usd: float
    
    # Timing
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Status
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED, MODIFIED
    approved_by: Optional[str] = None
    decision_at: Optional[datetime] = None
    approved_size_usd: Optional[float] = None


# ══════════════════════════════════════════════════════════════
# Execution Result (final response)
# ══════════════════════════════════════════════════════════════

class ExecutionResult(BaseModel):
    """
    Final result of execution request.
    
    Returned to Execution Brain.
    """
    request_id: str
    
    # Status
    success: bool
    status: OrderStatus
    
    # Order details
    order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    exchange: Optional[str] = None
    
    # Execution details
    symbol: str
    side: OrderSide
    requested_size_usd: float
    filled_size_usd: float = 0.0
    filled_size_base: float = 0.0
    avg_price: float = 0.0
    
    # Execution quality
    expected_price: float = 0.0
    slippage_bps: float = 0.0
    fee: float = 0.0
    total_cost: float = 0.0
    
    # Safety
    safety_check_passed: bool = True
    safety_adjustments: Optional[str] = None
    
    # Failure info
    failure_reason: Optional[str] = None
    
    # Timing
    latency_ms: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# Exchange Route Config
# ══════════════════════════════════════════════════════════════

class ExchangeRouteConfig(BaseModel):
    """
    Configuration for symbol routing.
    
    Simple version: symbol → exchange
    Future: Smart Order Routing
    """
    symbol: str
    preferred_exchange: str
    fallback_exchanges: List[str] = Field(default_factory=list)
    reason: str = ""


# ══════════════════════════════════════════════════════════════
# Gateway Config
# ══════════════════════════════════════════════════════════════

class GatewayConfig(BaseModel):
    """
    Execution Gateway configuration.
    """
    execution_mode: ExecutionMode = ExecutionMode.PAPER
    
    # Safety limits
    max_single_order_usd: float = 100000.0
    daily_loss_limit_usd: float = 50000.0
    max_portfolio_risk: float = 0.20  # 20%
    
    # Slippage tolerance
    max_slippage_bps: float = 100.0
    
    # Approval timeout
    approval_timeout_seconds: int = 300  # 5 minutes
    
    # Exchange defaults
    default_exchange: str = "BINANCE"
    testnet_mode: bool = True
    
    # Retries
    max_retries: int = 3
    retry_delay_ms: int = 1000
