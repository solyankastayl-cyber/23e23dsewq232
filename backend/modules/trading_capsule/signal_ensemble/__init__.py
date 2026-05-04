"""
PHASE 3.5.2 — Signal Ensemble Engine
=====================================

Объединение alpha-факторов в единый финальный торговый сигнал.

Компоненты:
- Ensemble Weights: веса для каждого alpha
- Signal Aggregator: агрегация сигналов
- Conflict Resolver: разрешение конфликтов
- Signal Scorer: расчёт финального score

Финальный результат:
- signal_direction (LONG/SHORT/NEUTRAL)
- signal_strength (0-1)
- signal_confidence (0-1)
- signal_quality (LOW/MEDIUM/HIGH/PREMIUM)
"""

from .ensemble_types import (
    SignalDirection,
    SignalQuality,
    EnsembleSignal,
    EnsembleResult,
    ConflictReport,
    EnsembleSnapshot
)
from .ensemble_weights import EnsembleWeights, get_default_weights
from .signal_aggregator import SignalAggregator
from .conflict_resolver import ConflictResolver
from .signal_scorer import SignalScorer
from .ensemble_repository import EnsembleRepository

__all__ = [
    # Types
    "SignalDirection",
    "SignalQuality",
    "EnsembleSignal",
    "EnsembleResult",
    "ConflictReport",
    "EnsembleSnapshot",
    # Components
    "EnsembleWeights",
    "get_default_weights",
    "SignalAggregator",
    "ConflictResolver",
    "SignalScorer",
    "EnsembleRepository"
]
