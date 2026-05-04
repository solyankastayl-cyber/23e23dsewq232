"""
TA Engine Module
=================
Phase 14.2 — TA Engine with Hypothesis Layer.
"""

from modules.ta_engine.hypothesis import (
    TAHypothesis,
    TADirection,
    MarketRegime,
    SetupType,
    TAHypothesisBuilder,
    get_hypothesis_builder,
)

__all__ = [
    "TAHypothesis",
    "TADirection",
    "MarketRegime",
    "SetupType",
    "TAHypothesisBuilder",
    "get_hypothesis_builder",
]
