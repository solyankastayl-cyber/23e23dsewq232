"""
PHASE 14.4 — Trading Decision Layer Module
===========================================
Final trading decision from TA + Exchange + Market State.
"""

from .decision_types import (
    TradingDecision,
    DecisionAction,
    ExecutionMode,
    TradeDirection,
    DecisionRule,
    TADecisionInput,
    ExchangeDecisionInput,
    MarketStateDecisionInput,
)
from .decision_engine import DecisionEngine, get_decision_engine
from .decision_rules import (
    SETUP_THRESHOLDS,
    AGREEMENT_THRESHOLDS,
    CONFLICT_THRESHOLDS,
    POSITION_MULTIPLIERS,
    CONFIDENCE_WEIGHTS,
)

__all__ = [
    # Types
    "TradingDecision",
    "DecisionAction",
    "ExecutionMode",
    "TradeDirection",
    "DecisionRule",
    "TADecisionInput",
    "ExchangeDecisionInput",
    "MarketStateDecisionInput",
    # Engine
    "DecisionEngine",
    "get_decision_engine",
    # Rules
    "SETUP_THRESHOLDS",
    "AGREEMENT_THRESHOLDS",
    "CONFLICT_THRESHOLDS",
    "POSITION_MULTIPLIERS",
    "CONFIDENCE_WEIGHTS",
]
