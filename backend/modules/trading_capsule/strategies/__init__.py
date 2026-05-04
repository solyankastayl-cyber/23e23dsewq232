"""
Strategy Taxonomy Module (STG1)
===============================

Formal classification and definition of trading strategies.

Defines:
- Strategy types (Trend, Momentum, Mean Reversion)
- Entry/Exit/Risk models
- Profile compatibility
- Market regime compatibility
"""

from .strategy_types import (
    StrategyType,
    MarketRegime,
    ProfileType,
    EntryModel,
    ExitModel,
    RiskModel,
    StrategyDefinition
)

from .strategy_registry import strategy_registry

from .strategy_routes import router

__all__ = [
    'StrategyType',
    'MarketRegime', 
    'ProfileType',
    'EntryModel',
    'ExitModel',
    'RiskModel',
    'StrategyDefinition',
    'strategy_registry',
    'router'
]
