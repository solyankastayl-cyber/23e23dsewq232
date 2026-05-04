"""
PHASE 13.6 - Alpha DAG Scheduler
==================================
Schedules DAG execution order.

Features:
1. Topological sort
2. Levelized scheduling for parallel execution
3. Cost-aware ordering
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque

from .dag_types import DagNode, DagEdge, NodeType


class DagScheduler:
    """
    Schedules DAG execution order using levelized topological sort.
    
    Nodes are organized into levels where all nodes in a level
    can be computed in parallel (their dependencies are satisfied).
    """
    
    def __init__(self, nodes: Dict[str, DagNode], edges: Dict[str, DagEdge]):
        """
        Initialize scheduler.
        
        Args:
            nodes: DAG nodes
            edges: DAG edges
        """
        self.nodes = nodes
        self.edges = edges
        
        # Build adjacency lists
        self.adj: Dict[str, List[str]] = defaultdict(list)
        self.rev_adj: Dict[str, List[str]] = defaultdict(list)
        self.in_degree: Dict[str, int] = {}
        
        self._build_adjacency()
        
        # Scheduling results
        self.levels: List[List[str]] = []
        self.execution_order: List[str] = []
        self.depth = 0
    
    def _build_adjacency(self):
        """Build adjacency lists from edges."""
        self.in_degree = {node_id: 0 for node_id in self.nodes}
        
        for edge in self.edges.values():
            self.adj[edge.source_node].append(edge.target_node)
            self.rev_adj[edge.target_node].append(edge.source_node)
            
            if edge.target_node in self.in_degree:
                self.in_degree[edge.target_node] += 1
    
    def schedule(self) -> Dict:
        """
        Compute levelized topological sort.
        
        Returns:
            Scheduling statistics
        """
        self.levels = []
        self.execution_order = []
        
        # Copy in-degree for modification
        in_deg = self.in_degree.copy()
        
        # Start with nodes that have no dependencies (level 0)
        current_level = [
            node_id for node_id, degree in in_deg.items()
            if degree == 0
        ]
        
        level_num = 0
        
        while current_level:
            # Sort current level by cost (lower cost first)
            current_level.sort(key=lambda nid: self.nodes[nid].cost)
            
            # Assign level to nodes
            for node_id in current_level:
                self.nodes[node_id].level = level_num
                self.nodes[node_id].execution_order = len(self.execution_order)
                self.execution_order.append(node_id)
            
            self.levels.append(current_level)
            
            # Find next level
            next_level = []
            for node_id in current_level:
                for neighbor in self.adj[node_id]:
                    in_deg[neighbor] -= 1
                    if in_deg[neighbor] == 0:
                        next_level.append(neighbor)
            
            current_level = next_level
            level_num += 1
        
        self.depth = len(self.levels)
        
        # Detect unscheduled nodes (indicates cycle)
        unscheduled = [
            node_id for node_id, deg in in_deg.items()
            if deg > 0
        ]
        
        return {
            "levels": len(self.levels),
            "total_scheduled": len(self.execution_order),
            "unscheduled": len(unscheduled),
            "depth": self.depth,
            "level_sizes": [len(level) for level in self.levels]
        }
    
    def get_levels(self) -> List[List[str]]:
        """
        Get nodes organized by level.
        
        Returns:
            List of levels, each containing node IDs that can run in parallel
        """
        return self.levels
    
    def get_execution_order(self) -> List[str]:
        """
        Get sequential execution order.
        
        Returns:
            List of node IDs in execution order
        """
        return self.execution_order
    
    def get_level_stats(self) -> Dict:
        """Get statistics about each level."""
        stats = []
        
        for level_idx, level in enumerate(self.levels):
            level_nodes = [self.nodes[nid] for nid in level if nid in self.nodes]
            
            level_stat = {
                "level": level_idx,
                "node_count": len(level),
                "total_cost": sum(n.cost for n in level_nodes),
                "estimated_latency_ms": max((n.latency_estimate for n in level_nodes), default=0),
                "node_types": {
                    "feature": sum(1 for n in level_nodes if n.node_type == NodeType.FEATURE),
                    "transform": sum(1 for n in level_nodes if n.node_type == NodeType.TRANSFORM),
                    "factor": sum(1 for n in level_nodes if n.node_type == NodeType.FACTOR),
                }
            }
            stats.append(level_stat)
        
        return {
            "levels": stats,
            "total_levels": len(self.levels),
            "max_parallelism": max(len(level) for level in self.levels) if self.levels else 0,
            "avg_level_size": sum(len(l) for l in self.levels) / len(self.levels) if self.levels else 0
        }
    
    def get_critical_path(self) -> List[str]:
        """
        Find the critical path (longest path through DAG).
        
        Returns:
            List of node IDs on the critical path
        """
        if not self.nodes:
            return []
        
        # Dynamic programming to find longest path
        dist: Dict[str, Tuple[float, Optional[str]]] = {}  # node -> (distance, predecessor)
        
        for node_id in self.execution_order:
            node = self.nodes[node_id]
            
            # Find max distance from predecessors
            max_dist = 0.0
            pred = None
            
            for prev_id in self.rev_adj[node_id]:
                if prev_id in dist:
                    prev_dist = dist[prev_id][0]
                    if prev_dist > max_dist:
                        max_dist = prev_dist
                        pred = prev_id
            
            dist[node_id] = (max_dist + node.cost, pred)
        
        # Find node with maximum distance (end of critical path)
        max_node = max(dist.items(), key=lambda x: x[1][0])[0] if dist else None
        
        # Backtrack to build path
        path = []
        current = max_node
        while current:
            path.append(current)
            current = dist[current][1] if current in dist else None
        
        return list(reversed(path))
    
    def get_parallel_schedule(self) -> List[Dict]:
        """
        Get a schedule suitable for parallel execution.
        
        Returns:
            List of batches, each with nodes that can run in parallel
        """
        schedule = []
        
        for level_idx, level in enumerate(self.levels):
            batch = {
                "batch_id": level_idx,
                "nodes": level,
                "count": len(level),
                "can_parallelize": len(level) > 1,
                "estimated_time_ms": max(
                    (self.nodes[nid].latency_estimate for nid in level if nid in self.nodes),
                    default=0
                )
            }
            schedule.append(batch)
        
        return schedule
    
    def estimate_total_time(self, parallel: bool = True) -> float:
        """
        Estimate total execution time.
        
        Args:
            parallel: Whether to assume parallel execution within levels
        
        Returns:
            Estimated time in milliseconds
        """
        if parallel:
            # Parallel: sum of max latency per level
            return sum(
                max((self.nodes[nid].latency_estimate for nid in level if nid in self.nodes), default=0)
                for level in self.levels
            )
        else:
            # Sequential: sum of all latencies
            return sum(n.latency_estimate for n in self.nodes.values())
