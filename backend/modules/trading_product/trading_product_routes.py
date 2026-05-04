"""
PHASE 14.7 — Trading Product API Routes
========================================
REST API endpoints for unified Trading Product.

Endpoints:
- GET /api/trading-product/status
- GET /api/trading-product/batch
- GET /api/trading-product/summary
- GET /api/trading-product/full/{symbol}
- GET /api/trading-product/{symbol}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone

from modules.trading_product.trading_product_engine import get_trading_product_engine

router = APIRouter(prefix="/api/trading-product", tags=["Trading Product"])


# ═══════════════════════════════════════════════════════════════
# STATIC ROUTES (must come before dynamic {symbol} routes)
# ═══════════════════════════════════════════════════════════════

@router.get("/status")
async def trading_product_status():
    """
    Get Trading Product module status.
    """
    return {
        "status": "ok",
        "module": "Trading Product",
        "phase": "14.7",
        "description": "Unified trading product combining all modules",
        "pipeline": [
            "TAHypothesis (14.2)",
            "ExchangeContext (13.8)",
            "MarketStateMatrix (14.3)",
            "TradingDecision (14.4)",
            "PositionSizing (14.5)",
            "ExecutionMode (14.6)",
        ],
        "product_statuses": [
            "READY",
            "BLOCKED",
            "WAIT",
            "CONFLICTED",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/batch")
async def get_trading_product_batch(
    symbols: str = Query(default="BTC,ETH,SOL", description="Comma-separated symbols")
):
    """
    Get trading product snapshots for multiple symbols.
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        engine = get_trading_product_engine()
        
        results = []
        for sym in symbol_list:
            try:
                snapshot = engine.compute(sym)
                results.append({
                    "symbol": sym,
                    "status": "ok",
                    "data": snapshot.to_dict(),
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
async def get_trading_product_summary(
    symbols: str = Query(default="BTC,ETH,SOL", description="Comma-separated symbols")
):
    """
    Get condensed trading product summary.
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        engine = get_trading_product_engine()
        
        summary = []
        for sym in symbol_list:
            try:
                snapshot = engine.compute(sym)
                summary.append(snapshot.to_summary_dict())
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
async def get_trading_product_full(symbol: str):
    """
    Get full trading product snapshot with all module outputs.
    
    This is THE endpoint for complete trading intelligence.
    """
    try:
        engine = get_trading_product_engine()
        snapshot = engine.compute(symbol.upper())
        
        return {
            "status": "ok",
            "data": snapshot.to_full_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}")
async def get_trading_product(symbol: str):
    """
    Get trading product snapshot for a symbol.
    
    Returns unified final outputs without module details.
    """
    try:
        engine = get_trading_product_engine()
        snapshot = engine.compute(symbol.upper())
        
        return {
            "status": "ok",
            "data": snapshot.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
