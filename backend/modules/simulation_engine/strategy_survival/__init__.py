"""
PHASE 23.3 — Strategy Survival Matrix
=====================================
Evaluates how each strategy behaves under different stress scenarios.

Answers key questions:
- Which strategies are robust?
- Which strategies are fragile?
- Which strategies survive only in certain regimes?

Components:
- strategy_survival_types: Type definitions
- strategy_scenario_runner: Runs scenarios per strategy
- strategy_survival_engine: Calculates robustness score
- strategy_survival_aggregator: Combines results into matrix
"""

from .strategy_survival_types import (
    StrategySurvivalState,
    StrategySurvivalMatrix,
    StrategySurvivalStateEnum,
    StrategyAction,
    ROBUSTNESS_THRESHOLDS,
    ROBUSTNESS_MODIFIERS,
)

from .strategy_survival_aggregator import StrategySurvivalAggregator

__all__ = [
    "StrategySurvivalState",
    "StrategySurvivalMatrix",
    "StrategySurvivalStateEnum",
    "StrategyAction",
    "ROBUSTNESS_THRESHOLDS",
    "ROBUSTNESS_MODIFIERS",
    "StrategySurvivalAggregator",
]
