"""
Regime Graph Engine Module

PHASE 36 — Market Regime Graph Engine

Models market as a graph of regime transitions:
- Nodes: market regime states
- Edges: transition probabilities

Key capabilities:
- Transition matrix: P(next_state | current_state)
- Sequence memory: P(state_C | state_A → state_B)
- Path prediction for simulation and hypothesis scoring
"""

from .graph_types import (
    RegimeGraphNode,
    RegimeGraphEdge,
    RegimeGraphState,
    RegimeGraphPath,
    RegimeGraphModifier,
    RegimeGraphSummary,
    REGIME_GRAPH_WEIGHT,
)
from .graph_engine import (
    RegimeGraphEngine,
    get_regime_graph_engine,
)
from .graph_registry import (
    RegimeGraphRegistry,
    get_regime_graph_registry,
)
from .graph_routes import router as regime_graph_router

__all__ = [
    # Types
    "RegimeGraphNode",
    "RegimeGraphEdge",
    "RegimeGraphState",
    "RegimeGraphPath",
    "RegimeGraphModifier",
    "RegimeGraphSummary",
    "REGIME_GRAPH_WEIGHT",
    # Engine
    "RegimeGraphEngine",
    "get_regime_graph_engine",
    # Registry
    "RegimeGraphRegistry",
    "get_regime_graph_registry",
    # Routes
    "regime_graph_router",
]
