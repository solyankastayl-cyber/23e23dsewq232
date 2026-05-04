"""
PHASE 17.2 — Factor Crowding Engine
====================================
Evaluates factor crowding risk.

Crowding measures:
- Correlation with market
- Similar strategies count
- Fund flow correlation
- Direct crowding indicator

Low crowding = unique alpha source
High crowding = overcrowded, reversal risk
"""

from typing import Dict, Optional
from modules.research_control.factor_governance.factor_governance_types import (
    FactorDimension,
    FactorDimensionResult,
)


# ══════════════════════════════════════════════════════════════
# CROWDING THRESHOLDS
# ══════════════════════════════════════════════════════════════

CROWDING_THRESHOLDS = {
    "market_corr_low": 0.30,     # < 0.30 correlation is good
    "market_corr_high": 0.60,   # > 0.60 correlation is concerning
    "strategies_few": 10,       # < 10 similar strategies is good
    "strategies_many": 50,      # > 50 is crowded
    "crowding_safe": 0.30,      # < 0.30 crowding indicator is safe
    "crowding_dangerous": 0.70, # > 0.70 is dangerous
}


# ══════════════════════════════════════════════════════════════
# CROWDING ENGINE
# ══════════════════════════════════════════════════════════════

class FactorCrowdingEngine:
    """
    Factor Crowding Engine - PHASE 17.2
    
    Evaluates crowding risk of alpha factors.
    """
    
    def __init__(self):
        pass
    
    def evaluate_from_scores(
        self,
        factor_name: str,
        market_corr_score: float,    # Lower correlation = higher score
        uniqueness_score: float,     # Higher uniqueness = higher score
        flow_corr_score: float,      # Lower flow correlation = higher score
        crowding_score: float,       # Lower crowding = higher score
    ) -> FactorDimensionResult:
        """
        Evaluate with pre-computed crowding scores (0-1).
        Higher scores mean lower crowding (better).
        """
        # Aggregate crowding score
        final_score = (
            0.25 * market_corr_score +
            0.25 * uniqueness_score +
            0.20 * flow_corr_score +
            0.30 * crowding_score
        )
        final_score = min(1.0, max(0.0, final_score))
        
        # Determine status
        if final_score >= 0.70:
            status = "EXCELLENT"
            reason = "Low crowding risk, unique alpha"
        elif final_score >= 0.55:
            status = "GOOD"
            reason = "Acceptable crowding levels"
        elif final_score >= 0.40:
            status = "WARNING"
            reason = "Elevated crowding risk"
        else:
            status = "POOR"
            reason = "High crowding risk, potential reversal"
        
        return FactorDimensionResult(
            dimension=FactorDimension.CROWDING,
            score=final_score,
            status=status,
            reason=reason,
            inputs={
                "market_corr_score": round(market_corr_score, 4),
                "uniqueness_score": round(uniqueness_score, 4),
                "flow_corr_score": round(flow_corr_score, 4),
                "crowding_indicator_score": round(crowding_score, 4),
            },
        )
    
    def calculate_crowding_from_indicator(self, crowding_indicator: float) -> float:
        """
        Convert crowding indicator (0-1, higher = more crowded) to score.
        Lower crowding = higher score.
        """
        return max(0.0, min(1.0, 1.0 - crowding_indicator))


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FactorCrowdingEngine] = None


def get_crowding_engine() -> FactorCrowdingEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FactorCrowdingEngine()
    return _engine
