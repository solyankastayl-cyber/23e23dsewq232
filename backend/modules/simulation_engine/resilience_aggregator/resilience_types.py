"""
PHASE 23.4 — Resilience Types
=============================
Type definitions for Portfolio Resilience Aggregator.

Core contracts:
- PortfolioResilienceState: Unified resilience state
- ResilienceStateEnum: Resilience classification
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# RESILIENCE STATE ENUM
# ══════════════════════════════════════════════════════════════

class ResilienceStateEnum(str, Enum):
    """Portfolio resilience state."""
    ROBUST = "ROBUST"       # score >= 0.75
    STABLE = "STABLE"       # score 0.55-0.75
    FRAGILE = "FRAGILE"     # score 0.35-0.55
    CRITICAL = "CRITICAL"   # score < 0.35


# ══════════════════════════════════════════════════════════════
# RESILIENCE ACTION ENUM
# ══════════════════════════════════════════════════════════════

class ResilienceAction(str, Enum):
    """Recommended action based on resilience state."""
    HOLD = "HOLD"               # ROBUST
    HEDGE = "HEDGE"             # STABLE
    DELEVER = "DELEVER"         # FRAGILE
    KILL_SWITCH = "KILL_SWITCH" # CRITICAL


# ══════════════════════════════════════════════════════════════
# RESILIENCE THRESHOLDS
# ══════════════════════════════════════════════════════════════

RESILIENCE_THRESHOLDS = {
    ResilienceStateEnum.ROBUST: 0.75,
    ResilienceStateEnum.STABLE: 0.55,
    ResilienceStateEnum.FRAGILE: 0.35,
    # < 0.35 = CRITICAL
}


# ══════════════════════════════════════════════════════════════
# COMPONENT SCORE MAPPING
# ══════════════════════════════════════════════════════════════

# Stress Grid state -> score
STRESS_GRID_SCORES = {
    "STRONG": 0.85,
    "STABLE": 0.65,
    "FRAGILE": 0.40,
    "CRITICAL": 0.15,
}

# Strategy Survival state -> score
STRATEGY_SURVIVAL_SCORES = {
    "ROBUST": 0.85,
    "STABLE": 0.65,
    "FRAGILE": 0.40,
    "BROKEN": 0.15,
}


# ══════════════════════════════════════════════════════════════
# RESILIENCE SCORE WEIGHTS
# ══════════════════════════════════════════════════════════════

RESILIENCE_WEIGHTS = {
    "stress_grid": 0.55,
    "strategy_survival": 0.45,
}


# ══════════════════════════════════════════════════════════════
# RESILIENCE STATE MODIFIERS
# ══════════════════════════════════════════════════════════════

RESILIENCE_MODIFIERS = {
    ResilienceStateEnum.ROBUST: {
        "confidence_modifier": 1.05,
        "capital_modifier": 1.05,
    },
    ResilienceStateEnum.STABLE: {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    ResilienceStateEnum.FRAGILE: {
        "confidence_modifier": 0.85,
        "capital_modifier": 0.75,
    },
    ResilienceStateEnum.CRITICAL: {
        "confidence_modifier": 0.65,
        "capital_modifier": 0.50,
    },
}


# ══════════════════════════════════════════════════════════════
# PORTFOLIO RESILIENCE STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class PortfolioResilienceState:
    """
    Unified Portfolio Resilience State.
    
    Combines Stress Grid and Strategy Survival into final resilience overlay.
    """
    # Component states
    stress_grid_state: str
    strategy_survival_state: str
    
    # Composite
    resilience_score: float
    resilience_state: ResilienceStateEnum
    
    # Stress Grid metrics
    average_drawdown: float
    worst_drawdown: float
    fragility_index: float
    
    # Strategy Survival metrics
    average_strategy_robustness: float
    most_robust_strategy: str
    most_fragile_strategy: str
    
    # Action
    recommended_action: ResilienceAction
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Component analysis
    strongest_component: str
    weakest_component: str
    
    # Explainability
    reason: str
    
    # Component scores (for reference)
    stress_grid_score: float = 0.0
    strategy_survival_score: float = 0.0
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stress_grid_state": self.stress_grid_state,
            "strategy_survival_state": self.strategy_survival_state,
            "resilience_score": round(self.resilience_score, 4),
            "resilience_state": self.resilience_state.value,
            "average_drawdown": round(self.average_drawdown, 4),
            "worst_drawdown": round(self.worst_drawdown, 4),
            "fragility_index": round(self.fragility_index, 4),
            "average_strategy_robustness": round(self.average_strategy_robustness, 4),
            "most_robust_strategy": self.most_robust_strategy,
            "most_fragile_strategy": self.most_fragile_strategy,
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "strongest_component": self.strongest_component,
            "weakest_component": self.weakest_component,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with component scores."""
        result = self.to_dict()
        result["component_scores"] = {
            "stress_grid": round(self.stress_grid_score, 4),
            "strategy_survival": round(self.strategy_survival_score, 4),
        }
        result["weights"] = RESILIENCE_WEIGHTS
        return result
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "resilience_score": round(self.resilience_score, 4),
            "resilience_state": self.resilience_state.value,
            "recommended_action": self.recommended_action.value,
            "strongest_component": self.strongest_component,
            "weakest_component": self.weakest_component,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
        }


# ══════════════════════════════════════════════════════════════
# RESILIENCE HISTORY ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass
class ResilienceHistoryEntry:
    """Single history entry for resilience state."""
    resilience_state: ResilienceStateEnum
    resilience_score: float
    weakest_component: str
    recommended_action: ResilienceAction
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resilience_state": self.resilience_state.value,
            "resilience_score": round(self.resilience_score, 4),
            "weakest_component": self.weakest_component,
            "recommended_action": self.recommended_action.value,
            "timestamp": self.timestamp.isoformat(),
        }
