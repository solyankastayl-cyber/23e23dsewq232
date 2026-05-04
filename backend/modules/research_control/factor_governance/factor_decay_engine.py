"""
PHASE 17.2 — Factor Decay Engine
=================================
Evaluates factor decay velocity.

Decay measures:
- Factor half-life
- Performance trend
- Information ratio decay

Slow decay = durable alpha
Fast decay = alpha is eroding quickly
"""

from typing import Dict, Optional
from modules.research_control.factor_governance.factor_governance_types import (
    FactorDimension,
    FactorDimensionResult,
)


# ══════════════════════════════════════════════════════════════
# DECAY THRESHOLDS
# ══════════════════════════════════════════════════════════════

DECAY_THRESHOLDS = {
    "half_life_long": 365,      # > 1 year half-life is excellent
    "half_life_medium": 180,    # > 6 months is good
    "half_life_short": 90,      # > 3 months is acceptable
    "half_life_critical": 30,   # < 1 month is critical
    "trend_positive": 0.0,      # Positive trend is good
    "trend_acceptable": -0.05,  # -5% is acceptable
    "trend_concerning": -0.15,  # -15% is concerning
}


# ══════════════════════════════════════════════════════════════
# DECAY ENGINE
# ══════════════════════════════════════════════════════════════

class FactorDecayEngine:
    """
    Factor Decay Engine - PHASE 17.2
    
    Evaluates decay velocity of alpha factors.
    """
    
    def __init__(self):
        pass
    
    def evaluate_from_scores(
        self,
        factor_name: str,
        half_life_score: float,       # Longer half-life = higher score
        trend_score: float,           # Positive/stable trend = higher score
        ir_stability_score: float,    # Stable IR = higher score
    ) -> FactorDimensionResult:
        """
        Evaluate with pre-computed decay scores (0-1).
        Higher scores mean slower decay (better).
        """
        # Aggregate decay score
        decay_score = (
            0.40 * half_life_score +
            0.35 * trend_score +
            0.25 * ir_stability_score
        )
        decay_score = min(1.0, max(0.0, decay_score))
        
        # Determine status
        if decay_score >= 0.75:
            status = "EXCELLENT"
            reason = "Durable alpha with slow decay"
        elif decay_score >= 0.60:
            status = "GOOD"
            reason = "Acceptable decay rate"
        elif decay_score >= 0.45:
            status = "WARNING"
            reason = "Alpha is decaying, monitor closely"
        else:
            status = "POOR"
            reason = "Rapid alpha decay, consider retirement"
        
        return FactorDimensionResult(
            dimension=FactorDimension.DECAY,
            score=decay_score,
            status=status,
            reason=reason,
            inputs={
                "half_life_score": round(half_life_score, 4),
                "trend_score": round(trend_score, 4),
                "ir_stability_score": round(ir_stability_score, 4),
            },
        )
    
    def calculate_half_life_score(self, half_life_days: float) -> float:
        """
        Convert half-life in days to score.
        Longer half-life = higher score.
        """
        if half_life_days >= 365:
            return min(1.0, 0.9 + (half_life_days - 365) / 3650)
        elif half_life_days >= 180:
            return 0.7 + ((half_life_days - 180) / 185) * 0.2
        elif half_life_days >= 90:
            return 0.5 + ((half_life_days - 90) / 90) * 0.2
        elif half_life_days >= 30:
            return 0.2 + ((half_life_days - 30) / 60) * 0.3
        else:
            return max(0.0, half_life_days / 30 * 0.2)
    
    def calculate_trend_score(self, performance_trend: float) -> float:
        """
        Convert performance trend to score.
        Positive/stable trend = higher score.
        """
        if performance_trend >= 0:
            return min(1.0, 0.8 + performance_trend)
        elif performance_trend >= -0.05:
            return 0.6 + ((performance_trend + 0.05) / 0.05) * 0.2
        elif performance_trend >= -0.15:
            return 0.3 + ((performance_trend + 0.15) / 0.10) * 0.3
        else:
            return max(0.0, 0.3 + (performance_trend + 0.15) / 0.15 * 0.3)


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FactorDecayEngine] = None


def get_decay_engine() -> FactorDecayEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FactorDecayEngine()
    return _engine
