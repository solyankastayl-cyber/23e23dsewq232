"""
PHASE 14.8 — Market Structure API Routes
=========================================
REST API endpoints for Dominance & Breadth analysis.

Endpoints:
- GET /api/market-structure/status
- GET /api/market-structure/dominance
- GET /api/market-structure/breadth
- GET /api/market-structure/state
- GET /api/market-structure/modifier/{symbol}
- GET /api/market-structure/summary
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone

from modules.market_structure.breadth_dominance.dominance_engine import get_dominance_engine
from modules.market_structure.breadth_dominance.breadth_engine import get_breadth_engine
from modules.market_structure.breadth_dominance.market_structure_engine import get_market_structure_engine

router = APIRouter(prefix="/api/market-structure", tags=["Market Structure"])


@router.get("/status")
async def market_structure_status():
    """
    Get Market Structure module status.
    """
    return {
        "status": "ok",
        "module": "Dominance & Breadth Layer",
        "phase": "14.8",
        "description": "Market structure analysis for capital distribution",
        "dominance_regimes": ["BTC_DOM", "ETH_DOM", "ALT_DOM", "BALANCED"],
        "rotation_states": ["ROTATING_TO_BTC", "ROTATING_TO_ETH", "ROTATING_TO_ALTS", "STABLE", "EXITING_MARKET"],
        "breadth_states": ["STRONG", "WEAK", "MIXED"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/dominance")
async def get_dominance():
    """
    Get current market dominance state.
    """
    try:
        engine = get_dominance_engine()
        dominance = engine.compute()
        
        return {
            "status": "ok",
            "data": dominance.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/breadth")
async def get_breadth():
    """
    Get current market breadth state.
    """
    try:
        engine = get_breadth_engine()
        breadth = engine.compute()
        
        return {
            "status": "ok",
            "data": breadth.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state")
async def get_market_structure_state():
    """
    Get full market structure state (dominance + breadth + modifiers).
    """
    try:
        engine = get_market_structure_engine()
        state = engine.compute()
        
        return {
            "status": "ok",
            "data": state.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modifier/{symbol}")
async def get_symbol_modifier(symbol: str):
    """
    Get trading modifiers for specific symbol based on market structure.
    """
    try:
        engine = get_market_structure_engine()
        modifiers = engine.get_modifier_for_symbol(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "modifiers": modifiers,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_market_structure_summary():
    """
    Get condensed market structure summary.
    """
    try:
        engine = get_market_structure_engine()
        state = engine.compute()
        
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": state.to_summary_dict(),
            "modifiers": {
                "btc": round(state.btc_confidence_modifier, 3),
                "eth": round(state.eth_confidence_modifier, 3),
                "alt": round(state.alt_confidence_modifier, 3),
                "size": round(state.size_modifier, 3),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
