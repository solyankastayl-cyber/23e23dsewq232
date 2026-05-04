"""
Reflexivity Engine Routes

PHASE 35 — Market Reflexivity Engine

API endpoints:
- GET  /api/v1/reflexivity/{symbol}           - Get current reflexivity state
- GET  /api/v1/reflexivity/state/{symbol}     - Get detailed state with source
- GET  /api/v1/reflexivity/history/{symbol}   - Get historical reflexivity data
- POST /api/v1/reflexivity/recompute/{symbol} - Recompute reflexivity for symbol
- GET  /api/v1/reflexivity/modifier/{symbol}  - Get hypothesis modifier
- GET  /api/v1/reflexivity/summary/{symbol}   - Get summary statistics
- GET  /api/v1/reflexivity/health             - Health check
"""

from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException

from .reflexivity_types import (
    ReflexivityState,
    ReflexivityModifier,
    ReflexivitySummary,
    ReflexivityHistory,
    REFLEXIVITY_WEIGHT,
)
from .reflexivity_engine import get_reflexivity_engine
from .reflexivity_registry import get_reflexivity_registry


router = APIRouter(
    prefix="/api/v1/reflexivity",
    tags=["PHASE 35 - Reflexivity Engine"]
)


# ══════════════════════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def reflexivity_health():
    """Health check for Reflexivity Engine."""
    engine = get_reflexivity_engine()
    registry = get_reflexivity_registry()
    
    # Check MongoDB
    db_connected = registry.collection is not None
    
    # Get symbols with data
    symbols = registry.get_all_symbols() if db_connected else []
    
    return {
        "status": "ok",
        "phase": "PHASE 35",
        "module": "Market Reflexivity Engine",
        "engine_ready": engine is not None,
        "db_connected": db_connected,
        "symbols_tracked": symbols,
        "reflexivity_weight": REFLEXIVITY_WEIGHT,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ══════════════════════════════════════════════════════════════
# Core Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/{symbol}")
async def get_reflexivity(symbol: str):
    """
    Get current reflexivity state for a symbol.
    
    Returns:
    - reflexivity_score: Overall reflexivity measure [0, 1]
    - feedback_direction: POSITIVE / NEGATIVE / NEUTRAL
    - strength: WEAK / MODERATE / STRONG
    - sentiment_state: Market sentiment derived from data
    """
    engine = get_reflexivity_engine()
    
    try:
        state = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": state.symbol,
            "reflexivity_score": state.reflexivity_score,
            "feedback_direction": state.feedback_direction,
            "strength": state.strength,
            "sentiment_state": state.sentiment_state,
            "crowd_positioning": state.crowd_positioning,
            "confidence": state.confidence,
            "reason": state.reason,
            "timestamp": state.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state/{symbol}")
async def get_reflexivity_state(symbol: str):
    """
    Get detailed reflexivity state including component scores and source data.
    """
    engine = get_reflexivity_engine()
    
    try:
        state = engine.analyze(symbol.upper())
        
        response = {
            "status": "ok",
            "symbol": state.symbol,
            
            # Core metrics
            "reflexivity_score": state.reflexivity_score,
            "feedback_direction": state.feedback_direction,
            "strength": state.strength,
            "confidence": state.confidence,
            
            # Sentiment
            "sentiment_state": state.sentiment_state,
            "crowd_positioning": state.crowd_positioning,
            
            # Component scores
            "components": {
                "sentiment_score": state.sentiment_score,
                "positioning_score": state.positioning_score,
                "trend_acceleration_score": state.trend_acceleration_score,
                "volatility_expansion_score": state.volatility_expansion_score,
            },
            
            # Weights
            "weights": {
                "sentiment": 0.35,
                "positioning": 0.25,
                "trend_acceleration": 0.20,
                "volatility_expansion": 0.20,
            },
            
            "reason": state.reason,
            "timestamp": state.timestamp.isoformat()
        }
        
        # Include source data if available
        if state.source:
            response["source"] = {
                "funding_rate": state.source.funding_rate,
                "funding_sentiment": state.source.funding_sentiment,
                "oi_change_24h": state.source.oi_change_24h,
                "oi_expansion": state.source.oi_expansion,
                "liquidation_imbalance": state.source.liquidation_imbalance,
                "volume_spike_ratio": state.source.volume_spike_ratio,
                "price_momentum": state.source.price_momentum,
                "trend_acceleration": state.source.trend_acceleration,
            }
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{symbol}")
async def get_reflexivity_history(
    symbol: str,
    limit: int = Query(default=100, le=500),
    hours_back: Optional[int] = Query(default=None, le=720),
):
    """
    Get historical reflexivity data for a symbol.
    """
    registry = get_reflexivity_registry()
    
    try:
        history = registry.get_history(symbol.upper(), limit, hours_back)
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "count": len(history),
            "records": [
                {
                    "reflexivity_score": h.reflexivity_score,
                    "feedback_direction": h.feedback_direction,
                    "sentiment_state": h.sentiment_state,
                    "crowd_positioning": h.crowd_positioning,
                    "confidence": h.confidence,
                    "recorded_at": h.recorded_at.isoformat(),
                }
                for h in history
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recompute/{symbol}")
async def recompute_reflexivity(
    symbol: str,
    save: bool = Query(default=True),
):
    """
    Recompute reflexivity for a symbol and optionally save to MongoDB.
    """
    engine = get_reflexivity_engine()
    registry = get_reflexivity_registry()
    
    try:
        state = engine.analyze(symbol.upper())
        
        saved = False
        if save:
            saved = registry.save_state(state)
        
        return {
            "status": "ok",
            "symbol": state.symbol,
            "reflexivity_score": state.reflexivity_score,
            "feedback_direction": state.feedback_direction,
            "strength": state.strength,
            "confidence": state.confidence,
            "saved": saved,
            "timestamp": state.timestamp.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modifier/{symbol}")
async def get_reflexivity_modifier(
    symbol: str,
    hypothesis_direction: str = Query(default="LONG", pattern="^(LONG|SHORT)$"),
):
    """
    Get reflexivity modifier for hypothesis engine.
    
    The modifier adjusts hypothesis scores based on reflexivity:
    - Positive feedback aligned with direction = boost
    - Negative feedback (exhaustion) = reduce
    """
    engine = get_reflexivity_engine()
    
    try:
        modifier = engine.get_modifier(symbol.upper(), hypothesis_direction)
        
        return {
            "status": "ok",
            "symbol": modifier.symbol,
            "reflexivity_score": modifier.reflexivity_score,
            "reflexivity_weight": modifier.reflexivity_weight,
            "weighted_contribution": modifier.weighted_contribution,
            "feedback_direction": modifier.feedback_direction,
            "is_trend_aligned": modifier.is_trend_aligned,
            "modifier": modifier.modifier,
            "strength": modifier.strength,
            "confidence": modifier.confidence,
            "reason": modifier.reason,
            "hypothesis_direction": hypothesis_direction,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{symbol}")
async def get_reflexivity_summary(symbol: str):
    """
    Get summary statistics for reflexivity analysis.
    """
    registry = get_reflexivity_registry()
    
    try:
        summary = registry.get_summary(symbol.upper())
        
        if summary is None:
            return {
                "status": "ok",
                "symbol": symbol.upper(),
                "total_records": 0,
                "message": "No reflexivity data available",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        return {
            "status": "ok",
            "symbol": summary.symbol,
            
            # Current
            "current_score": summary.current_score,
            "current_direction": summary.current_direction,
            "current_strength": summary.current_strength,
            
            # Historical
            "total_records": summary.total_records,
            "avg_score": summary.avg_score,
            
            # Distribution
            "direction_distribution": {
                "positive": summary.positive_feedback_count,
                "negative": summary.negative_feedback_count,
                "neutral": summary.neutral_count,
            },
            "strength_distribution": {
                "strong": summary.strong_reflexivity_count,
                "moderate": summary.moderate_reflexivity_count,
                "weak": summary.weak_reflexivity_count,
            },
            
            # Recent
            "recent_avg_score": summary.recent_avg_score,
            "score_trend": summary.score_trend,
            
            "last_updated": summary.last_updated.isoformat() if summary.last_updated else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Batch Operations
# ══════════════════════════════════════════════════════════════

@router.post("/batch/compute")
async def batch_compute_reflexivity(
    symbols: list[str] = Query(default=["BTC", "ETH", "SOL"]),
    save: bool = Query(default=True),
):
    """
    Compute reflexivity for multiple symbols.
    """
    engine = get_reflexivity_engine()
    registry = get_reflexivity_registry()
    
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
                "reflexivity_score": state.reflexivity_score,
                "feedback_direction": state.feedback_direction,
                "strength": state.strength,
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
    registry = get_reflexivity_registry()
    
    symbols = registry.get_all_symbols()
    summaries = []
    
    for symbol in symbols:
        summary = registry.get_summary(symbol)
        if summary:
            summaries.append({
                "symbol": summary.symbol,
                "current_score": summary.current_score,
                "current_direction": summary.current_direction,
                "current_strength": summary.current_strength,
                "total_records": summary.total_records,
            })
    
    return {
        "status": "ok",
        "symbols_count": len(symbols),
        "summaries": summaries,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
