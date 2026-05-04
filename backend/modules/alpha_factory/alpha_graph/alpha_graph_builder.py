"""
PHASE 13.5 - Alpha Graph Builder
=================================
Automatically builds graph from approved factors.

Builds edges based on:
1. Family logic (momentum supports breakout)
2. Input overlap (shared features)
3. Conflict detection (opposing families)
4. Regime dependency
"""

from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime, timezone
import hashlib

from .alpha_graph_types import GraphNode, GraphEdge, RelationType


# Family relationship matrix
FAMILY_SUPPORTS = {
    "momentum": ["trend", "breakout"],
    "trend": ["momentum", "structure"],
    "breakout": ["momentum", "volatility"],
    "volatility": ["breakout", "regime"],
    "volume": ["breakout", "momentum", "liquidity"],
    "liquidity": ["reversal", "microstructure"],
    "microstructure": ["liquidity", "volume"],
    "structure": ["trend", "reversal"],
    "correlation": ["macro", "regime"],
    "macro": ["correlation", "regime"],
    "regime": ["macro", "volatility"],
    "reversal": ["liquidity", "structure"],
}

# Family conflicts
FAMILY_CONTRADICTS = {
    "trend": ["reversal"],
    "reversal": ["trend", "momentum"],
    "momentum": ["reversal"],
    "breakout": ["regime"],  # Breakout fails in ranging regimes
}

# Family amplifications
FAMILY_AMPLIFIES = {
    "volume": ["breakout", "momentum"],
    "microstructure": ["liquidity", "reversal"],
    "volatility": ["breakout"],
    "correlation": ["macro"],
}

# Regime conditionals
REGIME_CONDITIONALS = {
    "TRENDING_UP": ["momentum", "trend", "breakout"],
    "TRENDING_DOWN": ["momentum", "trend"],
    "RANGE": ["reversal", "structure"],
    "HIGH_VOL": ["volatility", "breakout"],
    "LOW_VOL": ["structure", "correlation"],
}


