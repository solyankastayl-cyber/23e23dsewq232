"""
Prediction Engine V2/V3 with Validation Layer

TA-first prediction system.
NO external dependencies on Exchange/Sentiment/Fractal as core.
Those are OPTIONAL modifiers only.

Architecture:
    TA Engine → Prediction Engine → Sanity Check → Save → Evaluation → Calibration

Core principle:
    Prediction = f(TA Engine output)
    
V2: Basic scenarios (bull/base/bear) with paths and bands
V3: Drift adaptation, self-correction, version tracking

Validation Layer:
- prediction_repository: Save/load predictions from MongoDB
- prediction_evaluator: Evaluate predictions against outcomes
- prediction_metrics: Compute accuracy, bias, calibration metrics
- prediction_sanity: Validate predictions before saving
- calibration_engine: Self-adjusting weights
- prediction_worker: Background evaluation worker
"""

from .prediction_engine import PredictionEngine, build_prediction, get_prediction_engine
from .prediction_engine_v3 import PredictionEngineV3, get_prediction_engine_v3
from .types import (
    PredictionInput,
    PredictionOutput,
    Scenario,
    PathPoint,
    Direction,
    Confidence,
    PatternInput,
    StructureInput,
    IndicatorsInput,
)
from .ta_interpreter import (
    interpret_ta_output,
    build_input_from_raw,
)
from .prediction_repository import get_prediction_repository
from .prediction_evaluator import get_prediction_evaluator
from .prediction_metrics import compute_prediction_metrics
from .prediction_sanity import sanity_check_prediction
from .calibration_engine import get_calibration_engine, get_calibrated_weights

__all__ = [
    # V2
    "PredictionEngine",
    "build_prediction",
    "get_prediction_engine",
    # V3
    "PredictionEngineV3",
    "get_prediction_engine_v3",
    # Types
    "PredictionInput",
    "PredictionOutput",
    "Scenario",
    "PathPoint",
    "Direction",
    "Confidence",
    "PatternInput",
    "StructureInput",
    "IndicatorsInput",
    # Interpreter
    "interpret_ta_output",
    "build_input_from_raw",
    # Validation
    "get_prediction_repository",
    "get_prediction_evaluator",
    "compute_prediction_metrics",
    "sanity_check_prediction",
    "get_calibration_engine",
    "get_calibrated_weights",
]
