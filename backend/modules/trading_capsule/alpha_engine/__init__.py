"""
PHASE 3.5.1 — Alpha Engine
===========================

Alpha-факторы - атомарные сигналы для усиления торговых решений.

Модуль предоставляет:
- 10 alpha-факторов (trend, breakout, volatility, volume, reversal, liquidity)
- Alpha scoring engine для агрегации
- Alpha signal builder для финального alpha context
- Repository для хранения и истории

Alpha-факторы усиливают:
- Выбор стратегии
- Confidence
- Quality score
- Health score
- Risk multiplier
"""

from .alpha_types import (
    AlphaDirection,
    AlphaRegimeRelevance,
    AlphaResult,
    AlphaSummary,
    AlphaSnapshot,
    AlphaHistoryQuery
)
from .alpha_registry import AlphaRegistry, get_alpha_registry
from .alpha_scoring_engine import AlphaScoringEngine
from .alpha_signal_builder import AlphaSignalBuilder
from .alpha_repository import AlphaRepository

__all__ = [
    # Types
    "AlphaDirection",
    "AlphaRegimeRelevance", 
    "AlphaResult",
    "AlphaSummary",
    "AlphaSnapshot",
    "AlphaHistoryQuery",
    # Components
    "AlphaRegistry",
    "get_alpha_registry",
    "AlphaScoringEngine",
    "AlphaSignalBuilder",
    "AlphaRepository"
]
