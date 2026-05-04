"""
PHASE 14.6 — Execution Mode Module
===================================
Determines HOW to execute trades.
"""

from .execution_mode_types import (
    ExecutionModeDecision,
    ExecutionMode,
    EntryStyle,
    DecisionInputSnapshot,
    SizingInputSnapshot,
    ExchangeInputSnapshot,
    MarketStateInputSnapshot,
)
from .execution_mode_engine import ExecutionModeEngine, get_execution_mode_engine
from .execution_mode_rules import (
    BLOCKED_ACTIONS,
    AGGRESSIVE_RULES,
    NORMAL_RULES,
    SLIPPAGE_TOLERANCE,
)

__all__ = [
    # Types
    "ExecutionModeDecision",
    "ExecutionMode",
    "EntryStyle",
    "DecisionInputSnapshot",
    "SizingInputSnapshot",
    "ExchangeInputSnapshot",
    "MarketStateInputSnapshot",
    # Engine
    "ExecutionModeEngine",
    "get_execution_mode_engine",
    # Rules
    "BLOCKED_ACTIONS",
    "AGGRESSIVE_RULES",
    "NORMAL_RULES",
    "SLIPPAGE_TOLERANCE",
]
