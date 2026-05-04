"""
PHASE 13.6 - Alpha DAG Builder
================================
Builds computational DAG from approved factors.

Process:
1. Load approved factors
2. Extract feature dependencies
3. Extract transform operations
4. Build dependency graph
5. Detect cycles
"""

from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict
import hashlib
import re

from .dag_types import (
    DagNode, DagEdge, NodeType, TransformType,
    NODE_COST, NODE_LATENCY, TRANSFORM_COST,
    DagCycleError
)


# Feature patterns for parsing
FEATURE_PATTERNS = [
    r"price_return_(\d+)m?",
    r"volume_(\d+)m?",
    r"volatility_(\d+)m?",
    r"rsi_(\d+)",
    r"macd_(\w+)",
    r"ema_(\d+)",
    r"sma_(\d+)",
    r"bollinger_(\w+)",
    r"atr_(\d+)",
    r"obv",
    r"vwap",
    r"orderbook_(\w+)",
    r"funding_rate",
    r"open_interest",
    r"spread",
    r"trade_flow",
    r"whale_activity",
    r"liquidations",
]

# Transform patterns
TRANSFORM_PATTERNS = {
    r"zscore\((.+)\)": TransformType.ZSCORE,
    r"ema\((.+),\s*(\d+)\)": TransformType.EMA,
    r"sma\((.+),\s*(\d+)\)": TransformType.SMA,
    r"rolling_mean\((.+),\s*(\d+)\)": TransformType.ROLLING_MEAN,
    r"rolling_std\((.+),\s*(\d+)\)": TransformType.ROLLING_STD,
    r"lag\((.+),\s*(\d+)\)": TransformType.LAG,
    r"diff\((.+)\)": TransformType.DIFF,
    r"percentile\((.+),\s*(\d+)\)": TransformType.PERCENTILE,
    r"rank\((.+)\)": TransformType.RANK,
    r"log\((.+)\)": TransformType.LOG,
    r"abs\((.+)\)": TransformType.ABS,
    r"sign\((.+)\)": TransformType.SIGN,
    r"normalize\((.+)\)": TransformType.NORMALIZE,
}


