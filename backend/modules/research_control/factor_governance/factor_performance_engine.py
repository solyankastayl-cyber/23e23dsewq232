"""
PHASE 17.2 — Factor Performance Engine
=======================================
Evaluates factor performance stability.

Performance measures:
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Win Rate
- Profit Factor

High stability = consistent returns
Low stability = erratic/unreliable performance
"""

from typing import Dict, Optional
from modules.research_control.factor_governance.factor_governance_types import (
    FactorDimension,
    FactorDimensionResult,
)


# ══════════════════════════════════════════════════════════════
# PERFORMANCE THRESHOLDS
# ══════════════════════════════════════════════════════════════

PERFORMANCE_THRESHOLDS = {
    "sharpe_excellent": 2.0,
    "sharpe_good": 1.0,
    "sharpe_acceptable": 0.5,
    "sortino_excellent": 2.5,
    "sortino_good": 1.5,
    "calmar_excellent": 2.0,
    "calmar_good": 1.0,
    "win_rate_excellent": 0.60,
    "win_rate_good": 0.50,
    "profit_factor_excellent": 2.0,
    "profit_factor_good": 1.5,
}


# ══════════════════════════════════════════════════════════════
# PERFORMANCE ENGINE
# ══════════════════════════════════════════════════════════════

class FactorPerformanceEngine:
    """
    Factor Performance Engine - PHASE 17.2
    
    Evaluates performance stability of alpha factors.
    """
    
    def __init__(self):
        pass
    
    def evaluate_from_scores(
        self,
        factor_name: str,
        sharpe_score: float,
        sortino_score: float,
        calmar_score: float,
        win_rate_score: float,
        profit_factor_score: float,
    ) -> FactorDimensionResult:
        """
        Evaluate with pre-computed normalized scores (0-1).
        """
        # Aggregate performance score
        performance_score = (
            0.30 * sharpe_score +
            0.25 * sortino_score +
            0.15 * calmar_score +
            0.15 * win_rate_score +
            0.15 * profit_factor_score
        )
        performance_score = min(1.0, max(0.0, performance_score))
        
        # Determine status
        if performance_score >= 0.80:
            status = "EXCELLENT"
            reason = "Exceptional performance metrics"
        elif performance_score >= 0.65:
            status = "GOOD"
            reason = "Solid performance metrics"
        elif performance_score >= 0.50:
            status = "WARNING"
            reason = "Performance needs monitoring"
        else:
            status = "POOR"
            reason = "Performance is degrading"
        
        return FactorDimensionResult(
            dimension=FactorDimension.PERFORMANCE,
            score=performance_score,
            status=status,
            reason=reason,
            inputs={
                "sharpe_score": round(sharpe_score, 4),
                "sortino_score": round(sortino_score, 4),
                "calmar_score": round(calmar_score, 4),
                "win_rate_score": round(win_rate_score, 4),
                "profit_factor_score": round(profit_factor_score, 4),
            },
        )
    
    def normalize_sharpe(self, sharpe: float) -> float:
        """Normalize Sharpe ratio to 0-1 score."""
        if sharpe <= 0:
            return max(0.0, 0.2 + sharpe * 0.1)
        elif sharpe <= 1.0:
            return 0.2 + sharpe * 0.4  # 0->0.2, 1->0.6
        elif sharpe <= 2.0:
            return 0.6 + (sharpe - 1.0) * 0.3  # 1->0.6, 2->0.9
        else:
            return min(1.0, 0.9 + (sharpe - 2.0) * 0.05)
    
    def normalize_sortino(self, sortino: float) -> float:
        """Normalize Sortino ratio to 0-1 score."""
        if sortino <= 0:
            return max(0.0, 0.15 + sortino * 0.075)
        elif sortino <= 1.5:
            return 0.15 + (sortino / 1.5) * 0.45  # 0->0.15, 1.5->0.6
        elif sortino <= 2.5:
            return 0.6 + ((sortino - 1.5) / 1.0) * 0.3  # 1.5->0.6, 2.5->0.9
        else:
            return min(1.0, 0.9 + (sortino - 2.5) * 0.04)


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FactorPerformanceEngine] = None


def get_performance_engine() -> FactorPerformanceEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FactorPerformanceEngine()
    return _engine
