"""
Risk Budget Engine Types

PHASE 38.5 — Risk Budget Engine

Types for risk-based capital allocation.

Key concepts:
- Risk budget: distributes portfolio RISK, not capital
- Volatility targeting: position_size = risk_budget / asset_volatility
- Risk contribution: weight * volatility * correlation_adjustment

Integration:
- Portfolio Manager
- Execution Brain
- Capital Allocation Engine
"""

from typing import Literal, Optional, List, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Default risk budget allocations by strategy type
DEFAULT_RISK_BUDGETS = {
    "TREND_FOLLOWING": 0.30,      # 30% of portfolio risk
    "MEAN_REVERSION": 0.25,       # 25% of portfolio risk
    "BREAKOUT": 0.25,             # 25% of portfolio risk
    "VOLATILITY": 0.20,           # 20% of portfolio risk
}

# Portfolio risk limits
PORTFOLIO_RISK_LIMITS = {
    "MAX_TOTAL_RISK": 0.20,       # 20% max portfolio risk (annualized vol)
    "MAX_STRATEGY_RISK": 0.40,    # 40% max single strategy risk allocation
    "MIN_STRATEGY_RISK": 0.05,    # 5% min strategy risk allocation
}

# Volatility scaling parameters
VOLATILITY_PARAMS = {
    "TARGET_VOLATILITY": 0.15,    # 15% annualized target vol
    "LOOKBACK_DAYS": 20,          # Days for volatility calculation
    "MIN_VOLATILITY": 0.05,       # 5% min volatility floor
    "MAX_VOLATILITY": 0.80,       # 80% max volatility cap
}

# Risk contribution limits
RISK_CONTRIBUTION_LIMITS = {
    "MAX_SINGLE_CONTRIBUTION": 0.25,   # 25% max from single position
    "CONCENTRATION_THRESHOLD": 0.40,    # Warn if top position > 40%
}


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

StrategyType = Literal[
    "TREND_FOLLOWING",
    "MEAN_REVERSION",
    "BREAKOUT",
    "VOLATILITY",
    "MOMENTUM",
    "STATISTICAL_ARB",
]

RiskAllocationMethod = Literal[
    "EQUAL_RISK",           # Equal risk budget per strategy
    "VOLATILITY_WEIGHTED",  # Inverse volatility weighting
    "PERFORMANCE_WEIGHTED", # Based on recent performance
    "CUSTOM",               # Custom allocation
]

RiskState = Literal[
    "UNDER_BUDGET",    # Risk < target
    "ON_TARGET",       # Risk ~= target
    "OVER_BUDGET",     # Risk > target (needs reduction)
    "CRITICAL",        # Risk significantly over limit
]


# ══════════════════════════════════════════════════════════════
# Strategy Risk Budget
# ══════════════════════════════════════════════════════════════

class RiskBudget(BaseModel):
    """
    Risk budget allocation for a single strategy.
    
    Key formula:
    position_size = risk_budget / asset_volatility
    """
    strategy: str
    strategy_type: StrategyType = "MOMENTUM"
    
    # Risk allocation
    risk_target: float = Field(ge=0, le=1)         # Target % of portfolio risk
    risk_allocated: float = Field(ge=0, le=1, default=0.0)  # Currently allocated
    risk_used: float = Field(ge=0, le=1, default=0.0)       # Actually used
    
    # Capital derived from risk
    allocated_capital: float = Field(ge=0, default=0.0)     # $ allocated
    max_capital: float = Field(ge=0, default=0.0)           # Max $ allowed
    
    # Risk contribution metrics
    risk_contribution: float = Field(ge=0, le=1, default=0.0)  # Contribution to portfolio risk
    marginal_risk: float = Field(ge=0, default=0.0)            # Marginal risk per $
    
    # Volatility info
    volatility: float = Field(ge=0, default=0.0)            # Strategy volatility
    volatility_scaled: bool = False                          # Is vol-scaled?
    
    # Position sizing
    position_count: int = 0
    avg_position_risk: float = 0.0
    
    # Status
    is_active: bool = True
    is_over_budget: bool = False
    
    # Performance tracking
    sharpe_ratio: float = 0.0
    recent_pnl: float = 0.0
    
    # Timestamps
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Position Risk
# ══════════════════════════════════════════════════════════════

class PositionRisk(BaseModel):
    """
    Risk metrics for a single position.
    """
    symbol: str
    strategy: str
    
    # Size
    position_size_usd: float = Field(ge=0)
    weight: float = Field(ge=0, le=1)
    
    # Volatility
    asset_volatility: float = Field(ge=0)
    volatility_annualized: float = Field(ge=0)
    
    # Risk contribution
    risk_contribution: float = Field(ge=0, le=1)  # weight * vol * corr_adj
    marginal_risk: float = Field(ge=0)            # Marginal contribution
    
    # Correlation
    avg_correlation: float = Field(ge=-1, le=1, default=0.0)
    correlation_adjustment: float = Field(ge=0, le=2, default=1.0)
    
    # Derived from risk budget
    risk_budget_used: float = Field(ge=0, le=1, default=0.0)
    
    # Limits
    max_size_from_risk_budget: float = Field(ge=0, default=0.0)
    is_within_budget: bool = True


# ══════════════════════════════════════════════════════════════
# Portfolio Risk Budget
# ══════════════════════════════════════════════════════════════

