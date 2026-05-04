"""
PHASE 13.6 - Alpha DAG Types
==============================
Core data types for computational DAG.

Node Types:
- FEATURE_NODE: base features (price_return_1m, volume_spike)
- TRANSFORM_NODE: transformations (zscore, ema, rolling_mean)
- FACTOR_NODE: final factors (momentum_factor, breakout_factor)
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json


class NodeType(str, Enum):
    """Types of DAG nodes."""
    FEATURE = "feature"       # Base market features
    TRANSFORM = "transform"   # Transformations applied to features
    FACTOR = "factor"         # Final computed factors


class TransformType(str, Enum):
    """Available transform operations."""
    ZSCORE = "zscore"
    EMA = "ema"
    SMA = "sma"
    ROLLING_MEAN = "rolling_mean"
    ROLLING_STD = "rolling_std"
    ROLLING_ZSCORE = "rolling_zscore"  # Fused transform
    LAG = "lag"
    DIFF = "diff"
    PERCENTILE = "percentile"
    RANK = "rank"
    LOG = "log"
    ABS = "abs"
    SIGN = "sign"
    CLIP = "clip"
    NORMALIZE = "normalize"
    THRESHOLD = "threshold"


# Cost model for different node types
NODE_COST = {
    NodeType.FEATURE: 1.0,
    NodeType.TRANSFORM: 2.0,
    NodeType.FACTOR: 3.0,
}

# Latency estimates (ms)
NODE_LATENCY = {
    NodeType.FEATURE: 0.1,
    NodeType.TRANSFORM: 0.5,
    NodeType.FACTOR: 1.0,
}

# Transform-specific costs
TRANSFORM_COST = {
    TransformType.ZSCORE: 1.5,
    TransformType.EMA: 1.0,
    TransformType.SMA: 1.0,
    TransformType.ROLLING_MEAN: 2.0,
    TransformType.ROLLING_STD: 2.5,
    TransformType.ROLLING_ZSCORE: 3.0,
    TransformType.LAG: 0.5,
    TransformType.DIFF: 0.5,
    TransformType.PERCENTILE: 2.0,
    TransformType.RANK: 1.5,
    TransformType.LOG: 0.3,
    TransformType.ABS: 0.2,
    TransformType.SIGN: 0.2,
    TransformType.CLIP: 0.3,
    TransformType.NORMALIZE: 1.0,
    TransformType.THRESHOLD: 0.3,
}


@dataclass
class DagNode:
    """
    Node in the computational DAG.
    """
    node_id: str
    node_type: NodeType
    
    # Operation info
    operation: str = ""           # e.g., "zscore", "ema", "momentum_factor"
    params: Dict[str, Any] = field(default_factory=dict)  # e.g., {"window": 20}
    
    # Dependencies
    inputs: List[str] = field(default_factory=list)   # Input node IDs
    outputs: List[str] = field(default_factory=list)  # Output node IDs
    
    # Cost model
    cost: float = 1.0
    latency_estimate: float = 0.1  # ms
    
    # Execution metadata
    level: int = 0                # DAG level for parallel execution
    execution_order: int = 0      # Order in topological sort
    cacheable: bool = True        # Can be cached
    
    # Source tracking
    source_feature_id: Optional[str] = None
    source_factor_id: Optional[str] = None
    
    # Metadata
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value if isinstance(self.node_type, NodeType) else self.node_type,
            "operation": self.operation,
            "params": self.params,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "cost": self.cost,
            "latency_estimate": self.latency_estimate,
            "level": self.level,
            "execution_order": self.execution_order,
            "cacheable": self.cacheable,
            "source_feature_id": self.source_feature_id,
            "source_factor_id": self.source_factor_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DagNode":
        node_type = data.get("node_type", "feature")
        if isinstance(node_type, str):
            node_type = NodeType(node_type)
        
        return cls(
            node_id=data["node_id"],
            node_type=node_type,
            operation=data.get("operation", ""),
            params=data.get("params", {}),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            cost=data.get("cost", 1.0),
            latency_estimate=data.get("latency_estimate", 0.1),
            level=data.get("level", 0),
            execution_order=data.get("execution_order", 0),
            cacheable=data.get("cacheable", True),
            source_feature_id=data.get("source_feature_id"),
            source_factor_id=data.get("source_factor_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )
    
    def get_input_signature(self) -> str:
        """Generate a signature based on inputs and operation."""
        sig_data = {
            "operation": self.operation,
            "params": self.params,
            "inputs": sorted(self.inputs)
        }
        return hashlib.md5(json.dumps(sig_data, sort_keys=True).encode()).hexdigest()[:12]


@dataclass
class DagEdge:
    """
    Edge in the computational DAG.
    """
    edge_id: str
    source_node: str
    target_node: str
    
    # Metadata
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "edge_id": self.edge_id,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DagEdge":
        return cls(
            edge_id=data["edge_id"],
            source_node=data["source_node"],
            target_node=data["target_node"],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )


@dataclass
class CacheEntry:
    """
    Cache entry for DAG node values.
    """
    node_id: str
    input_hash: str       # Hash of input values
    value: Any            # Cached computed value
    timestamp: datetime   # When cached
    hits: int = 0         # Cache hit count
    
    def is_valid(self, current_input_hash: str) -> bool:
        """Check if cache entry is still valid."""
        return self.input_hash == current_input_hash
    
    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "input_hash": self.input_hash,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "hits": self.hits
        }


@dataclass
class DagSnapshot:
    """
    Snapshot of DAG state.
    """
    snapshot_id: str
    
    # Counts
    total_nodes: int = 0
    total_edges: int = 0
    depth: int = 0
    
    # By type
    feature_nodes: int = 0
    transform_nodes: int = 0
    factor_nodes: int = 0
    
    # Cost
    total_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    
    # Metadata
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "snapshot_id": self.snapshot_id,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "depth": self.depth,
            "nodes_by_type": {
                "feature": self.feature_nodes,
                "transform": self.transform_nodes,
                "factor": self.factor_nodes
            },
            "total_cost": self.total_cost,
            "estimated_latency_ms": self.estimated_latency_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class ExecutionResult:
    """
    Result of DAG execution.
    """
    # Factor values
    factor_values: Dict[str, float] = field(default_factory=dict)
    
    # Execution stats
    execution_time_ms: float = 0.0
    nodes_computed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict:
        return {
            "factor_values": self.factor_values,
            "execution_time_ms": self.execution_time_ms,
            "nodes_computed": self.nodes_computed,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "errors": self.errors
        }


class DagCycleError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass


class DagExecutionError(Exception):
    """Raised when DAG execution fails."""
    pass
