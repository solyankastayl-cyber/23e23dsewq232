"""
PHASE 20.2 — Factor Weight Adjustment Module
============================================
"""

from modules.research_loop.factor_weight_adjustment.factor_weight_adjustment_types import (
    FactorWeightAdjustment,
    FactorWeightAdjustmentSummary,
    FactorWeightState,
    AdjustmentAction,
    AdjustmentStrength,
    WEIGHT_MIN,
    WEIGHT_MAX,
    SHADOW_WEIGHT,
    RETIRE_WEIGHT,
)
from modules.research_loop.factor_weight_adjustment.factor_weight_policy import (
    FactorWeightPolicy,
    get_factor_weight_policy,
)
from modules.research_loop.factor_weight_adjustment.factor_weight_registry import (
    FactorWeightRegistry,
    get_factor_weight_registry,
    DEFAULT_FACTOR_WEIGHTS,
)
from modules.research_loop.factor_weight_adjustment.factor_weight_adjustment_engine import (
    FactorWeightAdjustmentEngine,
    get_factor_weight_adjustment_engine,
)

__all__ = [
    "FactorWeightAdjustment",
    "FactorWeightAdjustmentSummary",
    "FactorWeightState",
    "AdjustmentAction",
    "AdjustmentStrength",
    "WEIGHT_MIN",
    "WEIGHT_MAX",
    "SHADOW_WEIGHT",
    "RETIRE_WEIGHT",
    "FactorWeightPolicy",
    "get_factor_weight_policy",
    "FactorWeightRegistry",
    "get_factor_weight_registry",
    "DEFAULT_FACTOR_WEIGHTS",
    "FactorWeightAdjustmentEngine",
    "get_factor_weight_adjustment_engine",
]
