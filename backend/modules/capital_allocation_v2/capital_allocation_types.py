"""
PHASE 21.1 — Capital Allocation Types
=====================================
Type definitions for Capital Allocation Engine v2.

Core contracts:
- CapitalAllocationState: System-wide capital distribution
- AllocationSlice: Individual allocation slice
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# DOMINANT ROUTE ENUM
# ══════════════════════════════════════════════════════════════

class DominantRoute(str, Enum):
    """Primary capital routing dimension."""
    STRATEGY = "STRATEGY"      # Route by strategy performance
    FACTOR = "FACTOR"          # Route by factor governance
    ASSET = "ASSET"            # Route by asset dominance
    CLUSTER = "CLUSTER"        # Route by cluster exposure
    BALANCED = "BALANCED"      # No clear dominant route


# ══════════════════════════════════════════════════════════════
# ROUTING REGIME ENUM
# ══════════════════════════════════════════════════════════════

class RoutingRegime(str, Enum):
    """Market regime for capital routing."""
    TREND = "TREND"
    RANGE = "RANGE"
    SQUEEZE = "SQUEEZE"
    VOL = "VOL"
    MIXED = "MIXED"


# ══════════════════════════════════════════════════════════════
# ALLOCATION CONFIDENCE THRESHOLDS
# ══════════════════════════════════════════════════════════════

ALLOCATION_CONFIDENCE_THRESHOLDS = {
    "high": 0.75,       # Clear routing, good allocation
    "normal": 0.55,     # Standard allocation
    "low": 0.35,        # Concentrated/unclear
}


# ══════════════════════════════════════════════════════════════
# ALLOCATION MODIFIERS
# ══════════════════════════════════════════════════════════════

ALLOCATION_MODIFIERS = {
    "high": {
        "confidence_modifier": 1.05,
        "capital_modifier": 1.10,
    },
    "normal": {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    "low": {
        "confidence_modifier": 0.92,
        "capital_modifier": 0.88,
    },
}


# ══════════════════════════════════════════════════════════════
# ALLOCATION WEIGHTS
# ══════════════════════════════════════════════════════════════

ALLOCATION_CONFIDENCE_WEIGHTS = {
    "strategy_regime_confidence": 0.35,
    "factor_health": 0.25,
    "portfolio_health": 0.20,
    "market_regime_clarity": 0.20,
}


# ══════════════════════════════════════════════════════════════
# ALLOCATION SLICE
# ══════════════════════════════════════════════════════════════

@dataclass
class AllocationSlice:
    """Single allocation slice."""
    name: str
    allocation: float       # 0..1
    weight: float           # Governance weight
    confidence: float       # Confidence in this allocation
    status: str             # ACTIVE / REDUCED / DISABLED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "allocation": round(self.allocation, 4),
            "weight": round(self.weight, 4),
            "confidence": round(self.confidence, 4),
            "status": self.status,
        }


# ══════════════════════════════════════════════════════════════
# CAPITAL ALLOCATION STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class CapitalAllocationState:
    """
    System-wide Capital Allocation State.
    
    Distributes capital across:
    - Strategies
    - Factors
    - Assets
    - Clusters
    """
    total_capital: float
    
    # Allocations by dimension
    strategy_allocations: Dict[str, float]
    factor_allocations: Dict[str, float]
    asset_allocations: Dict[str, float]
    cluster_allocations: Dict[str, float]
    
    # Routing
    dominant_route: DominantRoute
    routing_regime: RoutingRegime
    
    # Scores
    allocation_confidence: float
    concentration_score: float
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Explainability
    reason: str
    
    # Detailed slices (optional)
    strategy_slices: List[AllocationSlice] = field(default_factory=list)
    factor_slices: List[AllocationSlice] = field(default_factory=list)
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_capital": round(self.total_capital, 4),
            
            "strategy_allocations": {k: round(v, 4) for k, v in self.strategy_allocations.items()},
            "factor_allocations": {k: round(v, 4) for k, v in self.factor_allocations.items()},
            "asset_allocations": {k: round(v, 4) for k, v in self.asset_allocations.items()},
            "cluster_allocations": {k: round(v, 4) for k, v in self.cluster_allocations.items()},
            
            "dominant_route": self.dominant_route.value,
            "routing_regime": self.routing_regime.value,
            
            "allocation_confidence": round(self.allocation_confidence, 4),
            "concentration_score": round(self.concentration_score, 4),
            
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            
            "reason": self.reason,
            
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with slice details."""
        result = self.to_dict()
        result["strategy_slices"] = [s.to_dict() for s in self.strategy_slices]
        result["factor_slices"] = [s.to_dict() for s in self.factor_slices]
        return result
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "total_capital": round(self.total_capital, 4),
            "dominant_route": self.dominant_route.value,
            "routing_regime": self.routing_regime.value,
            "allocation_confidence": round(self.allocation_confidence, 4),
            "concentration_score": round(self.concentration_score, 4),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
        }


# ══════════════════════════════════════════════════════════════
# STRATEGY ALLOCATION INPUT
# ══════════════════════════════════════════════════════════════

@dataclass
class StrategyAllocationInput:
    """Input from Strategy Brain."""
    strategy_name: str
    base_allocation: float
    regime_confidence: float
    strategy_state: str      # ACTIVE / REDUCED / DISABLED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "base_allocation": round(self.base_allocation, 4),
            "regime_confidence": round(self.regime_confidence, 4),
            "strategy_state": self.strategy_state,
        }


# ══════════════════════════════════════════════════════════════
# FACTOR ALLOCATION INPUT
# ══════════════════════════════════════════════════════════════

@dataclass
class FactorAllocationInput:
    """Input from Factor Governance."""
    factor_name: str
    governance_weight: float
    governance_state: str    # ELITE / STABLE / WATCHLIST / DEGRADED / RETIRE
    lifecycle_state: str     # LIVE / SHADOW / CANDIDATE / REDUCED / FROZEN / RETIRED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_name": self.factor_name,
            "governance_weight": round(self.governance_weight, 4),
            "governance_state": self.governance_state,
            "lifecycle_state": self.lifecycle_state,
        }
