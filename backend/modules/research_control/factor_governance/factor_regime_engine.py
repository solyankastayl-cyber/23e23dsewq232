"""
PHASE 17.2 — Factor Regime Engine
==================================
Evaluates factor robustness across market regimes.

Regime measures:
- Bull market performance
- Bear market performance
- Sideways market performance
- High volatility performance
- Low volatility performance

High robustness = works in all conditions
Low robustness = regime-dependent factor
"""

from typing import Dict, Optional
from modules.research_control.factor_governance.factor_governance_types import (
    FactorDimension,
    FactorDimensionResult,
)


# ══════════════════════════════════════════════════════════════
# REGIME ENGINE
# ══════════════════════════════════════════════════════════════

class FactorRegimeEngine:
    """
    Factor Regime Engine - PHASE 17.2
    
    Evaluates regime robustness of alpha factors.
    """
    
    def __init__(self):
        pass
    
    def evaluate_from_scores(
        self,
        factor_name: str,
        bull_score: float,
        bear_score: float,
        sideways_score: float,
        high_vol_score: float,
        low_vol_score: float,
    ) -> FactorDimensionResult:
        """
        Evaluate with pre-computed regime performance scores (0-1).
        """
        # Calculate regime consistency (prefer factors that work everywhere)
        scores = [bull_score, bear_score, sideways_score, high_vol_score, low_vol_score]
        
        # Average performance across regimes
        avg_score = sum(scores) / len(scores)
        
        # Consistency penalty: penalize high variance (regime-dependent factors)
        mean = avg_score
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        consistency_penalty = min(0.2, variance)  # Cap penalty at 0.2
        
        # Final score: average minus consistency penalty
        regime_score = max(0.0, min(1.0, avg_score - consistency_penalty))
        
        # Find weakest regime
        min_score = min(scores)
        weakest_idx = scores.index(min_score)
        regimes = ["bull", "bear", "sideways", "high_vol", "low_vol"]
        weakest_regime = regimes[weakest_idx]
        
        # Determine status
        if regime_score >= 0.75:
            status = "EXCELLENT"
            reason = "Robust across all market regimes"
        elif regime_score >= 0.60:
            status = "GOOD"
            reason = f"Good regime robustness (weakest: {weakest_regime})"
        elif regime_score >= 0.45:
            status = "WARNING"
            reason = f"Regime-dependent, weak in {weakest_regime}"
        else:
            status = "POOR"
            reason = f"Highly regime-dependent, poor in {weakest_regime}"
        
        return FactorDimensionResult(
            dimension=FactorDimension.REGIME,
            score=regime_score,
            status=status,
            reason=reason,
            inputs={
                "bull_score": round(bull_score, 4),
                "bear_score": round(bear_score, 4),
                "sideways_score": round(sideways_score, 4),
                "high_vol_score": round(high_vol_score, 4),
                "low_vol_score": round(low_vol_score, 4),
                "avg_performance": round(avg_score, 4),
                "consistency_penalty": round(consistency_penalty, 4),
                "weakest_regime": weakest_regime,
            },
        )


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FactorRegimeEngine] = None


def get_regime_engine() -> FactorRegimeEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FactorRegimeEngine()
    return _engine
