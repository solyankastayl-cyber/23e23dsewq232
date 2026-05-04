"""
PHASE 13.6 - Alpha DAG Executor
=================================
Executes DAG to compute factor values.

Modes:
1. Snapshot Mode - for backtesting and analysis
2. Streaming Mode - for live trading (tick-by-tick)
"""

from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone
import time
import math

from .dag_types import (
    DagNode, NodeType, TransformType, 
    ExecutionResult, DagExecutionError
)
from .dag_cache import DagCache, StreamingCache
from .dag_scheduler import DagScheduler


# Transform implementations
def _zscore(values: List[float], window: int = 20) -> float:
    """Compute z-score of last value."""
    if len(values) < 2:
        return 0.0
    recent = values[-window:] if len(values) >= window else values
    mean = sum(recent) / len(recent)
    std = (sum((x - mean) ** 2 for x in recent) / len(recent)) ** 0.5
    return (values[-1] - mean) / std if std > 0 else 0.0


def _ema(values: List[float], window: int = 20) -> float:
    """Compute exponential moving average."""
    if not values:
        return 0.0
    alpha = 2 / (window + 1)
    ema = values[0]
    for val in values[1:]:
        ema = alpha * val + (1 - alpha) * ema
    return ema


def _sma(values: List[float], window: int = 20) -> float:
    """Compute simple moving average."""
    if not values:
        return 0.0
    recent = values[-window:] if len(values) >= window else values
    return sum(recent) / len(recent)


def _rolling_mean(values: List[float], window: int = 20) -> float:
    """Compute rolling mean."""
    return _sma(values, window)


def _rolling_std(values: List[float], window: int = 20) -> float:
    """Compute rolling standard deviation."""
    if len(values) < 2:
        return 0.0
    recent = values[-window:] if len(values) >= window else values
    mean = sum(recent) / len(recent)
    return (sum((x - mean) ** 2 for x in recent) / len(recent)) ** 0.5


def _rolling_zscore(values: List[float], window: int = 20) -> float:
    """Compute rolling z-score (fused transform)."""
    return _zscore(values, window)


def _lag(values: List[float], periods: int = 1) -> float:
    """Get lagged value."""
    if len(values) <= periods:
        return 0.0
    return values[-(periods + 1)]


def _diff(values: List[float]) -> float:
    """Compute first difference."""
    if len(values) < 2:
        return 0.0
    return values[-1] - values[-2]


