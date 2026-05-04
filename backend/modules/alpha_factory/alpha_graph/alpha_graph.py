"""
PHASE 13.5 - Alpha Graph
=========================
Main Alpha Graph orchestrator.

Combines:
- GraphBuilder (creates nodes/edges)
- GraphReasoner (evaluates coherence)
- Repository (persistence)
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from .alpha_graph_types import (
    GraphNode, GraphEdge, RelationType, 
    GraphSnapshot, CoherenceResult
)
from .alpha_graph_builder import GraphBuilder
from .alpha_graph_reasoner import GraphReasoner
from .alpha_graph_repository import GraphRepository

# Import ranker repository
try:
    from modules.alpha_factory.factor_ranker.ranker_repository import RankerRepository
    RANKER_OK = True
except ImportError:
    RANKER_OK = False
    RankerRepository = None

# Import factor repository
try:
    from modules.alpha_factory.factor_generator.factor_repository import FactorRepository
    FACTOR_OK = True
except ImportError:
    FACTOR_OK = False
    FactorRepository = None


class BuildResult:
    """Result of graph build operation."""
    
    def __init__(self):
        self.build_id = str(uuid.uuid4())[:8]
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.duration_seconds: float = 0.0
        
        self.nodes_created: int = 0
        self.edges_created: int = 0
        self.edges_by_type: Dict[str, int] = {}
        
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
            "edges_by_type": self.edges_by_type,
            "status": self.status,
            "error_message": self.error_message
        }


class AlphaGraph:
    """
    Main Alpha Graph orchestrator.
    
    Provides:
    - Build graph from approved factors
    - Evaluate signal coherence
    - Query nodes and edges
    """
    
    def __init__(self):
        self.builder = GraphBuilder()
        self.reasoner = GraphReasoner()
        self.repository = GraphRepository()
        
        # External repositories
        self.ranker_repo = RankerRepository() if RANKER_OK else None
        self.factor_repo = FactorRepository() if FACTOR_OK else None
        
        self.last_build: Optional[BuildResult] = None
        self._loaded = False
    
    def build_graph(
        self,
        clear_existing: bool = True
    ) -> BuildResult:
        """
        Build the Alpha Graph from approved factors.
        
        Args:
            clear_existing: Clear existing graph before building
        
        Returns:
            BuildResult with stats
        """
        result = BuildResult()
        result.started_at = datetime.now(timezone.utc)
        result.status = "running"
        
        try:
            # Clear if requested
            if clear_existing:
                self.repository.clear_graph()
                self.builder.reset()
            
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
                            # Use ranking data as factor
                            approved_factors.append(ranking)
                    else:
                        approved_factors.append(ranking)
            
            if not approved_factors:
                raise ValueError("No approved factors found")
            
            # Add nodes
            for factor in approved_factors:
                factor_id = factor.get("factor_id", "")
                ranking = rankings.get(factor_id, {})
                self.builder.add_node(factor, ranking)
            
            result.nodes_created = len(self.builder.nodes)
            
            # Build edges
            edge_results = self.builder.build_all_edges()
            result.edges_created = edge_results.get("total", 0)
            result.edges_by_type = {
                "family": edge_results.get("family_edges", 0),
                "input_overlap": edge_results.get("input_overlap_edges", 0),
                "regime": edge_results.get("regime_edges", 0),
                "template": edge_results.get("template_edges", 0)
            }
            
            # Count by relation type
            for rt in RelationType:
                count = len(self.builder.get_edges_by_type(rt))
                result.edges_by_type[rt.value] = count
            
            # Save to repository
            for node in self.builder.get_nodes():
                self.repository.save_node(node)
            
            for edge in self.builder.get_edges():
                self.repository.save_edge(edge)
            
            # Create snapshot
            snapshot = self._create_snapshot()
            self.repository.save_snapshot(snapshot)
            
            # Load into reasoner
            self.reasoner.load_graph(
                self.builder.get_nodes(),
                self.builder.get_edges()
            )
            self._loaded = True
            
            result.status = "completed"
            
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
        
        result.finished_at = datetime.now(timezone.utc)
        result.duration_seconds = (result.finished_at - result.started_at).total_seconds()
        
        self.last_build = result
        return result
    
    def _create_snapshot(self) -> GraphSnapshot:
        """Create a snapshot of current graph state."""
        stats = self.builder.get_stats()
        
        snapshot = GraphSnapshot(
            snapshot_id=str(uuid.uuid4())[:8],
            total_nodes=stats["total_nodes"],
            total_edges=stats["total_edges"],
            supports_count=stats["edges_by_type"].get("supports", 0),
            amplifies_count=stats["edges_by_type"].get("amplifies", 0),
            contradicts_count=stats["edges_by_type"].get("contradicts", 0),
            conditional_count=stats["edges_by_type"].get("conditional_on", 0),
            invalidates_count=stats["edges_by_type"].get("invalidates", 0),
            nodes_by_family=stats["nodes_by_family"],
            created_at=datetime.now(timezone.utc)
        )
        
        return snapshot
    
    def load_graph(self):
        """
        Load graph from repository.
        """
        if self._loaded:
            return
        
        nodes = self.repository.get_nodes(limit=500)
        edges = self.repository.get_edges(limit=5000)
        
        if nodes and edges:
            # Rebuild builder state
            self.builder.nodes = {n.node_id: n for n in nodes}
            self.builder.edges = {e.edge_id: e for e in edges}
            
            # Load into reasoner
            self.reasoner.load_graph(nodes, edges)
            self._loaded = True
    
    def evaluate_coherence(
        self,
        active_factor_ids: List[str]
    ) -> CoherenceResult:
        """
        Evaluate signal coherence for active factors.
        """
        self.load_graph()
        return self.reasoner.evaluate_coherence(active_factor_ids)
    
    def reason(
        self,
        active_factor_ids: List[str]
    ) -> Dict:
        """
        Run reasoning and return result dict.
        """
        result = self.evaluate_coherence(active_factor_ids)
        return result.to_dict()
    
    def get_nodes(
        self,
        family: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get graph nodes.
        """
        nodes = self.repository.get_nodes(family=family, limit=limit)
        return [n.to_dict() for n in nodes]
    
    def get_edges(
        self,
        relation_type: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict]:
        """
        Get graph edges.
        """
        rt = RelationType(relation_type) if relation_type else None
        edges = self.repository.get_edges(relation_type=rt, limit=limit)
        return [e.to_dict() for e in edges]
    
    def get_node_context(self, node_id: str) -> Dict:
        """
        Get context for a node.
        """
        self.load_graph()
        return self.reasoner.get_node_context(node_id)
    
    def get_conflicts(self) -> List[Dict]:
        """
        Get all conflicts in the graph.
        """
        self.load_graph()
        conflicts = self.reasoner.get_conflicts()
        return [{"source": s, "target": t} for s, t in conflicts]
    
    def get_support_network(self, node_id: str) -> Dict:
        """
        Get support network for a node.
        """
        self.load_graph()
        return self.reasoner.get_support_network(node_id)
    
    def get_stats(self) -> Dict:
        """
        Get graph statistics.
        """
        repo_stats = self.repository.get_stats()
        builder_stats = self.builder.get_stats() if self.builder.nodes else {}
        
        return {
            "repository": repo_stats,
            "builder": builder_stats,
            "last_build": self.last_build.to_dict() if self.last_build else None,
            "loaded": self._loaded
        }


# Global singleton
_graph_instance: Optional[AlphaGraph] = None


def get_alpha_graph() -> AlphaGraph:
    """Get singleton graph instance."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = AlphaGraph()
    return _graph_instance
