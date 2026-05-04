"""
Meta-Alpha Module

PHASE 31.1 — Meta-Alpha Pattern Engine

Discovers meta-patterns across regime, hypothesis, and microstructure
to identify when the system performs best.

This is the 4th level of intelligence (Meta Intelligence):
1. Market Intelligence
2. Strategy Intelligence  
3. Portfolio Intelligence
4. Meta Intelligence ← This module
"""

from .meta_alpha_engine import (
    MetaAlphaEngine,
    get_meta_alpha_engine,
)
from .meta_alpha_registry import (
    MetaAlphaRegistry,
    get_meta_alpha_registry,
)
from .meta_alpha_routes import router as meta_alpha_router
from .meta_alpha_types import (
    MetaAlphaPattern,
    MetaAlphaSummary,
    PatternObservation,
    StrongMetaPattern,
    MIN_META_OBSERVATIONS,
    META_ALPHA_MODIFIERS,
    STRONG_META_ALPHA_THRESHOLD,
    MODERATE_META_ALPHA_THRESHOLD,
)

__all__ = [
    # Engine
    "MetaAlphaEngine",
    "get_meta_alpha_engine",
    # Registry
    "MetaAlphaRegistry",
    "get_meta_alpha_registry",
    # Router
    "meta_alpha_router",
    # Types
    "MetaAlphaPattern",
    "MetaAlphaSummary",
    "PatternObservation",
    "StrongMetaPattern",
    # Constants
    "MIN_META_OBSERVATIONS",
    "META_ALPHA_MODIFIERS",
    "STRONG_META_ALPHA_THRESHOLD",
    "MODERATE_META_ALPHA_THRESHOLD",
]
