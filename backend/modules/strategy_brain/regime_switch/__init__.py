"""
PHASE 19.3 — Strategy Regime Switch Module
==========================================
"""

from modules.strategy_brain.regime_switch.strategy_regime_types import (
    StrategyPriorityState,
    RegimeSwitchSummary,
    RegimeStrategyConfig,
    REGIME_CONFIDENCE_WEIGHTS,
    PRIORITY_MODIFIERS,
)
from modules.strategy_brain.regime_switch.strategy_regime_map import (
    REGIME_STRATEGY_MAP,
    get_regime_config,
    get_all_regimes,
    get_strategies_for_regime,
    get_regime_map_summary,
)
from modules.strategy_brain.regime_switch.strategy_priority_engine import (
    StrategyPriorityEngine,
    get_priority_engine,
)
from modules.strategy_brain.regime_switch.strategy_regime_switch_engine import (
    StrategyRegimeSwitchEngine,
    get_regime_switch_engine,
)

__all__ = [
    "StrategyPriorityState",
    "RegimeSwitchSummary",
    "RegimeStrategyConfig",
    "REGIME_CONFIDENCE_WEIGHTS",
    "PRIORITY_MODIFIERS",
    "REGIME_STRATEGY_MAP",
    "get_regime_config",
    "get_all_regimes",
    "get_strategies_for_regime",
    "get_regime_map_summary",
    "StrategyPriorityEngine",
    "get_priority_engine",
    "StrategyRegimeSwitchEngine",
    "get_regime_switch_engine",
]
