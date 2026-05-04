"""
PHASE 14.5 — Position Sizing API Routes
========================================
REST API endpoints for Position Sizing.

Endpoints:
- GET /api/position-sizing/status
- GET /api/position-sizing/batch
- GET /api/position-sizing/summary
- GET /api/position-sizing/full/{symbol}
- GET /api/position-sizing/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone

from modules.trading_decision.position_sizing.position_sizing_engine import get_position_sizing_engine

router = APIRouter(prefix="/api/position-sizing", tags=["Position Sizing"])


# ═══════════════════════════════════════════════════════════════
# STATIC ROUTES (must come before dynamic {symbol} routes)
# ═══════════════════════════════════════════════════════════════

@router.get("/status")
async def position_sizing_status():
    """
    Get Position Sizing module status.
    """
    return {
        "status": "ok",
        "module": "Position Sizing Logic v2",
        "phase": "14.5",
        "description": "Granular position sizing based on multiple factors",
        "base_risk_pct": 1.0,
        "size_buckets": ["NONE", "TINY", "SMALL", "NORMAL", "LARGE"],
        "adjustment_factors": [
            "risk_multiplier (from decision action)",
            "volatility_adjustment",
            "exchange_adjustment",
            "market_adjustment",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/batch")
async def get_position_sizing_batch(
    symbols: str = Query(default="BTC,ETH,SOL", description="Comma-separated symbols")
):
    """
    Get position sizing for multiple symbols.
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        engine = get_position_sizing_engine()
        
        results = []
        for sym in symbol_list:
            try:
                sizing = engine.compute(sym)
                results.append({
                    "symbol": sym,
                    "status": "ok",
                    "data": sizing.to_dict(),
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
async def get_position_sizing_summary(
    symbols: str = Query(default="BTC,ETH,SOL", description="Comma-separated symbols")
):
    """
    Get condensed position sizing summary.
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        engine = get_position_sizing_engine()
        
        summary = []
        for sym in symbol_list:
            try:
                sizing = engine.compute(sym)
                summary.append({
                    "symbol": sym,
                    "final_size_pct": round(sizing.final_size_pct, 4),
                    "size_bucket": sizing.size_bucket.value,
                    "risk_multiplier": round(sizing.risk_multiplier, 3),
                    "vol_adj": round(sizing.volatility_adjustment, 3),
                    "ex_adj": round(sizing.exchange_adjustment, 3),
                    "mkt_adj": round(sizing.market_adjustment, 3),
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
async def get_position_sizing_full(symbol: str):
    """
    Get full position sizing with decision summary.
    
    Includes debugging information.
    """
    try:
        engine = get_position_sizing_engine()
        sizing = engine.compute(symbol.upper())
        
        return {
            "status": "ok",
            "data": sizing.to_full_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}")
async def get_position_sizing(symbol: str):
    """
    Get position sizing for a symbol.
    
    Returns final position size and adjustments.
    """
    try:
        engine = get_position_sizing_engine()
        sizing = engine.compute(symbol.upper())
        
        return {
            "status": "ok",
            "data": sizing.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
