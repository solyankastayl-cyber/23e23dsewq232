"""
PHASE 19.4 — Strategy Brain Aggregator Module
=============================================
"""

from modules.strategy_brain.aggregator.strategy_brain_types import (
    StrategyBrainState,
    StrategyOverlayEffect,
    RecommendedBias,
    STRATEGY_BIAS_MAP,
    CONFIDENCE_MODIFIER_MIN,
    CONFIDENCE_MODIFIER_MAX,
    CAPITAL_MODIFIER_MIN,
    CAPITAL_MODIFIER_MAX,
)
from modules.strategy_brain.aggregator.strategy_brain_aggregator import (
    StrategyBrainAggregator,
    get_strategy_brain_aggregator,
)

__all__ = [
    "StrategyBrainState",
    "StrategyOverlayEffect",
    "RecommendedBias",
    "STRATEGY_BIAS_MAP",
    "CONFIDENCE_MODIFIER_MIN",
    "CONFIDENCE_MODIFIER_MAX",
    "CAPITAL_MODIFIER_MIN",
    "CAPITAL_MODIFIER_MAX",
    "StrategyBrainAggregator",
    "get_strategy_brain_aggregator",
]
