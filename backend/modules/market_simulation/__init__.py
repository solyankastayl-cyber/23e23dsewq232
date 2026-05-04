"""
Market Simulation Module

PHASE 32.3 — Market Simulation Engine

Forward-looking scenario intelligence for market prediction.
"""

from .simulation_engine import (
    MarketSimulationEngine,
    get_simulation_engine,
)

from .simulation_types import (
    MarketScenario,
    SimulationInput,
    SimulationResult,
    ScenarioModifier,
    SimulationSummary,
    SCENARIO_TYPES,
    SIMULATION_HORIZONS,
)

from .simulation_routes import router as simulation_router

__all__ = [
    "MarketSimulationEngine",
    "get_simulation_engine",
    "MarketScenario",
    "SimulationInput",
    "SimulationResult",
    "ScenarioModifier",
    "SimulationSummary",
    "SCENARIO_TYPES",
    "SIMULATION_HORIZONS",
    "simulation_router",
]
