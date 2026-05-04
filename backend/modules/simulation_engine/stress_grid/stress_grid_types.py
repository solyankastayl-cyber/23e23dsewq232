"""
PHASE 23.2 — Stress Grid Types
==============================
Type definitions for Multi-Scenario Stress Grid.

Core contracts:
- StressGridState: Grid execution results
- ResilienceState: System resilience classification
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# RESILIENCE STATE ENUM
# ══════════════════════════════════════════════════════════════

class ResilienceState(str, Enum):
    """System resilience state based on stress grid results."""
    STRONG = "STRONG"       # fragility_index < 0.20
    STABLE = "STABLE"       # fragility_index 0.20-0.40
    FRAGILE = "FRAGILE"     # fragility_index 0.40-0.60
    CRITICAL = "CRITICAL"   # fragility_index > 0.60


# ══════════════════════════════════════════════════════════════
# RESILIENCE ACTION ENUM
# ══════════════════════════════════════════════════════════════

class ResilienceAction(str, Enum):
    """Recommended action based on resilience state."""
    HOLD = "HOLD"                             # STRONG
    HEDGE = "HEDGE"                           # STABLE
    DELEVER = "DELEVER"                       # FRAGILE
    REDUCE_SYSTEM_RISK = "REDUCE_SYSTEM_RISK" # CRITICAL


# ══════════════════════════════════════════════════════════════
# RESILIENCE STATE THRESHOLDS
# ══════════════════════════════════════════════════════════════

RESILIENCE_THRESHOLDS = {
    ResilienceState.STRONG: 0.20,
    ResilienceState.STABLE: 0.40,
    ResilienceState.FRAGILE: 0.60,
    # > 0.60 = CRITICAL
}


# ══════════════════════════════════════════════════════════════
# FRAGILITY INDEX WEIGHTS
# ══════════════════════════════════════════════════════════════

FRAGILITY_WEIGHTS = {
    "broken": 0.50,
    "fragile": 0.30,
    "stressed": 0.20,
    "stable": 0.00,
}


# ══════════════════════════════════════════════════════════════
# RESILIENCE STATE MODIFIERS
# ══════════════════════════════════════════════════════════════

RESILIENCE_MODIFIERS = {
    ResilienceState.STRONG: {
        "confidence_modifier": 1.05,
        "capital_modifier": 1.05,
    },
    ResilienceState.STABLE: {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    ResilienceState.FRAGILE: {
        "confidence_modifier": 0.85,
        "capital_modifier": 0.75,
    },
    ResilienceState.CRITICAL: {
        "confidence_modifier": 0.70,
        "capital_modifier": 0.55,
    },
}


# ══════════════════════════════════════════════════════════════
# SCENARIO RESULT SUMMARY
# ══════════════════════════════════════════════════════════════

@dataclass
class ScenarioResultSummary:
    """Summary of a single scenario result."""
    scenario_name: str
    scenario_type: str
    severity: str
    estimated_drawdown: float
    survival_state: str
    recommended_action: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "scenario_type": self.scenario_type,
            "severity": self.severity,
            "estimated_drawdown": round(self.estimated_drawdown, 4),
            "survival_state": self.survival_state,
            "recommended_action": self.recommended_action,
        }


# ══════════════════════════════════════════════════════════════
# STRESS GRID STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class StressGridState:
    """
    Stress Grid execution state.
    
    Contains results from running all scenarios through the grid.
    """
    # Execution counts
    scenarios_run: int
    
    # Survival state distribution
    stable_count: int
    stressed_count: int
    fragile_count: int
    broken_count: int
    
    # Worst case analysis
    worst_scenario: str
    worst_drawdown: float
    
    # Aggregate metrics
    average_drawdown: float
    fragility_index: float
    
    # System state
    system_resilience_state: ResilienceState
    recommended_action: ResilienceAction
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Explainability
    reason: str
    
    # Scenario details
    scenario_results: List[ScenarioResultSummary] = field(default_factory=list)
    
    # By type breakdown
    by_type_breakdown: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scenarios_run": self.scenarios_run,
            "stable_count": self.stable_count,
            "stressed_count": self.stressed_count,
            "fragile_count": self.fragile_count,
            "broken_count": self.broken_count,
            "worst_scenario": self.worst_scenario,
            "worst_drawdown": round(self.worst_drawdown, 4),
            "average_drawdown": round(self.average_drawdown, 4),
            "fragility_index": round(self.fragility_index, 4),
            "system_resilience_state": self.system_resilience_state.value,
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with all details."""
        result = self.to_dict()
        result["scenario_results"] = [s.to_dict() for s in self.scenario_results]
        result["by_type_breakdown"] = self.by_type_breakdown
        return result
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "scenarios_run": self.scenarios_run,
            "fragility_index": round(self.fragility_index, 4),
            "system_resilience_state": self.system_resilience_state.value,
            "worst_scenario": self.worst_scenario,
            "worst_drawdown": round(self.worst_drawdown, 4),
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
        }


# ══════════════════════════════════════════════════════════════
# STRESS GRID HISTORY ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass
class StressGridHistoryEntry:
    """Single history entry for stress grid state."""
    system_resilience_state: ResilienceState
    fragility_index: float
    worst_scenario: str
    recommended_action: ResilienceAction
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_resilience_state": self.system_resilience_state.value,
            "fragility_index": round(self.fragility_index, 4),
            "worst_scenario": self.worst_scenario,
            "recommended_action": self.recommended_action.value,
            "timestamp": self.timestamp.isoformat(),
        }
