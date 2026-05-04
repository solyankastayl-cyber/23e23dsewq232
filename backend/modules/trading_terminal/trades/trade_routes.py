"""
Trade Routes (TR3)
==================

API endpoints for Trade Monitor.

Endpoints:
- GET /api/trades/orders         - List orders
- GET /api/trades/orders/{id}    - Get order
- GET /api/trades/fills          - List fills
- GET /api/trades/history        - Trade history
- GET /api/trades/symbol/{symbol}- Trades by symbol
- GET /api/trades/recent         - Recent trades
- GET /api/trades/logs           - Execution logs
- GET /api/trades/dashboard      - Dashboard summary
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from .trade_service import trade_service
from .order_service import order_service
from .trade_aggregator import trade_aggregator


# ===========================================
# Router
# ===========================================

router = APIRouter(prefix="/api/trades", tags=["TR3 - Trade Monitor"])


# ===========================================
# Health
# ===========================================

@router.get("/health")
async def get_service_health():
    """Get TR3 module health"""
    return {
        "module": "Trade Monitor",
        "phase": "TR3",
        "services": trade_service.get_health()
    }


# ===========================================
# Orders
# ===========================================

@router.get("/orders")
async def list_orders(limit: int = 100):
    """List recent orders"""
    orders = trade_service.get_orders(limit=limit)
    stats = order_service.get_stats()
    
    return {
        "orders": [o.to_dict() for o in orders],
        "count": len(orders),
        "stats": stats
    }


@router.get("/orders/open")
async def list_open_orders():
    """List open orders"""
    orders = trade_service.get_open_orders()
    
    return {
        "orders": [o.to_dict() for o in orders],
        "count": len(orders)
    }


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get specific order"""
    order = trade_service.get_order(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order.to_dict()


# ===========================================
# Fills
# ===========================================

@router.get("/fills")
async def list_fills(limit: int = 100):
    """List recent fills"""
    fills = trade_service.get_fills(limit=limit)
    
    return {
        "fills": [f.to_dict() for f in fills],
        "count": len(fills)
    }


# ===========================================
# Trades
# ===========================================

@router.get("/history")
async def get_trade_history(limit: int = 100):
    """Get trade history"""
    trades = trade_service.get_trades(limit=limit)
    
    return {
        "trades": [t.to_dict() for t in trades],
        "count": len(trades)
    }


@router.get("/recent")
async def get_recent_trades(limit: int = 20):
    """Get most recent trades"""
    trades = trade_service.get_trades(limit=limit)
    
    return {
        "trades": [t.to_dict() for t in trades],
        "count": len(trades)
    }


@router.get("/symbol/{symbol}")
async def get_trades_by_symbol(symbol: str):
    """Get trades for specific symbol"""
    trades = trade_service.get_trades_by_symbol(symbol.upper())
    
    return {
        "symbol": symbol.upper(),
        "trades": [t.to_dict() for t in trades],
        "count": len(trades)
    }


@router.get("/trade/{trade_id}")
async def get_trade(trade_id: str):
    """Get specific trade"""
    trade = trade_service.get_trade(trade_id)
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    return trade.to_dict()


# ===========================================
# Execution Logs
# ===========================================

@router.get("/logs")
async def get_execution_logs(limit: int = 100, errors_only: bool = False):
    """Get execution logs"""
    logs = trade_service.get_execution_logs(limit=limit, errors_only=errors_only)
    
    return {
        "logs": [l.to_dict() for l in logs],
        "count": len(logs),
        "errors_only": errors_only
    }


@router.get("/logs/order/{order_id}")
async def get_order_logs(order_id: str):
    """Get logs for specific order"""
    logs = trade_service.get_logs_by_order(order_id)
    
    return {
        "order_id": order_id,
        "logs": [l.to_dict() for l in logs],
        "count": len(logs)
    }


# ===========================================
# Summary & Dashboard
# ===========================================

@router.get("/summary")
async def get_trades_summary():
    """Get trades summary"""
    summary = trade_service.get_summary()
    return summary.to_dict()


@router.get("/dashboard")
async def get_dashboard():
    """Get dashboard data"""
    return trade_service.get_dashboard()
