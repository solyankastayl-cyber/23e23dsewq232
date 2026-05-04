"""
PHASE 23.2 — Stress Grid
========================
Multi-scenario stress testing grid.

Runs all scenarios and builds a resilience matrix to answer:
"If everything goes wrong — will we survive?"

Components:
- stress_grid_types: Type definitions
- stress_grid_runner: Executes all scenarios
- stress_grid_engine: Calculates fragility index
- stress_grid_aggregator: Combines results
"""

from .stress_grid_types import (
    ResilienceState,
    ResilienceAction,
    StressGridState,
    RESILIENCE_THRESHOLDS,
    RESILIENCE_MODIFIERS,
)

from .stress_grid_aggregator import StressGridAggregator

__all__ = [
    "ResilienceState",
    "ResilienceAction",
    "StressGridState",
    "RESILIENCE_THRESHOLDS",
    "RESILIENCE_MODIFIERS",
    "StressGridAggregator",
]
