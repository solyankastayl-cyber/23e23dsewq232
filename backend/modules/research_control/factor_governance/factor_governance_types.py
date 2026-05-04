"""
PHASE 17.2 — Factor Governance Types
=====================================
Contracts for Factor Governance Engine.

Purpose:
    Define governance evaluation contracts for alpha-factors.
    Factor Governance evaluates quality across 5 dimensions.

Key Difference from Feature Governance:
    - Feature Governance: raw signals, indicators, features
    - Factor Governance: alpha signals, factors, strategies
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# GOVERNANCE STATE ENUM
# ══════════════════════════════════════════════════════════════

class FactorGovernanceState(str, Enum):
    """Factor governance state classification."""
    ELITE = "ELITE"           # Top performing factor
    STABLE = "STABLE"         # Consistently good factor
    WATCHLIST = "WATCHLIST"   # Factor needs monitoring
    DEGRADED = "DEGRADED"     # Factor is degrading
    RETIRE = "RETIRE"         # Factor should be retired


class FactorDimension(str, Enum):
    """Factor governance evaluation dimensions."""
    PERFORMANCE = "performance"
    REGIME = "regime"
    CAPACITY = "capacity"
    CROWDING = "crowding"
    DECAY = "decay"


# ══════════════════════════════════════════════════════════════
# GOVERNANCE THRESHOLDS
# ══════════════════════════════════════════════════════════════

FACTOR_GOVERNANCE_THRESHOLDS = {
    "elite_min": 0.85,        # score > 0.85 = ELITE
    "stable_min": 0.70,       # score > 0.70 = STABLE
    "watchlist_min": 0.55,    # score > 0.55 = WATCHLIST
    "degraded_min": 0.40,     # score > 0.40 = DEGRADED
    # score <= 0.40 = RETIRE
}


# ══════════════════════════════════════════════════════════════
# GOVERNANCE WEIGHTS
# ══════════════════════════════════════════════════════════════

FACTOR_GOVERNANCE_WEIGHTS = {
    "performance": 0.30,
    "regime": 0.20,
    "capacity": 0.15,
    "crowding": 0.15,
    "decay": 0.20,
}


# ══════════════════════════════════════════════════════════════
# GOVERNANCE MODIFIERS BY STATE
# ══════════════════════════════════════════════════════════════

FACTOR_GOVERNANCE_MODIFIERS = {
    FactorGovernanceState.ELITE: {
        "capital_modifier": 1.15,
        "confidence_modifier": 1.10,
    },
    FactorGovernanceState.STABLE: {
        "capital_modifier": 1.05,
        "confidence_modifier": 1.03,
    },
    FactorGovernanceState.WATCHLIST: {
        "capital_modifier": 0.95,
        "confidence_modifier": 0.95,
    },
    FactorGovernanceState.DEGRADED: {
        "capital_modifier": 0.80,
        "confidence_modifier": 0.85,
    },
    FactorGovernanceState.RETIRE: {
        "capital_modifier": 0.50,
        "confidence_modifier": 0.60,
    },
}


# ══════════════════════════════════════════════════════════════
# DIMENSION INPUT TYPES
# ══════════════════════════════════════════════════════════════

@dataclass
class PerformanceInput:
    """Input for performance stability evaluation."""
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    
    def to_dict(self) -> Dict:
        return {
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "calmar_ratio": round(self.calmar_ratio, 4),
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
        }


@dataclass
class RegimeInput:
    """Input for regime robustness evaluation."""
    bull_performance: float   # Performance in bull regime
    bear_performance: float   # Performance in bear regime
    sideways_performance: float  # Performance in sideways regime
    high_vol_performance: float  # Performance in high volatility
    low_vol_performance: float   # Performance in low volatility
    
    def to_dict(self) -> Dict:
        return {
            "bull_performance": round(self.bull_performance, 4),
            "bear_performance": round(self.bear_performance, 4),
            "sideways_performance": round(self.sideways_performance, 4),
            "high_vol_performance": round(self.high_vol_performance, 4),
            "low_vol_performance": round(self.low_vol_performance, 4),
        }


@dataclass
class CapacityInput:
    """Input for capacity evaluation."""
    current_aum: float        # Current assets under management
    max_capacity: float       # Estimated maximum capacity
    slippage_impact: float    # Slippage at current size
    market_impact: float      # Market impact estimate
    
    def to_dict(self) -> Dict:
        return {
            "current_aum": self.current_aum,
            "max_capacity": self.max_capacity,
            "capacity_utilization": round(self.current_aum / self.max_capacity if self.max_capacity > 0 else 1.0, 4),
            "slippage_impact": round(self.slippage_impact, 4),
            "market_impact": round(self.market_impact, 4),
        }


@dataclass
class CrowdingInput:
    """Input for crowding risk evaluation."""
    correlation_with_market: float  # How correlated with overall market
    similar_strategies_count: int   # Number of similar strategies
    flow_correlation: float         # Correlation with fund flows
    crowding_indicator: float       # Direct crowding measure (0-1)
    
    def to_dict(self) -> Dict:
        return {
            "correlation_with_market": round(self.correlation_with_market, 4),
            "similar_strategies_count": self.similar_strategies_count,
            "flow_correlation": round(self.flow_correlation, 4),
            "crowding_indicator": round(self.crowding_indicator, 4),
        }


@dataclass
class DecayInput:
    """Input for decay velocity evaluation."""
    half_life_days: float        # Factor half-life in days
    performance_trend: float     # Trend of performance (negative = decay)
    information_ratio_decay: float  # How fast IR is decaying
    
    def to_dict(self) -> Dict:
        return {
            "half_life_days": round(self.half_life_days, 2),
            "performance_trend": round(self.performance_trend, 4),
            "information_ratio_decay": round(self.information_ratio_decay, 4),
        }


# ══════════════════════════════════════════════════════════════
# DIMENSION RESULT TYPE
# ══════════════════════════════════════════════════════════════

@dataclass
class FactorDimensionResult:
    """Result from a single dimension evaluation."""
    dimension: FactorDimension
    score: float  # 0..1
    status: str   # EXCELLENT / GOOD / WARNING / POOR
    reason: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "dimension": self.dimension.value,
            "score": round(self.score, 4),
            "status": self.status,
            "reason": self.reason,
            "inputs": self.inputs,
        }


# ══════════════════════════════════════════════════════════════
# FACTOR GOVERNANCE STATE CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class FactorGovernanceResult:
    """
    Output from Factor Governance Engine.
    
    Evaluates alpha-factor quality across 5 dimensions:
    - Performance: Return stability and consistency
    - Regime: Works across different market regimes
    - Capacity: Handles capital scaling
    - Crowding: Not overcrowded by market participants
    - Decay: How fast the factor degrades
    
    Key Principle:
        Factor Governance affects CAPITAL allocation.
        This is more impactful than Feature Governance.
    """
    factor_name: str
    timestamp: datetime
    
    # Dimension scores (0..1)
    performance_score: float
    regime_score: float
    capacity_score: float
    crowding_score: float
    decay_score: float
    
    # Aggregated governance
    governance_score: float  # 0..1
    governance_state: FactorGovernanceState
    
    # Modifiers for downstream use (affects capital!)
    capital_modifier: float     # 0.50 to 1.15
    confidence_modifier: float  # 0.60 to 1.10
    
    # Dimension analysis
    weakest_dimension: FactorDimension
    strongest_dimension: FactorDimension
    
    # Detailed results
    dimension_results: List[FactorDimensionResult] = field(default_factory=list)
    
    # Metadata
    drivers: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "factor_name": self.factor_name,
            "timestamp": self.timestamp.isoformat(),
            "performance_score": round(self.performance_score, 4),
            "regime_score": round(self.regime_score, 4),
            "capacity_score": round(self.capacity_score, 4),
            "crowding_score": round(self.crowding_score, 4),
            "decay_score": round(self.decay_score, 4),
            "governance_score": round(self.governance_score, 4),
            "governance_state": self.governance_state.value,
            "capital_modifier": round(self.capital_modifier, 4),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "weakest_dimension": self.weakest_dimension.value,
            "strongest_dimension": self.strongest_dimension.value,
            "dimension_results": [r.to_dict() for r in self.dimension_results],
            "drivers": self.drivers,
        }
    
    def to_summary(self) -> Dict:
        """Compact summary for quick integration."""
        return {
            "factor_name": self.factor_name,
            "governance_score": round(self.governance_score, 4),
            "governance_state": self.governance_state.value,
            "capital_modifier": round(self.capital_modifier, 4),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "weakest_dimension": self.weakest_dimension.value,
            "strongest_dimension": self.strongest_dimension.value,
        }


# ══════════════════════════════════════════════════════════════
# BATCH REQUEST/RESPONSE
# ══════════════════════════════════════════════════════════════

@dataclass
class FactorBatchRequest:
    """Request for batch factor governance evaluation."""
    factor_names: List[str]


@dataclass  
class FactorBatchResponse:
    """Response from batch factor governance evaluation."""
    results: Dict[str, FactorGovernanceResult]
    summary: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "results": {k: v.to_summary() for k, v in self.results.items()},
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
        }
