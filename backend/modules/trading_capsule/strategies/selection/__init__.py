"""
Strategy Selection Module (STG5)
================================

Strategy Comparison and Selection.

Answers: "Which strategy is best right now?"

Uses:
- STG3 Statistics
- STG4 Diagnostics
- Regime compatibility
- Profile compatibility
"""

from .selection_types import (
    StrategySelectionScore,
    StrategyRankingEntry,
    StrategySelectionResult,
    StrategyComparisonEntry,
    SelectionConfig
)

from .selection_service import selection_service

from .selection_routes import router

__all__ = [
    'StrategySelectionScore',
    'StrategyRankingEntry',
    'StrategySelectionResult',
    'StrategyComparisonEntry',
    'SelectionConfig',
    'selection_service',
    'router'
]
