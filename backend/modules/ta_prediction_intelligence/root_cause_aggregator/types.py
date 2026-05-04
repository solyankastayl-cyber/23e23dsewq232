"""
Locked typed primitives — axes enum, constants, contracts.

All constants here are LOCKED per spec. Do not introduce new axes
without bumping AGGREGATOR_VERSION and re-running QA.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Set

AGGREGATOR_VERSION = "v1"
AGGREGATOR_BUILDER_VERSION = "1.0.0"

# Cohort gating constants (locked)
MIN_COHORT: int = 20
MIN_ERROR_RATE: float = 0.50
MIN_CONCENTRATION: float = 0.30
MIN_STABILITY: float = 0.70

# Temporal split: only run baseline/recent split when cohort >= 2 * MIN_COHORT.
STABILITY_SPLIT_MIN: int = MIN_COHORT * 2

# Error definition: per spec, underconfident = system was right but underplayed
# itself; correct = no error. Both are EXCLUDED from the error denominator.
NON_ERROR_TYPES: Set[str] = {"correct", "underconfident"}


class Axis(str, Enum):
    SYMBOL_TF = "symbol_tf"
    INTERACTION_TYPE = "interaction_type"
    SIGNAL_STRENGTH = "signal_strength"
    DECISION_BIAS = "decision_bias"
    VOLATILITY_STATE = "volatility_state"
    TREND_STATE = "trend_state"


AXES: List[str] = [a.value for a in Axis]
