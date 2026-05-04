"""
PHASE 14.3 — Market State API Routes
=====================================
REST API endpoints for Market State Matrix.

Endpoints:
- GET /api/market-state/status
- GET /api/market-state/batch
- GET /api/market-state/summary
- GET /api/market-state/full/{symbol}
- GET /api/market-state/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone

from modules.trading_decision.market_state import (
    get_market_state_builder,
    MarketStateMatrix,
)

router = APIRouter(prefix="/api/market-state", tags=["Market State"])


# ═══════════════════════════════════════════════════════════════
# STATIC ROUTES (must come before dynamic {symbol} routes)
# ═══════════════════════════════════════════════════════════════

@router.get("/status")
async def market_state_status():
    """
    Get Market State module status.
    """
    return {
        "status": "ok",
        "module": "Market State Matrix",
        "phase": "14.3",
        "description": "Multi-dimensional market state for Trading Decision Layer",
        "available_states": {
            "trend": ["TREND_UP", "TREND_DOWN", "RANGE", "MIXED"],
            "volatility": ["LOW", "NORMAL", "HIGH", "EXPANDING"],
            "exchange": ["BULLISH", "BEARISH", "CONFLICTED", "NEUTRAL"],
            "derivatives": ["CROWDED_LONG", "CROWDED_SHORT", "BALANCED", "SQUEEZE"],
            "breadth": ["BTC_DOM", "ALT_DOM", "MIXED", "UNKNOWN"],
            "risk": ["RISK_ON", "RISK_OFF", "NEUTRAL"],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/batch")
async def get_market_state_batch(
    symbols: str = Query(default="BTC,ETH,SOL", description="Comma-separated symbols")
):
    """
    Get market state for multiple symbols.
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        builder = get_market_state_builder()
        
        results = []
        for sym in symbol_list:
            try:
                state = builder.build(sym)
                results.append({
                    "symbol": sym,
                    "status": "ok",
                    "data": state.to_dict(),
                })
            except Exception as e:
                results.append({
                    "symbol": sym,
                    "status": "error",
                    "error": str(e),
                })
        
        return {
            "status": "ok",
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_market_state_summary(
    symbols: str = Query(default="BTC,ETH,SOL", description="Comma-separated symbols")
):
    """
    Get condensed market state summary for multiple symbols.
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        builder = get_market_state_builder()
        
        summary = []
        for sym in symbol_list:
            try:
                state = builder.build(sym)
                summary.append({
                    "symbol": sym,
                    "trend": state.trend_state.value,
                    "volatility": state.volatility_state.value,
                    "exchange": state.exchange_state.value,
                    "combined": state.combined_state.value,
                    "confidence": round(state.confidence, 3),
                })
            except Exception as e:
                summary.append({
                    "symbol": sym,
                    "error": str(e),
                })
        
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════
# DYNAMIC ROUTES (with {symbol} parameter)
# ═══════════════════════════════════════════════════════════════

@router.get("/full/{symbol}")
async def get_market_state_full(symbol: str):
    """
    Get full market state matrix with raw scores.
    
    Includes debugging information.
    """
    try:
        builder = get_market_state_builder()
        state = builder.build(symbol.upper())
        
        return {
            "status": "ok",
            "data": state.to_full_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}")
async def get_market_state(symbol: str):
    """
    Get market state matrix for a symbol.
    
    Returns simplified state view.
    """
    try:
        builder = get_market_state_builder()
        state = builder.build(symbol.upper())
        
        return {
            "status": "ok",
            "data": state.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