def _percentile(values: List[float], pct: int = 50) -> float:
    """Compute percentile."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * pct / 100)
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


def _rank(values: List[float]) -> float:
    """Compute rank of last value."""
    if not values:
        return 0.0
    last = values[-1]
    return sum(1 for v in values if v <= last) / len(values)


TRANSFORM_FUNCTIONS: Dict[str, Callable] = {
    TransformType.ZSCORE.value: _zscore,
    TransformType.EMA.value: _ema,
    TransformType.SMA.value: _sma,
    TransformType.ROLLING_MEAN.value: _rolling_mean,
    TransformType.ROLLING_STD.value: _rolling_std,
    TransformType.ROLLING_ZSCORE.value: _rolling_zscore,
    TransformType.LAG.value: _lag,
    TransformType.DIFF.value: _diff,
    TransformType.PERCENTILE.value: _percentile,
    TransformType.RANK.value: _rank,
    TransformType.LOG.value: lambda v, **kw: math.log(v[-1]) if v and v[-1] > 0 else 0.0,
    TransformType.ABS.value: lambda v, **kw: abs(v[-1]) if v else 0.0,
    TransformType.SIGN.value: lambda v, **kw: (1 if v[-1] > 0 else -1 if v[-1] < 0 else 0) if v else 0,
    TransformType.NORMALIZE.value: lambda v, **kw: v[-1] / max(abs(x) for x in v) if v and max(abs(x) for x in v) > 0 else 0.0,
}


class DagExecutor:
    """
    Executes DAG to compute factor values.
    """
    
    def __init__(
        self,
        nodes: Dict[str, DagNode],
        scheduler: DagScheduler,
        cache: Optional[DagCache] = None
    ):
        """
        Initialize executor.
        
        Args:
            nodes: DAG nodes
            scheduler: Scheduler with execution order
            cache: Optional cache for computed values
        """
        self.nodes = nodes
        self.scheduler = scheduler
        self.cache = cache or DagCache()
        
        # Build dependency map for cache invalidation
        self.dependencies: Dict[str, List[str]] = {}
        for node in nodes.values():
            for out in node.outputs:
                if node.node_id not in self.dependencies:
                    self.dependencies[node.node_id] = []
                self.dependencies[node.node_id].append(out)
    
    def execute(self, snapshot: Dict[str, Any]) -> ExecutionResult:
        """
        Execute DAG on a market snapshot.
        
        Snapshot Mode - processes all data at once.
        
        Args:
            snapshot: Market data snapshot containing feature values
                      e.g., {"price_return_1m": [0.01, 0.02, ...], ...}
        
        Returns:
            ExecutionResult with factor values
        """
        result = ExecutionResult()
        start_time = time.time()
        
        # Node values storage
        node_values: Dict[str, Any] = {}
        
        try:
            # Execute in scheduled order
            for node_id in self.scheduler.get_execution_order():
                if node_id not in self.nodes:
                    continue
                
                node = self.nodes[node_id]
                
                # Get input values for this node
                input_values = self._get_input_values(node, snapshot, node_values)
                
                # Check cache
                if node.cacheable:
                    cached = self.cache.get(node_id, input_values)
                    if cached is not None:
                        node_values[node_id] = cached
                        result.cache_hits += 1
                        continue
                
                result.cache_misses += 1
                
                # Compute value
                value = self._compute_node(node, input_values, snapshot, node_values)
                node_values[node_id] = value
                result.nodes_computed += 1
                
                # Cache result
                if node.cacheable:
                    self.cache.set(node_id, input_values, value)
            
            # Extract factor values
            for node_id, node in self.nodes.items():
                if node.node_type == NodeType.FACTOR:
                    factor_id = node.source_factor_id or node_id
                    result.factor_values[factor_id] = node_values.get(node_id, 0.0)
        
        except Exception as e:
            result.errors.append(str(e))
        
        result.execution_time_ms = (time.time() - start_time) * 1000
        return result
    
    def execute_stream(
        self,
        market_tick: Dict[str, float],
        history: Dict[str, List[float]]
    ) -> ExecutionResult:
        """
        Execute DAG on a streaming market tick.
        
        Streaming Mode - processes one tick at a time.
        Optimized for high-frequency updates.
        
        Args:
            market_tick: Current tick values {"price": 100.5, "volume": 1000, ...}
            history: Historical values for rolling calculations
        
        Returns:
            ExecutionResult with factor values
        """
        # Build snapshot from tick + history
        snapshot = {}
        for key, value in market_tick.items():
            if key in history:
                snapshot[key] = history[key] + [value]
            else:
                snapshot[key] = [value]
        
        # Record tick in streaming cache
        if isinstance(self.cache, StreamingCache):
            self.cache.record_tick()
        
        return self.execute(snapshot)
    
    def _get_input_values(
        self,
        node: DagNode,
        snapshot: Dict[str, Any],
        node_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get input values for a node."""
        inputs = {}
        
        if node.node_type == NodeType.FEATURE:
            # Feature nodes get values from snapshot
            feature_key = node.operation
            if feature_key in snapshot:
                inputs["values"] = snapshot[feature_key]
        else:
            # Transform/Factor nodes get values from dependencies
            for inp_id in node.inputs:
                if inp_id in node_values:
                    inputs[inp_id] = node_values[inp_id]
        
        return inputs
    
    def _compute_node(
        self,
        node: DagNode,
        input_values: Dict[str, Any],
        snapshot: Dict[str, Any],
        node_values: Dict[str, Any]
    ) -> float:
        """Compute value for a single node."""
        
        if node.node_type == NodeType.FEATURE:
            # Feature: return last value from snapshot
            values = input_values.get("values", [])
            return values[-1] if values else 0.0
        
        elif node.node_type == NodeType.TRANSFORM:
            # Transform: apply transform function
            return self._apply_transform(node, input_values, snapshot, node_values)
        
        elif node.node_type == NodeType.FACTOR:
            # Factor: combine inputs
            return self._compute_factor(node, input_values, node_values)
        
        return 0.0
    
    def _apply_transform(
        self,
        node: DagNode,
        input_values: Dict[str, Any],
        snapshot: Dict[str, Any],
        node_values: Dict[str, Any]
    ) -> float:
        """Apply a transform operation."""
        transform_func = TRANSFORM_FUNCTIONS.get(node.operation)
        
        if not transform_func:
            return 0.0
        
        # Get values to transform
        values = []
        for inp_id in node.inputs:
            inp_node = self.nodes.get(inp_id)
            if inp_node and inp_node.node_type == NodeType.FEATURE:
                # Get full history from snapshot
                feature_key = inp_node.operation
                if feature_key in snapshot:
                    values = snapshot[feature_key]
                    break
            else:
                # Get computed value
                val = node_values.get(inp_id, 0.0)
                if isinstance(val, list):
                    values = val
                else:
                    values = [val]
        
        if not values:
            return 0.0
        
        # Apply transform with params
        params = node.params or {}
        try:
            return transform_func(values, **params)
        except Exception:
            return 0.0
    
    def _compute_factor(
        self,
        node: DagNode,
        input_values: Dict[str, Any],
        node_values: Dict[str, Any]
    ) -> float:
        """Compute factor value from inputs."""
        # Default: weighted average of inputs
        values = []
        for inp_id in node.inputs:
            val = node_values.get(inp_id, 0.0)
            if isinstance(val, (int, float)):
                values.append(val)
        
        if not values:
            return 0.0
        
        # Simple aggregation - can be extended
        operation = node.operation.lower()
        
        if "momentum" in operation:
            # Momentum: positive bias
            return sum(values) / len(values)
        elif "breakout" in operation:
            # Breakout: max signal
            return max(values)
        elif "reversal" in operation:
            # Reversal: negative of momentum
            return -sum(values) / len(values)
        else:
            # Default: average
            return sum(values) / len(values)
    
    def get_execution_stats(self) -> Dict:
        """Get execution statistics."""
        return {
            "total_nodes": len(self.nodes),
            "scheduled_nodes": len(self.scheduler.get_execution_order()),
            "depth": self.scheduler.depth,
            "cache_stats": self.cache.get_stats(),
            "estimated_time_parallel_ms": self.scheduler.estimate_total_time(parallel=True),
            "estimated_time_sequential_ms": self.scheduler.estimate_total_time(parallel=False)
        }


