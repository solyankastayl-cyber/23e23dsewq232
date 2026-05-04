"""
PHASE 14.6 — Execution Mode API Routes
=======================================
REST API endpoints for Execution Mode.

Endpoints:
- GET /api/execution-mode/status
- GET /api/execution-mode/batch
- GET /api/execution-mode/summary
- GET /api/execution-mode/full/{symbol}
- GET /api/execution-mode/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone

from modules.trading_decision.execution_mode.execution_mode_engine import get_execution_mode_engine

router = APIRouter(prefix="/api/execution-mode", tags=["Execution Mode"])


# ═══════════════════════════════════════════════════════════════
# STATIC ROUTES (must come before dynamic {symbol} routes)
# ═══════════════════════════════════════════════════════════════

@router.get("/status")
async def execution_mode_status():
    """
    Get Execution Mode module status.
    """
    return {
        "status": "ok",
        "module": "Execution Mode Layer",
        "phase": "14.6",
        "description": "Determines HOW to execute trades based on multiple factors",
        "execution_modes": [
            "NONE",
            "PASSIVE",
            "NORMAL",
            "AGGRESSIVE",
            "DELAYED",
            "PARTIAL_ENTRY",
        ],
        "entry_styles": [
            "MARKET",
            "LIMIT",
            "STAGED",
            "WAIT",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/batch")
async def get_execution_mode_batch(
    symbols: str = Query(default="BTC,ETH,SOL", description="Comma-separated symbols")
):
    """
    Get execution mode for multiple symbols.
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        engine = get_execution_mode_engine()
        
        results = []
        for sym in symbol_list:
            try:
                mode = engine.compute(sym)
                results.append({
                    "symbol": sym,
                    "status": "ok",
                    "data": mode.to_dict(),
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
async def get_execution_mode_summary(
    symbols: str = Query(default="BTC,ETH,SOL", description="Comma-separated symbols")
):
    """
    Get condensed execution mode summary.
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        engine = get_execution_mode_engine()
        
        summary = []
        for sym in symbol_list:
            try:
                mode = engine.compute(sym)
                summary.append({
                    "symbol": sym,
                    "execution_mode": mode.execution_mode.value,
                    "urgency_score": round(mode.urgency_score, 4),
                    "slippage_tolerance": round(mode.slippage_tolerance, 4),
                    "entry_style": mode.entry_style.value,
                    "partial_ratio": round(mode.partial_ratio, 4),
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
async def get_execution_mode_full(symbol: str):
    """
    Get full execution mode with decision and sizing summaries.
    
    Includes debugging information.
    """
    try:
        engine = get_execution_mode_engine()
        mode = engine.compute(symbol.upper())
        
        return {
            "status": "ok",
            "data": mode.to_full_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}")
async def get_execution_mode(symbol: str):
    """
    Get execution mode for a symbol.
    
    Returns how to execute the trade.
    """
    try:
        engine = get_execution_mode_engine()
        mode = engine.compute(symbol.upper())
        
        return {
            "status": "ok",
            "data": mode.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
