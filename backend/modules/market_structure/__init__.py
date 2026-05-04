"""
Market Structure Module
========================
Breadth & Dominance analysis.
"""

from .breadth_dominance import (
    MarketDominanceState,
    MarketBreadthState,
    MarketStructureState,
    DominanceRegime,
    RotationState,
    BreadthState,
    get_dominance_engine,
    get_breadth_engine,
    get_market_structure_engine,
)

__all__ = [
    "MarketDominanceState",
    "MarketBreadthState",
    "MarketStructureState",
    "DominanceRegime",
    "RotationState",
    "BreadthState",
    "get_dominance_engine",
    "get_breadth_engine",
    "get_market_structure_engine",
]
