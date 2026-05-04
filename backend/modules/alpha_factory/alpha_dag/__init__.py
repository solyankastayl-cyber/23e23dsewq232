"""
PHASE 13.6 - Alpha DAG
========================
Computational DAG for efficient factor calculation.

Features:
- DAG Builder: Creates computational graph from factors
- DAG Optimizer: Removes duplicates, merges transforms, applies fusion
- DAG Scheduler: Levelized topological sort for parallel execution
- DAG Executor: Computes factor values (snapshot & streaming modes)
- DAG Cache: Input-hash based caching with TTL

Node Types:
- FEATURE: Base market features (price_return_1m, volume_spike)
- TRANSFORM: Transformations (zscore, ema, rolling_mean)
- FACTOR: Final computed factors

Optimization:
- Duplicate removal
- Transform merging
- Transform fusion (e.g., zscore(rolling_mean) -> rolling_zscore)
- Depth minimization
"""

from .dag_types import (
    DagNode, DagEdge, NodeType, TransformType,
    DagSnapshot, CacheEntry, ExecutionResult,
    DagCycleError, DagExecutionError
)
from .dag_builder import DagBuilder
from .dag_optimizer import DagOptimizer
from .dag_scheduler import DagScheduler
from .dag_executor import DagExecutor, ParallelDagExecutor
from .dag_cache import DagCache, StreamingCache
from .alpha_dag import AlphaDag, get_alpha_dag

__all__ = [
    # Types
    "DagNode",
    "DagEdge",
    "NodeType",
    "TransformType",
    "DagSnapshot",
    "CacheEntry",
    "ExecutionResult",
    "DagCycleError",
    "DagExecutionError",
    # Components
    "DagBuilder",
    "DagOptimizer",
    "DagScheduler",
    "DagExecutor",
    "ParallelDagExecutor",
    "DagCache",
    "StreamingCache",
    # Main
    "AlphaDag",
    "get_alpha_dag"
]
