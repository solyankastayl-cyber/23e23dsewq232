"""
Fractal Similarity Module

PHASE 32.2 — Fractal Similarity Engine

Finds historical market structures similar to the current one
and uses that information to influence trading decisions.
"""

from .similarity_engine import (
    FractalSimilarityEngine,
    get_similarity_engine,
)

from .similarity_types import (
    StructureVector,
    SimilarityMatch,
    SimilarityAnalysis,
    SimilarityModifier,
    WINDOW_SIZES,
    SIMILARITY_THRESHOLD,
)

from .similarity_routes import router as similarity_router

__all__ = [
    "FractalSimilarityEngine",
    "get_similarity_engine",
    "StructureVector",
    "SimilarityMatch",
    "SimilarityAnalysis",
    "SimilarityModifier",
    "WINDOW_SIZES",
    "SIMILARITY_THRESHOLD",
    "similarity_router",
]
