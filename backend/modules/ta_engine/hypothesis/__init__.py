"""
TA Hypothesis - Package Init
"""

from modules.ta_engine.hypothesis.ta_hypothesis_types import (
    TAHypothesis,
    TADirection,
    MarketRegime,
    SetupType,
    TrendSignal,
    MomentumSignal,
    StructureSignal,
    BreakoutSignal,
)
from modules.ta_engine.hypothesis.ta_hypothesis_builder import (
    TAHypothesisBuilder,
    get_hypothesis_builder,
)
from modules.ta_engine.hypothesis.ta_hypothesis_rules import (
    CONVICTION_WEIGHTS,
    DRIVER_WEIGHTS,
)

__all__ = [
    "TAHypothesis",
    "TADirection",
    "MarketRegime",
    "SetupType",
    "TrendSignal",
    "MomentumSignal",
    "StructureSignal",
    "BreakoutSignal",
    "TAHypothesisBuilder",
    "get_hypothesis_builder",
    "CONVICTION_WEIGHTS",
    "DRIVER_WEIGHTS",
]
