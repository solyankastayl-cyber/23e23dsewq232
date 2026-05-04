"""
Hypothesis Pool — Routes

PHASE 30.1 — API endpoints for Hypothesis Pool Engine.

Endpoints:
- GET  /api/v1/hypothesis/pool/{symbol}
- GET  /api/v1/hypothesis/pool/summary/{symbol}
- GET  /api/v1/hypothesis/pool/history/{symbol}
- POST /api/v1/hypothesis/pool/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone

from .hypothesis_pool_engine import (
    HypothesisPoolEngine,
    get_hypothesis_pool_engine,
)
from .hypothesis_pool_registry import (
    HypothesisPoolRegistry,
    get_hypothesis_pool_registry,
)


router = APIRouter(prefix="/api/v1/hypothesis/pool", tags=["hypothesis-pool"])


@router.get("/{symbol}", response_model=Dict[str, Any])
async def get_hypothesis_pool(symbol: str):
    """
    Get current hypothesis pool for symbol.
    
    Returns pool of competing hypotheses ranked by confidence.
    Maximum 5 hypotheses per pool.
    """
    engine = get_hypothesis_pool_engine()
    
    # Generate pool
    pool = engine.generate_pool(symbol.upper())
    
    # Store in registry
    registry = get_hypothesis_pool_registry()
    await registry.store_pool(pool)
    
    return {
        "symbol": pool.symbol,
        "hypotheses": [
            {
                "hypothesis_type": h.hypothesis_type,
                "directional_bias": h.directional_bias,
                "confidence": h.confidence,
                "reliability": h.reliability,
                "structural_score": h.structural_score,
                "execution_score": h.execution_score,
                "conflict_score": h.conflict_score,
                "ranking_score": h.ranking_score,
                "execution_state": h.execution_state,
                "reason": h.reason,
            }
            for h in pool.hypotheses
        ],
        "top_hypothesis": pool.top_hypothesis,
        "pool_confidence": pool.pool_confidence,
        "pool_reliability": pool.pool_reliability,
        "pool_size": pool.pool_size,
        "created_at": pool.created_at.isoformat(),
    }


@router.get("/summary/{symbol}", response_model=Dict[str, Any])
async def get_pool_summary(symbol: str):
    """
    Get hypothesis pool summary statistics for symbol.
    """
    engine = get_hypothesis_pool_engine()
    
    # Ensure at least one pool exists
    if not engine.get_pool(symbol.upper()):
        engine.generate_pool(symbol.upper())
    
    summary = engine.get_summary(symbol.upper())
    
    return {
        "symbol": summary.symbol,
        "total_pools": summary.total_pools,
        "top_hypothesis_distribution": summary.top_hypothesis_counts,
        "averages": {
            "pool_size": summary.avg_pool_size,
            "pool_confidence": summary.avg_pool_confidence,
            "pool_reliability": summary.avg_pool_reliability,
        },
        "current": {
            "top_hypothesis": summary.current_top_hypothesis,
            "pool_size": summary.current_pool_size,
        },
    }


@router.get("/history/{symbol}", response_model=Dict[str, Any])
async def get_pool_history(symbol: str, limit: int = 50):
    """
    Get hypothesis pool history for symbol.
    """
    registry = get_hypothesis_pool_registry()
    history = await registry.get_history(symbol.upper(), limit=limit)
    
    return {
        "symbol": symbol.upper(),
        "total": len(history),
        "pools": [
            {
                "top_hypothesis": r.top_hypothesis,
                "pool_size": r.pool_size,
                "pool_confidence": r.pool_confidence,
                "pool_reliability": r.pool_reliability,
                "hypotheses": r.hypotheses,
                "created_at": r.created_at.isoformat(),
            }
            for r in history
        ],
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_pool(symbol: str):
    """
    Force recompute of hypothesis pool.
    """
    try:
        engine = get_hypothesis_pool_engine()
        
        # Recompute pool
        pool = engine.generate_pool(symbol.upper())
        
        # Store in registry
        registry = get_hypothesis_pool_registry()
        await registry.store_pool(pool)
        
        return {
            "status": "ok",
            "symbol": pool.symbol,
            "hypotheses": [
                {
                    "hypothesis_type": h.hypothesis_type,
                    "directional_bias": h.directional_bias,
                    "confidence": h.confidence,
                    "reliability": h.reliability,
                    "ranking_score": h.ranking_score,
                    "execution_state": h.execution_state,
                }
                for h in pool.hypotheses
            ],
            "top_hypothesis": pool.top_hypothesis,
            "pool_confidence": pool.pool_confidence,
            "pool_reliability": pool.pool_reliability,
            "pool_size": pool.pool_size,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pool recompute failed: {str(e)}",
        )
