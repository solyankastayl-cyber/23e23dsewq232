"""
Regime Graph Routes

PHASE 36 — Market Regime Graph Engine

API endpoints:
- GET  /api/v1/regime-graph/{symbol}           - Get regime graph state
- GET  /api/v1/regime-graph/next/{symbol}      - Get next state prediction
- GET  /api/v1/regime-graph/path/{symbol}      - Get predicted path
- POST /api/v1/regime-graph/recompute/{symbol} - Recompute graph
- GET  /api/v1/regime-graph/modifier/{symbol}  - Get hypothesis modifier
- GET  /api/v1/regime-graph/summary/{symbol}   - Get summary statistics
- GET  /api/v1/regime-graph/matrix/{symbol}    - Get transition matrix
- GET  /api/v1/regime-graph/health             - Health check
"""

from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException

from .graph_types import (
    RegimeGraphState,
    RegimeGraphModifier,
    RegimeGraphSummary,
    REGIME_GRAPH_WEIGHT,
)
from .graph_engine import get_regime_graph_engine
from .graph_registry import get_regime_graph_registry


router = APIRouter(
    prefix="/api/v1/regime-graph",
    tags=["PHASE 36 - Regime Graph Engine"]
)


# ══════════════════════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def graph_health():
    """Health check for Regime Graph Engine."""
    engine = get_regime_graph_engine()
    registry = get_regime_graph_registry()
    
    # Check MongoDB
    db_connected = registry.collection is not None
    
    # Get symbols with data
    symbols = registry.get_all_symbols() if db_connected else []
    
    return {
        "status": "ok",
        "phase": "PHASE 36",
        "module": "Market Regime Graph Engine",
        "engine_ready": engine is not None,
        "db_connected": db_connected,
        "symbols_tracked": symbols,
        "graph_weight": REGIME_GRAPH_WEIGHT,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ══════════════════════════════════════════════════════════════
# Core Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/{symbol}")
async def get_regime_graph(symbol: str):
    """
    Get regime graph state for a symbol.
    
    Returns:
    - nodes: Graph nodes (regime states) with visit counts
    - edges: Graph edges (transitions) with probabilities
    - current_state: Current regime state
    - likely_next_state: Most probable next state
    - path_confidence: Confidence in prediction
    """
    engine = get_regime_graph_engine()
    
    try:
        state = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": state.symbol,
            "current_state": state.current_state,
            "previous_state": state.previous_state,
            "likely_next_state": state.likely_next_state,
            "next_state_probability": state.next_state_probability,
            "alternative_states": state.alternative_states,
            "path_confidence": state.path_confidence,
            "recent_sequence": state.recent_sequence,
            "total_transitions": state.total_transitions,
            "unique_states_visited": state.unique_states_visited,
            "reason": state.reason,
            "timestamp": state.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/next/{symbol}")
async def get_next_state_prediction(symbol: str):
    """
    Get next state prediction for a symbol.
    """
    engine = get_regime_graph_engine()
    
    try:
        state = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": state.symbol,
            "current_state": state.current_state,
            "likely_next_state": state.likely_next_state,
            "next_state_probability": state.next_state_probability,
            "alternative_states": state.alternative_states,
            "path_confidence": state.path_confidence,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/path/{symbol}")
async def get_predicted_path(
    symbol: str,
    steps: int = Query(default=3, ge=1, le=10),
):
    """
    Get predicted path through regime graph.
    """
    engine = get_regime_graph_engine()
    
    try:
        path = engine.predict_path(symbol.upper(), steps)
        
        return {
            "status": "ok",
            "symbol": path.symbol,
            "current_state": path.current_state,
            "predicted_path": path.predicted_path,
            "path_probabilities": path.path_probabilities,
            "combined_probability": path.combined_probability,
            "path_confidence": path.path_confidence,
            "estimated_durations_minutes": path.estimated_durations_minutes,
            "total_estimated_minutes": path.total_estimated_minutes,
            "timestamp": path.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute/{symbol}")
async def recompute_graph(
    symbol: str,
    save: bool = Query(default=True),
):
    """
    Recompute regime graph for a symbol and optionally save to MongoDB.
    """
    engine = get_regime_graph_engine()
    registry = get_regime_graph_registry()
    
    try:
        state = engine.analyze(symbol.upper())
        
        saved = False
        if save:
            saved = registry.save_state(state)
        
        return {
            "status": "ok",
            "symbol": state.symbol,
            "current_state": state.current_state,
            "likely_next_state": state.likely_next_state,
            "path_confidence": state.path_confidence,
            "node_count": len([n for n in state.nodes if n.visits > 0]),
            "edge_count": len(state.edges),
            "saved": saved,
            "timestamp": state.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modifier/{symbol}")
async def get_graph_modifier(
    symbol: str,
    hypothesis_direction: str = Query(default="LONG", pattern="^(LONG|SHORT)$"),
):
    """
    Get graph modifier for hypothesis engine.
    """
    engine = get_regime_graph_engine()
    
    try:
        modifier = engine.get_modifier(symbol.upper(), hypothesis_direction)
        
        return {
            "status": "ok",
            "symbol": modifier.symbol,
            "graph_score": modifier.graph_score,
            "graph_weight": modifier.graph_weight,
            "weighted_contribution": modifier.weighted_contribution,
            "current_state": modifier.current_state,
            "likely_next_state": modifier.likely_next_state,
            "next_state_probability": modifier.next_state_probability,
            "path_confidence": modifier.path_confidence,
            "is_favorable_transition": modifier.is_favorable_transition,
            "modifier": modifier.modifier,
            "reason": modifier.reason,
            "hypothesis_direction": hypothesis_direction,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{symbol}")
async def get_graph_summary(symbol: str):
    """
    Get summary statistics for regime graph.
    """
    engine = get_regime_graph_engine()
    
    try:
        summary = engine.generate_summary(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": summary.symbol,
            "node_count": summary.node_count,
            "edge_count": summary.edge_count,
            "most_visited_state": summary.most_visited_state,
            "most_visited_count": summary.most_visited_count,
            "most_common_transition": summary.most_common_transition,
            "most_common_transition_count": summary.most_common_transition_count,
            "matrix_density": summary.matrix_density,
            "current_state": summary.current_state,
            "likely_next_state": summary.likely_next_state,
            "total_transitions": summary.total_transitions,
            "avg_state_duration_minutes": summary.avg_state_duration_minutes,
            "last_updated": summary.last_updated.isoformat() if summary.last_updated else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/matrix/{symbol}")
async def get_transition_matrix(symbol: str):
    """
    Get transition probability matrix.
    """
    engine = get_regime_graph_engine()
    
    try:
        # Ensure graph is built
        state = engine.analyze(symbol.upper())
        
        # Get matrix from cache
        matrix = engine._transition_matrices.get(symbol.upper(), {})
        
        # Format for response
        formatted_matrix = []
        for from_state, to_states in matrix.items():
            for to_state, probability in to_states.items():
                formatted_matrix.append({
                    "from_state": from_state,
                    "to_state": to_state,
                    "probability": probability
                })
        
        # Sort by probability
        formatted_matrix.sort(key=lambda x: x["probability"], reverse=True)
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "current_state": state.current_state,
            "matrix": formatted_matrix,
            "matrix_size": len(formatted_matrix),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{symbol}")
async def get_graph_nodes(symbol: str):
    """
    Get all nodes in regime graph with statistics.
    """
    engine = get_regime_graph_engine()
    
    try:
        state = engine.analyze(symbol.upper())
        
        # Filter to visited nodes
        visited_nodes = [n for n in state.nodes if n.visits > 0]
        
        return {
            "status": "ok",
            "symbol": state.symbol,
            "nodes": [
                {
                    "regime_state": n.regime_state,
                    "visits": n.visits,
                    "avg_duration_minutes": n.avg_duration_minutes,
                    "max_duration_minutes": n.max_duration_minutes,
                    "min_duration_minutes": n.min_duration_minutes,
                    "avg_success_rate": n.avg_success_rate,
                }
                for n in sorted(visited_nodes, key=lambda x: x.visits, reverse=True)
            ],
            "total_nodes": len(visited_nodes),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edges/{symbol}")
async def get_graph_edges(symbol: str):
    """
    Get all edges in regime graph with probabilities.
    """
    engine = get_regime_graph_engine()
    
    try:
        state = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": state.symbol,
            "edges": [
                {
                    "from_state": e.from_state,
                    "to_state": e.to_state,
                    "transition_probability": e.transition_probability,
                    "avg_transition_time_minutes": e.avg_transition_time_minutes,
                    "transition_count": e.transition_count,
                    "edge_confidence": e.edge_confidence,
                }
                for e in sorted(state.edges, key=lambda x: x.transition_probability, reverse=True)
            ],
            "total_edges": len(state.edges),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Batch Operations
# ══════════════════════════════════════════════════════════════

@router.post("/batch/compute")
async def batch_compute_graphs(
    symbols: list[str] = Query(default=["BTC", "ETH", "SOL"]),
    save: bool = Query(default=True),
):
    """
    Compute regime graphs for multiple symbols.
    """
    engine = get_regime_graph_engine()
    registry = get_regime_graph_registry()
    
    results = []
    saved_count = 0
    
    for symbol in symbols:
        try:
            state = engine.analyze(symbol.upper())
            
            if save:
                if registry.save_state(state):
                    saved_count += 1
            
            results.append({
                "symbol": state.symbol,
                "current_state": state.current_state,
                "likely_next_state": state.likely_next_state,
                "path_confidence": state.path_confidence,
            })
        except Exception as e:
            results.append({
                "symbol": symbol.upper(),
                "error": str(e),
            })
    
    return {
        "status": "ok",
        "computed": len(results),
        "saved": saved_count if save else 0,
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/batch/summary")
async def batch_summary():
    """
    Get summary for all tracked symbols.
    """
    engine = get_regime_graph_engine()
    registry = get_regime_graph_registry()
    
    symbols = registry.get_all_symbols()
    summaries = []
    
    for symbol in symbols:
        summary = engine.generate_summary(symbol)
        if summary:
            summaries.append({
                "symbol": summary.symbol,
                "current_state": summary.current_state,
                "likely_next_state": summary.likely_next_state,
                "node_count": summary.node_count,
                "edge_count": summary.edge_count,
            })
    
    return {
        "status": "ok",
        "symbols_count": len(symbols),
        "summaries": summaries,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/history/{symbol}")
async def get_graph_history(
    symbol: str,
    limit: int = Query(default=50, le=200),
    hours_back: Optional[int] = Query(default=None, le=720),
):
    """
    Get historical graph states.
    """
    registry = get_regime_graph_registry()
    
    try:
        history = registry.get_history(symbol.upper(), limit, hours_back)
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "count": len(history),
            "records": [
                {
                    "current_state": h.get("current_state"),
                    "likely_next_state": h.get("likely_next_state"),
                    "next_state_probability": h.get("next_state_probability"),
                    "path_confidence": h.get("path_confidence"),
                    "created_at": h.get("created_at").isoformat() if h.get("created_at") else None,
                }
                for h in history
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