class GraphBuilder:
    """
    Builds the Alpha Graph from approved factors.
    """
    
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self.edge_counter = 0
    
    def reset(self):
        """Reset builder state."""
        self.nodes = {}
        self.edges = {}
        self.edge_counter = 0
    
    def _generate_edge_id(self, source: str, target: str, relation: str) -> str:
        """Generate unique edge ID."""
        key = f"{source}:{target}:{relation}"
        return hashlib.md5(key.encode()).hexdigest()[:10]
    
    def add_node(self, factor: Dict, ranking: Dict = None) -> GraphNode:
        """
        Add a node from an approved factor.
        """
        factor_id = factor.get("factor_id", "")
        node_id = factor_id  # Use factor_id as node_id
        
        ranking = ranking or {}
        
        node = GraphNode(
            node_id=node_id,
            factor_id=factor_id,
            family=factor.get("family", ""),
            template=factor.get("template", ""),
            inputs=factor.get("inputs", []),
            composite_score=ranking.get("composite_score", factor.get("composite_score", 0.0)),
            verdict=ranking.get("verdict", factor.get("verdict", "")),
            ic=ranking.get("ic", 0.0),
            sharpe=ranking.get("sharpe", 0.0),
            weight=1.0,
            active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        self.nodes[node_id] = node
        return node
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        strength: float = 0.5,
        confidence: float = 0.5,
        reason: str = ""
    ) -> Optional[GraphEdge]:
        """
        Add an edge between two nodes.
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            return None
        
        if source_id == target_id:
            return None
        
        edge_id = self._generate_edge_id(source_id, target_id, relation_type.value)
        
        # Skip if edge already exists
        if edge_id in self.edges:
            return self.edges[edge_id]
        
        edge = GraphEdge(
            edge_id=edge_id,
            source_node=source_id,
            target_node=target_id,
            relation_type=relation_type,
            strength=strength,
            confidence=confidence,
            reason=reason,
            auto_generated=True,
            created_at=datetime.now(timezone.utc)
        )
        
        self.edges[edge_id] = edge
        
        # Update node edge counts
        self.nodes[source_id].outgoing_edges += 1
        self.nodes[target_id].incoming_edges += 1
        
        return edge
    
    def build_family_edges(self) -> int:
        """
        Build edges based on family relationships.
        """
        edges_created = 0
        node_list = list(self.nodes.values())
        
        for i, node1 in enumerate(node_list):
            for node2 in node_list[i+1:]:
                family1 = node1.family
                family2 = node2.family
                
                # Check SUPPORTS
                if family2 in FAMILY_SUPPORTS.get(family1, []):
                    edge = self.add_edge(
                        node1.node_id,
                        node2.node_id,
                        RelationType.SUPPORTS,
                        strength=0.6,
                        confidence=0.7,
                        reason=f"{family1} supports {family2}"
                    )
                    if edge:
                        edges_created += 1
                
                # Check reverse SUPPORTS
                if family1 in FAMILY_SUPPORTS.get(family2, []):
                    edge = self.add_edge(
                        node2.node_id,
                        node1.node_id,
                        RelationType.SUPPORTS,
                        strength=0.6,
                        confidence=0.7,
                        reason=f"{family2} supports {family1}"
                    )
                    if edge:
                        edges_created += 1
                
                # Check CONTRADICTS
                if family2 in FAMILY_CONTRADICTS.get(family1, []):
                    edge = self.add_edge(
                        node1.node_id,
                        node2.node_id,
                        RelationType.CONTRADICTS,
                        strength=0.7,
                        confidence=0.8,
                        reason=f"{family1} contradicts {family2}"
                    )
                    if edge:
                        edges_created += 1
                
                # Check AMPLIFIES
                if family2 in FAMILY_AMPLIFIES.get(family1, []):
                    edge = self.add_edge(
                        node1.node_id,
                        node2.node_id,
                        RelationType.AMPLIFIES,
                        strength=0.65,
                        confidence=0.75,
                        reason=f"{family1} amplifies {family2}"
                    )
                    if edge:
                        edges_created += 1
        
        return edges_created
    
    def build_input_overlap_edges(self) -> int:
        """
        Build edges based on shared inputs (features).
        """
        edges_created = 0
        node_list = list(self.nodes.values())
        
        for i, node1 in enumerate(node_list):
            inputs1 = set(node1.inputs)
            if not inputs1:
                continue
            
            for node2 in node_list[i+1:]:
                inputs2 = set(node2.inputs)
                if not inputs2:
                    continue
                
                # Calculate overlap
                overlap = inputs1 & inputs2
                if overlap:
                    overlap_ratio = len(overlap) / min(len(inputs1), len(inputs2))
                    
                    if overlap_ratio >= 0.5:
                        # High overlap = they support each other
                        edge = self.add_edge(
                            node1.node_id,
                            node2.node_id,
                            RelationType.SUPPORTS,
                            strength=overlap_ratio,
                            confidence=0.6,
                            reason=f"Shared inputs: {list(overlap)[:3]}"
                        )
                        if edge:
                            edges_created += 1
        
        return edges_created
    
    def build_regime_edges(self) -> int:
        """
        Build conditional edges based on regime dependencies.
        """
        edges_created = 0
        
        # Find regime factors
        regime_nodes = [n for n in self.nodes.values() if n.family == "regime"]
        
        for regime_node in regime_nodes:
            # Check if this regime factor conditions other families
            for family, conditioned_families in REGIME_CONDITIONALS.items():
                # Find factors from conditioned families
                for node in self.nodes.values():
                    if node.node_id == regime_node.node_id:
                        continue
                    
                    if node.family in conditioned_families:
                        edge = self.add_edge(
                            node.node_id,
                            regime_node.node_id,
                            RelationType.CONDITIONAL_ON,
                            strength=0.5,
                            confidence=0.6,
                            reason=f"{node.family} conditional on regime"
                        )
                        if edge:
                            edges_created += 1
        
        return edges_created
    
    def build_template_edges(self) -> int:
        """
        Build edges based on template complexity.
        
        Complex templates (triple, interaction) often amplify simpler ones.
        """
        edges_created = 0
        
        complex_templates = ["triple_feature", "interaction_feature", "conditional_feature"]
        simple_templates = ["single_feature", "pair_feature"]
        
        complex_nodes = [n for n in self.nodes.values() if n.template in complex_templates]
        simple_nodes = [n for n in self.nodes.values() if n.template in simple_templates]
        
        for complex_node in complex_nodes:
            for simple_node in simple_nodes:
                # Complex amplifies simple if same family
                if complex_node.family == simple_node.family:
                    edge = self.add_edge(
                        complex_node.node_id,
                        simple_node.node_id,
                        RelationType.AMPLIFIES,
                        strength=0.55,
                        confidence=0.5,
                        reason=f"Complex {complex_node.template} amplifies {simple_node.template}"
                    )
                    if edge:
                        edges_created += 1
        
        return edges_created
    
    def build_all_edges(self) -> Dict[str, int]:
        """
        Build all edge types.
        """
        results = {
            "family_edges": self.build_family_edges(),
            "input_overlap_edges": self.build_input_overlap_edges(),
            "regime_edges": self.build_regime_edges(),
            "template_edges": self.build_template_edges()
        }
        results["total"] = sum(results.values())
        return results
    
    def get_nodes(self) -> List[GraphNode]:
        """Get all nodes."""
        return list(self.nodes.values())
    
    def get_edges(self) -> List[GraphEdge]:
        """Get all edges."""
        return list(self.edges.values())
    
    def get_edges_by_type(self, relation_type: RelationType) -> List[GraphEdge]:
        """Get edges by type."""
        return [e for e in self.edges.values() if e.relation_type == relation_type]
    
    def get_stats(self) -> Dict:
        """Get builder statistics."""
        edges_by_type = {}
        for rt in RelationType:
            edges_by_type[rt.value] = len(self.get_edges_by_type(rt))
        
        nodes_by_family = {}
        for node in self.nodes.values():
            family = node.family or "unknown"
            nodes_by_family[family] = nodes_by_family.get(family, 0) + 1
        
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "edges_by_type": edges_by_type,
            "nodes_by_family": nodes_by_family
        }