class DagBuilder:
    """
    Builds computational DAG from approved factors.
    """
    
    def __init__(self):
        self.nodes: Dict[str, DagNode] = {}
        self.edges: Dict[str, DagEdge] = {}
        
        # Tracking
        self.feature_nodes: Set[str] = set()
        self.transform_nodes: Set[str] = set()
        self.factor_nodes: Set[str] = set()
        
        # Deduplication
        self.signature_to_node: Dict[str, str] = {}
    
    def reset(self):
        """Reset builder state."""
        self.nodes = {}
        self.edges = {}
        self.feature_nodes = set()
        self.transform_nodes = set()
        self.factor_nodes = set()
        self.signature_to_node = {}
    
    def _generate_node_id(self, operation: str, inputs: List[str], params: Dict = None) -> str:
        """Generate unique node ID based on operation and inputs."""
        sig_data = {
            "operation": operation,
            "inputs": sorted(inputs),
            "params": params or {}
        }
        return hashlib.md5(str(sig_data).encode()).hexdigest()[:12]
    
    def _generate_edge_id(self, source: str, target: str) -> str:
        """Generate unique edge ID."""
        return hashlib.md5(f"{source}:{target}".encode()).hexdigest()[:10]
    
    def add_feature_node(
        self,
        feature_id: str,
        operation: str = None,
        params: Dict = None
    ) -> DagNode:
        """
        Add a feature node (base market data).
        """
        operation = operation or feature_id
        node_id = self._generate_node_id(operation, [], params)
        
        # Check for existing
        if node_id in self.nodes:
            return self.nodes[node_id]
        
        node = DagNode(
            node_id=node_id,
            node_type=NodeType.FEATURE,
            operation=operation,
            params=params or {},
            inputs=[],
            outputs=[],
            cost=NODE_COST[NodeType.FEATURE],
            latency_estimate=NODE_LATENCY[NodeType.FEATURE],
            level=0,  # Features are level 0
            cacheable=True,
            source_feature_id=feature_id,
            created_at=datetime.now(timezone.utc)
        )
        
        self.nodes[node_id] = node
        self.feature_nodes.add(node_id)
        
        return node
    
    def add_transform_node(
        self,
        transform_type: TransformType,
        input_node_ids: List[str],
        params: Dict = None
    ) -> Optional[DagNode]:
        """
        Add a transform node.
        """
        params = params or {}
        node_id = self._generate_node_id(transform_type.value, input_node_ids, params)
        
        # Check signature for deduplication
        signature = f"{transform_type.value}:{sorted(input_node_ids)}:{params}"
        if signature in self.signature_to_node:
            existing_id = self.signature_to_node[signature]
            return self.nodes.get(existing_id)
        
        # Check for existing
        if node_id in self.nodes:
            return self.nodes[node_id]
        
        # Verify inputs exist
        for inp_id in input_node_ids:
            if inp_id not in self.nodes:
                return None
        
        cost = TRANSFORM_COST.get(transform_type, 1.0)
        
        node = DagNode(
            node_id=node_id,
            node_type=NodeType.TRANSFORM,
            operation=transform_type.value,
            params=params,
            inputs=input_node_ids,
            outputs=[],
            cost=cost,
            latency_estimate=cost * 0.5,
            cacheable=True,
            created_at=datetime.now(timezone.utc)
        )
        
        self.nodes[node_id] = node
        self.transform_nodes.add(node_id)
        self.signature_to_node[signature] = node_id
        
        # Create edges from inputs to this node
        for inp_id in input_node_ids:
            self._add_edge(inp_id, node_id)
            self.nodes[inp_id].outputs.append(node_id)
        
        return node
    
    def add_factor_node(
        self,
        factor_id: str,
        input_node_ids: List[str],
        operation: str = None
    ) -> Optional[DagNode]:
        """
        Add a factor node (final computed factor).
        """
        operation = operation or factor_id
        node_id = self._generate_node_id(f"factor:{operation}", input_node_ids)
        
        # Check for existing
        if node_id in self.nodes:
            return self.nodes[node_id]
        
        # Verify inputs exist
        for inp_id in input_node_ids:
            if inp_id not in self.nodes:
                return None
        
        node = DagNode(
            node_id=node_id,
            node_type=NodeType.FACTOR,
            operation=operation,
            inputs=input_node_ids,
            outputs=[],
            cost=NODE_COST[NodeType.FACTOR],
            latency_estimate=NODE_LATENCY[NodeType.FACTOR],
            cacheable=True,
            source_factor_id=factor_id,
            created_at=datetime.now(timezone.utc)
        )
        
        self.nodes[node_id] = node
        self.factor_nodes.add(node_id)
        
        # Create edges from inputs to this node
        for inp_id in input_node_ids:
            self._add_edge(inp_id, node_id)
            self.nodes[inp_id].outputs.append(node_id)
        
        return node
    
    def _add_edge(self, source: str, target: str) -> DagEdge:
        """Add edge between nodes."""
        edge_id = self._generate_edge_id(source, target)
        
        if edge_id in self.edges:
            return self.edges[edge_id]
        
        edge = DagEdge(
            edge_id=edge_id,
            source_node=source,
            target_node=target,
            created_at=datetime.now(timezone.utc)
        )
        
        self.edges[edge_id] = edge
        return edge
    
    def build_from_factors(self, factors: List[Dict], rankings: Dict[str, Dict] = None) -> Dict:
        """
        Build DAG from approved factors.
        
        Args:
            factors: List of factor dictionaries
            rankings: Optional ranking info by factor_id
        
        Returns:
            Build statistics
        """
        rankings = rankings or {}
        
        # Track all features used
        all_features: Set[str] = set()
        all_transforms: List[Tuple[str, List[str], Dict]] = []
        
        # Parse factors
        for factor in factors:
            factor_id = factor.get("factor_id", "")
            inputs = factor.get("inputs", [])
            transforms = factor.get("transforms", [])
            
            # Collect features
            all_features.update(inputs)
            
            # Collect transforms
            for transform in transforms:
                all_transforms.append((transform, inputs, factor.get("params", {})))
        
        # Step 1: Add feature nodes
        feature_node_map: Dict[str, str] = {}
        for feature_name in all_features:
            node = self.add_feature_node(feature_name)
            feature_node_map[feature_name] = node.node_id
        
        # Step 2: Add transform nodes
        transform_node_map: Dict[str, str] = {}
        for transform_name, inputs, params in all_transforms:
            # Parse transform
            transform_type = self._parse_transform(transform_name)
            if transform_type:
                # Get input node IDs
                input_node_ids = [feature_node_map.get(inp) for inp in inputs if inp in feature_node_map]
                input_node_ids = [i for i in input_node_ids if i]  # Filter None
                
                if input_node_ids:
                    node = self.add_transform_node(transform_type, input_node_ids, params)
                    if node:
                        key = f"{transform_name}:{sorted(inputs)}"
                        transform_node_map[key] = node.node_id
        
        # Step 3: Add factor nodes
        for factor in factors:
            factor_id = factor.get("factor_id", "")
            inputs = factor.get("inputs", [])
            transforms = factor.get("transforms", [])
            
            # Get input nodes for this factor
            input_node_ids = []
            
            # From features
            for inp in inputs:
                if inp in feature_node_map:
                    input_node_ids.append(feature_node_map[inp])
            
            # From transforms
            for transform in transforms:
                key = f"{transform}:{sorted(inputs)}"
                if key in transform_node_map:
                    input_node_ids.append(transform_node_map[key])
            
            if input_node_ids:
                self.add_factor_node(factor_id, input_node_ids, factor.get("operation", factor_id))
        
        # Step 4: Detect cycles
        self._detect_cycles()
        
        return {
            "features": len(self.feature_nodes),
            "transforms": len(self.transform_nodes),
            "factors": len(self.factor_nodes),
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges)
        }
    
    def _parse_transform(self, transform_name: str) -> Optional[TransformType]:
        """Parse transform string to TransformType."""
        transform_name = transform_name.lower().strip()
        
        # Direct mapping
        try:
            return TransformType(transform_name)
        except ValueError:
            pass
        
        # Pattern matching
        for pattern, transform_type in TRANSFORM_PATTERNS.items():
            if re.match(pattern, transform_name):
                return transform_type
        
        # Common aliases
        aliases = {
            "z_score": TransformType.ZSCORE,
            "z-score": TransformType.ZSCORE,
            "exponential_ma": TransformType.EMA,
            "simple_ma": TransformType.SMA,
            "mean": TransformType.ROLLING_MEAN,
            "std": TransformType.ROLLING_STD,
            "standard_deviation": TransformType.ROLLING_STD,
            "absolute": TransformType.ABS,
            "logarithm": TransformType.LOG,
        }
        
        return aliases.get(transform_name)
    
    def _detect_cycles(self):
        """
        Detect cycles in the DAG using DFS.
        Raises DagCycleError if cycle is found.
        """
        WHITE = 0  # Not visited
        GRAY = 1   # In current path
        BLACK = 2  # Completely processed
        
        color = {node_id: WHITE for node_id in self.nodes}
        
        def dfs(node_id: str, path: List[str]) -> bool:
            color[node_id] = GRAY
            
            node = self.nodes[node_id]
            for output_id in node.outputs:
                if color[output_id] == GRAY:
                    # Cycle detected
                    cycle_path = path + [node_id, output_id]
                    raise DagCycleError(f"Cycle detected: {' -> '.join(cycle_path)}")
                
                if color[output_id] == WHITE:
                    dfs(output_id, path + [node_id])
            
            color[node_id] = BLACK
            return True
        
        for node_id in self.nodes:
            if color[node_id] == WHITE:
                dfs(node_id, [])
    
    def get_nodes(self) -> List[DagNode]:
        """Get all nodes."""
        return list(self.nodes.values())
    
    def get_edges(self) -> List[DagEdge]:
        """Get all edges."""
        return list(self.edges.values())
    
    def get_stats(self) -> Dict:
        """Get builder statistics."""
        total_cost = sum(n.cost for n in self.nodes.values())
        total_latency = sum(n.latency_estimate for n in self.nodes.values())
        
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "feature_nodes": len(self.feature_nodes),
            "transform_nodes": len(self.transform_nodes),
            "factor_nodes": len(self.factor_nodes),
            "total_cost": total_cost,
            "estimated_latency_ms": total_latency,
            "deduplication_count": len(self.signature_to_node)
        }
