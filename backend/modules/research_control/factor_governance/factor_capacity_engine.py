"""
PHASE 17.2 — Factor Capacity Engine
====================================
Evaluates factor capacity constraints.

Capacity measures:
- Current AUM utilization
- Slippage impact
- Market impact
- Scalability headroom

High capacity = can handle more capital
Low capacity = constrained by market liquidity
"""

from typing import Dict, Optional
from modules.research_control.factor_governance.factor_governance_types import (
    FactorDimension,
    FactorDimensionResult,
)


# ══════════════════════════════════════════════════════════════
# CAPACITY THRESHOLDS
# ══════════════════════════════════════════════════════════════

CAPACITY_THRESHOLDS = {
    "utilization_safe": 0.50,     # < 50% utilization is safe
    "utilization_warning": 0.75,  # > 75% utilization is warning
    "utilization_critical": 0.90, # > 90% utilization is critical
    "slippage_acceptable": 0.005, # < 0.5% slippage acceptable
    "slippage_high": 0.02,        # > 2% slippage is problematic
}


# ══════════════════════════════════════════════════════════════
# CAPACITY ENGINE
# ══════════════════════════════════════════════════════════════

class FactorCapacityEngine:
    """
    Factor Capacity Engine - PHASE 17.2
    
    Evaluates capital capacity of alpha factors.
    """
    
    def __init__(self):
        pass
    
    def evaluate_from_scores(
        self,
        factor_name: str,
        utilization_score: float,  # Lower utilization = higher score
        slippage_score: float,     # Lower slippage = higher score
        market_impact_score: float, # Lower impact = higher score
        scalability_score: float,  # Higher scalability = higher score
    ) -> FactorDimensionResult:
        """
        Evaluate with pre-computed capacity scores (0-1).
        Higher scores mean better capacity.
        """
        # Aggregate capacity score
        capacity_score = (
            0.30 * utilization_score +
            0.25 * slippage_score +
            0.25 * market_impact_score +
            0.20 * scalability_score
        )
        capacity_score = min(1.0, max(0.0, capacity_score))
        
        # Determine status
        if capacity_score >= 0.75:
            status = "EXCELLENT"
            reason = "Ample capacity headroom"
        elif capacity_score >= 0.60:
            status = "GOOD"
            reason = "Good capacity with some constraints"
        elif capacity_score >= 0.45:
            status = "WARNING"
            reason = "Capacity constraints emerging"
        else:
            status = "POOR"
            reason = "Significant capacity constraints"
        
        return FactorDimensionResult(
            dimension=FactorDimension.CAPACITY,
            score=capacity_score,
            status=status,
            reason=reason,
            inputs={
                "utilization_score": round(utilization_score, 4),
                "slippage_score": round(slippage_score, 4),
                "market_impact_score": round(market_impact_score, 4),
                "scalability_score": round(scalability_score, 4),
            },
        )
    
    def calculate_utilization_score(self, current_aum: float, max_capacity: float) -> float:
        """
        Calculate utilization score.
        Lower utilization = higher score.
        """
        if max_capacity <= 0:
            return 0.0
        
        utilization = current_aum / max_capacity
        
        if utilization <= 0.50:
            return 1.0 - (utilization * 0.2)  # 0->1.0, 0.5->0.9
        elif utilization <= 0.75:
            return 0.9 - ((utilization - 0.5) * 1.2)  # 0.5->0.9, 0.75->0.6
        elif utilization <= 0.90:
            return 0.6 - ((utilization - 0.75) * 2.0)  # 0.75->0.6, 0.9->0.3
        else:
            return max(0.0, 0.3 - ((utilization - 0.9) * 3.0))


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FactorCapacityEngine] = None


def get_capacity_engine() -> FactorCapacityEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FactorCapacityEngine()
    return _engine
