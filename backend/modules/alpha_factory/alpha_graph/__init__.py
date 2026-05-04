"""
PHASE 13.5 - Alpha Graph
=========================
Reasoning engine for factor relationships.

Relation Types:
- supports: A supports B
- amplifies: A amplifies B  
- contradicts: A contradicts B
- conditional_on: A works only if B
- invalidates: A invalidates B

Enables:
- Signal coherence scoring
- Conflict detection
- Amplification chains
- Contextual reasoning
"""

from .alpha_graph_types import (
    GraphNode, GraphEdge, RelationType, 
    GraphSnapshot, CoherenceResult
)
from .alpha_graph_builder import GraphBuilder
from .alpha_graph_reasoner import GraphReasoner
from .alpha_graph import AlphaGraph, get_alpha_graph

__all__ = [
    "GraphNode",
    "GraphEdge", 
    "RelationType",
    "GraphSnapshot",
    "CoherenceResult",
    "GraphBuilder",
    "GraphReasoner",
    "AlphaGraph",
    "get_alpha_graph"
]
