"""
PHASE 23.1 — Simulation / Crisis Engine
========================================
Pre-crisis foresight layer that models how the system behaves in crisis
scenarios BEFORE they happen.

Components:
- scenario_registry: Predefined crisis scenarios
- shock_simulator: Applies shocks to system state
- portfolio_impact_engine: Estimates PnL/drawdown impact
- simulation_aggregator: Combines all components

Key difference from Risk Fabric:
- Risk Fabric answers: "What is current risk?"
- Simulation Engine answers: "What happens IF X occurs?"
"""

from .simulation_types import (
    ScenarioType,
    SeverityLevel,
    SurvivalState,
    SurvivalAction,
    SimulationScenario,
    SimulationResult,
    SURVIVAL_THRESHOLDS,
    SURVIVAL_MODIFIERS,
)

from .scenario_registry import (
    SCENARIO_REGISTRY,
    get_scenario,
    list_scenarios,
)

from .simulation_aggregator import SimulationAggregator

__all__ = [
    "ScenarioType",
    "SeverityLevel",
    "SurvivalState",
    "SurvivalAction",
    "SimulationScenario",
    "SimulationResult",
    "SCENARIO_REGISTRY",
    "get_scenario",
    "list_scenarios",
    "SimulationAggregator",
]
