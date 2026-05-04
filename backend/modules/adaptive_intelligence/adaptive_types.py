"""
PHASE 11 - Adaptive Intelligence Types
=======================================
Core data types for adaptive system.

Provides:
- Performance tracking types
- Parameter optimization types
- Edge decay detection types
- Adaptive control types
- Safety layer types
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class AdaptiveState(str, Enum):
    """System adaptive state"""
    STABLE = "STABLE"               # No changes needed
    OBSERVING = "OBSERVING"         # Monitoring potential changes
    ADAPTING = "ADAPTING"           # Actively making changes
    COOLDOWN = "COOLDOWN"           # Waiting after changes
    SHADOW_TESTING = "SHADOW_TESTING"  # Testing changes in shadow


class PerformanceTrend(str, Enum):
    """Strategy performance trend"""
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"
    CRITICAL = "CRITICAL"


class EdgeStatus(str, Enum):
    """Edge health status"""
    STRONG = "STRONG"               # Edge is strong and consistent
    HEALTHY = "HEALTHY"             # Edge is working normally
    WEAKENING = "WEAKENING"         # Signs of decay
    CRITICAL = "CRITICAL"           # Significant decay
    DEAD = "DEAD"                   # Edge no longer works


class ChangeDecision(str, Enum):
    """Safety layer decision on changes"""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING_COOLDOWN = "PENDING_COOLDOWN"
    PENDING_SHADOW = "PENDING_SHADOW"
    PENDING_OOS = "PENDING_OOS"
    TOO_LARGE = "TOO_LARGE"


class AdaptiveAction(str, Enum):
    """Types of adaptive actions"""
    NO_ACTION = "NO_ACTION"
    ADJUST_PARAMETER = "ADJUST_PARAMETER"
    ADJUST_WEIGHT = "ADJUST_WEIGHT"
    DISABLE_STRATEGY = "DISABLE_STRATEGY"
    ENABLE_STRATEGY = "ENABLE_STRATEGY"
    INCREASE_ALLOCATION = "INCREASE_ALLOCATION"
    DECREASE_ALLOCATION = "DECREASE_ALLOCATION"
    FULL_RESET = "FULL_RESET"


class OptimizationMethod(str, Enum):
    """Parameter optimization method"""
    GRID_SEARCH = "GRID_SEARCH"
    BAYESIAN = "BAYESIAN"
    ROLLING = "ROLLING"
    GENETIC = "GENETIC"


@dataclass
class StrategyPerformance:
    """Strategy performance tracking"""
    strategy_id: str
    name: str
    timestamp: datetime
    
    # Core metrics
    win_rate: float                 # Recent win rate
    long_term_win_rate: float       # Historical win rate
    profit_factor: float            # Gross profit / gross loss
    expectancy: float               # Expected value per trade
    
    # Risk metrics
    max_drawdown: float
    current_drawdown: float
    sharpe_ratio: float
    
    # Trend analysis
    performance_trend: PerformanceTrend
    trend_strength: float           # 0-1
    
    # Regime performance
    regime_performance: Dict[str, float] = field(default_factory=dict)
    
    # Trade counts
    total_trades: int = 0
    recent_trades: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "win_rate": round(self.win_rate, 4),
            "long_term_win_rate": round(self.long_term_win_rate, 4),
            "profit_factor": round(self.profit_factor, 3),
            "expectancy": round(self.expectancy, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "current_drawdown": round(self.current_drawdown, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "performance_trend": self.performance_trend.value,
            "trend_strength": round(self.trend_strength, 3),
            "regime_performance": self.regime_performance,
            "total_trades": self.total_trades,
            "recent_trades": self.recent_trades
        }


@dataclass
class ParameterAdjustment:
    """Parameter optimization result"""
    parameter_name: str
    strategy_id: str
    timestamp: datetime
    
    # Values
    current_value: float
    suggested_value: float
    optimal_range: tuple             # (min, max)
    
    # Improvement metrics
    expected_improvement: float      # Expected % improvement
    confidence: float                # 0-1 confidence in change
    
    # Safety checks
    change_magnitude: float          # How big is the change
    within_limits: bool              # Is it within allowed limits
    cooldown_clear: bool             # Has cooldown passed
    
    # Status
    decision: ChangeDecision = ChangeDecision.PENDING_OOS
    rejection_reason: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "parameter_name": self.parameter_name,
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "current_value": round(self.current_value, 6),
            "suggested_value": round(self.suggested_value, 6),
            "optimal_range": self.optimal_range,
            "expected_improvement": round(self.expected_improvement, 4),
            "confidence": round(self.confidence, 3),
            "change_magnitude": round(self.change_magnitude, 4),
            "within_limits": self.within_limits,
            "cooldown_clear": self.cooldown_clear,
            "decision": self.decision.value,
            "rejection_reason": self.rejection_reason
        }


@dataclass
class FactorWeight:
    """Factor weight adjustment"""
    factor_name: str
    category: str                    # alpha, ensemble, structure, etc.
    timestamp: datetime
    
    # Weights
    current_weight: float
    suggested_weight: float
    weight_change: float
    
    # Performance attribution
    contribution_to_pnl: float       # How much it contributed
    signal_accuracy: float           # Signal hit rate
    
    # Trend
    weight_trend: str                # UP, DOWN, STABLE
    
    # Status
    decision: ChangeDecision = ChangeDecision.PENDING_OOS
    
    def to_dict(self) -> Dict:
        return {
            "factor_name": self.factor_name,
            "category": self.category,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "current_weight": round(self.current_weight, 4),
            "suggested_weight": round(self.suggested_weight, 4),
            "weight_change": round(self.weight_change, 4),
            "contribution_to_pnl": round(self.contribution_to_pnl, 4),
            "signal_accuracy": round(self.signal_accuracy, 4),
            "weight_trend": self.weight_trend,
            "decision": self.decision.value
        }


@dataclass
class EdgeDecaySignal:
    """Edge decay detection result"""
    strategy_id: str
    edge_name: str
    timestamp: datetime
    
    # Status
    edge_status: EdgeStatus
    decay_probability: float         # 0-1
    
    # Metrics
    rolling_pf: float                # Rolling profit factor
    rolling_expectancy: float        # Rolling expectancy
    hit_rate_drift: float            # Change in hit rate
    confidence_degradation: float    # How confidence dropped
    
    # Confirmation
    confirmed_decay: bool            # Multi-axis confirmation
    confirmation_axes: List[str] = field(default_factory=list)
    
    # Recommendation
    recommended_action: AdaptiveAction = AdaptiveAction.NO_ACTION
    urgency: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "edge_name": self.edge_name,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "edge_status": self.edge_status.value,
            "decay_probability": round(self.decay_probability, 3),
            "rolling_pf": round(self.rolling_pf, 3),
            "rolling_expectancy": round(self.rolling_expectancy, 4),
            "hit_rate_drift": round(self.hit_rate_drift, 4),
            "confidence_degradation": round(self.confidence_degradation, 4),
            "confirmed_decay": self.confirmed_decay,
            "confirmation_axes": self.confirmation_axes,
            "recommended_action": self.recommended_action.value,
            "urgency": round(self.urgency, 3)
        }


@dataclass
class AdaptiveRecommendation:
    """Unified adaptive recommendation"""
    timestamp: datetime
    
    # Action
    action: AdaptiveAction
    target: str                      # Strategy/parameter/factor name
    
    # Details
    current_state: Dict
    proposed_change: Dict
    expected_impact: float
    
    # Safety
    safety_cleared: bool
    safety_checks: Dict[str, bool]
    
    # Confidence
    confidence: float
    evidence_strength: float
    
    # Timing
    execution_timing: str            # IMMEDIATE, NEXT_SESSION, COOLDOWN
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "action": self.action.value,
            "target": self.target,
            "current_state": self.current_state,
            "proposed_change": self.proposed_change,
            "expected_impact": round(self.expected_impact, 4),
            "safety_cleared": self.safety_cleared,
            "safety_checks": self.safety_checks,
            "confidence": round(self.confidence, 3),
            "evidence_strength": round(self.evidence_strength, 3),
            "execution_timing": self.execution_timing
        }


@dataclass
class SystemAdaptiveSnapshot:
    """Complete adaptive system state"""
    timestamp: datetime
    
    # Overall state
    adaptive_state: AdaptiveState
    system_adaptivity_score: float   # 0-1
    
    # Edge health
    edges_strengthening: int
    edges_stable: int
    edges_degrading: int
    edges_critical: int
    
    # Changes
    pending_parameter_changes: int
    pending_weight_changes: int
    strategies_disabled: int
    
    # Safety
    in_cooldown: bool
    shadow_tests_running: int
    
    # Health
    overall_system_health: float     # 0-1
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "adaptiveState": self.adaptive_state.value,
            "systemAdaptivityScore": round(self.system_adaptivity_score, 3),
            "edgesStrengthening": self.edges_strengthening,
            "edgesStable": self.edges_stable,
            "edgesDegrading": self.edges_degrading,
            "edgesCritical": self.edges_critical,
            "pendingParameterChanges": self.pending_parameter_changes,
            "pendingWeightChanges": self.pending_weight_changes,
            "strategiesDisabled": self.strategies_disabled,
            "inCooldown": self.in_cooldown,
            "shadowTestsRunning": self.shadow_tests_running,
            "overallSystemHealth": round(self.overall_system_health, 3)
        }


# Default configuration
DEFAULT_ADAPTIVE_CONFIG = {
    # Performance thresholds
    "min_trades_for_adaptation": 30,
    "win_rate_decline_threshold": 0.05,
    "pf_decline_threshold": 0.3,
    
    # Change limits
    "max_parameter_change_pct": 0.10,    # 10% max change per cycle
    "max_weight_change_pct": 0.15,       # 15% max weight change
    "max_allocation_change_pct": 0.20,   # 20% max allocation change
    
    # Cooldown periods (hours)
    "parameter_cooldown_hours": 168,      # 1 week
    "weight_cooldown_hours": 72,          # 3 days
    "strategy_cooldown_hours": 336,       # 2 weeks
    
    # Safety thresholds
    "shadow_test_duration_hours": 48,     # 2 days shadow testing
    "oos_validation_required": True,
    "min_confidence_for_change": 0.7,
    
    # Edge decay
    "edge_decay_lookback_days": 30,
    "edge_death_threshold": 0.9,          # PF below 0.9 = dead
    
    # Optimization
    "optimization_frequency_hours": 24,
    "rolling_window_size": 50,
}
