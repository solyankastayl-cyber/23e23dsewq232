"""
PHASE 21.3 — Capital Allocation Layer Types
===========================================
Type definitions for Capital Allocation Aggregator.

Core contracts:
- CapitalAllocationLayerState: Unified layer state
- AllocationState: Overall allocation state enum
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# ALLOCATION STATE ENUM
# ══════════════════════════════════════════════════════════════

class AllocationState(str, Enum):
    """Overall allocation state."""
    OPTIMAL = "OPTIMAL"           # Budget OPEN, high confidence, low concentration
    BALANCED = "BALANCED"         # Budget THROTTLED, normal confidence
    CONSTRAINED = "CONSTRAINED"   # Budget DEFENSIVE or high concentration
    STRESSED = "STRESSED"         # Budget EMERGENCY or very low efficiency


# ══════════════════════════════════════════════════════════════
# ALLOCATION STATE THRESHOLDS
# ══════════════════════════════════════════════════════════════

ALLOCATION_STATE_THRESHOLDS = {
    "efficiency_optimal": 0.55,
    "efficiency_balanced": 0.35,
    "efficiency_stressed": 0.15,
    "concentration_high": 0.50,
    "confidence_high": 0.75,
}


# ══════════════════════════════════════════════════════════════
# CAPITAL ALLOCATION LAYER STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class CapitalAllocationLayerState:
    """
    Unified Capital Allocation Layer State.
    
    Combines:
    - Core Allocator (PHASE 21.1)
    - Budget Constraints (PHASE 21.2)
    """
    # Capital
    total_capital: float
    deployable_capital: float
    reserve_capital: float
    dry_powder: float
    
    # Allocations
    strategy_allocations: Dict[str, float]
    factor_allocations: Dict[str, float]
    asset_allocations: Dict[str, float]
    cluster_allocations: Dict[str, float]
    
    # Routing
    dominant_route: str
    routing_regime: str
    
    # Budget
    budget_state: str
    budget_multiplier: float
    
    # Scores
    allocation_confidence: float
    concentration_score: float
    capital_efficiency: float
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # State
    allocation_state: AllocationState
    
    # Explainability
    reason: str
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_capital": round(self.total_capital, 4),
            "deployable_capital": round(self.deployable_capital, 4),
            "reserve_capital": round(self.reserve_capital, 4),
            "dry_powder": round(self.dry_powder, 4),
            
            "strategy_allocations": {k: round(v, 4) for k, v in self.strategy_allocations.items()},
            "factor_allocations": {k: round(v, 4) for k, v in self.factor_allocations.items()},
            "asset_allocations": {k: round(v, 4) for k, v in self.asset_allocations.items()},
            "cluster_allocations": {k: round(v, 4) for k, v in self.cluster_allocations.items()},
            
            "dominant_route": self.dominant_route,
            "routing_regime": self.routing_regime,
            
            "budget_state": self.budget_state,
            "budget_multiplier": round(self.budget_multiplier, 4),
            
            "allocation_confidence": round(self.allocation_confidence, 4),
            "concentration_score": round(self.concentration_score, 4),
            "capital_efficiency": round(self.capital_efficiency, 4),
            
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            
            "allocation_state": self.allocation_state.value,
            
            "reason": self.reason,
            
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "total_capital": round(self.total_capital, 4),
            "deployable_capital": round(self.deployable_capital, 4),
            "dominant_route": self.dominant_route,
            "budget_state": self.budget_state,
            "allocation_state": self.allocation_state.value,
            "capital_efficiency": round(self.capital_efficiency, 4),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with all details."""
        result = self.to_dict()
        result["details"] = {
            "allocator": {
                "dominant_route": self.dominant_route,
                "routing_regime": self.routing_regime,
                "allocation_confidence": round(self.allocation_confidence, 4),
                "concentration_score": round(self.concentration_score, 4),
            },
            "budget": {
                "budget_state": self.budget_state,
                "budget_multiplier": round(self.budget_multiplier, 4),
                "reserve_capital": round(self.reserve_capital, 4),
                "dry_powder": round(self.dry_powder, 4),
            },
        }
        return result


# ══════════════════════════════════════════════════════════════
# LAYER HISTORY ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass
class LayerHistoryEntry:
    """Single history entry for layer state."""
    allocation_state: AllocationState
    budget_state: str
    capital_efficiency: float
    deployable_capital: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allocation_state": self.allocation_state.value,
            "budget_state": self.budget_state,
            "capital_efficiency": round(self.capital_efficiency, 4),
            "deployable_capital": round(self.deployable_capital, 4),
            "timestamp": self.timestamp.isoformat(),
        }
