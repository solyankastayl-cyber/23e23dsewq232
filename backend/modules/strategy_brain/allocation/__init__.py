"""
PHASE 19.2 — Strategy Allocation Module
======================================
"""

from modules.strategy_brain.allocation.strategy_allocation_types import (
    StrategyAllocationState,
    StrategyAllocationSummary,
    BASE_WEIGHTS,
    STATE_MULTIPLIERS,
    CONFIDENCE_MODIFIER_MIN,
    CONFIDENCE_MODIFIER_MAX,
)
from modules.strategy_brain.allocation.strategy_weight_engine import (
    StrategyWeightEngine,
    get_weight_engine,
)
from modules.strategy_brain.allocation.strategy_capital_engine import (
    StrategyCapitalEngine,
    get_capital_engine,
)
from modules.strategy_brain.allocation.strategy_allocation_engine import (
    StrategyAllocationEngine,
    get_allocation_engine,
)

__all__ = [
    "StrategyAllocationState",
    "StrategyAllocationSummary",
    "BASE_WEIGHTS",
    "STATE_MULTIPLIERS",
    "CONFIDENCE_MODIFIER_MIN",
    "CONFIDENCE_MODIFIER_MAX",
    "StrategyWeightEngine",
    "get_weight_engine",
    "StrategyCapitalEngine",
    "get_capital_engine",
    "StrategyAllocationEngine",
    "get_allocation_engine",
]
