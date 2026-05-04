"""
Portfolio Routes (TR2)
======================

API endpoints for Portfolio Monitor.

Endpoints:
- GET /api/portfolio/state     - Full unified state
- GET /api/portfolio/balances  - All balances
- GET /api/portfolio/positions - All positions
- GET /api/portfolio/equity    - Equity summary
- GET /api/portfolio/pnl       - PnL summary
- GET /api/portfolio/exposure  - Exposure breakdown
- GET /api/portfolio/metrics   - Portfolio metrics
- GET /api/portfolio/dashboard - Dashboard data
- GET /api/portfolio/snapshots - History snapshots
"""

from fastapi import APIRouter
from typing import Optional

from .portfolio_service import portfolio_service
from .portfolio_aggregator import portfolio_aggregator


# ===========================================
# Router
# ===========================================

router = APIRouter(prefix="/api/portfolio", tags=["TR2 - Portfolio Monitor"])


# ===========================================
# Health
# ===========================================

@router.get("/health")
async def get_service_health():
    """Get TR2 module health"""
    return {
        "module": "Portfolio Monitor",
        "phase": "TR2",
        "services": {
            "portfolio_service": portfolio_service.get_health(),
            "portfolio_aggregator": portfolio_aggregator.get_health()
        }
    }


# ===========================================
# Portfolio State
# ===========================================

@router.get("/state")
async def get_portfolio_state(refresh: bool = False):
    """
    Get unified portfolio state.
    
    Aggregates data from all connected exchanges.
    """
    state = portfolio_service.get_portfolio_state(force_refresh=refresh)
    return state.to_dict()


# ===========================================
# Balances
# ===========================================

@router.get("/balances")
async def get_balances():
    """Get all balances aggregated across exchanges"""
    balances = portfolio_service.get_balances()
    return {
        "balances": [b.to_dict() for b in balances],
        "count": len(balances)
    }


# ===========================================
# Positions
# ===========================================

@router.get("/positions")
async def get_positions():
    """Get all positions from all exchanges"""
    positions = portfolio_service.get_positions()
    return {
        "positions": [p.to_dict() for p in positions],
        "count": len(positions)
    }


# ===========================================
# Equity
# ===========================================

@router.get("/equity")
async def get_equity():
    """Get equity summary"""
    return portfolio_service.get_equity()


# ===========================================
# PnL
# ===========================================

@router.get("/pnl")
async def get_pnl():
    """Get PnL summary"""
    return portfolio_service.get_pnl()


# ===========================================
# Exposure
# ===========================================

@router.get("/exposure")
async def get_exposure():
    """Get exposure breakdown"""
    exposure = portfolio_service.get_exposure()
    return exposure.to_dict()


# ===========================================
# Metrics
# ===========================================

@router.get("/metrics")
async def get_metrics():
    """Get portfolio metrics"""
    metrics = portfolio_service.get_metrics()
    return metrics.to_dict()


# ===========================================
# Dashboard
# ===========================================

@router.get("/dashboard")
async def get_dashboard():
    """Get dashboard data (compact format)"""
    return portfolio_service.get_dashboard()


# ===========================================
# Snapshots
# ===========================================

@router.get("/snapshots")
async def get_snapshots(limit: int = 100):
    """Get portfolio snapshots history"""
    snapshots = portfolio_service.get_snapshots(limit=limit)
    return {
        "snapshots": [s.to_dict() for s in snapshots],
        "count": len(snapshots)
    }


@router.get("/equity-history")
async def get_equity_history(limit: int = 100):
    """Get equity curve data"""
    return {
        "history": portfolio_service.get_equity_history(limit=limit)
    }
