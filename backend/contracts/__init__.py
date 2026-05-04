"""
System Contracts — PHASE 47.3

All modules communicate through these contracts.
No direct imports between modules allowed.
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# Common Types
# ═══════════════════════════════════════════════════════════════

class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class Timeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class SignalStrength(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class Regime(str, Enum):
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE = "range"
    COMPRESSION = "compression"
    EXPANSION = "expansion"
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════
# Market Types
# ═══════════════════════════════════════════════════════════════

class MarketState(BaseModel):
    """Current market state snapshot."""
    symbol: str
    timeframe: str
    timestamp: datetime
    price: float
    regime: Regime = Regime.UNKNOWN
    volatility: float = 0.0
    trend_strength: float = 0.0
    volume_profile: str = "normal"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PriceLevel(BaseModel):
    """Significant price level."""
    price: float
    type: str  # support/resistance/pivot/fib
    strength: float
    touches: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LiquidityZone(BaseModel):
    """Liquidity concentration zone."""
    price_low: float
    price_high: float
    type: str  # bid/ask/both
    volume: float
    significance: float


# ═══════════════════════════════════════════════════════════════
# Hypothesis Types
# ═══════════════════════════════════════════════════════════════

class AlphaSignal(BaseModel):
    """Signal from an alpha source."""
    alpha_id: str
    alpha_type: str
    symbol: str
    direction: Direction
    confidence: float = Field(ge=0.0, le=1.0)
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timeframe: str = "1h"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HypothesisSignal(BaseModel):
    """Aggregated hypothesis signal."""
    hypothesis_id: str
    symbol: str
    direction: Direction
    confidence: float = Field(ge=0.0, le=1.0)
    strength: SignalStrength = SignalStrength.MODERATE
    
    # Components
    alpha_score: float = 0.0
    regime_score: float = 0.0
    microstructure_score: float = 0.0
    macro_score: float = 0.0
    fractal_market_score: float = 0.0
    fractal_similarity_score: float = 0.0
    cross_asset_score: float = 0.0
    capital_flow_score: float = 0.0
    reflexivity_score: float = 0.0
    
    # Pricing
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    invalidation_price: Optional[float] = None
    
    # Meta
    alpha_sources: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    decay_factor: float = 1.0
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScenarioPath(BaseModel):
    """Projected price path scenario."""
    scenario_id: str
    type: str  # base/bull/bear/extreme
    probability: float = Field(ge=0.0, le=1.0)
    expected_price: float
    price_path: List[float] = Field(default_factory=list)
    time_horizon_minutes: int = 240
    confidence_band: tuple = (0.0, 0.0)
    triggers: List[str] = Field(default_factory=list)
    invalidation_conditions: List[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Execution Types
# ═══════════════════════════════════════════════════════════════

class ExecutionRequest(BaseModel):
    """Request to execute a trade."""
    request_id: str
    hypothesis_id: str
    symbol: str
    direction: Direction
    size: float
    size_type: str = "notional"  # notional/quantity
    entry_type: str = "market"  # market/limit/twap/vwap
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    max_slippage_bps: int = 50
    timeout_seconds: int = 30
    urgency: str = "normal"  # low/normal/high
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    """Result of an execution."""
    execution_id: str
    request_id: str
    hypothesis_id: str
    symbol: str
    direction: Direction
    
    # Fills
    requested_size: float
    filled_size: float
    avg_fill_price: float
    slippage_bps: float
    
    # Costs
    commission: float = 0.0
    funding_cost: float = 0.0
    
    # Status
    status: str  # pending/filled/partial/failed/cancelled
    fill_ratio: float = 0.0
    
    # Orders
    orders: List[str] = Field(default_factory=list)
    
    # Meta
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Portfolio Types
# ═══════════════════════════════════════════════════════════════

class PortfolioPosition(BaseModel):
    """Portfolio position."""
    position_id: str
    symbol: str
    direction: Direction
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    realized_pnl: float
    weight: float = 0.0
    leverage: int = 1
    opened_at: datetime
    hypothesis_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PortfolioState(BaseModel):
    """Complete portfolio state."""
    portfolio_id: str
    timestamp: datetime
    
    # Value
    total_value: float
    cash: float
    positions_value: float
    
    # Performance
    total_pnl: float
    total_pnl_pct: float
    unrealized_pnl: float
    realized_pnl: float
    
    # Risk metrics
    portfolio_var: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Positions
    positions: List[PortfolioPosition] = Field(default_factory=list)
    position_count: int = 0
    
    # Exposure
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    long_exposure: float = 0.0
    short_exposure: float = 0.0
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AllocationRequest(BaseModel):
    """Request to allocate capital."""
    hypothesis_id: str
    symbol: str
    direction: Direction
    requested_weight: float
    max_weight: float = 0.20
    priority: int = 1
    alpha_type: str = "unknown"
    confidence: float = 0.0


class AllocationResult(BaseModel):
    """Result of allocation."""
    hypothesis_id: str
    symbol: str
    direction: Direction
    allocated_weight: float
    allocated_size: float
    rejected: bool = False
    rejection_reason: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# Risk Types
# ═══════════════════════════════════════════════════════════════

class RiskMetrics(BaseModel):
    """Risk metrics snapshot."""
    timestamp: datetime
    portfolio_var: float
    portfolio_cvar: float
    max_drawdown: float
    current_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    correlation_risk: float
    concentration_risk: float
    liquidity_risk: float
    
    # Limits
    var_utilization: float = 0.0
    drawdown_utilization: float = 0.0
    
    # Warnings
    warnings: List[str] = Field(default_factory=list)
    breaches: List[str] = Field(default_factory=list)


class RiskBudget(BaseModel):
    """Risk budget allocation."""
    total_risk_budget: float
    allocated_risk: float
    available_risk: float
    utilization_pct: float
    
    # Per category
    alpha_risk_budget: Dict[str, float] = Field(default_factory=dict)
    symbol_risk_budget: Dict[str, float] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Visualization Types
# ═══════════════════════════════════════════════════════════════

class ChartOverlay(BaseModel):
    """Chart overlay object for visualization."""
    object_id: str
    object_type: str  # trend_line, zone, channel, triangle, etc.
    symbol: str
    timeframe: str
    
    # Geometry
    points: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Style
    style: Dict[str, Any] = Field(default_factory=dict)
    
    # Meta
    label: Optional[str] = None
    confidence: Optional[float] = None
    source: str = "system"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IndicatorSeries(BaseModel):
    """Indicator data series."""
    indicator_id: str
    name: str
    type: str  # line, histogram, area, band
    values: List[float] = Field(default_factory=list)
    timestamps: List[datetime] = Field(default_factory=list)
    style: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChartPayload(BaseModel):
    """Complete chart data payload."""
    symbol: str
    timeframe: str
    timestamp: datetime
    
    # Price data
    candles: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Overlays
    overlays: List[ChartOverlay] = Field(default_factory=list)
    
    # Indicators
    indicators: List[IndicatorSeries] = Field(default_factory=list)
    
    # Hypotheses
    hypotheses: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Scenarios
    scenarios: List[ScenarioPath] = Field(default_factory=list)
    
    # Suggested configuration
    suggested_indicators: List[str] = Field(default_factory=list)
    suggested_overlays: List[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Event Types
# ═══════════════════════════════════════════════════════════════

class SystemEvent(BaseModel):
    """System event for event bus."""
    event_id: str
    event_type: str
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TradeEvent(BaseModel):
    """Trade-related event."""
    event_id: str
    event_type: str  # signal/execution/fill/close
    hypothesis_id: str
    symbol: str
    direction: Direction
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = Field(default_factory=dict)


class AlertEvent(BaseModel):
    """Alert event."""
    alert_id: str
    severity: str  # info/warning/critical
    category: str  # risk/execution/system/market
    title: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any] = Field(default_factory=dict)
    acknowledged: bool = False


# ═══════════════════════════════════════════════════════════════
# Validation Types
# ═══════════════════════════════════════════════════════════════

class ValidationResult(BaseModel):
    """Validation test result."""
    test_id: str
    test_name: str
    category: str
    status: str  # passed/failed/warning/error
    severity: str  # info/warning/critical
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0.0


class ValidationReport(BaseModel):
    """Complete validation report."""
    report_id: str
    timestamp: datetime
    
    # Scores
    overall_score: float
    coefficient_score: float
    integration_score: float
    logic_score: float
    stress_score: float
    chaos_score: float
    
    # Results
    results: List[ValidationResult] = Field(default_factory=list)
    
    # Summary
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)


__all__ = [
    # Enums
    "Direction",
    "Timeframe",
    "SignalStrength",
    "Regime",
    # Market
    "MarketState",
    "PriceLevel",
    "LiquidityZone",
    # Hypothesis
    "AlphaSignal",
    "HypothesisSignal",
    "ScenarioPath",
    # Execution
    "ExecutionRequest",
    "ExecutionResult",
    # Portfolio
    "PortfolioPosition",
    "PortfolioState",
    "AllocationRequest",
    "AllocationResult",
    # Risk
    "RiskMetrics",
    "RiskBudget",
    # Visualization
    "ChartOverlay",
    "IndicatorSeries",
    "ChartPayload",
    # Events
    "SystemEvent",
    "TradeEvent",
    "AlertEvent",
    # Validation
    "ValidationResult",
    "ValidationReport",
]
