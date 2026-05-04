"""
PHASE 23.3 — Strategy Survival Types
====================================
Type definitions for Strategy Survival Matrix.

Core contracts:
- StrategySurvivalState: Single strategy survival analysis
- StrategySurvivalMatrix: All strategies combined
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# STRATEGY SURVIVAL STATE ENUM
# ══════════════════════════════════════════════════════════════

class StrategySurvivalStateEnum(str, Enum):
    """Strategy survival state classification."""
    ROBUST = "ROBUST"       # robustness > 0.70
    STABLE = "STABLE"       # robustness 0.50-0.70
    FRAGILE = "FRAGILE"     # robustness 0.30-0.50
    BROKEN = "BROKEN"       # robustness < 0.30


# ══════════════════════════════════════════════════════════════
# STRATEGY ACTION ENUM
# ══════════════════════════════════════════════════════════════

class StrategyAction(str, Enum):
    """Recommended action for strategy under stress."""
    KEEP_ACTIVE = "KEEP_ACTIVE"   # ROBUST
    REDUCE = "REDUCE"             # STABLE
    SHADOW = "SHADOW"             # FRAGILE
    DISABLE = "DISABLE"           # BROKEN


# ══════════════════════════════════════════════════════════════
# ROBUSTNESS THRESHOLDS
# ══════════════════════════════════════════════════════════════

ROBUSTNESS_THRESHOLDS = {
    StrategySurvivalStateEnum.ROBUST: 0.70,
    StrategySurvivalStateEnum.STABLE: 0.50,
    StrategySurvivalStateEnum.FRAGILE: 0.30,
    # < 0.30 = BROKEN
}


# ══════════════════════════════════════════════════════════════
# ROBUSTNESS SCORE WEIGHTS
# ══════════════════════════════════════════════════════════════

ROBUSTNESS_WEIGHTS = {
    "stable": 0.40,
    "stressed": 0.25,
    "fragile": -0.20,
    "broken": -0.35,
}


# ══════════════════════════════════════════════════════════════
# STRATEGY STRESS SENSITIVITY
# ══════════════════════════════════════════════════════════════

# Strategy type -> scenario type sensitivity multipliers
STRATEGY_SENSITIVITY = {
    "TREND_FOLLOWING": {
        "FLASH_CRASH": 1.3,
        "REGIME_FLIP": 1.5,
        "VOL_SHOCK": 1.2,
        "CORR_SPIKE": 1.1,
        "LIQ_FREEZE": 1.0,
    },
    "MEAN_REVERSION": {
        "FLASH_CRASH": 1.1,
        "REGIME_FLIP": 1.2,
        "VOL_SHOCK": 1.4,
        "CORR_SPIKE": 1.2,
        "LIQ_FREEZE": 1.0,
    },
    "MTF_BREAKOUT": {
        "FLASH_CRASH": 1.2,
        "REGIME_FLIP": 1.3,
        "VOL_SHOCK": 1.1,
        "CORR_SPIKE": 1.0,
        "LIQ_FREEZE": 1.4,
    },
    "CHANNEL_BREAKOUT": {
        "FLASH_CRASH": 1.2,
        "REGIME_FLIP": 1.3,
        "VOL_SHOCK": 1.1,
        "CORR_SPIKE": 1.0,
        "LIQ_FREEZE": 1.3,
    },
    "MOMENTUM_CONTINUATION": {
        "FLASH_CRASH": 1.4,
        "REGIME_FLIP": 1.4,
        "VOL_SHOCK": 1.2,
        "CORR_SPIKE": 1.1,
        "LIQ_FREEZE": 1.0,
    },
    "FUNDING_ARB": {
        "FLASH_CRASH": 0.8,
        "REGIME_FLIP": 0.7,
        "VOL_SHOCK": 0.9,
        "CORR_SPIKE": 0.8,
        "LIQ_FREEZE": 1.1,
    },
    "LIQUIDATION_CAPTURE": {
        "FLASH_CRASH": 0.6,  # Benefits from crashes
        "REGIME_FLIP": 1.0,
        "VOL_SHOCK": 0.7,
        "CORR_SPIKE": 0.9,
        "LIQ_FREEZE": 0.8,
    },
    "HARMONIC_ABCD": {
        "FLASH_CRASH": 1.2,
        "REGIME_FLIP": 1.1,
        "VOL_SHOCK": 1.3,
        "CORR_SPIKE": 1.1,
        "LIQ_FREEZE": 1.0,
    },
    "DEFAULT": {
        "FLASH_CRASH": 1.0,
        "REGIME_FLIP": 1.0,
        "VOL_SHOCK": 1.0,
        "CORR_SPIKE": 1.0,
        "LIQ_FREEZE": 1.0,
    },
}


# ══════════════════════════════════════════════════════════════
# ROBUSTNESS STATE MODIFIERS
# ══════════════════════════════════════════════════════════════

ROBUSTNESS_MODIFIERS = {
    StrategySurvivalStateEnum.ROBUST: {
        "confidence_modifier": 1.10,
        "capital_modifier": 1.10,
    },
    StrategySurvivalStateEnum.STABLE: {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    StrategySurvivalStateEnum.FRAGILE: {
        "confidence_modifier": 0.80,
        "capital_modifier": 0.70,
    },
    StrategySurvivalStateEnum.BROKEN: {
        "confidence_modifier": 0.60,
        "capital_modifier": 0.50,
    },
}


# ══════════════════════════════════════════════════════════════
# DEFAULT STRATEGIES
# ══════════════════════════════════════════════════════════════

DEFAULT_STRATEGIES = [
    "TREND_FOLLOWING",
    "MEAN_REVERSION",
    "MTF_BREAKOUT",
    "CHANNEL_BREAKOUT",
    "MOMENTUM_CONTINUATION",
    "FUNDING_ARB",
    "LIQUIDATION_CAPTURE",
    "HARMONIC_ABCD",
]


# ══════════════════════════════════════════════════════════════
# STRATEGY SURVIVAL STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class StrategySurvivalState:
    """
    Single strategy survival analysis.
    
    Contains robustness metrics for one strategy across all scenarios.
    """
    strategy_name: str
    
    # Scenario execution
    scenarios_run: int
    
    # Survival distribution
    stable_count: int
    stressed_count: int
    fragile_count: int
    broken_count: int
    
    # Drawdown metrics
    average_drawdown: float
    worst_drawdown: float
    
    # Robustness
    robustness_score: float
    survival_state: StrategySurvivalStateEnum
    
    # Action
    recommended_action: StrategyAction
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Worst case
    worst_scenario: str
    
    # Explainability
    reason: str
    
    # By scenario type breakdown
    by_scenario_type: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_name": self.strategy_name,
            "scenarios_run": self.scenarios_run,
            "stable_count": self.stable_count,
            "stressed_count": self.stressed_count,
            "fragile_count": self.fragile_count,
            "broken_count": self.broken_count,
            "average_drawdown": round(self.average_drawdown, 4),
            "worst_drawdown": round(self.worst_drawdown, 4),
            "robustness_score": round(self.robustness_score, 4),
            "survival_state": self.survival_state.value,
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "worst_scenario": self.worst_scenario,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with breakdown."""
        result = self.to_dict()
        result["by_scenario_type"] = self.by_scenario_type
        return result
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "strategy_name": self.strategy_name,
            "robustness_score": round(self.robustness_score, 4),
            "survival_state": self.survival_state.value,
            "recommended_action": self.recommended_action.value,
            "worst_scenario": self.worst_scenario,
        }


