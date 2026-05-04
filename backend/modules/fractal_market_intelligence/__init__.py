"""
Fractal Market Intelligence Module

PHASE 32.1 — Fractal Market Intelligence Engine

Determines structural market state across multiple timeframes
to identify fractal alignment and provide context modifiers.

This is the 5th level of intelligence (Fractal Intelligence):
1. Market Intelligence
2. Strategy Intelligence
3. Portfolio Intelligence
4. Meta Intelligence
5. Fractal Intelligence ← This module
"""

from .fractal_engine import (
    FractalEngine,
    get_fractal_engine,
)
from .fractal_registry import (
    FractalRegistry,
    get_fractal_registry,
)
from .fractal_routes import router as fractal_router
from .fractal_types import (
    FractalMarketState,
    FractalSummary,
    TimeframeAnalysis,
    FractalModifier,
    TIMEFRAMES,
    ALIGNMENT_BIAS_THRESHOLD,
    ALIGNMENT_NEUTRAL_THRESHOLD,
    FRACTAL_ALIGNED_MODIFIER,
    FRACTAL_CONFLICT_MODIFIER,
)

__all__ = [
    # Engine
    "FractalEngine",
    "get_fractal_engine",
    # Registry
    "FractalRegistry",
    "get_fractal_registry",
    # Router
    "fractal_router",
    # Types
    "FractalMarketState",
    "FractalSummary",
    "TimeframeAnalysis",
    "FractalModifier",
    # Constants
    "TIMEFRAMES",
    "ALIGNMENT_BIAS_THRESHOLD",
    "ALIGNMENT_NEUTRAL_THRESHOLD",
    "FRACTAL_ALIGNED_MODIFIER",
    "FRACTAL_CONFLICT_MODIFIER",
]
