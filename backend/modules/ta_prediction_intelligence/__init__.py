"""
TA Prediction Intelligence (Phase 6 / next)
===========================================
Independent analytical layer that reads existing TA outputs and produces
a rich, typed, explainable prediction context for MetaBrain.

Mirrors the architecture of `modules/exchange_intelligence`:
  engines (5)  →  conflict resolver  →  aggregated context (+ scenarios)

IMPORTANT — this module:
  * is NOT trading
  * is NOT a replacement for `modules/ta_engine` or `modules/prediction_core`
  * does NOT mutate any existing analysis / decision pipelines
  * is NOT auto-wired into MetaBrain — orchestration is the caller's choice

It is a pure, self-contained intelligence module. The router it ships is NOT
registered in `server.py` until the architect explicitly opts in.
"""

from .types import (
    PredictionBias,
    PredictionHorizon,
    TAEngineName,
    EngineContribution,
    PredictionScenario,
    TAPredictionContext,
)
from .ta_prediction_service import TAPredictionService

__all__ = [
    "PredictionBias",
    "PredictionHorizon",
    "TAEngineName",
    "EngineContribution",
    "PredictionScenario",
    "TAPredictionContext",
    "TAPredictionService",
]
