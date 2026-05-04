"""
Alpha Decay Module

PHASE 43.8 — Alpha Decay Engine
"""

from .decay_types import (
    DecayStage,
    SignalType,
    AlphaDecayState,
    AlphaDecayConfig,
    DecayComputeResult,
    DecaySummary,
    SIGNAL_HALF_LIVES,
    DECAY_STAGE_THRESHOLDS,
)
from .decay_engine import AlphaDecayEngine, get_alpha_decay_engine
from .decay_registry import AlphaDecayRegistry, get_alpha_decay_registry
from .decay_routes import router as alpha_decay_router

__all__ = [
    "DecayStage",
    "SignalType",
    "AlphaDecayState",
    "AlphaDecayConfig",
    "DecayComputeResult",
    "DecaySummary",
    "SIGNAL_HALF_LIVES",
    "DECAY_STAGE_THRESHOLDS",
    "AlphaDecayEngine",
    "get_alpha_decay_engine",
    "AlphaDecayRegistry",
    "get_alpha_decay_registry",
    "alpha_decay_router",
]
