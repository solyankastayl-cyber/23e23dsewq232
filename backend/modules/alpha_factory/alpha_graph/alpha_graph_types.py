"""
PHASE 13.5 - Alpha Graph Types
===============================
Core data types for Alpha Graph.
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime


class RelationType(str, Enum):
    """Types of relationships between factors."""
    SUPPORTS = "supports"           # A supports B
    AMPLIFIES = "amplifies"         # A amplifies B
    CONTRADICTS = "contradicts"     # A contradicts B
    CONDITIONAL_ON = "conditional_on"  # A works only if B
    INVALIDATES = "invalidates"     # A invalidates B


@dataclass
class GraphNode:
    """
    Node in the Alpha Graph.
    
    Represents an approved factor.
    """
    node_id: str
    factor_id: str
    
    # Factor info
    family: str = ""
    template: str = ""
    inputs: List[str] = field(default_factory=list)
    
    # Ranking info
    composite_score: float = 0.0
    verdict: str = ""
    ic: float = 0.0
    sharpe: float = 0.0
    
    # Graph properties
    weight: float = 1.0
    active: bool = True
    
    # Connections
    outgoing_edges: int = 0
    incoming_edges: int = 0
    
    # Metadata
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "factor_id": self.factor_id,
            "family": self.family,
            "template": self.template,
            "inputs": self.inputs,
            "composite_score": self.composite_score,
            "verdict": self.verdict,
            "ic": self.ic,
            "sharpe": self.sharpe,
            "weight": self.weight,
            "active": self.active,
            "outgoing_edges": self.outgoing_edges,
            "incoming_edges": self.incoming_edges,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "GraphNode":
        return cls(
            node_id=data["node_id"],
            factor_id=data["factor_id"],
            family=data.get("family", ""),
            template=data.get("template", ""),
            inputs=data.get("inputs", []),
            composite_score=data.get("composite_score", 0.0),
            verdict=data.get("verdict", ""),
            ic=data.get("ic", 0.0),
            sharpe=data.get("sharpe", 0.0),
            weight=data.get("weight", 1.0),
            active=data.get("active", True),
            outgoing_edges=data.get("outgoing_edges", 0),
            incoming_edges=data.get("incoming_edges", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )


@dataclass  
class GraphEdge:
    """
    Edge in the Alpha Graph.
    
    Represents a relationship between two factors.
    """
    edge_id: str
    source_node: str  # node_id
    target_node: str  # node_id
    
    # Relationship
    relation_type: RelationType
    
    # Properties
    strength: float = 0.5      # 0-1, how strong the relationship
    confidence: float = 0.5    # 0-1, confidence in this relationship
    
    # Context
    reason: str = ""           # Why this relationship exists
    auto_generated: bool = True
    
    # Metadata
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "edge_id": self.edge_id,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "relation_type": self.relation_type.value if isinstance(self.relation_type, RelationType) else self.relation_type,
            "strength": self.strength,
            "confidence": self.confidence,
            "reason": self.reason,
            "auto_generated": self.auto_generated,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "GraphEdge":
        return cls(
            edge_id=data["edge_id"],
            source_node=data["source_node"],
            target_node=data["target_node"],
            relation_type=RelationType(data["relation_type"]) if data.get("relation_type") else RelationType.SUPPORTS,
            strength=data.get("strength", 0.5),
            confidence=data.get("confidence", 0.5),
            reason=data.get("reason", ""),
            auto_generated=data.get("auto_generated", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )


@dataclass
class GraphSnapshot:
    """
    Snapshot of the Alpha Graph at a point in time.
    """
    snapshot_id: str
    
    # Counts
    total_nodes: int = 0
    total_edges: int = 0
    
    # By relation type
    supports_count: int = 0
    amplifies_count: int = 0
    contradicts_count: int = 0
    conditional_count: int = 0
    invalidates_count: int = 0
    
    # By family
    nodes_by_family: Dict[str, int] = field(default_factory=dict)
    
    # Metadata
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "snapshot_id": self.snapshot_id,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "edges_by_type": {
                "supports": self.supports_count,
                "amplifies": self.amplifies_count,
                "contradicts": self.contradicts_count,
                "conditional_on": self.conditional_count,
                "invalidates": self.invalidates_count
            },
            "nodes_by_family": self.nodes_by_family,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class CoherenceResult:
    """
    Result of reasoning over the graph.
    """
    # Main score
    coherence_score: float = 0.0  # 0-1
    
    # Breakdown
    supporting_edges: int = 0
    amplifying_edges: int = 0
    conflicting_edges: int = 0
    conditional_edges: int = 0
    invalidating_edges: int = 0
    
    # Active factors
    active_nodes: List[str] = field(default_factory=list)
    
    # Detailed analysis
    support_chains: List[List[str]] = field(default_factory=list)
    conflict_pairs: List[tuple] = field(default_factory=list)
    amplification_chains: List[List[str]] = field(default_factory=list)
    
    # Recommendation
    signal_quality: str = "NEUTRAL"  # STRONG, MODERATE, WEAK, CONFLICTED, NEUTRAL
    recommendation: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "coherence_score": self.coherence_score,
            "supporting_edges": self.supporting_edges,
            "amplifying_edges": self.amplifying_edges,
            "conflicting_edges": self.conflicting_edges,
            "conditional_edges": self.conditional_edges,
            "invalidating_edges": self.invalidating_edges,
            "active_nodes": self.active_nodes,
            "support_chains": self.support_chains,
            "conflict_pairs": [(a, b) for a, b in self.conflict_pairs],
            "amplification_chains": self.amplification_chains,
            "signal_quality": self.signal_quality,
            "recommendation": self.recommendation
        }
