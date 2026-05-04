"""
PHASE 13.5 - Alpha Graph Routes
================================
API endpoints for Alpha Graph.

Endpoints:
- GET  /api/alpha-graph/health
- POST /api/alpha-graph/build
- GET  /api/alpha-graph/nodes
- GET  /api/alpha-graph/edges
- POST /api/alpha-graph/reason
- GET  /api/alpha-graph/context/{node_id}
- GET  /api/alpha-graph/conflicts
- GET  /api/alpha-graph/network/{node_id}
- GET  /api/alpha-graph/snapshots
- GET  /api/alpha-graph/stats
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .alpha_graph import get_alpha_graph, AlphaGraph
from .alpha_graph_types import RelationType


router = APIRouter(prefix="/api/alpha-graph", tags=["Alpha Graph"])


# ===== Pydantic Models =====

class BuildRequest(BaseModel):
    clear_existing: bool = True


class ReasonRequest(BaseModel):
    active_factor_ids: List[str] = Field(..., min_items=1)


# ===== Singleton =====

_graph: Optional[AlphaGraph] = None


def get_graph() -> AlphaGraph:
    global _graph
    if _graph is None:
        _graph = get_alpha_graph()
    return _graph


# ===== Health & Stats =====

@router.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "module": "alpha_graph",
        "version": "phase13.5_alpha_graph",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/stats")
async def get_stats():
    """Get Alpha Graph statistics."""
    graph = get_graph()
    return {
        "graph": graph.get_stats(),
        "computed_at": datetime.now(timezone.utc).isoformat()
    }


# ===== Build =====

@router.post("/build")
async def build_graph(request: BuildRequest = None):
    """
    Build the Alpha Graph from approved factors.
    """
    request = request or BuildRequest()
    
    graph = get_graph()
    result = graph.build_graph(clear_existing=request.clear_existing)
    
    return {
        "status": "completed" if result.status == "completed" else "failed",
        "build": result.to_dict()
    }


# ===== Nodes =====

@router.get("/nodes")
async def get_nodes(
    family: Optional[str] = Query(None, description="Filter by family"),
    limit: int = Query(100, ge=1, le=500)
):
    """Get graph nodes."""
    graph = get_graph()
    nodes = graph.get_nodes(family=family, limit=limit)
    
    return {
        "count": len(nodes),
        "nodes": nodes,
        "filters": {"family": family}
    }


# ===== Edges =====

@router.get("/edges")
async def get_edges(
    relation_type: Optional[str] = Query(None, description="Filter by relation type"),
    limit: int = Query(500, ge=1, le=2000)
):
    """Get graph edges."""
    graph = get_graph()
    edges = graph.get_edges(relation_type=relation_type, limit=limit)
    
    return {
        "count": len(edges),
        "edges": edges,
        "filters": {"relation_type": relation_type}
    }


@router.get("/relation-types")
async def get_relation_types():
    """Get available relation types."""
    graph = get_graph()
    repo_stats = graph.repository.get_stats()
    
    return {
        "relation_types": [rt.value for rt in RelationType],
        "counts": repo_stats.get("edges_by_type", {})
    }


# ===== Reasoning =====

@router.post("/reason")
async def reason(request: ReasonRequest):
    """
    Evaluate signal coherence for active factors.
    
    Returns coherence score and analysis.
    """
    graph = get_graph()
    
    # Ensure graph is loaded
    graph.load_graph()
    
    result = graph.reason(request.active_factor_ids)
    
    return {
        "reasoning": result,
        "active_factors_count": len(request.active_factor_ids)
    }


# ===== Context =====

@router.get("/context/{node_id}")
async def get_node_context(node_id: str):
    """Get context for a specific node."""
    graph = get_graph()
    context = graph.get_node_context(node_id)
    
    if not context:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    
    return {
        "context": context
    }


@router.get("/conflicts")
async def get_conflicts():
    """Get all conflicts in the graph."""
    graph = get_graph()
    conflicts = graph.get_conflicts()
    
    return {
        "count": len(conflicts),
        "conflicts": conflicts
    }


@router.get("/network/{node_id}")
async def get_support_network(
    node_id: str,
    depth: int = Query(2, ge=1, le=4)
):
    """Get support network for a node."""
    graph = get_graph()
    network = graph.get_support_network(node_id)
    
    return {
        "network": network
    }


# ===== Snapshots =====

@router.get("/snapshots")
async def get_snapshots(limit: int = Query(10, ge=1, le=50)):
    """Get graph snapshots."""
    graph = get_graph()
    snapshots = graph.repository.get_snapshots(limit=limit)
    
    return {
        "count": len(snapshots),
        "snapshots": snapshots
    }


# ===== Clear =====

@router.delete("/clear")
async def clear_graph():
    """Clear the graph."""
    graph = get_graph()
    result = graph.repository.clear_graph()
    
    return {
        "cleared": result,
        "message": f"Cleared {result.get('nodes_deleted', 0)} nodes and {result.get('edges_deleted', 0)} edges"
    }
