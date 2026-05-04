"""
Terminal State Routes - Unified API for Trading Terminal

This is THE ONLY endpoint the /trading UI should call.
All other terminal APIs are INTERNAL.

Endpoints:
- GET /api/terminal/state/{symbol}?timeframe=4H - Full terminal state
- GET /api/terminal/state/{symbol}/health - Health check
- GET /api/terminal/state/{symbol}/decision?timeframe=4H - Decision only
- GET /api/terminal/state/{symbol}/micro - Microstructure only
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional

from .terminal_state_engine import get_terminal_engine

router = APIRouter(prefix="/api/terminal/state", tags=["Terminal State Orchestrator"])

# Valid timeframes
VALID_TIMEFRAMES = ["1H", "4H", "1D"]


@router.get("/health")
async def state_orchestrator_health():
    """Health check for terminal state orchestrator"""
    return {
        "ok": True,
        "module": "terminal_state_orchestrator",
        "version": "2.0",
        "description": "Unified Trading Terminal API with Timeframe Support",
        "usage": "GET /api/terminal/state/{symbol}?timeframe=4H",
        "valid_timeframes": VALID_TIMEFRAMES,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/{symbol}")
async def get_terminal_state(
    symbol: str, 
    timeframe: str = Query(default="4H", description="Timeframe: 1H, 4H, or 1D")
):
    """
    GET UNIFIED TERMINAL STATE
    
    This is THE endpoint for /trading UI.
    Returns ALL data needed for the terminal in ONE call.
    
    Query Parameters:
    - timeframe: 1H | 4H | 1D (default: 4H)
    
    Response includes:
    - timeframe: active timeframe (system parameter)
    - decision: action, confidence, direction, mode, reasons
    - execution: mode, size, entry, stop, target, rr, timeframe
    - micro: imbalance, spread, liquidity, state
    - position: current position for symbol
    - portfolio: equity, exposure, risk
    - risk: heat, drawdown, status, alerts
    - strategy: profile, paused, override
    - system: mode, adaptive, scheduler
    - validation: consistency checks with timeframe awareness
    """
    symbol = symbol.upper()
    timeframe = timeframe.upper() if timeframe.upper() in VALID_TIMEFRAMES else "4H"
    
    engine = get_terminal_engine()
    state = await engine.get_terminal_state(symbol, timeframe)
    
    return {
        "ok": True,
        "data": state
    }


@router.get("/{symbol}/decision")
async def get_decision_only(
    symbol: str,
    timeframe: str = Query(default="4H", description="Timeframe: 1H, 4H, or 1D")
):
    """Get decision block only (lighter endpoint)"""
    symbol = symbol.upper()
    timeframe = timeframe.upper() if timeframe.upper() in VALID_TIMEFRAMES else "4H"
    
    engine = get_terminal_engine()
    state = await engine.get_terminal_state(symbol, timeframe)
    
    return {
        "ok": True,
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": state.get("timestamp"),
        "decision": state.get("decision"),
        "execution": state.get("execution")
    }


@router.get("/{symbol}/micro")
async def get_micro_only(symbol: str):
    """Get microstructure block only (lighter endpoint)"""
    symbol = symbol.upper()
    
    engine = get_terminal_engine()
    state = await engine.get_terminal_state(symbol)
    
    return {
        "ok": True,
        "symbol": symbol,
        "timestamp": state.get("timestamp"),
        "micro": state.get("micro")
    }


@router.get("/{symbol}/position")
async def get_position_only(symbol: str):
    """Get position block only"""
    symbol = symbol.upper()
    
    engine = get_terminal_engine()
    state = await engine.get_terminal_state(symbol)
    
    return {
        "ok": True,
        "symbol": symbol,
        "timestamp": state.get("timestamp"),
        "position": state.get("position"),
        "portfolio": state.get("portfolio")
    }


@router.get("/{symbol}/risk")
async def get_risk_only(symbol: str):
    """Get risk block only"""
    symbol = symbol.upper()
    
    engine = get_terminal_engine()
    state = await engine.get_terminal_state(symbol)
    
    return {
        "ok": True,
        "symbol": symbol,
        "timestamp": state.get("timestamp"),
        "risk": state.get("risk"),
        "strategy": state.get("strategy")
    }



def _get_integration_engine():
    """
    Get IntegrationEngine instance for AF6.
    
    Returns:
        IntegrationEngine instance or None
    """
    try:
        engine = get_terminal_engine()
        return engine._integration_engine if hasattr(engine, '_integration_engine') else None
    except Exception:
        return None