# ══════════════════════════════════════════════════════════════
# STRATEGY SURVIVAL MATRIX
# ══════════════════════════════════════════════════════════════

@dataclass
class StrategySurvivalMatrix:
    """
    Complete strategy survival matrix.
    
    Contains survival analysis for all strategies.
    """
    strategies: Dict[str, StrategySurvivalState]
    
    most_robust: str
    most_fragile: str
    
    average_system_strategy_robustness: float
    
    # Counts
    robust_count: int
    stable_count: int
    fragile_count: int
    broken_count: int
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategies": {k: v.to_dict() for k, v in self.strategies.items()},
            "most_robust": self.most_robust,
            "most_fragile": self.most_fragile,
            "average_system_strategy_robustness": round(self.average_system_strategy_robustness, 4),
            "strategy_distribution": {
                "robust": self.robust_count,
                "stable": self.stable_count,
                "fragile": self.fragile_count,
                "broken": self.broken_count,
            },
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "strategy_count": len(self.strategies),
            "most_robust": self.most_robust,
            "most_fragile": self.most_fragile,
            "average_system_strategy_robustness": round(self.average_system_strategy_robustness, 4),
            "strategy_distribution": {
                "robust": self.robust_count,
                "stable": self.stable_count,
                "fragile": self.fragile_count,
                "broken": self.broken_count,
            },
        }
