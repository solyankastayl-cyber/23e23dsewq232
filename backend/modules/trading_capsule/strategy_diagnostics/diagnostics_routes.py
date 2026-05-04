"""
Strategy Diagnostics Routes (STR4)
==================================

API endpoints for Strategy Diagnostics.

Endpoints:
- GET  /api/strategy/diagnostics    - Full snapshot
- GET  /api/strategy/state          - Current state
- GET  /api/strategy/health         - Health status
- GET  /api/strategy/performance    - Performance metrics
- GET  /api/strategy/risk           - Risk metrics
- GET  /api/strategy/warnings       - Active warnings
- POST /api/strategy/warnings/{id}/acknowledge
- POST /api/strategy/warnings/{id}/resolve
- GET  /api/strategy/switch-history - Switch history
- GET  /api/strategy/dashboard      - Dashboard data
- POST /api/strategy/update/trade   - Update from trade
- POST /api/strategy/update/portfolio - Update from portfolio
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

from .diagnostics_service import strategy_diagnostics_service


# ===========================================
# Router
# ===========================================

router = APIRouter(prefix="/api/strategy", tags=["STR4 - Strategy Diagnostics"])


# ===========================================
# Request Models
# ===========================================

class AcknowledgeWarningRequest(BaseModel):
    acknowledged_by: str = Field(default="admin")


class TradeUpdateRequest(BaseModel):
    trade_id: str
    symbol: str
    side: str  # BUY / SELL
    pnl_pct: float
    pnl_usd: float = 0.0
    closed_at: str


class PortfolioUpdateRequest(BaseModel):
    drawdown_pct: float = 0.0
    daily_loss_pct: float = 0.0
    exposure_pct: float = 0.0
    leverage: float = 1.0


class MonteCarloUpdateRequest(BaseModel):
    var_95: float
    cvar_95: float


# ===========================================
# Full Diagnostics
# ===========================================

@router.get("/diagnostics")
async def get_diagnostics():
    """
    Get full diagnostics snapshot.
    
    Aggregates state, health, performance, risk, and warnings.
    """
    snapshot = strategy_diagnostics_service.get_diagnostics()
    return snapshot.to_dict()


# ===========================================
# Health Check
# ===========================================

@router.get("/diagnostics/health")
async def get_diagnostics_health():
    """Get STR4 module health"""
    return strategy_diagnostics_service.get_service_health()


# ===========================================
# Strategy State
# ===========================================

@router.get("/state")
async def get_strategy_state():
    """
    Get current strategy state.
    
    Shows active profile, config, and activation source.
    """
    state = strategy_diagnostics_service.get_strategy_state()
    return state.to_dict()


# ===========================================
# Health Status
# ===========================================

@router.get("/health")
async def get_health_status():
    """
    Get strategy health evaluation.
    
    Returns health status and all checks.
    """
    health = strategy_diagnostics_service.get_health_status()
    return health.to_dict()


# ===========================================
# Performance
# ===========================================

@router.get("/performance")
async def get_performance():
    """
    Get performance summary.
    
    Returns PnL, win rate, trade stats.
    """
    performance = strategy_diagnostics_service.get_performance()
    return performance.to_dict()


# ===========================================
# Risk
# ===========================================

@router.get("/risk")
async def get_risk():
    """
    Get risk summary.
    
    Returns drawdown, exposure, leverage, VaR.
    """
    risk = strategy_diagnostics_service.get_risk()
    return risk.to_dict()


# ===========================================
# Warnings
# ===========================================

@router.get("/warnings")
async def get_warnings(active_only: bool = True):
    """Get strategy warnings"""
    warnings = strategy_diagnostics_service.get_warnings(active_only=active_only)
    return {
        "warnings": [w.to_dict() for w in warnings],
        "count": len(warnings),
        "active_only": active_only
    }


@router.post("/warnings/{warning_id}/acknowledge")
async def acknowledge_warning(
    warning_id: str,
    request: AcknowledgeWarningRequest
):
    """Acknowledge a warning"""
    success = strategy_diagnostics_service.acknowledge_warning(
        warning_id=warning_id,
        acknowledged_by=request.acknowledged_by
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Warning '{warning_id}' not found")
    
    return {
        "success": True,
        "message": f"Warning '{warning_id}' acknowledged",
        "warning_id": warning_id
    }


@router.post("/warnings/{warning_id}/resolve")
async def resolve_warning(warning_id: str):
    """Resolve a warning"""
    success = strategy_diagnostics_service.resolve_warning(warning_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Warning '{warning_id}' not found")
    
    return {
        "success": True,
        "message": f"Warning '{warning_id}' resolved",
        "warning_id": warning_id
    }


# ===========================================
# Switch History
# ===========================================

@router.get("/switch-history")
async def get_switch_history(limit: int = 50):
    """Get profile switch history"""
    history = strategy_diagnostics_service.get_switch_history(limit=limit)
    return {
        "switches": [s.to_dict() for s in history],
        "count": len(history)
    }


# ===========================================
# Dashboard (Compact)
# ===========================================

@router.get("/dashboard")
async def get_dashboard():
    """
    Get dashboard data.
    
    Returns compact format for admin terminal.
    """
    return strategy_diagnostics_service.get_dashboard()


# ===========================================
# Data Updates
# ===========================================

@router.post("/update/trade")
async def update_from_trade(request: TradeUpdateRequest):
    """Update metrics from a new trade"""
    strategy_diagnostics_service.update_from_trade({
        "trade_id": request.trade_id,
        "symbol": request.symbol,
        "side": request.side,
        "pnl_pct": request.pnl_pct,
        "pnl_usd": request.pnl_usd,
        "closed_at": request.closed_at
    })
    
    return {
        "success": True,
        "message": "Trade data updated",
        "trade_id": request.trade_id
    }


@router.post("/update/portfolio")
async def update_from_portfolio(request: PortfolioUpdateRequest):
    """Update metrics from portfolio state"""
    strategy_diagnostics_service.update_from_portfolio({
        "drawdown_pct": request.drawdown_pct,
        "daily_loss_pct": request.daily_loss_pct,
        "exposure_pct": request.exposure_pct,
        "leverage": request.leverage
    })
    
    return {
        "success": True,
        "message": "Portfolio data updated"
    }


@router.post("/update/monte-carlo")
async def update_from_monte_carlo(request: MonteCarloUpdateRequest):
    """Update VaR from Monte Carlo results"""
    strategy_diagnostics_service.update_from_monte_carlo({
        "var_95": request.var_95,
        "cvar_95": request.cvar_95
    })
    
    return {
        "success": True,
        "message": "Monte Carlo data updated"
    }


# ===========================================
# Snapshot History
# ===========================================

@router.get("/snapshots")
async def get_snapshot_history(limit: int = 10):
    """Get historical diagnostics snapshots"""
    snapshots = strategy_diagnostics_service.get_snapshot_history(limit=limit)
    return {
        "snapshots": [s.to_dict() for s in snapshots],
        "count": len(snapshots)
    }
