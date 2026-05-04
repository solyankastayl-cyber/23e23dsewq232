"""
PHASE 10 - Portfolio Construction Types
========================================
Core data types for portfolio management.

Provides:
- Risk parity allocation
- Volatility targeting
- Drawdown control
- Strategy correlation management
- Capital rebalancing
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class AllocationMethod(str, Enum):
    """Capital allocation method"""
    EQUAL_WEIGHT = "EQUAL_WEIGHT"
    RISK_PARITY = "RISK_PARITY"
    VOLATILITY_SCALED = "VOLATILITY_SCALED"
    DRAWDOWN_AWARE = "DRAWDOWN_AWARE"
    CORRELATION_ADJUSTED = "CORRELATION_ADJUSTED"
    COMPOSITE = "COMPOSITE"


class RebalanceAction(str, Enum):
    """Rebalancing action recommendation"""
    NO_ACTION = "NO_ACTION"
    MINOR_ADJUSTMENT = "MINOR_ADJUSTMENT"
    REBALANCE_REQUIRED = "REBALANCE_REQUIRED"
    URGENT_REBALANCE = "URGENT_REBALANCE"
    REDUCE_EXPOSURE = "REDUCE_EXPOSURE"
    INCREASE_EXPOSURE = "INCREASE_EXPOSURE"


class DrawdownState(str, Enum):
    """Portfolio drawdown state"""
    NORMAL = "NORMAL"           # DD < 3%
    CAUTION = "CAUTION"         # DD 3-5%
    WARNING = "WARNING"         # DD 5-10%
    CRITICAL = "CRITICAL"       # DD 10-15%
    EMERGENCY = "EMERGENCY"     # DD > 15%


class VolatilityRegime(str, Enum):
    """Market volatility regime"""
    LOW = "LOW"                 # Vol < 10%
    NORMAL = "NORMAL"           # Vol 10-20%
    HIGH = "HIGH"               # Vol 20-35%
    EXTREME = "EXTREME"         # Vol > 35%


class CorrelationLevel(str, Enum):
    """Strategy correlation level"""
    NEGATIVE = "NEGATIVE"       # corr < -0.2
    LOW = "LOW"                 # corr -0.2 to 0.3
    MODERATE = "MODERATE"       # corr 0.3 to 0.6
    HIGH = "HIGH"               # corr 0.6 to 0.8
    VERY_HIGH = "VERY_HIGH"     # corr > 0.8


@dataclass
class StrategyMetrics:
    """Strategy performance metrics for allocation"""
    strategy_id: str
    name: str
    
    # Performance
    returns: float              # Expected/historical return
    volatility: float           # Strategy volatility
    sharpe_ratio: float         # Risk-adjusted return
    
    # Risk
    max_drawdown: float         # Historical max DD
    current_drawdown: float     # Current DD
    var_95: float               # Value at Risk 95%
    
    # Status
    active: bool = True
    weight: float = 0.0         # Current allocation weight
    
    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "returns": round(self.returns, 4),
            "volatility": round(self.volatility, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "max_drawdown": round(self.max_drawdown, 4),
            "current_drawdown": round(self.current_drawdown, 4),
            "var_95": round(self.var_95, 4),
            "active": self.active,
            "weight": round(self.weight, 4)
        }


@dataclass
class StrategyAllocation:
    """Single strategy allocation"""
    strategy_id: str
    name: str
    
    # Allocation
    target_weight: float        # Target allocation (0-1)
    current_weight: float       # Current allocation (0-1)
    delta: float                # Required change
    
    # Risk contribution
    risk_contribution: float    # % of portfolio risk
    marginal_risk: float        # Marginal risk impact
    
    # Constraints
    min_weight: float = 0.0
    max_weight: float = 1.0
    
    # Flags
    needs_adjustment: bool = False
    adjustment_reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "target_weight": round(self.target_weight, 4),
            "current_weight": round(self.current_weight, 4),
            "delta": round(self.delta, 4),
            "risk_contribution": round(self.risk_contribution, 4),
            "marginal_risk": round(self.marginal_risk, 4),
            "min_weight": round(self.min_weight, 4),
            "max_weight": round(self.max_weight, 4),
            "needs_adjustment": self.needs_adjustment,
            "adjustment_reason": self.adjustment_reason
        }


@dataclass
class RiskParityResult:
    """Risk parity calculation result"""
    timestamp: datetime
    
    # Allocations
    allocations: Dict[str, float]  # strategy_id -> weight
    
    # Risk metrics
    total_portfolio_risk: float
    risk_contributions: Dict[str, float]  # strategy_id -> risk %
    risk_concentration: float       # Herfindahl index of risk
    
    # Convergence
    converged: bool = True
    iterations: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "allocations": {k: round(v, 4) for k, v in self.allocations.items()},
            "total_portfolio_risk": round(self.total_portfolio_risk, 4),
            "risk_contributions": {k: round(v, 4) for k, v in self.risk_contributions.items()},
            "risk_concentration": round(self.risk_concentration, 4),
            "converged": self.converged,
            "iterations": self.iterations
        }


@dataclass
class VolatilityTarget:
    """Volatility targeting result"""
    timestamp: datetime
    
    # Targets
    target_volatility: float        # Target vol (e.g., 0.12 = 12%)
    current_volatility: float       # Current portfolio vol
    realized_volatility: float      # Recent realized vol
    
    # Scaling
    volatility_scalar: float        # Multiplier for positions
    position_size_adjustment: float # % adjustment to positions
    
    # Regime
    volatility_regime: VolatilityRegime
    
    # Forecast
    vol_forecast_1d: float = 0.0
    vol_forecast_5d: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "target_volatility": round(self.target_volatility, 4),
            "current_volatility": round(self.current_volatility, 4),
            "realized_volatility": round(self.realized_volatility, 4),
            "volatility_scalar": round(self.volatility_scalar, 4),
            "position_size_adjustment": round(self.position_size_adjustment, 4),
            "volatility_regime": self.volatility_regime.value,
            "vol_forecast_1d": round(self.vol_forecast_1d, 4),
            "vol_forecast_5d": round(self.vol_forecast_5d, 4)
        }


@dataclass
class DrawdownControl:
    """Drawdown control state"""
    timestamp: datetime
    
    # Current state
    current_drawdown: float         # Current DD from peak
    max_drawdown_limit: float       # Max allowed DD
    drawdown_state: DrawdownState
    
    # Control actions
    risk_reduction_factor: float    # How much to reduce risk (0-1)
    capital_deployment: float       # How much capital to deploy (0-1)
    
    # Recovery
    peak_equity: float = 0.0
    current_equity: float = 0.0
    recovery_distance: float = 0.0  # % needed to recover
    
    # Time in drawdown
    drawdown_start: Optional[datetime] = None
    days_in_drawdown: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "current_drawdown": round(self.current_drawdown, 4),
            "max_drawdown_limit": round(self.max_drawdown_limit, 4),
            "drawdown_state": self.drawdown_state.value,
            "risk_reduction_factor": round(self.risk_reduction_factor, 4),
            "capital_deployment": round(self.capital_deployment, 4),
            "peak_equity": round(self.peak_equity, 2),
            "current_equity": round(self.current_equity, 2),
            "recovery_distance": round(self.recovery_distance, 4),
            "drawdown_start": self.drawdown_start.isoformat() if self.drawdown_start else None,
            "days_in_drawdown": self.days_in_drawdown
        }


@dataclass
class CorrelationMatrix:
    """Strategy correlation matrix"""
    timestamp: datetime
    
    # Correlations
    matrix: Dict[str, Dict[str, float]]  # strategy_id -> strategy_id -> correlation
    
    # Summary metrics
    avg_correlation: float          # Average pairwise correlation
    max_correlation: float          # Highest correlation
    min_correlation: float          # Lowest correlation
    
    # Problematic pairs
    high_corr_pairs: List[tuple] = field(default_factory=list)  # (strat1, strat2, corr)
    
    # Diversification benefit
    diversification_ratio: float = 1.0
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "matrix": {k: {k2: round(v2, 4) for k2, v2 in v.items()} 
                      for k, v in self.matrix.items()},
            "avg_correlation": round(self.avg_correlation, 4),
            "max_correlation": round(self.max_correlation, 4),
            "min_correlation": round(self.min_correlation, 4),
            "high_corr_pairs": [(p[0], p[1], round(p[2], 4)) for p in self.high_corr_pairs],
            "diversification_ratio": round(self.diversification_ratio, 4)
        }


@dataclass
class RebalanceRecommendation:
    """Portfolio rebalancing recommendation"""
    timestamp: datetime
    
    # Action
    action: RebalanceAction
    urgency: float                  # 0-1 urgency score
    
    # Changes
    allocations_delta: Dict[str, float]  # strategy_id -> change needed
    
    # Reasons
    trigger_reason: str             # What triggered this
    rebalance_reasons: List[str] = field(default_factory=list)
    
    # Timing
    recommended_execution_time: str = "IMMEDIATE"  # or "END_OF_DAY", "NEXT_SESSION"
    
    # Costs
    estimated_turnover: float = 0.0
    estimated_cost_bps: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "action": self.action.value,
            "urgency": round(self.urgency, 3),
            "allocations_delta": {k: round(v, 4) for k, v in self.allocations_delta.items()},
            "trigger_reason": self.trigger_reason,
            "rebalance_reasons": self.rebalance_reasons,
            "recommended_execution_time": self.recommended_execution_time,
            "estimated_turnover": round(self.estimated_turnover, 4),
            "estimated_cost_bps": round(self.estimated_cost_bps, 2)
        }


@dataclass
class PortfolioState:
    """Complete portfolio state snapshot"""
    timestamp: datetime
    
    # Overall metrics
    portfolio_volatility: float
    target_volatility: float
    portfolio_drawdown: float
    
    # Budget
    risk_budget_used: float         # 0-1
    capital_deployment: float       # 0-1
    
    # Allocations
    strategy_allocations: Dict[str, float]
    
    # Control states
    drawdown_state: DrawdownState
    volatility_regime: VolatilityRegime
    
    # Recommendation
    rebalance_recommendation: RebalanceAction
    
    # Health
    portfolio_health_score: float = 0.0  # 0-1
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "portfolioVolatility": round(self.portfolio_volatility, 4),
            "targetVolatility": round(self.target_volatility, 4),
            "portfolioDrawdown": round(self.portfolio_drawdown, 4),
            "riskBudgetUsed": round(self.risk_budget_used, 4),
            "capitalDeployment": round(self.capital_deployment, 4),
            "strategyAllocations": {k: round(v, 4) for k, v in self.strategy_allocations.items()},
            "drawdownState": self.drawdown_state.value,
            "volatilityRegime": self.volatility_regime.value,
            "rebalanceRecommendation": self.rebalance_recommendation.value,
            "portfolioHealthScore": round(self.portfolio_health_score, 3)
        }


# Default configuration
DEFAULT_PORTFOLIO_CONFIG = {
    "target_volatility": 0.12,          # 12% annualized
    "max_drawdown_limit": 0.15,         # 15% max DD
    "rebalance_threshold": 0.05,        # 5% drift triggers rebalance
    "correlation_threshold": 0.7,       # High correlation threshold
    "max_strategy_weight": 0.35,        # Max 35% in single strategy
    "min_strategy_weight": 0.05,        # Min 5% if active
    "risk_parity_tolerance": 0.02,      # 2% risk contribution tolerance
    "vol_scaling_max": 1.5,             # Max volatility scalar
    "vol_scaling_min": 0.3,             # Min volatility scalar
    "drawdown_reduction_rate": 0.1,     # 10% risk reduction per 1% DD above threshold
}
