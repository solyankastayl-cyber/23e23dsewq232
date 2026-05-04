"""
PHASE 4.6 — Entry Timing Backtest Routes

API endpoints for Entry Timing Stack validation.
"""

from fastapi import APIRouter, Query
from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel

from .entry_timing_backtester import get_entry_timing_backtester


router = APIRouter(prefix="/api/entry-timing/backtest", tags=["entry-timing-backtest"])


class TradeInput(BaseModel):
    entry_mode: str = "ENTER_NOW"
    execution_strategy: str = "FULL_ENTRY_NOW"
    wrong_early: bool = False
    win: bool = True
    pnl: float = 0.0
    rr: float = 1.0
    slippage: float = 0.0


class BacktestInput(BaseModel):
    trades_before: List[TradeInput]
    trades_after: List[TradeInput]


@router.get("/health")
async def backtest_health():
    """Health check for backtester module."""
    engine = get_entry_timing_backtester()
    return engine.health_check()


@router.post("/run")
async def run_backtest(data: BacktestInput):
    """
    Run backtest comparison between before/after trades.
    
    Compares Wrong Early rate, win rate, PnL, and other metrics.
    """
    engine = get_entry_timing_backtester()
    
    trades_before = [t.dict() for t in data.trades_before]
    trades_after = [t.dict() for t in data.trades_after]
    
    result = engine.run(trades_before, trades_after)
    
    return {
        "ok": True,
        **result
    }


@router.post("/simulate")
async def simulate_backtest(count: int = Query(100, ge=20, le=500)):
    """
    Run simulated backtest with generated trades.
    
    Useful for testing and demonstrating the backtester.
    """
    engine = get_entry_timing_backtester()
    result = engine.simulate_backtest(count)
    
    return {
        "ok": True,
        **result
    }


@router.get("/history")
async def get_history(limit: int = Query(10, ge=1, le=50)):
    """Get recent backtest results."""
    engine = get_entry_timing_backtester()
    history = engine.get_history(limit)
    
    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/validate-phase4")
async def validate_phase4():
    """
    Run simulation and validate Phase 4 goals.
    
    Returns whether Entry Timing Stack achieved its targets.
    """
    engine = get_entry_timing_backtester()
    result = engine.simulate_backtest(150)
    
    return {
        "ok": True,
        "validation": result["phase_4_validation"],
        "wrong_early": result["wrong_early_remeasurement"],
        "summary": result["comparison"]["summary"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
