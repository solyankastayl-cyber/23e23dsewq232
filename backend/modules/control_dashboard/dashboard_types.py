"""
Dashboard Types

PHASE 40.1 — Dashboard State Aggregator

Types for Real-Time Control Dashboard.

Key models:
- DashboardState: Aggregated system state
- DashboardAlert: System alerts
- DashboardAuditLog: User action audit
- PendingExecution: Orders awaiting approval
- ApprovalAction: User approval actions
"""

from typing import Literal, Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

ExecutionModeType = Literal["PAPER", "APPROVAL", "LIVE"]
AlertSeverity = Literal["INFO", "WARNING", "CRITICAL", "EMERGENCY"]
ApprovalActionType = Literal["APPROVE", "REJECT", "REDUCE", "OVERRIDE"]


# ══════════════════════════════════════════════════════════════
# Dashboard State (Main Aggregated State)
# ══════════════════════════════════════════════════════════════

class MarketOverview(BaseModel):
    """Market state overview."""
    regime: str = "UNKNOWN"
    regime_confidence: float = 0.0
    fractal_bias: str = "NEUTRAL"
    reflexivity_state: str = "STABLE"
    volatility_regime: str = "NORMAL"
    trend_strength: float = 0.0


class HypothesisState(BaseModel):
    """Current hypothesis state."""
    top_hypothesis: str = ""
    top_hypothesis_id: Optional[str] = None
    confidence: float = 0.0
    reliability: float = 0.0
    competing_count: int = 0
    conflict_state: str = "NONE"
    top_scenario: str = ""


class PositionSummary(BaseModel):
    """Position summary for dashboard."""
    symbol: str
    side: str  # LONG / SHORT
    size_base: float
    size_usd: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    strategy: str


class OrderSummary(BaseModel):
    """Order summary for dashboard."""
    order_id: str
    symbol: str
    side: str
    size_usd: float
    order_type: str
    status: str
    exchange: str
    created_at: datetime


class FillSummary(BaseModel):
    """Fill summary for dashboard."""
    fill_id: str
    symbol: str
    side: str
    filled_size: float
    avg_price: float
    slippage_bps: float
    fee: float
    filled_at: datetime


class PortfolioState(BaseModel):
    """Portfolio state for dashboard."""
    total_capital: float = 0.0
    deployed_capital: float = 0.0
    available_capital: float = 0.0
    
    long_exposure: float = 0.0
    short_exposure: float = 0.0
    net_exposure: float = 0.0
    gross_exposure: float = 0.0
    
    position_count: int = 0
    active_positions: List[PositionSummary] = Field(default_factory=list)
    
    # Diversification
    concentration_top: float = 0.0  # Top position %
    strategy_count: int = 0


class RiskState(BaseModel):
    """Risk state for dashboard."""
    portfolio_risk: float = 0.0
    portfolio_risk_limit: float = 0.20
    risk_utilization: float = 0.0
    
    var_95: float = 0.0
    var_99: float = 0.0
    
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    
    vol_scale_factor: float = 1.0
    
    risk_state: str = "NORMAL"  # NORMAL, ELEVATED, CRITICAL
    risk_budget_remaining: float = 1.0


class PnLState(BaseModel):
    """PnL state for dashboard."""
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_pnl: float = 0.0
    
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0
    
    avg_slippage_bps: float = 0.0
    total_fees: float = 0.0
    
    win_rate: float = 0.0
    profit_factor: float = 0.0


class ExecutionState(BaseModel):
    """Execution state for dashboard."""
    mode: ExecutionModeType = "PAPER"
    
    pending_orders: List[OrderSummary] = Field(default_factory=list)
    pending_count: int = 0
    
    active_orders: List[OrderSummary] = Field(default_factory=list)
    active_count: int = 0
    
    recent_fills: List[FillSummary] = Field(default_factory=list)
    fill_count_today: int = 0
    
    daily_volume: float = 0.0
    
    connected_exchanges: List[str] = Field(default_factory=list)


class DashboardState(BaseModel):
    """
    Complete aggregated dashboard state.
    
    This is the main contract for PHASE 40.
    """
    # Identity
    symbol: str = "PORTFOLIO"  # Or specific symbol
    
    # Execution mode
    execution_mode: ExecutionModeType = "PAPER"
    
    # Market state
    market: MarketOverview = Field(default_factory=MarketOverview)
    
    # Hypothesis
    hypothesis: HypothesisState = Field(default_factory=HypothesisState)
    
    # Portfolio
    portfolio: PortfolioState = Field(default_factory=PortfolioState)
    
    # Risk
    risk: RiskState = Field(default_factory=RiskState)
    
    # PnL
    pnl: PnLState = Field(default_factory=PnLState)
    
    # Execution
    execution: ExecutionState = Field(default_factory=ExecutionState)
    
    # Alerts
    alerts: List["DashboardAlert"] = Field(default_factory=list)
    alert_count: int = 0
    critical_alert_count: int = 0
    
    # Meta
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_freshness_ms: int = 0


# ══════════════════════════════════════════════════════════════
# Pending Execution (Approval Queue)
# ══════════════════════════════════════════════════════════════

