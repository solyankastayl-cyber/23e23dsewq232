"""
Capital Allocation Routes

PHASE 30.3 — API endpoints for Capital Allocation Engine.

Endpoints:
- GET  /api/v1/hypothesis/portfolio/{symbol}
- GET  /api/v1/hypothesis/portfolio/summary/{symbol}
- GET  /api/v1/hypothesis/portfolio/history/{symbol}
- POST /api/v1/hypothesis/portfolio/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone

from .capital_allocation_engine import (
    CapitalAllocationEngine,
    get_capital_allocation_engine,
)
from .capital_allocation_registry import get_capital_allocation_registry


router = APIRouter(prefix="/api/v1/hypothesis/portfolio", tags=["hypothesis-portfolio"])


@router.get("/{symbol}", response_model=Dict[str, Any])
async def get_portfolio_allocation(symbol: str):
    """
    Get capital allocation portfolio for symbol.
    
    Returns portfolio with:
    - Hypothesis allocations with capital weights
    - Portfolio confidence and reliability
    - Allocation metadata (caps, filters applied)
    """
    engine = get_capital_allocation_engine()
    
    # Generate allocation
    allocation = engine.generate_allocation(symbol.upper())
    
    # Save to MongoDB
    registry = get_capital_allocation_registry()
    registry.save_allocation(allocation)
    
    return {
        "symbol": allocation.symbol,
        "allocations": [
            {
                "hypothesis_type": a.hypothesis_type,
                "directional_bias": a.directional_bias,
                "ranking_score": a.ranking_score,
                "capital_weight": a.capital_weight,
                "capital_percent": a.capital_percent,
                "execution_state": a.execution_state,
            }
            for a in allocation.allocations
        ],
        "total_allocated": allocation.total_allocated,
        "portfolio_confidence": allocation.portfolio_confidence,
        "portfolio_reliability": allocation.portfolio_reliability,
        "allocation_metadata": {
            "total_hypotheses_input": allocation.total_hypotheses_input,
            "hypotheses_removed_unfavorable": allocation.hypotheses_removed_unfavorable,
            "hypotheses_removed_min_threshold": allocation.hypotheses_removed_min_threshold,
            "directional_cap_applied": allocation.directional_cap_applied,
            "neutral_cap_applied": allocation.neutral_cap_applied,
        },
        "created_at": allocation.created_at.isoformat(),
    }


@router.get("/summary/{symbol}", response_model=Dict[str, Any])
async def get_portfolio_summary(symbol: str):
    """
    Get capital allocation summary for symbol.
    
    Returns aggregated statistics from allocation history.
    """
    # Try MongoDB registry first
    registry = get_capital_allocation_registry()
    summary = registry.get_summary(symbol.upper())
    
    # Fallback to in-memory if no MongoDB data
    if summary.total_allocations == 0:
        engine = get_capital_allocation_engine()
        summary = engine.get_summary(symbol.upper())
    
    return {
        "symbol": summary.symbol,
        "total_allocations": summary.total_allocations,
        "directional_distribution": {
            "avg_long_exposure": summary.avg_long_exposure,
            "avg_short_exposure": summary.avg_short_exposure,
            "avg_neutral_exposure": summary.avg_neutral_exposure,
        },
        "averages": {
            "avg_portfolio_confidence": summary.avg_portfolio_confidence,
            "avg_portfolio_reliability": summary.avg_portfolio_reliability,
            "avg_hypothesis_count": summary.avg_hypothesis_count,
        },
        "current_state": {
            "allocation_count": summary.current_allocation_count,
            "top_hypothesis": summary.current_top_hypothesis,
        },
    }


@router.get("/history/{symbol}", response_model=Dict[str, Any])
async def get_portfolio_history(symbol: str, limit: int = 50):
    """
    Get capital allocation history for symbol.
    """
    registry = get_capital_allocation_registry()
    history = registry.get_history(symbol.upper(), limit=limit)
    
    # Fallback to in-memory
    if not history:
        engine = get_capital_allocation_engine()
        in_memory_history = engine.get_history(symbol.upper(), limit=limit)
        history = [
            {
                "symbol": h.symbol,
                "allocations": [
                    {
                        "hypothesis_type": a.hypothesis_type,
                        "directional_bias": a.directional_bias,
                        "capital_percent": a.capital_percent,
                    }
                    for a in h.allocations
                ],
                "portfolio_confidence": h.portfolio_confidence,
                "portfolio_reliability": h.portfolio_reliability,
                "created_at": h.created_at.isoformat(),
            }
            for h in in_memory_history
        ]
    
    return {
        "symbol": symbol.upper(),
        "total": len(history),
        "allocations": history,
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_portfolio_allocation(symbol: str):
    """
    Force recompute of capital allocation portfolio.
    """
    try:
        engine = get_capital_allocation_engine()
        
        # Recompute
        allocation = engine.generate_allocation(symbol.upper())
        
        # Save to MongoDB
        registry = get_capital_allocation_registry()
        registry.save_allocation(allocation)
        
        return {
            "status": "ok",
            "symbol": allocation.symbol,
            "allocations": [
                {
                    "hypothesis_type": a.hypothesis_type,
                    "directional_bias": a.directional_bias,
                    "capital_percent": a.capital_percent,
                    "execution_state": a.execution_state,
                }
                for a in allocation.allocations
            ],
            "portfolio_confidence": allocation.portfolio_confidence,
            "portfolio_reliability": allocation.portfolio_reliability,
            "allocation_metadata": {
                "total_hypotheses_input": allocation.total_hypotheses_input,
                "hypotheses_removed_unfavorable": allocation.hypotheses_removed_unfavorable,
                "hypotheses_removed_min_threshold": allocation.hypotheses_removed_min_threshold,
                "directional_cap_applied": allocation.directional_cap_applied,
                "neutral_cap_applied": allocation.neutral_cap_applied,
            },
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Portfolio allocation recompute failed: {str(e)}",
        )
