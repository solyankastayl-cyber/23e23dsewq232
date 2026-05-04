"""
State Reconciliation Layer - Data Types
Models for reconciliation runs, mismatches, and exchange state.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MismatchType(str, Enum):
    """Types of reconciliation mismatches"""
    # Position mismatches
    GHOST_POSITION = "GHOST_POSITION"          # Internal position not on exchange
    MISSING_POSITION = "MISSING_POSITION"      # Exchange position not in internal
    POSITION_SIZE_MISMATCH = "POSITION_SIZE_MISMATCH"
    POSITION_SIDE_MISMATCH = "POSITION_SIDE_MISMATCH"
    POSITION_PRICE_MISMATCH = "POSITION_PRICE_MISMATCH"
    
    # Order mismatches
    GHOST_ORDER = "GHOST_ORDER"                # Internal order not on exchange
    MISSING_ORDER = "MISSING_ORDER"            # Exchange order not in internal
    ORDER_STATUS_MISMATCH = "ORDER_STATUS_MISMATCH"
    ORDER_FILL_MISMATCH = "ORDER_FILL_MISMATCH"
    
    # Balance mismatches
    BALANCE_DRIFT = "BALANCE_DRIFT"            # Balance differs from expected
    MARGIN_MISMATCH = "MARGIN_MISMATCH"
    
    # Fill mismatches
    PARTIAL_FILL_DESYNC = "PARTIAL_FILL_DESYNC"
    FILL_MISSING = "FILL_MISSING"


class MismatchSeverity(str, Enum):
    """Severity levels for mismatches"""
    CRITICAL = "CRITICAL"    # Requires immediate action, may halt trading
    HIGH = "HIGH"            # Significant issue, needs attention
    MEDIUM = "MEDIUM"        # Notable discrepancy
    LOW = "LOW"              # Minor difference, informational


class ReconciliationStatus(str, Enum):
    """Status of a reconciliation run"""
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"      # Some exchanges failed


class ReconciliationAction(str, Enum):
    """Actions taken to resolve mismatches"""
    NONE = "NONE"
    AUTO_FIXED = "AUTO_FIXED"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"
    QUARANTINE = "QUARANTINE"
    ALERT_SENT = "ALERT_SENT"


# ===========================================
# Exchange State Models
# ===========================================

class ExchangePosition(BaseModel):
    """Position as reported by exchange"""
    symbol: str
    side: str                  # LONG, SHORT
    size: float
    entry_price: float
    unrealized_pnl: float
    leverage: Optional[float] = None
    margin_type: Optional[str] = None
    liquidation_price: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExchangeOrder(BaseModel):
    """Order as reported by exchange"""
    order_id: str
    symbol: str
    side: str                  # BUY, SELL
    type: str                  # LIMIT, MARKET, etc.
    status: str                # NEW, FILLED, CANCELLED, etc.
    price: Optional[float] = None
    quantity: float
    filled_quantity: float = 0
    avg_fill_price: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ExchangeBalance(BaseModel):
    """Balance as reported by exchange"""
    asset: str
    free: float
    locked: float
    total: float


class ExchangeFill(BaseModel):
    """Fill/Trade as reported by exchange"""
    trade_id: str
    order_id: str
    symbol: str
    side: str
    price: float
    quantity: float
    fee: float
    fee_asset: str
    timestamp: datetime


class ExchangeState(BaseModel):
    """Complete exchange state snapshot"""
    exchange: str
    account_id: Optional[str] = None
    
    positions: List[ExchangePosition] = []
    orders: List[ExchangeOrder] = []
    balances: List[ExchangeBalance] = []
    fills: List[ExchangeFill] = []
    
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Metadata
    api_latency_ms: Optional[int] = None
    rate_limit_remaining: Optional[int] = None


# ===========================================
# Internal State Models
# ===========================================

class InternalPosition(BaseModel):
    """Position in our internal system"""
    position_id: str
    symbol: str
    side: str
    size: float
    entry_price: float
    strategy_id: Optional[str] = None
    profile_id: Optional[str] = None
    opened_at: datetime


class InternalOrder(BaseModel):
    """Order in our internal system"""
    order_id: str
    exchange_order_id: Optional[str] = None
    symbol: str
    side: str
    type: str
    status: str
    price: Optional[float] = None
    quantity: float
    filled_quantity: float = 0
    created_at: datetime


class InternalState(BaseModel):
    """Complete internal state snapshot"""
    positions: List[InternalPosition] = []
    orders: List[InternalOrder] = []
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ===========================================
# Mismatch Models
# ===========================================

class ReconciliationMismatch(BaseModel):
    """A single mismatch detected during reconciliation"""
    mismatch_id: str = Field(..., description="Unique identifier")
    
    mismatch_type: MismatchType
    severity: MismatchSeverity
    
    # Context
    exchange: str
    symbol: Optional[str] = None
    
    # What we expected
    internal_value: Optional[Dict[str, Any]] = None
    
    # What we found
    exchange_value: Optional[Dict[str, Any]] = None
    
    # Difference details
    description: str
    details: Optional[Dict[str, Any]] = None
    
    # Resolution
    action_taken: ReconciliationAction = ReconciliationAction.NONE
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    # Timestamps
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


# ===========================================
# Reconciliation Run Models
# ===========================================

class ReconciliationResult(BaseModel):
    """Result of reconciling a single exchange"""
    exchange: str
    
    status: ReconciliationStatus
    
    # Counts
    positions_checked: int = 0
    orders_checked: int = 0
    balances_checked: int = 0
    
    # Mismatches found
    mismatches: List[ReconciliationMismatch] = []
    mismatch_count: int = 0
    critical_count: int = 0
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # Error if failed
    error: Optional[str] = None

    class Config:
        use_enum_values = True


class ReconciliationRun(BaseModel):
    """A complete reconciliation run across exchanges"""
    run_id: str = Field(..., description="Unique run identifier")
    
    status: ReconciliationStatus
    
    # Which exchanges were checked
    exchanges: List[str]
    
    # Results per exchange
    results: List[ReconciliationResult] = []
    
    # Aggregate counts
    total_mismatches: int = 0
    total_critical: int = 0
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # Trigger
    trigger: str = "manual"  # manual, scheduled, alert
    triggered_by: Optional[str] = None
    
    # Actions taken
    quarantined_exchanges: List[str] = []
    alerts_sent: int = 0

    class Config:
        use_enum_values = True


# ===========================================
# Request/Response Models
# ===========================================

class ReconciliationRequest(BaseModel):
    """Request to run reconciliation"""
    exchanges: Optional[List[str]] = None  # None = all active
    check_positions: bool = True
    check_orders: bool = True
    check_balances: bool = True
    auto_fix: bool = False
    trigger: str = "manual"


class ReconciliationSummary(BaseModel):
    """Summary of recent reconciliation"""
    last_run: Optional[datetime] = None
    last_status: Optional[ReconciliationStatus] = None
    total_runs_24h: int = 0
    total_mismatches_24h: int = 0
    exchanges_in_sync: List[str] = []
    exchanges_with_issues: List[str] = []
    quarantined_exchanges: List[str] = []

    class Config:
        use_enum_values = True


class ReconciliationHealthResponse(BaseModel):
    """Health status of reconciliation service"""
    status: str
    version: str
    last_run: Optional[datetime]
    next_scheduled_run: Optional[datetime]
    active_exchanges: int
    quarantined_exchanges: int
    mismatches_unresolved: int
    timestamp: datetime

    class Config:
        use_enum_values = True
