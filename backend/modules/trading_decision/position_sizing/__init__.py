"""
PHASE 14.5 — Position Sizing Module
====================================
Granular position sizing based on multiple factors.
"""

from .position_sizing_types import (
    PositionSizingDecision,
    SizeBucket,
    DecisionInputSnapshot,
    TAInputSnapshot,
    ExchangeInputSnapshot,
    MarketStateInputSnapshot,
)
from .position_sizing_engine import PositionSizingEngine, get_position_sizing_engine
from .position_sizing_rules import (
    BASE_RISK_PCT,
    RISK_MULTIPLIER_RANGES,
    VOLATILITY_ADJUSTMENTS,
    SIZE_BUCKET_THRESHOLDS,
)

__all__ = [
    # Types
    "PositionSizingDecision",
    "SizeBucket",
    "DecisionInputSnapshot",
    "TAInputSnapshot",
    "ExchangeInputSnapshot",
    "MarketStateInputSnapshot",
    # Engine
    "PositionSizingEngine",
    "get_position_sizing_engine",
    # Rules
    "BASE_RISK_PCT",
    "RISK_MULTIPLIER_RANGES",
    "VOLATILITY_ADJUSTMENTS",
    "SIZE_BUCKET_THRESHOLDS",
]
