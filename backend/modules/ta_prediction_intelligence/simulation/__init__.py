"""
TA Prediction Intelligence — Simulation Engine (Replay Engine).

Strictly isolated offline replay over historical candles. Never touches
live collections (ta_prediction_history / ta_prediction_debug). Every
record lives in `ta_prediction_history_sim` and `ta_prediction_debug_sim`.
ML readiness, dataset gates, data_health and root_cause_aggregator stay
live-only by reading the live collections only.

Public API:
  POST /api/ta-prediction-intelligence/simulation/replay
  GET  /api/ta-prediction-intelligence/simulation/stats
"""

from .types import (
    ReplayRequest,
    ReplayResponse,
    ReplayStepResult,
    SimStats,
    SIM_HISTORY_COLLECTION,
    SIM_DEBUG_COLLECTION,
    SIMULATION_VERSION,
    SIMULATION_BUILDER_VERSION,
    SimulationSource,
)

__all__ = [
    "ReplayRequest",
    "ReplayResponse",
    "ReplayStepResult",
    "SimStats",
    "SIM_HISTORY_COLLECTION",
    "SIM_DEBUG_COLLECTION",
    "SIMULATION_VERSION",
    "SIMULATION_BUILDER_VERSION",
    "SimulationSource",
]
