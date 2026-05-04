"""
PHASE 13.6 - Alpha DAG Optimizer
==================================
Optimizes DAG for efficient computation.

Optimizations:
1. Remove duplicate nodes
2. Merge consecutive transforms
3. Transform fusion (e.g., zscore(rolling_mean) -> rolling_zscore)
4. Minimize depth
"""

from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict

from .dag_types import DagNode, DagEdge, NodeType, TransformType


# Transform fusion rules
# (transform1, transform2) -> fused_transform
FUSION_RULES = {
    (TransformType.ROLLING_MEAN, TransformType.ZSCORE): TransformType.ROLLING_ZSCORE,
    (TransformType.ROLLING_STD, TransformType.ZSCORE): TransformType.ROLLING_ZSCORE,
    (TransformType.SMA, TransformType.ZSCORE): TransformType.ROLLING_ZSCORE,
}

# Transforms that can be merged
MERGEABLE_TRANSFORMS = {
    TransformType.ROLLING_MEAN,
    TransformType.ROLLING_STD,
    TransformType.EMA,
    TransformType.SMA,
}


class DagOptimizer:
    """
    Optimizes computational DAG.
    """
    
    def __init__(self, nodes: Dict[str, DagNode], edges: Dict[str, DagEdge]):
        self.nodes = nodes.copy()
        self.edges = edges.copy()
        
        # Track optimizations
        self.duplicates_removed = 0
        self.transforms_merged = 0
        self.transforms_fused = 0
        self.depth_reduction = 0
    
    def optimize(self) -> Dict:
        """
        Run all optimizations.
        
        Returns:
            Optimization statistics
        """
        initial_nodes = len(self.nodes)
        initial_edges = len(self.edges)
        initial_depth = self._calculate_depth()
        
        # Run optimizations in order
        self._remove_duplicates()
        self._merge_transforms()
        self._apply_fusion()
        self._minimize_depth()
        
        final_depth = self._calculate_depth()
        self.depth_reduction = initial_depth - final_depth
        
        return {
            "initial_nodes": initial_nodes,
            "final_nodes": len(self.nodes),
            "nodes_removed": initial_nodes - len(self.nodes),
            "initial_edges": initial_edges,
            "final_edges": len(self.edges),
            "edges_removed": initial_edges - len(self.edges),
            "duplicates_removed": self.duplicates_removed,
            "transforms_merged": self.transforms_merged,
            "transforms_fused": self.transforms_fused,
            "depth_reduction": self.depth_reduction,
            "initial_depth": initial_depth,
            "final_depth": final_depth
        }
    
    def _remove_duplicates(self):
        """
        Remove duplicate nodes with same operation and inputs.
        """
        # Group nodes by signature
        signature_groups: Dict[str, List[str]] = defaultdict(list)
        
        for node_id, node in self.nodes.items():
            sig = node.get_input_signature()
            signature_groups[sig].append(node_id)
        
        # Merge duplicates
        for sig, node_ids in signature_groups.items():
            if len(node_ids) <= 1:
                continue
            
            # Keep the first node, remove others
            keep_id = node_ids[0]
            for remove_id in node_ids[1:]:
                self._merge_nodes(keep_id, remove_id)
                self.duplicates_removed += 1
    
    def _merge_nodes(self, keep_id: str, remove_id: str):
        """
        Merge remove_id into keep_id.
        """
        if remove_id not in self.nodes or keep_id not in self.nodes:
            return
        
        remove_node = self.nodes[remove_id]
        keep_node = self.nodes[keep_id]
        
        # Redirect outputs from remove_node to keep_node
        for output_id in remove_node.outputs:
            if output_id in self.nodes:
                output_node = self.nodes[output_id]
                # Replace input reference
                output_node.inputs = [keep_id if i == remove_id else i for i in output_node.inputs]
                
                # Update edges
                self._update_edge(remove_id, output_id, keep_id, output_id)
        
        # Add outputs to keep node
        keep_node.outputs.extend(remove_node.outputs)
        keep_node.outputs = list(set(keep_node.outputs))
        
        # Remove the duplicate node
        del self.nodes[remove_id]
        
        # Remove orphaned edges
        self._cleanup_edges()
    
    def _merge_transforms(self):
        """
        Merge consecutive transforms of the same type.
        
        Example: rolling_mean(rolling_mean(x)) -> rolling_mean(x)
        """
        nodes_to_check = [
            n for n in self.nodes.values() 
            if n.node_type == NodeType.TRANSFORM
        ]
        
        for node in nodes_to_check:
            if node.node_id not in self.nodes:
                continue
            
            try:
                transform_type = TransformType(node.operation)
                if transform_type not in MERGEABLE_TRANSFORMS:
                    continue
            except ValueError:
                continue
            
            # Check if any input is the same transform
            for input_id in node.inputs:
                if input_id not in self.nodes:
                    continue
                
                input_node = self.nodes[input_id]
                if input_node.node_type != NodeType.TRANSFORM:
                    continue
                
                if input_node.operation == node.operation:
                    # Same transform - can potentially merge
                    # Skip the intermediate node
                    self._bypass_node(input_id, node.node_id)
                    self.transforms_merged += 1
    
    def _apply_fusion(self):
        """
        Apply transform fusion rules.
        
        Example: zscore(rolling_mean(x)) -> rolling_zscore(x)
        """
        nodes_to_check = list(self.nodes.values())
        
        for node in nodes_to_check:
            if node.node_id not in self.nodes:
                continue
            
            if node.node_type != NodeType.TRANSFORM:
                continue
            
            try:
                transform2 = TransformType(node.operation)
            except ValueError:
                continue
            
            # Check inputs for fusion opportunities
            for input_id in node.inputs:
                if input_id not in self.nodes:
                    continue
                
                input_node = self.nodes[input_id]
                if input_node.node_type != NodeType.TRANSFORM:
                    continue
                
                try:
                    transform1 = TransformType(input_node.operation)
                except ValueError:
                    continue
                
                # Check fusion rules
                fused = FUSION_RULES.get((transform1, transform2))
                if fused:
                    # Apply fusion
                    node.operation = fused.value
                    node.inputs = input_node.inputs.copy()
                    
                    # Update cost
                    node.cost = max(node.cost, input_node.cost)
                    
                    # Remove the fused input node if no other outputs
                    if len(input_node.outputs) == 1:
                        self._remove_node(input_id)
                    
                    # Update edges
                    self._rebuild_edges_for_node(node.node_id)
                    
                    self.transforms_fused += 1
    
    def _minimize_depth(self):
        """
        Minimize DAG depth by parallelizing independent branches.
        """
        # This is handled by the scheduler's levelized sort
        # Here we can do some structural optimizations
        
        # Find bottleneck nodes (single node connecting many)
        for node_id, node in list(self.nodes.items()):
            if len(node.inputs) == 1 and len(node.outputs) == 1:
                # Potential bypass candidate
                input_node = self.nodes.get(node.inputs[0])
                output_node = self.nodes.get(node.outputs[0])
                
                if input_node and output_node:
                    # If this is just a pass-through transform with no change
                    if node.operation in ["identity", "passthrough"]:
                        self._bypass_node(node_id, node.outputs[0])
    
    def _bypass_node(self, bypass_id: str, target_id: str):
        """
        Bypass a node, connecting its inputs directly to target.
        """
        if bypass_id not in self.nodes:
            return
        
        bypass_node = self.nodes[bypass_id]
        target_node = self.nodes.get(target_id)
        
        if not target_node:
            return
        
        # Connect bypass inputs to target
        for inp_id in bypass_node.inputs:
            if inp_id in self.nodes:
                self.nodes[inp_id].outputs.append(target_id)
        
        # Update target inputs
        target_node.inputs = [
            inp for inp in target_node.inputs 
            if inp != bypass_id
        ] + bypass_node.inputs
        
        # Remove duplicates
        target_node.inputs = list(set(target_node.inputs))
    
    def _remove_node(self, node_id: str):
        """Remove a node and its edges."""
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        
        # Remove from inputs' outputs
        for inp_id in node.inputs:
            if inp_id in self.nodes:
                inp_node = self.nodes[inp_id]
                inp_node.outputs = [o for o in inp_node.outputs if o != node_id]
        
        # Remove from outputs' inputs
        for out_id in node.outputs:
            if out_id in self.nodes:
                out_node = self.nodes[out_id]
                out_node.inputs = [i for i in out_node.inputs if i != node_id]
        
        del self.nodes[node_id]
        self._cleanup_edges()
    
    def _update_edge(self, old_source: str, old_target: str, new_source: str, new_target: str):
        """Update an edge."""
        old_edge_id = f"{old_source}:{old_target}"
        old_edge_id = next(
            (e.edge_id for e in self.edges.values() 
             if e.source_node == old_source and e.target_node == old_target),
            None
        )
        
        if old_edge_id and old_edge_id in self.edges:
            edge = self.edges[old_edge_id]
            edge.source_node = new_source
            edge.target_node = new_target
    
    def _rebuild_edges_for_node(self, node_id: str):
        """Rebuild edges for a specific node."""
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        
        # Remove old incoming edges
        self.edges = {
            eid: e for eid, e in self.edges.items()
            if e.target_node != node_id
        }
        
        # Add new incoming edges
        from .dag_builder import DagBuilder
        builder = DagBuilder()
        
        for inp_id in node.inputs:
            edge_id = builder._generate_edge_id(inp_id, node_id)
            self.edges[edge_id] = DagEdge(
                edge_id=edge_id,
                source_node=inp_id,
                target_node=node_id
            )
    
    def _cleanup_edges(self):
        """Remove edges that reference non-existent nodes."""
        valid_nodes = set(self.nodes.keys())
        
        self.edges = {
            eid: e for eid, e in self.edges.items()
            if e.source_node in valid_nodes and e.target_node in valid_nodes
        }
    
    def _calculate_depth(self) -> int:
        """Calculate DAG depth."""
        if not self.nodes:
            return 0
        
        # Build adjacency
        in_degree = {node_id: 0 for node_id in self.nodes}
        adj = defaultdict(list)
        
        for edge in self.edges.values():
            adj[edge.source_node].append(edge.target_node)
            if edge.target_node in in_degree:
                in_degree[edge.target_node] += 1
        
        # BFS to find depth
        depth = 0
        current_level = [n for n, d in in_degree.items() if d == 0]
        
        while current_level:
            depth += 1
            next_level = []
            
            for node_id in current_level:
                for neighbor in adj[node_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_level.append(neighbor)
            
            current_level = next_level
        
        return depth
    
    def get_nodes(self) -> Dict[str, DagNode]:
        """Get optimized nodes."""
        return self.nodes
    
    def get_edges(self) -> Dict[str, DagEdge]:
        """Get optimized edges."""
        return self.edges
