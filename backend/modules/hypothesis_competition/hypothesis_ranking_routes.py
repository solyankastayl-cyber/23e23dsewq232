"""
Hypothesis Ranking — Routes

PHASE 30.2 — API endpoints for Hypothesis Ranking Engine.

Endpoints:
- GET  /api/v1/hypothesis/ranked/{symbol}
- POST /api/v1/hypothesis/ranked/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone

from .hypothesis_ranking_engine import (
    HypothesisRankingEngine,
    get_hypothesis_ranking_engine,
)


router = APIRouter(prefix="/api/v1/hypothesis/ranked", tags=["hypothesis-ranked"])


@router.get("/{symbol}", response_model=Dict[str, Any])
async def get_ranked_pool(symbol: str):
    """
    Get ranked hypothesis pool for symbol.
    
    Returns pool with:
    - Duplicate suppression applied
    - Dominance penalties applied
    - Diversity penalties applied
    - Directional balance for capital allocation
    """
    engine = get_hypothesis_ranking_engine()
    
    # Generate ranked pool
    ranked_pool = engine.generate_ranked_pool(symbol.upper())
    
    return {
        "symbol": ranked_pool.symbol,
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
            for h in ranked_pool.hypotheses
        ],
        "top_hypothesis": ranked_pool.top_hypothesis,
        "directional_balance": ranked_pool.directional_balance,
        "pool_confidence": ranked_pool.pool_confidence,
        "pool_reliability": ranked_pool.pool_reliability,
        "pool_size": ranked_pool.pool_size,
        "ranking_metadata": {
            "duplicates_removed": ranked_pool.duplicates_removed,
            "dominance_penalty_applied": ranked_pool.dominance_penalty_applied,
            "diversity_penalties_applied": ranked_pool.diversity_penalties_applied,
        },
        "created_at": ranked_pool.created_at.isoformat(),
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_ranked_pool(symbol: str):
    """
    Force recompute of ranked hypothesis pool.
    """
    try:
        engine = get_hypothesis_ranking_engine()
        
        # Recompute
        ranked_pool = engine.generate_ranked_pool(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": ranked_pool.symbol,
            "hypotheses": [
                {
                    "hypothesis_type": h.hypothesis_type,
                    "directional_bias": h.directional_bias,
                    "ranking_score": h.ranking_score,
                    "execution_state": h.execution_state,
                }
                for h in ranked_pool.hypotheses
            ],
            "top_hypothesis": ranked_pool.top_hypothesis,
            "directional_balance": ranked_pool.directional_balance,
            "pool_size": ranked_pool.pool_size,
            "ranking_metadata": {
                "duplicates_removed": ranked_pool.duplicates_removed,
                "dominance_penalty_applied": ranked_pool.dominance_penalty_applied,
                "diversity_penalties_applied": ranked_pool.diversity_penalties_applied,
            },
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ranked pool recompute failed: {str(e)}",
        )


@router.get("/history/{symbol}", response_model=Dict[str, Any])
async def get_ranked_pool_history(symbol: str, limit: int = 50):
    """
    Get ranked pool history for symbol.
    """
    engine = get_hypothesis_ranking_engine()
    history = engine.get_history(symbol.upper(), limit=limit)
    
    return {
        "symbol": symbol.upper(),
        "total": len(history),
        "pools": [
            {
                "top_hypothesis": p.top_hypothesis,
                "directional_balance": p.directional_balance,
                "pool_size": p.pool_size,
                "pool_confidence": p.pool_confidence,
                "pool_reliability": p.pool_reliability,
                "duplicates_removed": p.duplicates_removed,
                "dominance_penalty_applied": p.dominance_penalty_applied,
                "diversity_penalties_applied": p.diversity_penalties_applied,
                "created_at": p.created_at.isoformat(),
            }
            for p in history
        ],
    }
