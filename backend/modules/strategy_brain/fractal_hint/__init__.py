"""
PHASE 24.3 — Fractal Hint Module

Provides fractal-based hints to Strategy Brain with LIMITED influence (≤10%).
"""

from .fractal_hint_types import (
    FractalHintInput,
    FractalHintScore,
    FractalPhase,
    FRACTAL_PHASE_STRATEGY_MAP,
    REGIME_CONFIDENCE_WEIGHTS_WITH_FRACTAL,
)
from .fractal_hint_engine import (
    FractalHintEngine,
    get_fractal_hint_engine,
)

__all__ = [
    "FractalHintInput",
    "FractalHintScore",
    "FractalPhase",
    "FRACTAL_PHASE_STRATEGY_MAP",
    "REGIME_CONFIDENCE_WEIGHTS_WITH_FRACTAL",
    "FractalHintEngine",
    "get_fractal_hint_engine",
]