class ParallelDagExecutor(DagExecutor):
    """
    DAG Executor with parallel level execution.
    
    Executes nodes within each level in parallel.
    Note: For production use with concurrent.futures or asyncio.
    """
    
    def execute_parallel(self, snapshot: Dict[str, Any]) -> ExecutionResult:
        """
        Execute DAG with parallel level processing.
        
        In production, this would use threading or asyncio.
        Here we simulate the timing benefits.
        """
        result = ExecutionResult()
        start_time = time.time()
        
        node_values: Dict[str, Any] = {}
        
        try:
            # Execute level by level
            for level in self.scheduler.get_levels():
                level_values = {}
                
                # Process level (would be parallel in production)
                for node_id in level:
                    if node_id not in self.nodes:
                        continue
                    
                    node = self.nodes[node_id]
                    input_values = self._get_input_values(node, snapshot, node_values)
                    
                    # Check cache
                    if node.cacheable:
                        cached = self.cache.get(node_id, input_values)
                        if cached is not None:
                            level_values[node_id] = cached
                            result.cache_hits += 1
                            continue
                    
                    result.cache_misses += 1
                    
                    # Compute
                    value = self._compute_node(node, input_values, snapshot, node_values)
                    level_values[node_id] = value
                    result.nodes_computed += 1
                    
                    if node.cacheable:
                        self.cache.set(node_id, input_values, value)
                
                # Merge level values
                node_values.update(level_values)
            
            # Extract factors
            for node_id, node in self.nodes.items():
                if node.node_type == NodeType.FACTOR:
                    factor_id = node.source_factor_id or node_id
                    result.factor_values[factor_id] = node_values.get(node_id, 0.0)
        
        except Exception as e:
            result.errors.append(str(e))
        
        result.execution_time_ms = (time.time() - start_time) * 1000
        return result
