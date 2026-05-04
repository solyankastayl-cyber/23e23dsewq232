"""
Alpha Decay Monitor

Automatically detects alpha factor degradation and recommends actions.

Components:
- decay_types: Contracts and constants
- decay_engine: Core decay detection logic
- decay_registry: History storage
- decay_routes: API endpoints
"""

from .decay_types import (
    AlphaDecayState,
    DecayHistoryRecord,
    DecaySummary,
    DecayState,
    RecommendedAction,
    DRIFT_STABLE_MAX,
    DRIFT_DECAYING_MAX,
    DECAY_RATE_STABLE_MAX,
    DECAY_RATE_DECAYING_MAX,
    MODIFIERS,
)
from .decay_engine import (
    AlphaDecayEngine,
    get_alpha_decay_engine,
)
from .decay_registry import (
    AlphaDecayRegistry,
    get_alpha_decay_registry,
)
from .decay_routes import router as decay_router

__all__ = [
    # Types
    "AlphaDecayState",
    "DecayHistoryRecord",
    "DecaySummary",
    "DecayState",
    "RecommendedAction",
    # Constants
    "DRIFT_STABLE_MAX",
    "DRIFT_DECAYING_MAX",
    "DECAY_RATE_STABLE_MAX",
    "DECAY_RATE_DECAYING_MAX",
    "MODIFIERS",
    # Engine
    "AlphaDecayEngine",
    "get_alpha_decay_engine",
    # Registry
    "AlphaDecayRegistry",
    "get_alpha_decay_registry",
    # Routes
    "decay_router",
]
