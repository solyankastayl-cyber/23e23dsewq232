"""
Reflexivity Engine Module

PHASE 35 — Market Reflexivity Engine

Models behavioral feedback loops in markets (Soros reflexivity theory):
- Market influences expectations
- Expectations influence actions  
- Actions change market

Key components:
- ReflexivityState: Current reflexivity snapshot
- ReflexivityEngine: Core calculation engine
- ReflexivityRegistry: MongoDB persistence
"""

from .reflexivity_types import (
    ReflexivityState,
    ReflexivitySource,
    ReflexivityHistory,
    ReflexivityModifier,
    ReflexivitySummary,
    REFLEXIVITY_WEIGHT,
)
from .reflexivity_engine import (
    ReflexivityEngine,
    get_reflexivity_engine,
)
from .reflexivity_registry import (
    ReflexivityRegistry,
    get_reflexivity_registry,
)
from .reflexivity_routes import router as reflexivity_router

__all__ = [
    # Types
    "ReflexivityState",
    "ReflexivitySource",
    "ReflexivityHistory",
    "ReflexivityModifier",
    "ReflexivitySummary",
    "REFLEXIVITY_WEIGHT",
    # Engine
    "ReflexivityEngine",
    "get_reflexivity_engine",
    # Registry
    "ReflexivityRegistry",
    "get_reflexivity_registry",
    # Routes
    "reflexivity_router",
]
