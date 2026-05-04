"""
Statistics Routes (STG3)
========================

API endpoints for Strategy Statistics Layer.

Endpoints:
- GET  /api/strategy-stats/health                  - Module health
- GET  /api/strategy-stats/summary                 - All strategies summary
- GET  /api/strategy-stats/{strategy_id}           - Strategy statistics
- GET  /api/strategy-stats/{strategy_id}/decisions - Decision statistics
- GET  /api/strategy-stats/{strategy_id}/profiles  - Profile statistics
- GET  /api/strategy-stats/{strategy_id}/symbols   - Symbol statistics
- GET  /api/strategy-stats/{strategy_id}/regimes   - Regime statistics
- GET  /api/strategy-stats/{strategy_id}/trades    - Trade history
- POST /api/strategy-stats/record/trade            - Record a trade
- POST /api/strategy-stats/record/decision         - Record a decision
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from .statistics_service import statistics_service


router = APIRouter(prefix="/api/strategy-stats", tags=["STG3 - Strategy Statistics"])


# ===========================================
# Request Models
# ===========================================

class RecordTradeInput(BaseModel):
    """Input for recording a trade"""
    strategy_id: str
    symbol: str
    profile_id: str = "BALANCED"
    regime: str = "TRENDING"
    side: str = "LONG"
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float = 0.0
    entry_reason: str = ""
    exit_reason: str = ""
    hold_bars: int = 0
    hold_minutes: float = 0.0


class RecordDecisionInput(BaseModel):
    """Input for recording a decision"""
    strategy_id: str
    symbol: str
    profile_id: str = "BALANCED"
    regime: str = "TRENDING"
    action: str
    reason: str = ""
    signal_score: float = 0.0
    confidence: float = 0.0
    filters_passed: List[str] = []
    filters_blocked: List[str] = []
    risk_veto: bool = False


# ===========================================
# Health & Summary
# ===========================================

@router.get("/health")
async def get_health():
    """Get STG3 module health."""
    return statistics_service.get_health()


@router.get("/summary")
async def get_summary():
    """Get summary of all tracked strategies."""
    return statistics_service.get_all_statistics_summary()


# ===========================================
# Strategy Statistics
# ===========================================

@router.get("/{strategy_id}")
async def get_strategy_statistics(strategy_id: str):
    """Get complete statistics for a strategy."""
    stats = statistics_service.get_statistics(strategy_id)
    
    if not stats:
        # Return empty stats instead of 404
        return {
            "strategyId": strategy_id,
            "trades": {"total": 0, "winning": 0, "losing": 0, "winRate": 0},
            "pnl": {"total": 0, "avg": 0, "expectancy": 0, "profitFactor": 0},
            "message": "No trades recorded yet"
        }
    
    return stats.to_dict()


@router.get("/{strategy_id}/decisions")
async def get_decision_statistics(strategy_id: str):
    """Get decision-level statistics for a strategy."""
    stats = statistics_service.get_decision_statistics(strategy_id)
    
    if not stats or stats.total_decisions == 0:
        return {
            "strategyId": strategy_id,
            "actions": {
                "enterLong": 0,
                "enterShort": 0,
                "exit": 0,
                "hold": 0,
                "block": 0
            },
            "message": "No decisions recorded yet"
        }
    
    return stats.to_dict()


@router.get("/{strategy_id}/profiles")
async def get_profile_statistics(strategy_id: str):
    """Get statistics per profile for a strategy."""
    stats = statistics_service.get_profile_statistics(strategy_id)
    
    return {
        "strategyId": strategy_id,
        "profiles": {pid: s.to_dict() for pid, s in stats.items()},
        "count": len(stats)
    }


@router.get("/{strategy_id}/profiles/{profile_id}")
async def get_profile_stat(strategy_id: str, profile_id: str):
    """Get statistics for specific profile."""
    stat = statistics_service.get_profile_stat(strategy_id, profile_id)
    
    if not stat:
        return {
            "strategyId": strategy_id,
            "profileId": profile_id,
            "message": "No trades for this profile yet"
        }
    
    return stat.to_dict()


@router.get("/{strategy_id}/symbols")
async def get_symbol_statistics(strategy_id: str):
    """Get statistics per symbol for a strategy."""
    stats = statistics_service.get_symbol_statistics(strategy_id)
    
    return {
        "strategyId": strategy_id,
        "symbols": {sym: s.to_dict() for sym, s in stats.items()},
        "count": len(stats)
    }


@router.get("/{strategy_id}/symbols/{symbol}")
async def get_symbol_stat(strategy_id: str, symbol: str):
    """Get statistics for specific symbol."""
    stat = statistics_service.get_symbol_stat(strategy_id, symbol)
    
    if not stat:
        return {
            "strategyId": strategy_id,
            "symbol": symbol,
            "message": "No trades for this symbol yet"
        }
    
    return stat.to_dict()


@router.get("/{strategy_id}/regimes")
async def get_regime_statistics(strategy_id: str):
    """Get statistics per market regime for a strategy."""
    stats = statistics_service.get_regime_statistics(strategy_id)
    
    return {
        "strategyId": strategy_id,
        "regimes": {reg: s.to_dict() for reg, s in stats.items()},
        "count": len(stats)
    }


@router.get("/{strategy_id}/regimes/{regime}")
async def get_regime_stat(strategy_id: str, regime: str):
    """Get statistics for specific regime."""
    stat = statistics_service.get_regime_stat(strategy_id, regime)
    
    if not stat:
        return {
            "strategyId": strategy_id,
            "regime": regime,
            "message": "No trades for this regime yet"
        }
    
    return stat.to_dict()


@router.get("/{strategy_id}/trades")
async def get_trade_history(
    strategy_id: str,
    limit: int = Query(100, ge=1, le=500)
):
    """Get trade history for a strategy."""
    trades = statistics_service.get_trades(strategy_id, limit=limit)
    
    return {
        "strategyId": strategy_id,
        "trades": [t.to_dict() for t in trades],
        "count": len(trades)
    }


# ===========================================
# Recording Endpoints
# ===========================================

@router.post("/record/trade")
async def record_trade(input: RecordTradeInput):
    """Record a completed trade."""
    trade = statistics_service.record_trade_from_dict(input.dict())
    
    return {
        "success": True,
        "tradeId": trade.trade_id,
        "message": f"Trade recorded for {input.strategy_id}"
    }


@router.post("/record/decision")
async def record_decision(input: RecordDecisionInput):
    """Record a strategy decision."""
    decision = statistics_service.record_decision_from_dict(input.dict())
    
    return {
        "success": True,
        "decisionId": decision.decision_id,
        "message": f"Decision recorded for {input.strategy_id}"
    }


# ===========================================
# Batch Recording
# ===========================================

class BatchTradesInput(BaseModel):
    """Input for batch trade recording"""
    trades: List[RecordTradeInput]


@router.post("/record/trades/batch")
async def record_trades_batch(input: BatchTradesInput):
    """Record multiple trades at once."""
    recorded = []
    for trade_input in input.trades:
        trade = statistics_service.record_trade_from_dict(trade_input.dict())
        recorded.append(trade.trade_id)
    
    return {
        "success": True,
        "tradesRecorded": len(recorded),
        "tradeIds": recorded
    }


# ===========================================
# Comparison
# ===========================================

@router.get("/compare")
async def compare_strategies(
    strategies: str = Query(..., description="Comma-separated strategy IDs")
):
    """Compare statistics across strategies."""
    strategy_ids = [s.strip() for s in strategies.split(",")]
    
    comparison = []
    for sid in strategy_ids:
        stats = statistics_service.get_statistics(sid)
        if stats:
            comparison.append({
                "strategyId": sid,
                "winRate": round(stats.win_rate, 4),
                "profitFactor": round(stats.profit_factor, 2),
                "expectancy": round(stats.expectancy, 4),
                "totalTrades": stats.total_trades,
                "maxDrawdown": round(stats.max_drawdown, 4)
            })
        else:
            comparison.append({
                "strategyId": sid,
                "message": "No data"
            })
    
    return {
        "comparison": comparison,
        "count": len(comparison)
    }
