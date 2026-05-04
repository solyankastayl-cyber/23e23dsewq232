"""
PHASE 13.5 - Alpha Graph Reasoner
==================================
Reasoning engine for signal coherence.

Evaluates:
- Support chains
- Conflict detection
- Amplification chains
- Invalidation conditions
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

from .alpha_graph_types import (
    GraphNode, GraphEdge, RelationType, CoherenceResult
)


class GraphReasoner:
    """
    Reasoning engine for Alpha Graph.
    
    Evaluates signal coherence and detects conflicts.
    """
    
    # Weights for coherence calculation
    SUPPORT_WEIGHT = 0.15
    AMPLIFY_WEIGHT = 0.20
    CONFLICT_PENALTY = -0.30
    CONDITIONAL_WEIGHT = 0.10
    INVALIDATE_PENALTY = -0.40
    
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        
        # Index for fast lookup
        self.outgoing: Dict[str, List[GraphEdge]] = defaultdict(list)
        self.incoming: Dict[str, List[GraphEdge]] = defaultdict(list)
        self.by_type: Dict[RelationType, List[GraphEdge]] = defaultdict(list)
    
    def load_graph(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ):
        """
        Load graph into reasoner.
        """
        self.nodes = {n.node_id: n for n in nodes}
        self.edges = {e.edge_id: e for e in edges}
        
        # Build indexes
        self.outgoing = defaultdict(list)
        self.incoming = defaultdict(list)
        self.by_type = defaultdict(list)
        
        for edge in edges:
            self.outgoing[edge.source_node].append(edge)
            self.incoming[edge.target_node].append(edge)
            self.by_type[edge.relation_type].append(edge)
    
    def evaluate_coherence(
        self,
        active_factor_ids: List[str]
    ) -> CoherenceResult:
        """
        Evaluate signal coherence for active factors.
        
        Args:
            active_factor_ids: List of currently active factor IDs
        
        Returns:
            CoherenceResult with coherence score and breakdown
        """
        result = CoherenceResult()
        result.active_nodes = active_factor_ids
        
        if not active_factor_ids or len(active_factor_ids) < 2:
            result.coherence_score = 0.5
            result.signal_quality = "NEUTRAL"
            result.recommendation = "Not enough active signals for reasoning"
            return result
        
        active_set = set(active_factor_ids)
        
        # Find all edges between active nodes
        relevant_edges = []
        for edge in self.edges.values():
            if edge.source_node in active_set and edge.target_node in active_set:
                relevant_edges.append(edge)
        
        # Count by type
        supports = []
        amplifies = []
        contradicts = []
        conditionals = []
        invalidates = []
        
        for edge in relevant_edges:
            if edge.relation_type == RelationType.SUPPORTS:
                supports.append(edge)
            elif edge.relation_type == RelationType.AMPLIFIES:
                amplifies.append(edge)
            elif edge.relation_type == RelationType.CONTRADICTS:
                contradicts.append(edge)
            elif edge.relation_type == RelationType.CONDITIONAL_ON:
                conditionals.append(edge)
            elif edge.relation_type == RelationType.INVALIDATES:
                invalidates.append(edge)
        
        result.supporting_edges = len(supports)
        result.amplifying_edges = len(amplifies)
        result.conflicting_edges = len(contradicts)
        result.conditional_edges = len(conditionals)
        result.invalidating_edges = len(invalidates)
        
        # Find support chains
        result.support_chains = self._find_chains(supports, active_set)
        
        # Find amplification chains
        result.amplification_chains = self._find_chains(amplifies, active_set)
        
        # Find conflict pairs
        result.conflict_pairs = [(e.source_node, e.target_node) for e in contradicts]
        
        # Calculate coherence score
        base_score = 0.5
        
        # Positive contributions
        support_bonus = len(supports) * self.SUPPORT_WEIGHT * 0.1
        amplify_bonus = len(amplifies) * self.AMPLIFY_WEIGHT * 0.1
        conditional_bonus = len(conditionals) * self.CONDITIONAL_WEIGHT * 0.1
        
        # Negative contributions
        conflict_penalty = len(contradicts) * self.CONFLICT_PENALTY * 0.1
        invalidate_penalty = len(invalidates) * self.INVALIDATE_PENALTY * 0.1
        
        # Chain bonuses
        chain_bonus = len(result.support_chains) * 0.05
        amplify_chain_bonus = len(result.amplification_chains) * 0.07
        
        coherence = base_score + support_bonus + amplify_bonus + conditional_bonus \
                    + conflict_penalty + invalidate_penalty + chain_bonus + amplify_chain_bonus
        
        # Clamp to 0-1
        result.coherence_score = max(0.0, min(1.0, coherence))
        
        # Determine signal quality
        result.signal_quality = self._determine_signal_quality(
            result.coherence_score,
            len(contradicts),
            len(invalidates)
        )
        
        # Generate recommendation
        result.recommendation = self._generate_recommendation(result)
        
        return result
    
    def _find_chains(
        self,
        edges: List[GraphEdge],
        active_set: Set[str],
        max_length: int = 4
    ) -> List[List[str]]:
        """
        Find chains in the graph.
        """
        chains = []
        
        # Build adjacency for these edges
        adj = defaultdict(list)
        for edge in edges:
            adj[edge.source_node].append(edge.target_node)
        
        # DFS to find chains
        def dfs(node: str, path: List[str]):
            if len(path) >= max_length:
                return
            
            for next_node in adj[node]:
                if next_node not in path and next_node in active_set:
                    new_path = path + [next_node]
                    if len(new_path) >= 3:
                        chains.append(new_path)
                    dfs(next_node, new_path)
        
        for start in active_set:
            if start in adj:
                dfs(start, [start])
        
        # Remove duplicates and subsets
        unique_chains = []
        for chain in chains:
            chain_set = set(chain)
            is_subset = False
            for other in unique_chains:
                if chain_set.issubset(set(other)):
                    is_subset = True
                    break
            if not is_subset:
                unique_chains.append(chain)
        
        return unique_chains[:10]  # Limit to top 10
    
    def _determine_signal_quality(
        self,
        coherence: float,
        conflicts: int,
        invalidations: int
    ) -> str:
        """
        Determine overall signal quality.
        """
        if invalidations > 0:
            return "INVALIDATED"
        
        if conflicts > 2:
            return "CONFLICTED"
        
        if coherence >= 0.75:
            return "STRONG"
        elif coherence >= 0.55:
            return "MODERATE"
        elif coherence >= 0.35:
            return "WEAK"
        else:
            return "CONFLICTED"
    
    def _generate_recommendation(
        self,
        result: CoherenceResult
    ) -> str:
        """
        Generate trading recommendation based on result.
        """
        if result.signal_quality == "INVALIDATED":
            return "Signal invalidated by macro/regime conditions. Wait for clarity."
        
        if result.signal_quality == "CONFLICTED":
            conflicts = len(result.conflict_pairs)
            return f"Conflicting signals ({conflicts} conflicts). Reduce position size or wait."
        
        if result.signal_quality == "STRONG":
            chains = len(result.support_chains) + len(result.amplification_chains)
            return f"Strong signal coherence with {chains} supporting chains. Full position size."
        
        if result.signal_quality == "MODERATE":
            return "Moderate signal coherence. Standard position size."
        
        return "Weak signal coherence. Reduced position size recommended."
    
    def get_node_context(
        self,
        node_id: str
    ) -> Dict:
        """
        Get context for a specific node.
        """
        if node_id not in self.nodes:
            return {}
        
        node = self.nodes[node_id]
        outgoing = self.outgoing.get(node_id, [])
        incoming = self.incoming.get(node_id, [])
        
        supports = [e.target_node for e in outgoing if e.relation_type == RelationType.SUPPORTS]
        supported_by = [e.source_node for e in incoming if e.relation_type == RelationType.SUPPORTS]
        amplifies = [e.target_node for e in outgoing if e.relation_type == RelationType.AMPLIFIES]
        contradicts = [e.target_node for e in outgoing if e.relation_type == RelationType.CONTRADICTS]
        conditional_on = [e.target_node for e in outgoing if e.relation_type == RelationType.CONDITIONAL_ON]
        
        return {
            "node_id": node_id,
            "family": node.family,
            "template": node.template,
            "supports": supports,
            "supported_by": supported_by,
            "amplifies": amplifies,
            "contradicts": contradicts,
            "conditional_on": conditional_on,
            "total_connections": len(outgoing) + len(incoming)
        }
    
    def get_conflicts(self) -> List[Tuple[str, str]]:
        """
        Get all conflict pairs in the graph.
        """
        conflicts = []
        for edge in self.by_type.get(RelationType.CONTRADICTS, []):
            conflicts.append((edge.source_node, edge.target_node))
        return conflicts
    
    def get_support_network(self, node_id: str, depth: int = 2) -> Dict:
        """
        Get support network for a node.
        """
        visited = set()
        network = {"center": node_id, "nodes": [], "edges": []}
        
        def explore(current: str, current_depth: int):
            if current_depth > depth or current in visited:
                return
            visited.add(current)
            network["nodes"].append(current)
            
            for edge in self.outgoing.get(current, []):
                if edge.relation_type in [RelationType.SUPPORTS, RelationType.AMPLIFIES]:
                    network["edges"].append({
                        "source": current,
                        "target": edge.target_node,
                        "type": edge.relation_type.value
                    })
                    explore(edge.target_node, current_depth + 1)
        
        explore(node_id, 0)
        return network
