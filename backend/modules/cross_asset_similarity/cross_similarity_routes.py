"""
Cross-Asset Similarity API Routes

PHASE 32.4 — API endpoints for Cross-Asset Similarity Engine.

Endpoints:
- GET  /api/v1/cross-similarity/health             - Health check
- GET  /api/v1/cross-similarity/{symbol}           - Get current analysis
- GET  /api/v1/cross-similarity/top/{symbol}       - Get top matches
- GET  /api/v1/cross-similarity/assets/{symbol}    - Get asset breakdown
- GET  /api/v1/cross-similarity/history/{symbol}   - Get analysis history
- POST /api/v1/cross-similarity/recompute/{symbol} - Force recomputation
- GET  /api/v1/cross-similarity/modifier/{symbol}  - Get hypothesis modifier
- GET  /api/v1/cross-similarity/summary/{symbol}   - Get summary
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException

from .cross_similarity_engine import get_cross_similarity_engine
from .cross_similarity_registry import get_cross_similarity_registry
from .cross_similarity_types import (
    CrossAssetAnalysis,
    CrossAssetMatch,
    CrossAssetModifier,
    CrossAssetSummary,
    ASSET_UNIVERSE,
    SIMILARITY_THRESHOLD,
)


router = APIRouter(
    prefix="/api/v1/cross-similarity",
    tags=["Cross-Asset Similarity Engine"],
)


# ══════════════════════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def cross_similarity_health() -> dict:
    """Health check for cross-asset similarity engine."""
    return {
        "status": "ok",
        "module": "cross_asset_similarity",
        "phase": "32.4",
        "version": "1.0.0",
        "asset_universe": ASSET_UNIVERSE,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/cross-similarity/matrix (MUST BE BEFORE /{symbol})
# ══════════════════════════════════════════════════════════════

@router.get("/matrix")
async def get_cross_asset_matrix() -> dict:
    """
    Get full cross-asset similarity matrix for all assets.
    """
    engine = get_cross_similarity_engine()
    
    matrix = {}
    for symbol in ASSET_UNIVERSE:
        analysis = engine.analyze(symbol)
        matrix[symbol] = {
            "top_match": analysis.top_match.reference_symbol if analysis.top_match else "NONE",
            "direction": analysis.expected_direction,
            "confidence": analysis.aggregated_confidence,
            "asset_signals": analysis.asset_signals,
        }
    
    return {
        "status": "ok",
        "asset_universe": ASSET_UNIVERSE,
        "matrix": matrix,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/cross-similarity/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/{symbol}")
async def get_cross_similarity(
    symbol: str,
    threshold: float = Query(default=SIMILARITY_THRESHOLD, ge=0.5, le=0.99),
) -> dict:
    """
    Get current cross-asset similarity analysis for symbol.
    
    Returns matches with other assets' historical patterns.
    """
    engine = get_cross_similarity_engine()
    
    analysis = engine.get_current_analysis(symbol)
    
    if analysis is None:
        analysis = engine.analyze(symbol, threshold)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "expected_direction": analysis.expected_direction,
        "aggregated_confidence": analysis.aggregated_confidence,
        "matches_found": analysis.matches_found,
        "assets_compared": analysis.assets_compared,
        "top_match": {
            "reference_symbol": analysis.top_match.reference_symbol,
            "reference_timestamp": analysis.top_match.reference_timestamp.isoformat(),
            "similarity_score": analysis.top_match.similarity_score,
            "expected_direction": analysis.top_match.expected_direction,
            "historical_move_percent": analysis.top_match.historical_move_percent,
            "confidence": analysis.top_match.confidence,
        } if analysis.top_match else None,
        "asset_signals": analysis.asset_signals,
        "asset_confidences": analysis.asset_confidences,
        "created_at": analysis.created_at.isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/cross-similarity/top/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/top/{symbol}")
async def get_top_matches(
    symbol: str,
    limit: int = Query(default=5, ge=1, le=20),
) -> dict:
    """
    Get top cross-asset matches for symbol.
    """
    engine = get_cross_similarity_engine()
    
    matches = engine.get_top_matches(symbol, limit)
    
    if not matches:
        analysis = engine.analyze(symbol)
        matches = analysis.matches[:limit]
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "count": len(matches),
        "matches": [
            {
                "match_id": m.match_id,
                "reference_symbol": m.reference_symbol,
                "reference_timestamp": m.reference_timestamp.isoformat(),
                "similarity_score": m.similarity_score,
                "expected_direction": m.expected_direction,
                "historical_move_percent": m.historical_move_percent,
                "confidence": m.confidence,
                "cross_asset_weight": m.cross_asset_weight,
            }
            for m in matches
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/cross-similarity/assets/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/assets/{symbol}")
async def get_asset_signals(
    symbol: str,
) -> dict:
    """
    Get signal breakdown by reference asset.
    """
    engine = get_cross_similarity_engine()
    
    signals = engine.get_asset_signals(symbol)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "asset_universe": [a for a in ASSET_UNIVERSE if a != symbol.upper()],
        "signals": signals,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/cross-similarity/history/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/history/{symbol}")
async def get_analysis_history(
    symbol: str,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """
    Get cross-asset similarity analysis history.
    """
    engine = get_cross_similarity_engine()
    
    history = engine.get_history(symbol, limit)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "count": len(history),
        "history": [
            {
                "top_reference": a.top_match.reference_symbol if a.top_match else "NONE",
                "top_similarity": a.top_match.similarity_score if a.top_match else 0.0,
                "expected_direction": a.expected_direction,
                "aggregated_confidence": a.aggregated_confidence,
                "matches_found": a.matches_found,
                "created_at": a.created_at.isoformat(),
            }
            for a in history
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# POST /api/v1/cross-similarity/recompute/{symbol}
# ══════════════════════════════════════════════════════════════

@router.post("/recompute/{symbol}")
async def recompute_cross_similarity(
    symbol: str,
    threshold: float = Query(default=SIMILARITY_THRESHOLD, ge=0.5, le=0.99),
) -> dict:
    """
    Force recomputation of cross-asset similarity.
    """
    engine = get_cross_similarity_engine()
    
    analysis = engine.analyze(symbol, threshold)
    
    # Save to database
    try:
        registry = get_cross_similarity_registry()
        registry.save_analysis(analysis)
    except Exception:
        pass
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "expected_direction": analysis.expected_direction,
        "aggregated_confidence": analysis.aggregated_confidence,
        "matches_found": analysis.matches_found,
        "top_match": {
            "reference_symbol": analysis.top_match.reference_symbol,
            "similarity_score": analysis.top_match.similarity_score,
            "expected_direction": analysis.top_match.expected_direction,
        } if analysis.top_match else None,
        "recomputed_at": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/cross-similarity/modifier/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/modifier/{symbol}")
async def get_hypothesis_modifier(
    symbol: str,
    hypothesis_direction: str = Query(default="LONG"),
) -> dict:
    """
    Get modifier for hypothesis engine based on cross-asset similarity.
    
    Returns:
    - 1.10 if cross-asset signal aligns with hypothesis
    - 0.92 if cross-asset signal conflicts
    - 1.00 if neutral or no strong signal
    """
    engine = get_cross_similarity_engine()
    
    modifier = engine.get_cross_asset_modifier(symbol, hypothesis_direction.upper())
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "hypothesis_direction": hypothesis_direction.upper(),
        "modifier": {
            "value": modifier.modifier,
            "top_reference_symbol": modifier.top_reference_symbol,
            "top_similarity": modifier.top_similarity,
            "cross_asset_direction": modifier.expected_direction,
            "confidence": modifier.confidence,
            "reason": modifier.reason,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/cross-similarity/summary/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/summary/{symbol}")
async def get_cross_similarity_summary(
    symbol: str,
) -> dict:
    """
    Get cross-asset similarity summary for symbol.
    """
    engine = get_cross_similarity_engine()
    
    summary = engine.get_summary(symbol)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "summary": {
            "current_top_reference": summary.current_top_reference,
            "current_similarity": summary.current_similarity,
            "current_direction": summary.current_direction,
            "total_analyses": summary.total_analyses,
            "avg_similarity": summary.avg_similarity,
            "most_similar_asset": summary.most_similar_asset,
            "asset_correlations": summary.asset_correlations,
            "last_updated": summary.last_updated.isoformat() if summary.last_updated else None,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
