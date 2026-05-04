"""
Regime Memory Routes

PHASE 34 — Market Regime Memory Layer

API Endpoints:
- GET  /api/v1/regime-memory/{symbol}           — Current memory analysis
- GET  /api/v1/regime-memory/top/{symbol}       — Top matches
- GET  /api/v1/regime-memory/patterns/{symbol}  — Patterns analysis
- POST /api/v1/regime-memory/recompute/{symbol} — Trigger recomputation
- GET  /api/v1/regime-memory/summary/{symbol}   — Memory summary
- GET  /api/v1/regime-memory/modifier/{symbol}  — Get hypothesis modifier
- GET  /api/v1/regime-memory/health             — Module health check
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException

from .memory_types import (
    MemoryResponse,
    MemoryMatch,
    MemoryPattern,
    MemorySummary,
    MemoryModifier,
    RegimeMemoryRecord,
    SIMILARITY_THRESHOLD,
)
from .memory_engine import get_memory_engine
from .memory_registry import get_memory_registry


# ══════════════════════════════════════════════════════════════
# Router
# ══════════════════════════════════════════════════════════════

router = APIRouter(
    prefix="/api/v1/regime-memory",
    tags=["PHASE 34 - Regime Memory"],
)


# ══════════════════════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def memory_health():
    """
    Regime Memory module health check.
    """
    registry = get_memory_registry()
    engine = get_memory_engine()
    
    # TASK 93: Include auto-writer stats
    try:
        from .memory_auto_writer import get_memory_auto_writer
        auto_writer = get_memory_auto_writer()
        auto_writer_stats = auto_writer.get_stats()
    except Exception:
        auto_writer_stats = {"total_written": 0, "error": "not available"}
    
    return {
        "status": "ok",
        "module": "regime_memory",
        "phase": "34",
        "registry_initialized": registry._initialized,
        "engine_ready": engine is not None,
        "auto_writer": auto_writer_stats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/auto-writer/stats")
async def get_auto_writer_stats():
    """
    TASK 93: Get auto-writer statistics.
    
    Returns:
    - total_written: Total outcomes written to memory
    - registry_initialized: MongoDB connection status
    """
    try:
        from .memory_auto_writer import get_memory_auto_writer
        auto_writer = get_memory_auto_writer()
        stats = auto_writer.get_stats()
        
        return {
            "status": "ok",
            "total_written": stats["total_written"],
            "registry_initialized": stats["registry_initialized"],
            "feature": "TASK 93 - Auto-write Memory Records",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Main Analysis Endpoint
# ══════════════════════════════════════════════════════════════

@router.get("/{symbol}", response_model=MemoryResponse)
async def get_memory_analysis(
    symbol: str,
    threshold: float = Query(default=SIMILARITY_THRESHOLD, ge=0.5, le=1.0),
    limit: int = Query(default=10, ge=1, le=100),
):
    """
    Get memory analysis for a symbol.
    
    Finds historical situations similar to current market state
    and returns aggregated signals.
    
    Parameters:
    - symbol: Trading symbol (e.g., BTC, ETH)
    - threshold: Minimum similarity threshold (default: 0.75)
    - limit: Maximum matches to return (default: 10)
    """
    symbol = symbol.upper()
    
    try:
        registry = get_memory_registry()
        engine = get_memory_engine()
        
        # Get historical records
        records = registry.get_records_by_symbol(symbol, limit=1000)
        
        # Query memory
        response = engine.query_memory(
            symbol=symbol,
            records=records,
            threshold=threshold,
            limit=limit,
        )
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Top Matches Endpoint
# ══════════════════════════════════════════════════════════════

@router.get("/top/{symbol}")
async def get_top_matches(
    symbol: str,
    limit: int = Query(default=5, ge=1, le=20),
):
    """
    Get top memory matches for a symbol.
    
    Returns the most similar historical situations.
    """
    symbol = symbol.upper()
    
    try:
        registry = get_memory_registry()
        engine = get_memory_engine()
        
        records = registry.get_records_by_symbol(symbol, limit=1000)
        response = engine.query_memory(symbol, records, limit=limit)
        
        return {
            "symbol": symbol,
            "top_matches": [m.model_dump() for m in response.top_matches],
            "best_similarity": response.best_similarity,
            "expected_direction": response.expected_direction,
            "memory_score": response.memory_score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Patterns Endpoint
# ══════════════════════════════════════════════════════════════

@router.get("/patterns/{symbol}")
async def get_memory_patterns(
    symbol: str,
    min_occurrences: int = Query(default=3, ge=1),
):
    """
    Get recurring patterns from memory analysis.
    
    Analyzes historical records to find patterns by regime and hypothesis.
    """
    symbol = symbol.upper()
    
    try:
        registry = get_memory_registry()
        engine = get_memory_engine()
        
        records = registry.get_records_by_symbol(symbol, limit=1000)
        patterns = engine.analyze_patterns(symbol, records)
        
        # Filter by minimum occurrences
        patterns = [p for p in patterns if p.occurrence_count >= min_occurrences]
        
        return {
            "symbol": symbol,
            "patterns": [p.model_dump() for p in patterns],
            "total_patterns": len(patterns),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Recompute Endpoint
# ══════════════════════════════════════════════════════════════

@router.post("/recompute/{symbol}")
async def recompute_memory(
    symbol: str,
    prune_old: bool = Query(default=False, description="Prune records older than 365 days"),
):
    """
    Trigger memory recomputation for a symbol.
    
    This is typically called by the scheduler every 60 minutes.
    
    Steps:
    1. Optionally prune old records
    2. Rebuild structure vector
    3. Query memory with fresh data
    4. Update cached response
    """
    symbol = symbol.upper()
    
    try:
        registry = get_memory_registry()
        engine = get_memory_engine()
        
        pruned_count = 0
        if prune_old:
            pruned_count = registry.prune_old_records(symbol, days_to_keep=365)
        
        # Get fresh records
        records = registry.get_records_by_symbol(symbol, limit=1000)
        
        # Recompute
        response = engine.query_memory(symbol, records)
        
        return {
            "status": "ok",
            "symbol": symbol,
            "records_pruned": pruned_count,
            "records_analyzed": response.total_records_searched,
            "matches_found": response.matches_found,
            "memory_score": response.memory_score,
            "expected_direction": response.expected_direction,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Summary Endpoint
# ══════════════════════════════════════════════════════════════

@router.get("/summary/{symbol}", response_model=MemorySummary)
async def get_memory_summary(symbol: str):
    """
    Get summary statistics for regime memory.
    
    Returns success rates by regime and hypothesis type.
    """
    symbol = symbol.upper()
    
    try:
        registry = get_memory_registry()
        engine = get_memory_engine()
        
        records = registry.get_records_by_symbol(symbol, limit=1000)
        summary = engine.generate_summary(symbol, records)
        
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Modifier Endpoint (for Hypothesis Engine)
# ══════════════════════════════════════════════════════════════

@router.get("/modifier/{symbol}", response_model=MemoryModifier)
async def get_memory_modifier(
    symbol: str,
    hypothesis_direction: str = Query(default="NEUTRAL", description="LONG, SHORT, or NEUTRAL"),
):
    """
    Get memory modifier for hypothesis engine.
    
    Returns a modifier value based on historical pattern alignment.
    
    Parameters:
    - symbol: Trading symbol
    - hypothesis_direction: Current hypothesis direction (LONG/SHORT/NEUTRAL)
    """
    symbol = symbol.upper()
    hypothesis_direction = hypothesis_direction.upper()
    
    if hypothesis_direction not in ["LONG", "SHORT", "NEUTRAL"]:
        hypothesis_direction = "NEUTRAL"
    
    try:
        registry = get_memory_registry()
        engine = get_memory_engine()
        
        records = registry.get_records_by_symbol(symbol, limit=1000)
        modifier = engine.get_memory_modifier(symbol, hypothesis_direction, records)
        
        return modifier
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Stats Endpoint
# ══════════════════════════════════════════════════════════════

@router.get("/stats/{symbol}")
async def get_memory_stats(symbol: str):
    """
    Get database statistics for regime memory.
    """
    symbol = symbol.upper()
    
    try:
        registry = get_memory_registry()
        stats = registry.get_stats(symbol)
        
        return {
            "status": "ok",
            **stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Vector Endpoint (for debugging)
# ══════════════════════════════════════════════════════════════

@router.get("/vector/{symbol}")
async def get_current_vector(symbol: str):
    """
    Get current structure vector for a symbol.
    
    Returns the 7-element normalized vector used for similarity matching.
    """
    symbol = symbol.upper()
    
    try:
        engine = get_memory_engine()
        vector = engine.build_structure_vector(symbol)
        
        return {
            "symbol": symbol,
            "vector": vector.to_vector(),
            "components": {
                "trend_slope": vector.trend_slope,
                "volatility": vector.volatility,
                "volume_delta": vector.volume_delta,
                "microstructure_bias": vector.microstructure_bias,
                "liquidity_state": vector.liquidity_state,
                "regime_numeric": vector.regime_numeric,
                "fractal_alignment": vector.fractal_alignment,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Filter Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/by-regime/{symbol}/{regime_state}")
async def get_memory_by_regime(
    symbol: str,
    regime_state: str,
    limit: int = Query(default=100, ge=1, le=500),
):
    """
    Get memory records filtered by regime state.
    
    Parameters:
    - symbol: Trading symbol
    - regime_state: TRENDING, RANGING, VOLATILE, or UNCERTAIN
    """
    symbol = symbol.upper()
    regime_state = regime_state.upper()
    
    valid_regimes = ["TRENDING", "RANGING", "VOLATILE", "UNCERTAIN"]
    if regime_state not in valid_regimes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid regime_state. Must be one of: {valid_regimes}",
        )
    
    try:
        registry = get_memory_registry()
        records = registry.get_records_by_regime(symbol, regime_state, limit)
        
        successful = sum(1 for r in records if r.success)
        success_rate = successful / len(records) if records else 0.0
        
        return {
            "symbol": symbol,
            "regime_state": regime_state,
            "records_count": len(records),
            "success_rate": round(success_rate, 4),
            "avg_future_move": round(
                sum(r.future_move_percent for r in records) / len(records) if records else 0.0,
                4
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-hypothesis/{symbol}/{hypothesis_type}")
async def get_memory_by_hypothesis(
    symbol: str,
    hypothesis_type: str,
    limit: int = Query(default=100, ge=1, le=500),
):
    """
    Get memory records filtered by hypothesis type.
    
    Parameters:
    - symbol: Trading symbol
    - hypothesis_type: BULLISH_CONTINUATION, BEARISH_CONTINUATION, etc.
    """
    symbol = symbol.upper()
    hypothesis_type = hypothesis_type.upper()
    
    valid_types = [
        "BULLISH_CONTINUATION",
        "BEARISH_CONTINUATION",
        "BREAKOUT_FORMING",
        "RANGE_MEAN_REVERSION",
        "NO_EDGE",
    ]
    if hypothesis_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid hypothesis_type. Must be one of: {valid_types}",
        )
    
    try:
        registry = get_memory_registry()
        records = registry.get_records_by_hypothesis(symbol, hypothesis_type, limit)
        
        successful = sum(1 for r in records if r.success)
        success_rate = successful / len(records) if records else 0.0
        
        return {
            "symbol": symbol,
            "hypothesis_type": hypothesis_type,
            "records_count": len(records),
            "success_rate": round(success_rate, 4),
            "avg_future_move": round(
                sum(r.future_move_percent for r in records) / len(records) if records else 0.0,
                4
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
