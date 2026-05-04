"""
Strategy Statistics Module (STG3)
=================================

Statistics layer for measuring strategy performance.

Provides:
- Trade statistics (win rate, expectancy, PF)
- Decision statistics (action distribution)
- Profile statistics (per profile)
- Symbol statistics (per symbol)
- Regime statistics (per market regime)
"""

from .statistics_types import (
    StrategyStatisticsSnapshot,
    StrategyDecisionStatistics,
    StrategyProfileStatistics,
    StrategySymbolStatistics,
    StrategyRegimeStatistics,
    TradeRecord,
    DecisionRecord
)

from .statistics_service import statistics_service

from .statistics_routes import router

__all__ = [
    'StrategyStatisticsSnapshot',
    'StrategyDecisionStatistics',
    'StrategyProfileStatistics',
    'StrategySymbolStatistics',
    'StrategyRegimeStatistics',
    'TradeRecord',
    'DecisionRecord',
    'statistics_service',
    'router'
]