class PendingExecution(BaseModel):
    """
    Order awaiting human approval.
    
    Used in APPROVAL mode (Decision Support).
    """
    pending_id: str = Field(default_factory=lambda: f"pend_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    order_id: Optional[str] = None
    
    # Trade details
    symbol: str
    side: str  # BUY / SELL
    size_usd: float
    size_base: float = 0.0
    
    # Order params
    order_type: str = "MARKET"
    limit_price: Optional[float] = None
    
    # Strategy context
    strategy: str
    hypothesis_id: Optional[str] = None
    
    # Entry/Exit levels
    expected_entry: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Confidence
    confidence: float = 0.0
    reliability: float = 0.0
    
    # Risk context
    position_risk: float = 0.0
    portfolio_risk_after: float = 0.0
    impact_state: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Recommendation
    system_recommendation: str = "APPROVE"
    recommendation_reason: str = ""
    
    # Status
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED, MODIFIED
    
    # Timing
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ══════════════════════════════════════════════════════════════
# Approval Action
# ══════════════════════════════════════════════════════════════

class ApprovalAction(BaseModel):
    """
    User action on pending execution.
    
    Actions:
    - APPROVE: Send to execution
    - REJECT: Remove from queue
    - REDUCE: Decrease size
    - OVERRIDE: Modify params
    """
    action: ApprovalActionType
    
    pending_id: str
    symbol: str
    
    # Optional overrides
    size_override: Optional[float] = None
    order_type_override: Optional[str] = None
    venue_override: Optional[str] = None
    limit_price_override: Optional[float] = None
    
    # User info
    user: str = "operator"
    note: Optional[str] = None
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalResult(BaseModel):
    """Result of approval action."""
    success: bool
    action: ApprovalActionType
    pending_id: str
    
    # Result
    order_id: Optional[str] = None
    execution_status: Optional[str] = None
    
    # Details
    message: str = ""
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Dashboard Alert
# ══════════════════════════════════════════════════════════════

class DashboardAlert(BaseModel):
    """
    System alert for dashboard.
    
    Severity levels:
    - INFO: Informational
    - WARNING: Needs attention
    - CRITICAL: Immediate action needed
    - EMERGENCY: System risk
    """
    alert_id: str = Field(default_factory=lambda: f"alert_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    symbol: str = "SYSTEM"
    
    severity: AlertSeverity = "INFO"
    
    title: str
    message: str
    
    source: str  # Module that generated alert
    category: str = "GENERAL"  # RISK, LIQUIDITY, EXECUTION, MARKET, SYSTEM
    
    # Context
    value: Optional[float] = None
    threshold: Optional[float] = None
    
    # Status
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# Dashboard Audit Log
# ══════════════════════════════════════════════════════════════

class DashboardAuditLog(BaseModel):
    """
    Audit log for user actions.
    
    Every action is recorded for compliance.
    """
    audit_id: str = Field(default_factory=lambda: f"audit_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    # Action
    action: str
    action_type: str  # APPROVAL, CONFIG, OVERRIDE, etc.
    
    # Target
    symbol: Optional[str] = None
    order_id: Optional[str] = None
    pending_id: Optional[str] = None
    
    # Changes
    previous_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    
    previous_size: Optional[float] = None
    new_size: Optional[float] = None
    
    # Context
    execution_mode: str = "PAPER"
    
    # User
    user: str = "operator"
    ip_address: Optional[str] = None
    
    # Result
    success: bool = True
    error_message: Optional[str] = None
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Dashboard Config
# ══════════════════════════════════════════════════════════════

class DashboardConfig(BaseModel):
    """Dashboard configuration."""
    # Mode
    default_execution_mode: ExecutionModeType = "APPROVAL"
    
    # Refresh
    refresh_interval_ms: int = 5000
    state_cache_ttl_seconds: int = 10
    
    # Alerts
    alert_retention_hours: int = 24
    max_alerts_displayed: int = 50
    
    # Approval
    approval_timeout_seconds: int = 300
    auto_reject_expired: bool = True
    
    # Audit
    audit_retention_days: int = 90
    
    # Risk thresholds for alerts
    risk_warning_threshold: float = 0.15
    risk_critical_threshold: float = 0.18
    drawdown_warning_threshold: float = 0.05
    drawdown_critical_threshold: float = 0.10


# ══════════════════════════════════════════════════════════════
# Multi-Symbol Dashboard
# ══════════════════════════════════════════════════════════════

class MultiSymbolDashboard(BaseModel):
    """Dashboard state for multiple symbols."""
    symbols: List[str] = Field(default_factory=list)
    symbol_states: Dict[str, DashboardState] = Field(default_factory=dict)
    
    # Aggregated portfolio
    portfolio: PortfolioState = Field(default_factory=PortfolioState)
    risk: RiskState = Field(default_factory=RiskState)
    pnl: PnLState = Field(default_factory=PnLState)
    execution: ExecutionState = Field(default_factory=ExecutionState)
    
    # Alerts
    alerts: List[DashboardAlert] = Field(default_factory=list)
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
