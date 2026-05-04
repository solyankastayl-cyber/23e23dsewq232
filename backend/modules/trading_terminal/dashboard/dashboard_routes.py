"""
TR6 Dashboard Routes
====================

API endpoints for unified trading dashboard.
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .dashboard_service import dashboard_service


router = APIRouter(prefix="/api/dashboard", tags=["tr6-dashboard"])


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for TR6 Dashboard"""
    return dashboard_service.get_health()


# ===========================================
# Main Dashboard State
# ===========================================

@router.get("/state")
async def get_dashboard_state():
    """
    Get complete unified dashboard state.
    
    Returns aggregated data from all system layers:
    - Accounts (exchange connections)
    - Portfolio (equity, margin, PnL)
    - Trades (recent activity, performance)
    - Risk (levels, alerts, metrics)
    - Strategy (active profile, selected strategy)
    - Regime (current market regime)
    - Reconciliation (sync status)
    - Connections (exchange health)
    - Events (recent system events)
    - System Health (overall status)
    """
    state = dashboard_service.get_dashboard_state()
    return state.to_dict()


# ===========================================
# Individual Widgets
# ===========================================

@router.get("/accounts")
async def get_accounts_widget():
    """
    Get accounts widget.
    
    Shows:
    - Connected exchanges
    - Healthy/degraded/quarantined counts
    - Total equity and balance
    """
    widget = dashboard_service.get_accounts_widget()
    return {
        "widget": "accounts",
        "data": widget.to_dict(),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/portfolio")
async def get_portfolio_widget():
    """
    Get portfolio widget.
    
    Shows:
    - Total equity, margin usage
    - PnL (unrealized, realized, daily)
    - Exposure
    - Open positions count
    """
    widget = dashboard_service.get_portfolio_widget()
    return {
        "widget": "portfolio",
        "data": widget.to_dict(),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/trades")
async def get_trades_widget():
    """
    Get trades widget.
    
    Shows:
    - Recent orders, fills, closed trades
    - Trades today/week
    - Performance metrics (win rate, profit factor)
    """
    widget = dashboard_service.get_trades_widget()
    return {
        "widget": "trades",
        "data": widget.to_dict(),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/risk")
async def get_risk_widget():
    """
    Get risk widget.
    
    Shows:
    - Risk level and score
    - Drawdown
    - Daily loss vs limit
    - VaR/CVaR
    - Active alerts
    """
    widget = dashboard_service.get_risk_widget()
    return {
        "widget": "risk",
        "data": widget.to_dict(),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/strategy")
async def get_strategy_widget():
    """
    Get strategy widget.
    
    Shows:
    - Active profile and config
    - Selected strategy
    - Strategy health
    - Trading controls (pause, kill switch)
    """
    widget = dashboard_service.get_strategy_widget()
    return {
        "widget": "strategy",
        "data": widget.to_dict(),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/regime")
async def get_regime_widget():
    """
    Get regime widget.
    
    Shows:
    - Current market regime
    - Confidence and stability
    - Transition risk
    """
    widget = dashboard_service.get_regime_widget()
    return {
        "widget": "regime",
        "data": widget.to_dict(),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/reconciliation")
async def get_reconciliation_widget():
    """
    Get reconciliation widget.
    
    Shows:
    - Sync status
    - Mismatch count
    - Frozen symbols
    - Quarantined exchanges
    """
    widget = dashboard_service.get_reconciliation_widget()
    return {
        "widget": "reconciliation",
        "data": widget.to_dict(),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/connections")
async def get_connections_widget():
    """
    Get connections widget.
    
    Shows:
    - Exchange health counts
    - Active incidents
    - Overall connection health
    - Per-exchange status
    """
    widget = dashboard_service.get_connections_widget()
    return {
        "widget": "connections",
        "data": widget.to_dict(),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/events")
async def get_events_widget():
    """
    Get events widget.
    
    Shows:
    - Recent events by severity
    - Latest events list
    - Event breakdown by type
    """
    widget = dashboard_service.get_events_widget()
    return {
        "widget": "events",
        "data": widget.to_dict(),
        "timestamp": int(time.time() * 1000)
    }


# ===========================================
# System Health
# ===========================================

@router.get("/system-health")
async def get_system_health():
    """
    Get overall system health.
    
    Returns:
    - Health status (HEALTHY, WARNING, DEGRADED, CRITICAL)
    - Health details and reasons
    """
    state = dashboard_service.get_dashboard_state()
    return {
        "systemHealth": state.system_health.value,
        "details": state.health_details,
        "timestamp": int(time.time() * 1000)
    }
