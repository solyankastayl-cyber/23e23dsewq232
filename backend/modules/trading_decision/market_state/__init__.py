"""
PHASE 14.3 — Market State Matrix Module
========================================
Multi-dimensional market state for Trading Decision Layer.
"""

from .market_state_types import (
    MarketStateMatrix,
    TrendState,
    VolatilityState,
    ExchangeState,
    DerivativesState,
    BreadthState,
    RiskState,
    CombinedState,
    TAInputSnapshot,
    ExchangeInputSnapshot,
    VolatilityInputSnapshot,
)
from .market_state_builder import MarketStateBuilder, get_market_state_builder
from .market_state_rules import (
    TREND_RULES,
    VOLATILITY_RULES,
    EXCHANGE_RULES,
    DERIVATIVES_RULES,
    RISK_RULES,
    CONFIDENCE_WEIGHTS,
    COMBINED_STATE_RULES,
)

__all__ = [
    # Types
    "MarketStateMatrix",
    "TrendState",
    "VolatilityState",
    "ExchangeState",
    "DerivativesState",
    "BreadthState",
    "RiskState",
    "CombinedState",
    "TAInputSnapshot",
    "ExchangeInputSnapshot",
    "VolatilityInputSnapshot",
    # Builder
    "MarketStateBuilder",
    "get_market_state_builder",
    # Rules
    "TREND_RULES",
    "VOLATILITY_RULES",
    "EXCHANGE_RULES",
    "DERIVATIVES_RULES",
    "RISK_RULES",
    "CONFIDENCE_WEIGHTS",
    "COMBINED_STATE_RULES",
]
