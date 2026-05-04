"""
Execution Brain Types

PHASE 37 — Execution Brain

Types for intelligent trade execution.

Key contracts:
- ExecutionPlan: Complete execution plan with entry/stop/target
- RiskLevel: Risk classification
- ExecutionType: Order type selection
"""

from typing import Literal, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Risk modifiers for position sizing
RISK_MODIFIERS = {
    "LOW": 1.0,
    "MEDIUM": 0.7,
    "HIGH": 0.4,
    "EXTREME": 0.0,
}

# Stop loss multipliers (ATR-based)
STOP_MULTIPLIERS = {
    "TIGHT": 1.5,
    "NORMAL": 2.0,
    "WIDE": 3.0,
}

# Confidence threshold for execution
MIN_CONFIDENCE_THRESHOLD = 0.45


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

ExecutionType = Literal[
    "MARKET",    # Immediate execution
    "LIMIT",     # Price-limited order
    "TWAP",      # Time-weighted average
    "ICEBERG",   # Large orders split
]

RiskLevel = Literal[
    "LOW",       # Safe to execute full size
    "MEDIUM",    # Reduce position size
    "HIGH",      # Significantly reduce size
    "EXTREME",   # Block execution
]

DirectionType = Literal["LONG", "SHORT"]

StrategyType = Literal[
    "BREAKOUT_TRADING",
    "RANGE_TRADING",
    "VOLATILITY_TRADING",
    "MOMENTUM_TRADING",
    "MEAN_REVERSION",
]

ExecutionStatus = Literal[
    "PENDING",
    "APPROVED",
    "BLOCKED",
    "EXECUTED",
    "CANCELLED",
]


# ══════════════════════════════════════════════════════════════
# Execution Plan
# ══════════════════════════════════════════════════════════════

class ExecutionPlan(BaseModel):
    """
    Main contract for execution planning.
    
    Contains everything needed to execute a trade.
    """
    symbol: str
    
    # Strategy
    strategy: StrategyType = "MOMENTUM_TRADING"
    hypothesis_type: str = ""
    
    # Direction
    direction: DirectionType
    
    # Position sizing
    position_size_usd: float = Field(ge=0)
    position_size_adjusted: float = Field(ge=0)  # After impact adjustment
    capital_allocation_weight: float = Field(ge=0, le=1)
    
    # Prices
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: float = Field(gt=0)
    invalidation_level: Optional[float] = None
    
    # Risk
    risk_level: RiskLevel = "MEDIUM"
    risk_modifier: float = Field(ge=0, le=1)
    risk_reward_ratio: float = 0.0
    
    # Execution
    execution_type: ExecutionType = "LIMIT"
    execution_type_original: ExecutionType = "LIMIT"
    
    # Confidence
    confidence: float = Field(ge=0, le=1)
    reliability: float = Field(ge=0, le=1)
    
    # Status
    status: ExecutionStatus = "PENDING"
    blocked_reason: str = ""
    
    # Impact adjustment
    impact_adjusted: bool = False
    size_reduction_pct: float = 0.0
    type_changed: bool = False
    
    # Timestamps
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Explanation
    reason: str = ""


# ══════════════════════════════════════════════════════════════
# Capital Input
# ══════════════════════════════════════════════════════════════

class CapitalInput(BaseModel):
    """
    Input from Capital Allocation Engine.
    """
    symbol: str
    portfolio_capital_usd: float
    allocation_weight: float
    recommended_risk_level: str = "MEDIUM"


# ══════════════════════════════════════════════════════════════
# Decision Input
# ══════════════════════════════════════════════════════════════

class DecisionInput(BaseModel):
    """
    Input from Decision Engine.
    """
    symbol: str
    hypothesis_type: str
    direction: str
    confidence: float
    reliability: float
    target_price: float
    invalidation_price: float


# ══════════════════════════════════════════════════════════════
# Execution Summary
# ══════════════════════════════════════════════════════════════

class ExecutionSummary(BaseModel):
    """
    Summary statistics for execution plans.
    """
    symbol: str
    
    # Current
    has_active_plan: bool = False
    current_direction: str = ""
    current_status: str = ""
    
    # Historical
    total_plans: int = 0
    approved_count: int = 0
    blocked_count: int = 0
    executed_count: int = 0
    
    # Risk distribution
    low_risk_count: int = 0
    medium_risk_count: int = 0
    high_risk_count: int = 0
    extreme_risk_count: int = 0
    
    # Execution type distribution
    market_count: int = 0
    limit_count: int = 0
    twap_count: int = 0
    iceberg_count: int = 0
    
    # Stats
    avg_confidence: float = 0.0
    avg_risk_reward: float = 0.0
    
    last_updated: Optional[datetime] = None
