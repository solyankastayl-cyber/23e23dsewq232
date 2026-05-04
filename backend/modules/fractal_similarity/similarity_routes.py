"""
Fractal Similarity API Routes

PHASE 32.2 — API endpoints for Fractal Similarity Engine.

Endpoints:
- GET  /api/v1/fractal-similarity/{symbol}           - Get current analysis
- GET  /api/v1/fractal-similarity/top/{symbol}       - Get top matches
- GET  /api/v1/fractal-similarity/history/{symbol}   - Get analysis history
- POST /api/v1/fractal-similarity/recompute/{symbol} - Force recomputation
- GET  /api/v1/fractal-similarity/modifier/{symbol}  - Get modifier for hypothesis
- GET  /api/v1/fractal-similarity/summary/{symbol}   - Get summary
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException

from .similarity_engine import get_similarity_engine
from .similarity_registry import get_similarity_registry
from .similarity_types import (
    SimilarityAnalysis,
    SimilarityMatch,
    SimilarityModifier,
    SimilaritySummary,
)


router = APIRouter(
    prefix="/api/v1/fractal-similarity",
    tags=["Fractal Similarity Engine"],
)


# ══════════════════════════════════════════════════════════════
# Health Check (MUST BE BEFORE {symbol} to avoid route conflict)
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def similarity_health() -> dict:
    """Health check for similarity engine."""
    return {
        "status": "ok",
        "module": "fractal_similarity",
        "phase": "32.2",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/fractal-similarity/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/{symbol}")
async def get_similarity_analysis(
    symbol: str,
) -> dict:
    """
    Get current similarity analysis for symbol.
    
    Returns the latest analysis with:
    - Current structure vector
    - Top matches found
    - Expected direction
    - Confidence scores
    """
    engine = get_similarity_engine()
    
    analysis = engine.get_current_analysis(symbol)
    
    if analysis is None:
        # Run analysis if not exists
        analysis = engine.analyze_similarity(symbol)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "analysis": {
            "expected_direction": analysis.expected_direction,
            "direction_confidence": analysis.direction_confidence,
            "similarity_confidence": analysis.similarity_confidence,
            "best_similarity": analysis.best_similarity,
            "matches_found": analysis.matches_found,
            "patterns_searched": analysis.patterns_searched,
            "historical_success_rate": analysis.historical_success_rate,
            "avg_historical_return": analysis.avg_historical_return,
        },
        "top_matches": [
            {
                "pattern_id": m.pattern_id,
                "similarity": m.similarity_score,
                "direction": m.historical_direction,
                "return": m.historical_return,
                "successful": m.was_successful,
                "window_size": m.window_size,
            }
            for m in analysis.top_matches
        ],
        "current_vector": analysis.current_vector.model_dump() if analysis.current_vector else None,
        "created_at": analysis.created_at.isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/fractal-similarity/top/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/top/{symbol}")
async def get_top_matches(
    symbol: str,
    limit: int = Query(default=5, ge=1, le=20),
) -> dict:
    """
    Get top similarity matches for symbol.
    
    Returns the most similar historical patterns.
    """
    engine = get_similarity_engine()
    
    matches = engine.get_top_matches(symbol, limit)
    
    if not matches:
        # Run analysis first
        analysis = engine.analyze_similarity(symbol)
        matches = analysis.top_matches[:limit]
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "count": len(matches),
        "matches": [
            {
                "pattern_id": m.pattern_id,
                "similarity_score": m.similarity_score,
                "historical_direction": m.historical_direction,
                "historical_return": m.historical_return,
                "was_successful": m.was_successful,
                "window_size": m.window_size,
                "pattern_timestamp": m.pattern_timestamp.isoformat(),
            }
            for m in matches
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/fractal-similarity/history/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/history/{symbol}")
async def get_similarity_history(
    symbol: str,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """
    Get similarity analysis history for symbol.
    
    Returns past analyses with their results.
    """
    engine = get_similarity_engine()
    
    history = engine.get_history(symbol, limit)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "count": len(history),
        "history": [
            {
                "expected_direction": a.expected_direction,
                "direction_confidence": a.direction_confidence,
                "similarity_confidence": a.similarity_confidence,
                "best_similarity": a.best_similarity,
                "matches_found": a.matches_found,
                "historical_success_rate": a.historical_success_rate,
                "created_at": a.created_at.isoformat(),
            }
            for a in history
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# POST /api/v1/fractal-similarity/recompute/{symbol}
# ══════════════════════════════════════════════════════════════

@router.post("/recompute/{symbol}")
async def recompute_similarity(
    symbol: str,
) -> dict:
    """
    Force recomputation of similarity analysis.
    
    Runs fresh analysis regardless of cache.
    """
    engine = get_similarity_engine()
    
    analysis = engine.analyze_similarity(symbol)
    
    # Save to database
    try:
        registry = get_similarity_registry()
        registry.save_analysis(analysis)
    except Exception as e:
        # Continue even if DB fails
        pass
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "analysis": {
            "expected_direction": analysis.expected_direction,
            "direction_confidence": analysis.direction_confidence,
            "similarity_confidence": analysis.similarity_confidence,
            "best_similarity": analysis.best_similarity,
            "matches_found": analysis.matches_found,
            "historical_success_rate": analysis.historical_success_rate,
        },
        "recomputed_at": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/fractal-similarity/modifier/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/modifier/{symbol}")
async def get_similarity_modifier(
    symbol: str,
    hypothesis_direction: str = Query(default="LONG"),
) -> dict:
    """
    Get similarity modifier for hypothesis scoring.
    
    Returns modifier value:
    - 1.12 if aligned with historical pattern
    - 0.90 if conflicting
    - 1.00 if neutral
    """
    engine = get_similarity_engine()
    
    modifier = engine.get_similarity_modifier(symbol, hypothesis_direction)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "modifier": {
            "hypothesis_direction": modifier.hypothesis_direction,
            "expected_direction": modifier.expected_direction,
            "similarity_confidence": modifier.similarity_confidence,
            "is_aligned": modifier.is_aligned,
            "modifier_value": modifier.modifier,
            "matches_found": modifier.matches_found,
            "best_similarity": modifier.best_similarity,
            "historical_success_rate": modifier.historical_success_rate,
            "reason": modifier.reason,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/fractal-similarity/summary/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/summary/{symbol}")
async def get_similarity_summary(
    symbol: str,
) -> dict:
    """
    Get similarity summary for symbol.
    
    Returns aggregated statistics across all analyses.
    """
    engine = get_similarity_engine()
    
    # Ensure analysis exists
    if not engine.get_current_analysis(symbol):
        engine.analyze_similarity(symbol)
    
    summary = engine.get_summary(symbol)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "summary": {
            "current_direction": summary.current_direction,
            "current_confidence": summary.current_confidence,
            "total_patterns_stored": summary.total_patterns_stored,
            "total_analyses": summary.total_analyses,
            "avg_match_rate": summary.avg_match_rate,
            "avg_success_rate": summary.avg_success_rate,
            "best_window_size": summary.best_window_size,
            "best_window_success_rate": summary.best_window_success_rate,
            "last_updated": summary.last_updated.isoformat() if summary.last_updated else None,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# End of routes
