"""
PHASE 14.8 — Market Structure Module
=====================================
Dominance & Breadth analysis for market structure.
"""

from .dominance_types import (
    MarketDominanceState,
    MarketBreadthState,
    MarketStructureState,
    DominanceRegime,
    RotationState,
    BreadthState,
)
from .dominance_engine import DominanceEngine, get_dominance_engine
from .breadth_engine import BreadthEngine, get_breadth_engine
from .market_structure_engine import MarketStructureEngine, get_market_structure_engine

__all__ = [
    # Types
    "MarketDominanceState",
    "MarketBreadthState",
    "MarketStructureState",
    "DominanceRegime",
    "RotationState",
    "BreadthState",
    # Engines
    "DominanceEngine",
    "get_dominance_engine",
    "BreadthEngine",
    "get_breadth_engine",
    "MarketStructureEngine",
    "get_market_structure_engine",
]
