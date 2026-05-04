"""
PHASE 25.4 — Macro-Fractal Brain Module

Unified intelligence layer combining:
- MacroContext
- AssetFractalContext (BTC, SPX, DXY)
- CrossAssetAlignment

Into MacroFractalContext.
"""

from .macro_fractal_types import (
    MacroFractalContext,
    MacroFractalSummary,
    MacroFractalDrivers,
    MacroFractalHealthStatus,
    FinalBiasType,
    ContextStateType,
    DriverType,
    CONFIDENCE_WEIGHTS,
    RELIABILITY_WEIGHTS,
)
from .macro_fractal_engine import (
    MacroFractalEngine,
    get_macro_fractal_engine,
)
from .macro_fractal_routes import router as macro_fractal_router

__all__ = [
    # Types
    "MacroFractalContext",
    "MacroFractalSummary",
    "MacroFractalDrivers",
    "MacroFractalHealthStatus",
    "FinalBiasType",
    "ContextStateType",
    "DriverType",
    # Constants
    "CONFIDENCE_WEIGHTS",
    "RELIABILITY_WEIGHTS",
    # Engine
    "MacroFractalEngine",
    "get_macro_fractal_engine",
    # Routes
    "macro_fractal_router",
]
