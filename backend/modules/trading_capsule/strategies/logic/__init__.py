"""
Strategy Logic Engine (STG2)
============================

Decision engine for strategy execution.

Provides:
- Signal interpretation
- Regime filtering
- Entry/Exit evaluation
- Risk veto
- Decision building
"""

from .logic_types import (
    StrategyInputContext,
    StrategyDecision,
    DecisionReason,
    FilterResult
)

from .logic_engine import strategy_logic_engine

from .logic_routes import router

__all__ = [
    'StrategyInputContext',
    'StrategyDecision',
    'DecisionReason',
    'FilterResult',
    'strategy_logic_engine',
    'router'
]