class PortfolioRiskBudget(BaseModel):
    """
    Complete portfolio risk budget state.
    
    Main contract for PHASE 38.5.
    
    Formula:
    Σ risk_contribution ≤ portfolio_risk_limit
    """
    # Portfolio-level risk
    total_risk: float = Field(ge=0, le=1, default=0.0)      # Total portfolio risk
    total_risk_limit: float = Field(ge=0, le=1, default=PORTFOLIO_RISK_LIMITS["MAX_TOTAL_RISK"])
    risk_utilization: float = Field(ge=0, default=0.0)      # total_risk / limit
    
    # Strategy budgets
    strategy_budgets: List[RiskBudget] = Field(default_factory=list)
    strategy_count: int = 0
    
    # Position-level risk
    position_risks: List[PositionRisk] = Field(default_factory=list)
    position_count: int = 0
    
    # Risk decomposition
    systematic_risk: float = Field(ge=0, default=0.0)       # Market-related
    idiosyncratic_risk: float = Field(ge=0, default=0.0)    # Position-specific
    
    # Volatility targeting
    target_volatility: float = Field(ge=0, default=VOLATILITY_PARAMS["TARGET_VOLATILITY"])
    current_volatility: float = Field(ge=0, default=0.0)
    volatility_ratio: float = Field(ge=0, default=0.0)      # current / target
    
    # Scaling factor
    vol_scale_factor: float = Field(ge=0, default=1.0)      # Multiply sizes by this
    
    # Capital implications
    total_capital: float = Field(ge=0, default=0.0)
    risk_capital: float = Field(ge=0, default=0.0)          # Capital at risk
    
    # State
    risk_state: RiskState = "ON_TARGET"
    needs_rebalance: bool = False
    
    # Warnings
    warnings: List[str] = Field(default_factory=list)
    
    # Timestamp
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Risk Budget Allocation Request
# ══════════════════════════════════════════════════════════════

class RiskBudgetAllocationRequest(BaseModel):
    """
    Request to allocate risk budget.
    """
    strategies: List[str]
    method: RiskAllocationMethod = "EQUAL_RISK"
    custom_allocations: Optional[Dict[str, float]] = None
    
    # Constraints
    max_single_strategy_risk: float = PORTFOLIO_RISK_LIMITS["MAX_STRATEGY_RISK"]
    min_single_strategy_risk: float = PORTFOLIO_RISK_LIMITS["MIN_STRATEGY_RISK"]


# ══════════════════════════════════════════════════════════════
# Volatility Target Request
# ══════════════════════════════════════════════════════════════

class VolatilityTargetRequest(BaseModel):
    """
    Request to compute volatility-targeted position size.
    """
    symbol: str
    strategy: str
    direction: str
    base_size_usd: float
    
    # Override defaults
    target_volatility: Optional[float] = None
    max_position_risk: Optional[float] = None


# ══════════════════════════════════════════════════════════════
# Volatility Target Response
# ══════════════════════════════════════════════════════════════

class VolatilityTargetResponse(BaseModel):
    """
    Response with volatility-targeted position size.
    """
    symbol: str
    strategy: str
    
    # Original request
    base_size_usd: float
    
    # Asset volatility
    asset_volatility: float
    asset_volatility_annualized: float
    
    # Volatility targeting
    target_volatility: float
    volatility_ratio: float  # target / asset
    
    # Adjusted size
    vol_scaled_size_usd: float
    size_reduction_pct: float
    
    # Risk budget check
    strategy_risk_budget: float
    risk_budget_remaining: float
    within_budget: bool
    
    # Final size
    final_size_usd: float
    reason: str


# ══════════════════════════════════════════════════════════════
# Risk Contribution Calculation
# ══════════════════════════════════════════════════════════════

class RiskContributionResult(BaseModel):
    """
    Result of risk contribution calculation.
    
    Formula:
    risk_contribution = weight * volatility * correlation_adjustment
    """
    symbol: str
    strategy: str
    
    # Components
    weight: float
    volatility: float
    correlation_adjustment: float
    
    # Contribution
    risk_contribution: float
    risk_contribution_pct: float  # As % of total portfolio risk
    
    # Marginal risk
    marginal_risk: float
    
    # Portfolio impact
    impact_on_portfolio_risk: float


# ══════════════════════════════════════════════════════════════
# Risk Rebalance Result
# ══════════════════════════════════════════════════════════════

class RiskRebalanceResult(BaseModel):
    """
    Result of risk budget rebalancing.
    """
    triggered: bool = False
    reason: str = ""
    
    # Before state
    risk_before: float = 0.0
    strategy_risks_before: Dict[str, float] = Field(default_factory=dict)
    
    # Adjustments
    strategies_to_reduce: List[Dict] = Field(default_factory=list)
    strategies_to_increase: List[Dict] = Field(default_factory=list)
    positions_to_scale: List[Dict] = Field(default_factory=list)
    
    # After state (projected)
    risk_after: float = 0.0
    strategy_risks_after: Dict[str, float] = Field(default_factory=dict)
    
    # Scale factors
    global_scale_factor: float = 1.0
    strategy_scale_factors: Dict[str, float] = Field(default_factory=dict)
    
    # Impact
    capital_freed: float = 0.0
    risk_reduction: float = 0.0
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Risk Budget History Entry
# ══════════════════════════════════════════════════════════════

class RiskBudgetHistoryEntry(BaseModel):
    """
    Historical snapshot for risk budget tracking.
    """
    total_risk: float
    risk_limit: float
    risk_utilization: float
    
    strategy_count: int
    position_count: int
    
    current_volatility: float
    target_volatility: float
    vol_scale_factor: float
    
    risk_state: RiskState
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
