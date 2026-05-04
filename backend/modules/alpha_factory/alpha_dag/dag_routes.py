"""
PHASE 13.6 - Alpha DAG Routes
===============================
API endpoints for Alpha DAG.

Endpoints:
- GET  /api/alpha-dag/health
- POST /api/alpha-dag/build
- GET  /api/alpha-dag/nodes
- GET  /api/alpha-dag/edges
- POST /api/alpha-dag/execute
- GET  /api/alpha-dag/execution-order
- GET  /api/alpha-dag/levels
- GET  /api/alpha-dag/snapshots
- GET  /api/alpha-dag/stats
- DELETE /api/alpha-dag/clear
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .alpha_dag import get_alpha_dag, AlphaDag


router = APIRouter(prefix="/api/alpha-dag", tags=["Alpha DAG"])


# ===== Pydantic Models =====

class BuildRequest(BaseModel):
    clear_existing: bool = True


class ExecuteRequest(BaseModel):
    """Market snapshot for DAG execution."""
    snapshot: Dict[str, List[float]] = Field(
        ...,
        description="Market data: feature_name -> list of values"
    )


class StreamExecuteRequest(BaseModel):
    """Streaming tick for DAG execution."""
    tick: Dict[str, float] = Field(
        ...,
        description="Current tick: feature_name -> current value"
    )
    history: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Historical values for rolling calculations"
    )


# ===== Singleton =====

_dag: Optional[AlphaDag] = None


def get_dag() -> AlphaDag:
    global _dag
    if _dag is None:
        _dag = get_alpha_dag()
    return _dag


# ===== Health & Stats =====

@router.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "module": "alpha_dag",
        "version": "phase13.6_alpha_dag",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/stats")
async def get_stats():
    """Get Alpha DAG statistics."""
    dag = get_dag()
    stats = dag.get_stats()
    
    # Add summary for quick view
    repo = stats.get("repository", {})
    cache = stats.get("cache", {})
    
    return {
        "summary": {
            "nodes": repo.get("total_nodes", 0),
            "edges": repo.get("total_edges", 0),
            "depth": repo.get("depth", 0),
            "features": repo.get("nodes_by_type", {}).get("feature", 0),
            "transforms": repo.get("nodes_by_type", {}).get("transform", 0),
            "factors": repo.get("nodes_by_type", {}).get("factor", 0),
            "cache_hit_rate": cache.get("hit_rate", 0.0)
        },
        "full_stats": stats,
        "computed_at": datetime.now(timezone.utc).isoformat()
    }


# ===== Build =====

@router.post("/build")
async def build_dag(request: BuildRequest = None):
    """
    Build the computational DAG from approved factors.
    """
    request = request or BuildRequest()
    
    dag = get_dag()
    result = dag.build_dag(clear_existing=request.clear_existing)
    
    return {
        "status": "completed" if result.status == "completed" else "failed",
        "build": result.to_dict()
    }


# ===== Nodes =====

@router.get("/nodes")
async def get_nodes(
    node_type: Optional[str] = Query(None, description="Filter by type: feature, transform, factor"),
    level: Optional[int] = Query(None, description="Filter by level"),
    limit: int = Query(100, ge=1, le=500)
):
    """Get DAG nodes."""
    dag = get_dag()
    nodes = dag.get_nodes(node_type=node_type, level=level, limit=limit)
    
    return {
        "count": len(nodes),
        "nodes": nodes,
        "filters": {"node_type": node_type, "level": level}
    }


# ===== Edges =====

@router.get("/edges")
async def get_edges(
    limit: int = Query(500, ge=1, le=2000)
):
    """Get DAG edges."""
    dag = get_dag()
    edges = dag.get_edges(limit=limit)
    
    return {
        "count": len(edges),
        "edges": edges
    }


# ===== Execution =====

@router.post("/execute")
async def execute_dag(request: ExecuteRequest):
    """
    Execute DAG on a market snapshot.
    
    Returns computed factor values.
    """
    dag = get_dag()
    
    # Ensure DAG is loaded
    dag.load_dag()
    
    result = dag.execute(request.snapshot)
    
    return {
        "execution": result.to_dict(),
        "factors_computed": len(result.factor_values)
    }


@router.post("/execute-stream")
async def execute_stream(request: StreamExecuteRequest):
    """
    Execute DAG on a streaming market tick.
    
    Optimized for tick-by-tick execution.
    """
    dag = get_dag()
    
    dag.load_dag()
    
    result = dag.execute_stream(request.tick, request.history)
    
    return {
        "execution": result.to_dict(),
        "factors_computed": len(result.factor_values)
    }


# ===== Scheduling =====

@router.get("/execution-order")
async def get_execution_order():
    """Get the scheduled execution order of nodes."""
    dag = get_dag()
    order = dag.get_execution_order()
    
    return {
        "count": len(order),
        "execution_order": order
    }


@router.get("/levels")
async def get_levels():
    """Get DAG levels for parallel execution."""
    dag = get_dag()
    levels = dag.get_levels()
    
    return {
        "count": len(levels),
        "levels": levels,
        "max_parallelism": max((l["count"] for l in levels), default=0) if levels else 0
    }


# ===== Cache =====

@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    dag = get_dag()
    return {
        "cache": dag.cache.get_stats(),
        "top_hits": dag.cache.get_top_hits(10)
    }


@router.post("/cache/clear")
async def clear_cache():
    """Clear the execution cache."""
    dag = get_dag()
    dag.cache.invalidate_all()
    
    return {
        "cleared": True,
        "message": "Cache cleared"
    }


# ===== Snapshots =====

@router.get("/snapshots")
async def get_snapshots(limit: int = Query(10, ge=1, le=50)):
    """Get DAG build snapshots."""
    dag = get_dag()
    snapshots = dag.repository.get_snapshots(limit=limit)
    
    return {
        "count": len(snapshots),
        "snapshots": snapshots
    }


# ===== Clear =====

@router.delete("/clear")
async def clear_dag():
    """Clear the DAG."""
    dag = get_dag()
    result = dag.repository.clear_dag()
    dag.cache.invalidate_all()
    dag._loaded = False
    
    return {
        "cleared": result,
        "message": f"Cleared {result.get('nodes_deleted', 0)} nodes and {result.get('edges_deleted', 0)} edges"
    }


# ===== Node Types =====

@router.get("/node-types")
async def get_node_types():
    """Get available node types."""
    from .dag_types import NodeType, TransformType
    
    dag = get_dag()
    repo_stats = dag.repository.get_stats()
    
    return {
        "node_types": [nt.value for nt in NodeType],
        "transform_types": [tt.value for tt in TransformType],
        "counts": repo_stats.get("nodes_by_type", {})
    }
