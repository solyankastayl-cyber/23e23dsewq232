"""
PHASE 13.6 - Alpha DAG
========================
Main Alpha DAG orchestrator.

Combines:
- DagBuilder (creates DAG from factors)
- DagOptimizer (optimizes DAG)
- DagScheduler (schedules execution)
- DagExecutor (computes values)
- DagCache (caches results)
- Repository (persistence)
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid

from .dag_types import (
    DagNode, DagEdge, NodeType, DagSnapshot,
    ExecutionResult, DagCycleError
)
from .dag_builder import DagBuilder
from .dag_optimizer import DagOptimizer
from .dag_scheduler import DagScheduler
from .dag_executor import DagExecutor, ParallelDagExecutor
from .dag_cache import DagCache, StreamingCache
from .dag_repository import DagRepository


# Import factor repository
try:
    from modules.alpha_factory.factor_generator.factor_repository import FactorRepository
    FACTOR_OK = True
except ImportError:
    FACTOR_OK = False
    FactorRepository = None

# Import ranker repository
try:
    from modules.alpha_factory.factor_ranker.ranker_repository import RankerRepository
    RANKER_OK = True
except ImportError:
    RANKER_OK = False
    RankerRepository = None


class BuildResult:
    """Result of DAG build operation."""
    
    def __init__(self):
        self.build_id = str(uuid.uuid4())[:8]
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.duration_seconds: float = 0.0
        
        # Counts
        self.nodes_created: int = 0
        self.edges_created: int = 0
        self.depth: int = 0
        
        # By type
        self.feature_nodes: int = 0
        self.transform_nodes: int = 0
        self.factor_nodes: int = 0
        
        # Optimization
        self.optimization_stats: Dict = {}
        
        # Scheduling
        self.scheduling_stats: Dict = {}
        
        self.status: str = "pending"
        self.error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "build_id": self.build_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "nodes_created": self.nodes_created,
            "edges_created": self.edges_created,
            "depth": self.depth,
            "nodes_by_type": {
                "feature": self.feature_nodes,
                "transform": self.transform_nodes,
                "factor": self.factor_nodes
            },
            "optimization": self.optimization_stats,
            "scheduling": self.scheduling_stats,
            "status": self.status,
            "error_message": self.error_message
        }


class AlphaDag:
    """
    Main Alpha DAG orchestrator.
    
    Provides:
    - Build DAG from approved factors
    - Execute DAG on market snapshots
    - Query nodes and edges
    """
    
    def __init__(self):
        self.builder = DagBuilder()
        self.repository = DagRepository()
        self.cache = StreamingCache(max_size=10000, ttl_seconds=60.0)
        
        # External repositories
        self.factor_repo = FactorRepository() if FACTOR_OK else None
        self.ranker_repo = RankerRepository() if RANKER_OK else None
        
        # Components (initialized after build)
        self.optimizer: Optional[DagOptimizer] = None
        self.scheduler: Optional[DagScheduler] = None
        self.executor: Optional[DagExecutor] = None
        
        self.last_build: Optional[BuildResult] = None
        self._loaded = False
    
    def build_dag(self, clear_existing: bool = True) -> BuildResult:
        """
        Build the computational DAG from approved factors.
        
        Args:
            clear_existing: Clear existing DAG before building
        
        Returns:
            BuildResult with stats
        """
        result = BuildResult()
        result.started_at = datetime.now(timezone.utc)
        result.status = "running"
        
        try:
            # Clear if requested
            if clear_existing:
                self.repository.clear_dag()
                self.builder.reset()
                self.cache.invalidate_all()
            
            # Load approved factors
            approved_factors = []
            rankings = {}
            
            if self.ranker_repo and self.ranker_repo.connected:
                approved_rankings = self.ranker_repo.get_rankings(
                    approved_only=True,
                    limit=500
                )
                
                for ranking in approved_rankings:
                    factor_id = ranking.get("factor_id")
                    rankings[factor_id] = ranking
                    
                    # Get factor details
                    if self.factor_repo:
                        factor = self.factor_repo.get_factor(factor_id)
                        if factor:
                            approved_factors.append(factor.to_dict())
                        else:
                            approved_factors.append(ranking)
                    else:
                        approved_factors.append(ranking)
            
            if not approved_factors:
                raise ValueError("No approved factors found")
            
            # Step 1: Build DAG
            build_stats = self.builder.build_from_factors(approved_factors, rankings)
            
            result.feature_nodes = build_stats["features"]
            result.transform_nodes = build_stats["transforms"]
            result.factor_nodes = build_stats["factors"]
            
            # Step 2: Optimize DAG
            self.optimizer = DagOptimizer(
                self.builder.nodes.copy(),
                self.builder.edges.copy()
            )
            result.optimization_stats = self.optimizer.optimize()
            
            # Update with optimized data
            optimized_nodes = self.optimizer.get_nodes()
            optimized_edges = self.optimizer.get_edges()
            
            # Step 3: Schedule DAG
            self.scheduler = DagScheduler(optimized_nodes, optimized_edges)
            result.scheduling_stats = self.scheduler.schedule()
            result.depth = self.scheduler.depth
            
            # Step 4: Create executor
            self.executor = ParallelDagExecutor(
                optimized_nodes,
                self.scheduler,
                self.cache
            )
            
            result.nodes_created = len(optimized_nodes)
            result.edges_created = len(optimized_edges)
            
            # Update node counts after optimization
            result.feature_nodes = sum(
                1 for n in optimized_nodes.values() 
                if n.node_type == NodeType.FEATURE
            )
            result.transform_nodes = sum(
                1 for n in optimized_nodes.values() 
                if n.node_type == NodeType.TRANSFORM
            )
            result.factor_nodes = sum(
                1 for n in optimized_nodes.values() 
                if n.node_type == NodeType.FACTOR
            )
            
            # Save to repository
            self.repository.save_nodes_bulk(list(optimized_nodes.values()))
            self.repository.save_edges_bulk(list(optimized_edges.values()))
            
            # Create snapshot
            snapshot = self._create_snapshot(result)
            self.repository.save_snapshot(snapshot)
            
            self._loaded = True
            result.status = "completed"
            
        except DagCycleError as e:
            result.status = "failed"
            result.error_message = f"Cycle detected: {e}"
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
        
        result.finished_at = datetime.now(timezone.utc)
        result.duration_seconds = (result.finished_at - result.started_at).total_seconds()
        
        self.last_build = result
        return result
    
    def _create_snapshot(self, build_result: BuildResult) -> DagSnapshot:
        """Create a snapshot of current DAG state."""
        return DagSnapshot(
            snapshot_id=build_result.build_id,
            total_nodes=build_result.nodes_created,
            total_edges=build_result.edges_created,
            depth=build_result.depth,
            feature_nodes=build_result.feature_nodes,
            transform_nodes=build_result.transform_nodes,
            factor_nodes=build_result.factor_nodes,
            total_cost=sum(n.cost for n in self.optimizer.get_nodes().values()) if self.optimizer else 0,
            estimated_latency_ms=self.scheduler.estimate_total_time(parallel=True) if self.scheduler else 0,
            created_at=datetime.now(timezone.utc)
        )
    
    def load_dag(self):
        """Load DAG from repository."""
        if self._loaded:
            return
        
        nodes = self.repository.get_nodes(limit=1000)
        edges = self.repository.get_edges(limit=2000)
        
        if nodes and edges:
            nodes_dict = {n.node_id: n for n in nodes}
            edges_dict = {e.edge_id: e for e in edges}
            
            self.scheduler = DagScheduler(nodes_dict, edges_dict)
            self.scheduler.schedule()
            
            self.executor = ParallelDagExecutor(
                nodes_dict,
                self.scheduler,
                self.cache
            )
            
            self._loaded = True
    
    def execute(self, snapshot: Dict[str, Any]) -> ExecutionResult:
        """
        Execute DAG on a market snapshot.
        
        Args:
            snapshot: Market data {"price_return_1m": [...], "volume": [...], ...}
        
        Returns:
            ExecutionResult with factor values
        """
        self.load_dag()
        
        if not self.executor:
            return ExecutionResult(errors=["DAG not built"])
        
        return self.executor.execute(snapshot)
    
    def execute_stream(
        self,
        market_tick: Dict[str, float],
        history: Dict[str, List[float]]
    ) -> ExecutionResult:
        """
        Execute DAG on a streaming market tick.
        
        Args:
            market_tick: Current tick {"price": 100.5, "volume": 1000}
            history: Historical values for rolling calculations
        
        Returns:
            ExecutionResult with factor values
        """
        self.load_dag()
        
        if not self.executor:
            return ExecutionResult(errors=["DAG not built"])
        
        return self.executor.execute_stream(market_tick, history)
    
    def get_nodes(
        self,
        node_type: Optional[str] = None,
        level: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get DAG nodes."""
        nt = NodeType(node_type) if node_type else None
        nodes = self.repository.get_nodes(node_type=nt, level=level, limit=limit)
        return [n.to_dict() for n in nodes]
    
    def get_edges(self, limit: int = 500) -> List[Dict]:
        """Get DAG edges."""
        edges = self.repository.get_edges(limit=limit)
        return [e.to_dict() for e in edges]
    
    def get_execution_order(self) -> List[str]:
        """Get scheduled execution order."""
        self.load_dag()
        
        if self.scheduler:
            return self.scheduler.get_execution_order()
        return []
    
    def get_levels(self) -> List[Dict]:
        """Get DAG levels for parallel execution."""
        self.load_dag()
        
        if self.scheduler:
            return self.scheduler.get_parallel_schedule()
        return []
    
    def get_stats(self) -> Dict:
        """Get DAG statistics."""
        repo_stats = self.repository.get_stats()
        cache_stats = self.cache.get_stats()
        
        execution_stats = {}
        if self.executor:
            execution_stats = self.executor.get_execution_stats()
        
        return {
            "repository": repo_stats,
            "cache": cache_stats,
            "execution": execution_stats,
            "last_build": self.last_build.to_dict() if self.last_build else None,
            "loaded": self._loaded
        }


# Global singleton
_dag_instance: Optional[AlphaDag] = None


def get_alpha_dag() -> AlphaDag:
    """Get singleton DAG instance."""
    global _dag_instance
    if _dag_instance is None:
        _dag_instance = AlphaDag()
    return _dag_instance
