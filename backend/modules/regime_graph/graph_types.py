"""
Regime Graph Types

PHASE 36 — Market Regime Graph Engine

Types for modeling market regime transitions as a directed graph.

Graph Structure:
- Nodes: Regime states (TRENDING, RANGING, VOLATILE, etc.)
- Edges: Transition probabilities between states

Path Confidence Formula:
  path_confidence = 0.50 * next_state_probability
                  + 0.25 * regime_transition_confidence
                  + 0.25 * regime_memory_score
"""

from typing import List, Literal, Optional, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Regime graph weight in Hypothesis Engine formula
REGIME_GRAPH_WEIGHT = 0.04

# Path confidence weights
WEIGHT_NEXT_STATE_PROB = 0.50
WEIGHT_TRANSITION_CONFIDENCE = 0.25
WEIGHT_MEMORY_SCORE = 0.25

# Minimum transitions for edge to be valid
MIN_TRANSITION_COUNT = 3

# Sequence depth for path memory
SEQUENCE_DEPTH = 3

# Regime states
REGIME_STATES = [
    "TRENDING",
    "TREND_UP",
    "TREND_DOWN",
    "RANGING",
    "VOLATILE",
    "COMPRESSION",
    "EXPANSION",
    "UNCERTAIN",
]


# ══════════════════════════════════════════════════════════════
# Regime Graph Node
# ══════════════════════════════════════════════════════════════

class RegimeGraphNode(BaseModel):
    """
    Node in regime graph representing a market state.
    """
    regime_state: str
    
    # Visit statistics
    visits: int = 0
    avg_duration_minutes: float = 0.0
    max_duration_minutes: float = 0.0
    min_duration_minutes: float = 0.0
    
    # Performance in this state
    avg_success_rate: float = 0.0
    
    # Last visit
    last_visited: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# Regime Graph Edge
# ══════════════════════════════════════════════════════════════

class RegimeGraphEdge(BaseModel):
    """
    Edge in regime graph representing transition between states.
    """
    from_state: str
    to_state: str
    
    # Transition probability P(to_state | from_state)
    transition_probability: float = Field(ge=0.0, le=1.0)
    
    # Timing
    avg_transition_time_minutes: float = 0.0
    
    # Statistics
    transition_count: int = 0
    
    # Confidence in this edge
    edge_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Last transition on this edge
    last_transition: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# Regime Sequence
# ══════════════════════════════════════════════════════════════

class RegimeSequence(BaseModel):
    """
    Sequence of regime transitions for path memory.
    
    E.g., TRENDING → RANGING → VOLATILE
    """
    sequence: List[str] = Field(default_factory=list)
    occurrence_count: int = 0
    avg_total_duration_minutes: float = 0.0
    
    # Probability of this sequence
    sequence_probability: float = Field(ge=0.0, le=1.0, default=0.0)


# ══════════════════════════════════════════════════════════════
# Regime Graph State
# ══════════════════════════════════════════════════════════════

class RegimeGraphState(BaseModel):
    """
    Complete graph state for a symbol.
    
    Main contract for PHASE 36.
    """
    symbol: str
    
    # Graph structure
    nodes: List[RegimeGraphNode] = Field(default_factory=list)
    edges: List[RegimeGraphEdge] = Field(default_factory=list)
    
    # Current position in graph
    current_state: str = "UNCERTAIN"
    previous_state: Optional[str] = None
    
    # Prediction
    likely_next_state: str = "UNCERTAIN"
    next_state_probability: float = Field(ge=0.0, le=1.0, default=0.0)
    alternative_states: List[Dict] = Field(default_factory=list)  # [{state, probability}]
    
    # Path confidence
    path_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Sequence memory
    recent_sequence: List[str] = Field(default_factory=list)
    likely_sequence: Optional[RegimeSequence] = None
    
    # Statistics
    total_transitions: int = 0
    unique_states_visited: int = 0
    
    # Timestamp
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Explanation
    reason: str = ""


# ══════════════════════════════════════════════════════════════
# Regime Graph Path
# ══════════════════════════════════════════════════════════════

class RegimeGraphPath(BaseModel):
    """
    Predicted path through regime graph.
    """
    symbol: str
    
    # Current position
    current_state: str
    
    # Predicted path (next N states)
    predicted_path: List[str] = Field(default_factory=list)
    path_probabilities: List[float] = Field(default_factory=list)
    
    # Combined probability
    combined_probability: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Confidence
    path_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Time estimates
    estimated_durations_minutes: List[float] = Field(default_factory=list)
    total_estimated_minutes: float = 0.0
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
# Regime Graph Modifier (for Hypothesis Engine)
# ══════════════════════════════════════════════════════════════

class RegimeGraphModifier(BaseModel):
    """
    Modifier for hypothesis scoring based on graph analysis.
    
    Updated Hypothesis Formula (PHASE 36):
      0.27 alpha
    + 0.19 regime
    + 0.14 microstructure
    + 0.08 macro
    + 0.05 fractal_market
    + 0.05 fractal_similarity
    + 0.05 cross_asset_similarity
    + 0.08 regime_memory
    + 0.05 reflexivity
    + 0.04 regime_graph  <-- NEW
    = 1.00
    """
    symbol: str
    
    # Graph contribution
    graph_score: float = Field(ge=0.0, le=1.0)
    graph_weight: float = REGIME_GRAPH_WEIGHT
    
    # Weighted contribution to hypothesis
    weighted_contribution: float = Field(ge=0.0, le=1.0)
    
    # Prediction
    current_state: str = "UNCERTAIN"
    likely_next_state: str = "UNCERTAIN"
    next_state_probability: float = 0.0
    
    # Path info
    path_confidence: float = 0.0
    
    # Alignment with hypothesis
    is_favorable_transition: bool = False
    
    # Modifier value
    modifier: float = 1.0  # >1 boosts, <1 reduces
    
    reason: str = ""


# ══════════════════════════════════════════════════════════════
# Regime Graph Summary
# ══════════════════════════════════════════════════════════════

class RegimeGraphSummary(BaseModel):
    """
    Summary statistics for regime graph.
    """
    symbol: str
    
    # Graph size
    node_count: int = 0
    edge_count: int = 0
    
    # Most visited states
    most_visited_state: str = ""
    most_visited_count: int = 0
    
    # Most common transitions
    most_common_transition: str = ""  # "FROM → TO"
    most_common_transition_count: int = 0
    
    # Transition matrix density
    matrix_density: float = 0.0  # edges / (nodes * nodes)
    
    # Current state
    current_state: str = "UNCERTAIN"
    likely_next_state: str = "UNCERTAIN"
    
    # History
    total_transitions: int = 0
    avg_state_duration_minutes: float = 0.0
    
    last_updated: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# Transition Matrix Entry
# ══════════════════════════════════════════════════════════════

class TransitionMatrixEntry(BaseModel):
    """
    Single entry in transition probability matrix.
    """
    from_state: str
    to_state: str
    probability: float = Field(ge=0.0, le=1.0)
    count: int = 0
