"""
TA Composition Engine
======================
Aggregates all TA stack components into a single coherent technical setup view.

Purpose:
- Transform structure markup into active technical analysis
- Select ONE primary active figure for current market
- Bind figure to price with breakout/invalidation
- Select relevant overlays that support the setup
- Build visual composition for chart rendering
"""

from .composition_engine import (
    TACompositionEngine,
    get_composition_engine,
    TAComposition,
    ActiveFigure,
    ActiveFib,
    RelevantOverlay,
    BreakoutLogic,
)

__all__ = [
    "TACompositionEngine",
    "get_composition_engine",
    "TAComposition",
    "ActiveFigure",
    "ActiveFib",
    "RelevantOverlay",
    "BreakoutLogic",
]
