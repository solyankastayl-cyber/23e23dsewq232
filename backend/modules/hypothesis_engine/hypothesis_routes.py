"""
Hypothesis Engine — Routes

PHASE 29.1 — API endpoints for market hypothesis.
PHASE 29.4 — Extended registry endpoints with stats and recent.

Endpoints:
- GET  /api/v1/hypothesis/current/{symbol}
- GET  /api/v1/hypothesis/history/{symbol}
- GET  /api/v1/hypothesis/summary/{symbol}
- GET  /api/v1/hypothesis/stats/{symbol}        (PHASE 29.4)
- GET  /api/v1/hypothesis/recent                (PHASE 29.4)
- POST /api/v1/hypothesis/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from datetime import datetime, timezone

from .hypothesis_engine import (
    HypothesisEngine,
    get_hypothesis_engine,
)
from .hypothesis_registry import (
    HypothesisRegistry,
    get_hypothesis_registry,
)


router = APIRouter(prefix="/api/v1/hypothesis", tags=["hypothesis"])


@router.get("/current/{symbol}", response_model=Dict[str, Any])
async def get_current_hypothesis(symbol: str):
    """
    Get current market hypothesis for symbol.

    Generates hypothesis from intelligence layers if not cached.
    
    PHASE 29.2: Returns new scoring components:
    - structural_score
    - execution_score
    - conflict_score
    
    PHASE 29.3: Returns conflict_state (LOW/MODERATE/HIGH)
    """
    engine = get_hypothesis_engine()

    # Build hypothesis
    hypothesis = engine.generate_hypothesis_simulated(symbol.upper())

    # Store in registry
    registry = get_hypothesis_registry()
    await registry.store_hypothesis(hypothesis)

    return {
        "symbol": hypothesis.symbol,
        "hypothesis_type": hypothesis.hypothesis_type,
        "directional_bias": hypothesis.directional_bias,
        # PHASE 29.2 scores
        "structural_score": hypothesis.structural_score,
        "execution_score": hypothesis.execution_score,
        "conflict_score": hypothesis.conflict_score,
        # PHASE 29.3 conflict state
        "conflict_state": hypothesis.conflict_state,
        # Derived (adjusted by conflict resolver)
        "confidence": hypothesis.confidence,
        "reliability": hypothesis.reliability,
        # Support layers
        "alpha_support": hypothesis.alpha_support,
        "regime_support": hypothesis.regime_support,
        "microstructure_support": hypothesis.microstructure_support,
        "macro_fractal_support": hypothesis.macro_fractal_support,
        # Execution (adjusted by conflict resolver)
        "execution_state": hypothesis.execution_state,
        "reason": hypothesis.reason,
        "created_at": hypothesis.created_at.isoformat(),
    }


@router.get("/history/{symbol}", response_model=Dict[str, Any])
async def get_hypothesis_history(symbol: str, limit: int = 50):
    """
    Get hypothesis history for symbol.
    
    PHASE 29.4: Extended with all scoring fields.
    """
    registry = get_hypothesis_registry()
    history = await registry.get_history(symbol.upper(), limit=limit)

    return {
        "symbol": symbol.upper(),
        "total": len(history),
        "records": [
            {
                "hypothesis_type": r.hypothesis_type,
                "directional_bias": r.directional_bias,
                # PHASE 29.2/29.3 scores
                "structural_score": r.structural_score,
                "execution_score": r.execution_score,
                "conflict_score": r.conflict_score,
                "conflict_state": r.conflict_state,
                # Core scores
                "confidence": r.confidence,
                "reliability": r.reliability,
                "execution_state": r.execution_state,
                # PHASE 29.4 price tracking
                "price_at_creation": r.price_at_creation,
                "created_at": r.created_at.isoformat(),
            }
            for r in history
        ],
    }


@router.get("/summary/{symbol}", response_model=Dict[str, Any])
async def get_hypothesis_summary(symbol: str):
    """
    Get hypothesis summary statistics for symbol.
    """
    engine = get_hypothesis_engine()

    # Ensure at least one hypothesis exists
    if not engine.get_hypothesis(symbol.upper()):
        engine.generate_hypothesis_simulated(symbol.upper())

    summary = engine.get_summary(symbol.upper())

    return {
        "symbol": summary.symbol,
        "total_records": summary.total_records,
        "types": {
            "bullish_continuation": summary.bullish_continuation_count,
            "bearish_continuation": summary.bearish_continuation_count,
            "breakout_forming": summary.breakout_forming_count,
            "range_mean_reversion": summary.range_mean_reversion_count,
            "no_edge": summary.no_edge_count,
            "other": summary.other_count,
        },
        "bias": {
            "long": summary.long_count,
            "short": summary.short_count,
            "neutral": summary.neutral_count,
        },
        "execution_states": {
            "favorable": summary.favorable_count,
            "cautious": summary.cautious_count,
            "unfavorable": summary.unfavorable_count,
        },
        "averages": {
            "confidence": summary.average_confidence,
            "reliability": summary.average_reliability,
        },
        "current": {
            "hypothesis": summary.current_hypothesis,
            "bias": summary.current_bias,
        },
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_hypothesis(symbol: str):
    """
    Force recompute of market hypothesis.

    Regenerates hypothesis from all intelligence layers.
    
    PHASE 29.2: Returns new scoring components.
    PHASE 29.3: Returns conflict_state.
    """
    try:
        engine = get_hypothesis_engine()

        # Recompute
        hypothesis = engine.generate_hypothesis_simulated(symbol.upper())

        # Store in registry
        registry = get_hypothesis_registry()
        await registry.store_hypothesis(hypothesis)

        return {
            "status": "ok",
            "symbol": hypothesis.symbol,
            "hypothesis_type": hypothesis.hypothesis_type,
            "directional_bias": hypothesis.directional_bias,
            # PHASE 29.2 scores
            "structural_score": hypothesis.structural_score,
            "execution_score": hypothesis.execution_score,
            "conflict_score": hypothesis.conflict_score,
            # PHASE 29.3 conflict state
            "conflict_state": hypothesis.conflict_state,
            # Derived (adjusted)
            "confidence": hypothesis.confidence,
            "reliability": hypothesis.reliability,
            # Support layers
            "alpha_support": hypothesis.alpha_support,
            "regime_support": hypothesis.regime_support,
            "microstructure_support": hypothesis.microstructure_support,
            "macro_fractal_support": hypothesis.macro_fractal_support,
            # Execution (adjusted)
            "execution_state": hypothesis.execution_state,
            "reason": hypothesis.reason,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recompute failed: {str(e)}",
        )



# ═══════════════════════════════════════════════════════════════
# PHASE 29.4 — New Registry Endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("/stats/{symbol}", response_model=Dict[str, Any])
async def get_hypothesis_stats(symbol: str):
    """
    Get comprehensive hypothesis statistics for symbol.
    
    PHASE 29.4: Full statistics with all scoring breakdowns.
    
    Returns:
    - Total hypotheses count
    - Directional breakdown (bullish/bearish/neutral)
    - Type breakdown
    - Conflict state breakdown
    - Execution state breakdown
    - Score averages
    - Recent bias trend
    """
    registry = get_hypothesis_registry()
    stats = await registry.get_hypothesis_stats(symbol.upper())

    return {
        "symbol": stats.symbol,
        "total_hypotheses": stats.total_hypotheses,
        "directional": {
            "bullish": stats.bullish,
            "bearish": stats.bearish,
            "neutral": stats.neutral,
        },
        "types": {
            "bullish_continuation": stats.bullish_continuation,
            "bearish_continuation": stats.bearish_continuation,
            "breakout_forming": stats.breakout_forming,
            "range_mean_reversion": stats.range_mean_reversion,
            "no_edge": stats.no_edge,
        },
        "conflict_states": {
            "low": stats.low_conflict,
            "moderate": stats.moderate_conflict,
            "high": stats.high_conflict,
        },
        "execution_states": {
            "favorable": stats.favorable,
            "cautious": stats.cautious,
            "unfavorable": stats.unfavorable,
        },
        "averages": {
            "confidence": stats.avg_confidence,
            "reliability": stats.avg_reliability,
            "structural_score": stats.avg_structural_score,
            "execution_score": stats.avg_execution_score,
            "conflict_score": stats.avg_conflict_score,
        },
        "recent_bias_trend": stats.recent_bias_trend,
    }


@router.get("/recent", response_model=Dict[str, Any])
async def get_recent_hypotheses(limit: int = Query(default=100, le=500)):
    """
    Get recent hypotheses across all symbols.
    
    PHASE 29.4: System-wide hypothesis monitoring.
    
    Returns most recent hypotheses sorted by creation time.
    """
    registry = get_hypothesis_registry()
    recent = await registry.get_recent_hypotheses(limit=limit)

    return {
        "total": len(recent),
        "limit": limit,
        "hypotheses": [
            {
                "symbol": r.symbol,
                "hypothesis_type": r.hypothesis_type,
                "directional_bias": r.directional_bias,
                "structural_score": r.structural_score,
                "execution_score": r.execution_score,
                "conflict_score": r.conflict_score,
                "conflict_state": r.conflict_state,
                "confidence": r.confidence,
                "reliability": r.reliability,
                "execution_state": r.execution_state,
                "price_at_creation": r.price_at_creation,
                "created_at": r.created_at.isoformat(),
            }
            for r in recent
        ],
    }


@router.get("/symbols", response_model=Dict[str, Any])
async def get_all_symbols():
    """
    Get list of all symbols with hypothesis history.
    
    PHASE 29.4: Useful for discovering tracked symbols.
    """
    registry = get_hypothesis_registry()
    symbols = await registry.get_all_symbols()

    return {
        "total": len(symbols),
        "symbols": symbols,
    }
