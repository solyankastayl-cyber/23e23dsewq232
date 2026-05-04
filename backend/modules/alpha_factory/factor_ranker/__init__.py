"""
PHASE 13.4 - Factor Ranker
===========================
Ranks and filters candidate factors.

1140 candidate factors → ~150 approved factors

Metrics:
- IC (Information Coefficient)
- Sharpe Ratio
- Stability
- Decay
- Regime Consistency

Verdicts:
- ELITE (top 2%)
- STRONG (top 10%)
- PROMISING (top 25%)
- WEAK (bottom 50%)
- REJECTED (fails thresholds)
"""

from .factor_metrics import FactorMetrics, MetricsResult
from .factor_evaluator import FactorEvaluator
from .factor_ranker import FactorRanker, get_factor_ranker

__all__ = [
    "FactorMetrics",
    "MetricsResult",
    "FactorEvaluator",
    "FactorRanker",
    "get_factor_ranker"
]
