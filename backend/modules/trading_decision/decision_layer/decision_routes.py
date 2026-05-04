"""
PHASE 14.4 — Trading Decision API Routes
=========================================
REST API endpoints for Trading Decision Layer.

Endpoints:
- GET /api/trading-decision/status
- GET /api/trading-decision/batch
- GET /api/trading-decision/full/{symbol}
- GET /api/trading-decision/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone

from modules.trading_decision.decision_layer.decision_engine import get_decision_engine

router = APIRouter(prefix="/api/trading-decision", tags=["Trading Decision"])


# ═══════════════════════════════════════════════════════════════
# STATIC ROUTES (must come before dynamic {symbol} routes)
# ═══════════════════════════════════════════════════════════════

@router.get("/status")
async def trading_decision_status():
    """
    Get Trading Decision module status.
    """
    return {
        "status": "ok",
        "module": "Trading Decision Layer",
        "phase": "14.4",
        "description": "Final trading decision from TA + Exchange + Market State",
        "available_actions": [
            "ALLOW",
            "ALLOW_REDUCED",
            "ALLOW_AGGRESSIVE",
            "BLOCK",
            "WAIT",
            "REVERSE_CANDIDATE",
        ],
        "execution_modes": [
            "NONE",
            "PASSIVE",
            "NORMAL",
            "AGGRESSIVE",
            "WAIT",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/batch")
async def get_trading_decision_batch(
    symbols: str = Query(default="BTC,ETH,SOL", description="Comma-separated symbols")
):
    """
    Get trading decisions for multiple symbols.
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        engine = get_decision_engine()
        
        results = []
        for sym in symbol_list:
            try:
                decision = engine.decide(sym)
                results.append({
                    "symbol": sym,
                    "status": "ok",
                    "data": decision.to_dict(),
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
async def get_trading_decision_summary(
    symbols: str = Query(default="BTC,ETH,SOL", description="Comma-separated symbols")
):
    """
    Get condensed trading decision summary.
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        engine = get_decision_engine()
        
        summary = []
        for sym in symbol_list:
            try:
                decision = engine.decide(sym)
                summary.append({
                    "symbol": sym,
                    "action": decision.action.value,
                    "direction": decision.direction.value,
                    "confidence": round(decision.confidence, 3),
                    "position_multiplier": round(decision.position_multiplier, 3),
                    "execution_mode": decision.execution_mode.value,
                    "reason": decision.reason,
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
async def get_trading_decision_full(symbol: str):
    """
    Get full trading decision with all input summaries.
    
    Includes TA, Exchange, and Market State summaries for debugging.
    """
    try:
        engine = get_decision_engine()
        decision = engine.decide(symbol.upper())
        
        return {
            "status": "ok",
            "data": decision.to_full_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}")
async def get_trading_decision(symbol: str):
    """
    Get trading decision for a symbol.
    
    Returns the final trading action recommendation.
    """
    try:
        engine = get_decision_engine()
        decision = engine.decide(symbol.upper())
        
        return {
            "status": "ok",
            "data": decision.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
