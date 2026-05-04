"""
PHASE 21.1 — Factor Capital Engine
==================================
Sub-engine for factor-level capital allocation.

Uses factor governance weights and lifecycle state
to distribute capital across factors.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from modules.capital_allocation_v2.capital_allocation_types import (
    AllocationSlice,
    FactorAllocationInput,
)


class FactorCapitalEngine:
    """
    Factor Capital Allocation Sub-Engine.
    
    Distributes capital across factors based on:
    - Factor governance weights
    - Governance state (ELITE/STABLE/WATCHLIST/DEGRADED/RETIRE)
    - Lifecycle state (LIVE/SHADOW/CANDIDATE/REDUCED/FROZEN/RETIRED)
    - Research loop recommendations
    """
    
    def __init__(self):
        """Initialize engine."""
        self._base_weights: Dict[str, float] = {}
        self._initialize_baseline()
    
    def _initialize_baseline(self):
        """Initialize baseline factor weights."""
        self._base_weights = {
            "funding_factor": 0.18,
            "trend_breakout_factor": 0.15,
            "mean_reversion_factor": 0.14,
            "structure_factor": 0.12,
            "flow_factor": 0.12,
            "volatility_factor": 0.10,
            "momentum_factor": 0.10,
            "liquidation_factor": 0.05,
            "correlation_factor": 0.04,
        }
    
    def compute_allocations(
        self,
        governance_states: Optional[Dict[str, str]] = None,
        lifecycle_states: Optional[Dict[str, str]] = None,
        recommended_increases: Optional[List[str]] = None,
        recommended_decreases: Optional[List[str]] = None,
        research_modifier: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Compute factor allocations.
        
        Returns:
            {
                "allocations": {factor: allocation},
                "slices": [AllocationSlice],
                "total": float,
                "concentration": float,
            }
        """
        if governance_states is None:
            governance_states = {f: "STABLE" for f in self._base_weights}
        if lifecycle_states is None:
            lifecycle_states = {f: "LIVE" for f in self._base_weights}
        if recommended_increases is None:
            recommended_increases = []
        if recommended_decreases is None:
            recommended_decreases = []
        
        allocations = {}
        slices = []
        
        # Governance state multipliers
        governance_multipliers = {
            "ELITE": 1.15,
            "STABLE": 1.0,
            "WATCHLIST": 0.85,
            "DEGRADED": 0.60,
            "RETIRE": 0.0,
        }
        
        # Lifecycle state multipliers
        lifecycle_multipliers = {
            "LIVE": 1.0,
            "CANDIDATE": 0.7,
            "SHADOW": 0.3,
            "REDUCED": 0.5,
            "FROZEN": 0.0,
            "RETIRED": 0.0,
        }
        
        for factor, base_weight in self._base_weights.items():
            gov_state = governance_states.get(factor, "STABLE")
            life_state = lifecycle_states.get(factor, "LIVE")
            
            gov_mult = governance_multipliers.get(gov_state, 1.0)
            life_mult = lifecycle_multipliers.get(life_state, 1.0)
            
            # Apply research recommendations
            if factor in recommended_increases:
                research_mult = 1.10
            elif factor in recommended_decreases:
                research_mult = 0.85
            else:
                research_mult = 1.0
            
            # Calculate adjusted allocation
            adjusted = base_weight * gov_mult * life_mult * research_mult * research_modifier
            
            # Determine status
            if life_state in ["FROZEN", "RETIRED"] or gov_state == "RETIRE":
                status = "DISABLED"
            elif life_state in ["REDUCED", "SHADOW"] or gov_state in ["WATCHLIST", "DEGRADED"]:
                status = "REDUCED"
            else:
                status = "ACTIVE"
            
            allocations[factor] = adjusted
            
            slices.append(AllocationSlice(
                name=factor,
                allocation=adjusted,
                weight=base_weight,
                confidence=gov_mult * life_mult,
                status=status,
            ))
        
        # Normalize
        total = sum(allocations.values())
        if total > 0:
            allocations = {k: v / total for k, v in allocations.items()}
            for slice in slices:
                slice.allocation = slice.allocation / total if total > 0 else 0
        
        # Calculate concentration
        concentration = max(allocations.values()) if allocations else 0.0
        
        return {
            "allocations": allocations,
            "slices": slices,
            "total": 1.0,
            "concentration": concentration,
        }
    
    def get_factor_health(self, allocations: Dict[str, float]) -> float:
        """Calculate overall factor health score."""
        if not allocations:
            return 0.5
        
        # Health = diversity of allocation (inverse of concentration)
        concentration = max(allocations.values())
        diversity = 1.0 - concentration
        
        # Bonus for having multiple active factors
        active_count = sum(1 for v in allocations.values() if v > 0.05)
        activity_bonus = min(0.2, active_count * 0.02)
        
        return min(1.0, diversity + activity_bonus)


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[FactorCapitalEngine] = None


def get_factor_capital_engine() -> FactorCapitalEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FactorCapitalEngine()
    return _engine
