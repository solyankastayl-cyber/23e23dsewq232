"""Trading Core API Routes — Week 2/3/4

Week 3 Update: Uses portfolio_service (MongoDB-backed) + Execution Events
Week 4 Update: AutoTrading toggle, performance stats
"""

from fastapi import APIRouter
from typing import Dict, Any
from pydantic import BaseModel

from .portfolio_service import get_portfolio_service
from .execution_events import get_events_service
from .autotrading_service import get_autotrading_service
from .performance_service import get_performance_service
from .trading_runtime import (
    run_trading_cycle,
    get_last_cycle_results,
    start_trading_scheduler,
    stop_trading_scheduler,
    get_last_explainability_snapshot,
)

router = APIRouter(prefix="/api/trading", tags=["trading_core"])


class ToggleRequest(BaseModel):
    """AutoTrading toggle request."""
    enabled: bool


@router.get("/portfolio")
async def get_portfolio_endpoint() -> Dict[str, Any]:
    """Get current portfolio state.
    
    Returns:
        Portfolio: {balance, equity, positions, pnl, risk}
    """
    portfolio_service = get_portfolio_service()
    portfolio = await portfolio_service.get_portfolio_state()
    
    return {
        "ok": True,
        "portfolio": portfolio,
    }


@router.get("/positions")
async def get_positions_endpoint() -> Dict[str, Any]:
    """Get all open positions."""
    portfolio_service = get_portfolio_service()
    portfolio = await portfolio_service.get_portfolio_state()
    
    return {
        "ok": True,
        "positions": portfolio.get("positions", []),
        "count": len(portfolio.get("positions", [])),
    }


@router.post("/positions/{position_id}/close")
async def close_position_endpoint(position_id: str) -> Dict[str, Any]:
    """Close a specific position.
    
    Args:
        position_id: Position ID to close
    
    Returns:
        Result of close operation
    """
    portfolio_service = get_portfolio_service()
    
    try:
        # Get position
        portfolio = await portfolio_service.get_portfolio_state()
        position = next(
            (p for p in portfolio.get("positions", []) if p.get("position_id") == position_id),
            None
        )
        
        if not position:
            return {
                "ok": False,
                "error": f"Position not found: {position_id}"
            }
        
        # Close position (create opposite order)
        from .close_positions import close_position
        
        result = await close_position(
            symbol=position["symbol"],
            position_id=position_id,
            reason="Manual close via UI"
        )
        
        return {
            "ok": True,
            "result": result,
            "message": f"Position {position_id} closed"
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


@router.get("/pnl")
async def get_pnl_endpoint() -> Dict[str, Any]:
    """Get PnL summary."""
    portfolio_service = get_portfolio_service()
    portfolio = await portfolio_service.get_portfolio_state()
    
    return {
        "ok": True,
        "pnl": {
            "realized": portfolio.get("realized_pnl", 0),
            "unrealized": portfolio.get("unrealized_pnl", 0),
            "total": portfolio.get("total_pnl", 0),
        },
    }


@router.post("/run")
async def run_trading_cycle_endpoint() -> Dict[str, Any]:
    """Trigger manual trading cycle.
    
    Runs: Scanner → Decisions → Orders → Fills → Positions
    """
    result = await run_trading_cycle()
    
    return {
        "ok": True,
        "cycle_result": result,
    }


@router.get("/status")
async def get_trading_status() -> Dict[str, Any]:
    """Get trading system status."""
    portfolio_service = get_portfolio_service()
    portfolio = await portfolio_service.get_portfolio_state()
    last_cycle = get_last_cycle_results()
    
    return {
        "ok": True,
        "status": {
            "balance": portfolio.get("balance", 0),
            "equity": portfolio.get("equity", 0),
            "positions_count": len(portfolio.get("positions", [])),
            "total_pnl": portfolio.get("total_pnl", 0),
            "last_cycle": last_cycle,
        },
    }


@router.post("/scheduler/start")
async def start_scheduler_endpoint() -> Dict[str, Any]:
    """Start automatic trading scheduler (60s interval)."""
    start_trading_scheduler()
    
    return {
        "ok": True,
        "message": "Trading scheduler started",
    }


@router.post("/scheduler/stop")
async def stop_scheduler_endpoint() -> Dict[str, Any]:
    """Stop automatic trading scheduler."""
    stop_trading_scheduler()
    
    return {
        "ok": True,
        "message": "Trading scheduler stopped",
    }


@router.get("/events")
async def get_execution_events(limit: int = 50) -> Dict[str, Any]:
    """Get recent execution events.
    
    Args:
        limit: Max events to return (default 50)
    
    Returns:
        List of execution events (newest first)
    """
    events_service = get_events_service()
    events = await events_service.get_recent_events(limit=limit)
    
    return {
        "ok": True,
        "events": events,
        "count": len(events),
    }


@router.post("/toggle")
async def toggle_autotrading(request: ToggleRequest) -> Dict[str, Any]:
    """Toggle autotrading ON/OFF.
    
    Args:
        request: {enabled: bool}
    
    Returns:
        Current autotrading status
    """
    autotrading_service = get_autotrading_service()
    await autotrading_service.toggle(request.enabled)
    
    return {
        "ok": True,
        "enabled": request.enabled,
        "message": f"AutoTrading {'ENABLED' if request.enabled else 'DISABLED'}",
    }


@router.get("/autotrading/status")
async def get_autotrading_status() -> Dict[str, Any]:
    """Get autotrading status."""
    autotrading_service = get_autotrading_service()
    status = autotrading_service.get_status()
    
    return {
        "ok": True,
        "autotrading": status,
    }


@router.post("/autotrading/enable")
async def enable_autotrading() -> Dict[str, Any]:
    """Enable autotrading (persisted)."""
    autotrading_service = get_autotrading_service()
    await autotrading_service.toggle(True)
    
    return {
        "ok": True,
        "enabled": True,
        "message": "AutoTrading ENABLED (persisted to DB)"
    }


@router.post("/autotrading/disable")
async def disable_autotrading() -> Dict[str, Any]:
    """Disable autotrading (persisted)."""
    autotrading_service = get_autotrading_service()
    await autotrading_service.toggle(False)
    
    return {
        "ok": True,
        "enabled": False,
        "message": "AutoTrading DISABLED (persisted to DB)"
    }


@router.post("/autotrading/interval")
async def set_autotrading_interval(seconds: int) -> Dict[str, Any]:
    """Set autotrading interval (persisted).
    
    Args:
        seconds: Interval in seconds (min: 5, max: 300)
    """
    if seconds < 5 or seconds > 300:
        return {
            "ok": False,
            "error": "Interval must be between 5 and 300 seconds"
        }
    
    autotrading_service = get_autotrading_service()
    await autotrading_service.set_interval(seconds)
    
    return {
        "ok": True,
        "interval_seconds": seconds,
        "message": f"Interval set to {seconds}s (persisted to DB)"
    }


@router.get("/performance")
async def get_performance() -> Dict[str, Any]:
    """Get trading performance statistics."""
    performance_service = get_performance_service()
    stats = await performance_service.get_performance_stats()
    
    return {
        "ok": True,
        "performance": stats,
    }



@router.get("/portfolio/equity-curve")
async def equity_curve() -> Dict[str, Any]:
    """Get equity curve with drawdown."""
    try:
        from modules.trading_core.portfolio_service import get_portfolio_service
        portfolio_service = get_portfolio_service()
        db = portfolio_service.db
        
        cursor = db.portfolio_snapshots.find().sort("updated_at", -1).limit(200)
        rows = await cursor.to_list(length=200)
        
        if not rows:
            return {"ok": True, "points": []}
        
        equity_peak = 0.0
        points = []
        
        for r in reversed(rows):
            equity = float(r.get("equity", 0.0))
            equity_peak = max(equity_peak, equity)
            drawdown = (equity - equity_peak) / equity_peak if equity_peak > 0 else 0.0
            
            points.append({
                "time": r["updated_at"].strftime("%H:%M:%S"),
                "equity": round(equity, 2),
                "drawdown": round(drawdown, 4),
            })
        
        return {"ok": True, "points": points}
    except Exception as e:
        return {"ok": False, "error": str(e), "points": []}


@router.get("/execution-quality")
async def execution_quality() -> Dict[str, Any]:
    """Get execution quality metrics."""
    try:
        from modules.trading_core.portfolio_service import get_portfolio_service
        portfolio_service = get_portfolio_service()
        db = portfolio_service.db
        
        cursor = db.exchange_orders.find().sort("created_at", -1).limit(50)
        rows = await cursor.to_list(length=50)
        
        if not rows:
            return {"ok": True, "avg_quality": 0, "avg_slippage": 0, "avg_latency": 0, "orders": []}
        
        total, q_sum, s_sum, l_sum = len(rows), 0.0, 0.0, 0.0
        result = []
        
        for o in rows:
            q = float(o.get("execution_quality_score", 0))
            s = float(o.get("slippage_bps", 0))
            l = float(o.get("latency_ms", 0))
            q_sum, s_sum, l_sum = q_sum + q, s_sum + s, l_sum + l
            
            result.append({
                "symbol": o.get("symbol"),
                "quality": round(q, 1),
                "slippage": round(s, 2),
                "latency": round(l, 0),
                "fills": o.get("fill_count", 1),
            })
        
        return {
            "ok": True,
            "avg_quality": round(q_sum / total, 1),
            "avg_slippage": round(s_sum / total, 2),
            "avg_latency": round(l_sum / total, 0),
            "orders": result[:10],
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "avg_quality": 0, "avg_slippage": 0, "avg_latency": 0, "orders": []}



@router.get("/system/explainability")
async def get_system_explainability() -> Dict[str, Any]:
    """
    Get system explainability snapshot for UI visibility.
    
    Returns full breakdown of why system is trading or not trading:
    - Mode (bootstrap/production)
    - Regime
    - Signals generated
    - Ranking results
    - Risk engine state
    - Allocator results
    
    Critical for operational transparency and debugging.
    """
    try:
        snapshot = get_last_explainability_snapshot()
        return {
            "ok": True,
            "data": snapshot
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[Routes] Explainability error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }


@router.get("/execution/heatmap")
async def get_execution_heatmap(symbol: str = "BTCUSDT") -> Dict[str, Any]:
    """
    Get execution heatmap (liquidity wall visualization).
    
    Returns aggregated orderbook buckets showing bid/ask liquidity walls.
    
    Args:
        symbol: Trading symbol (default: BTCUSDT)
    
    Returns:
        Heatmap buckets with intensity levels for visualization
    """
    try:
        from modules.execution.liquidity_heatmap import aggregate_orderbook
        import httpx
        import random
        
        # Try to fetch real orderbook from Binance
        bids = []
        asks = []
        
        try:
            url = f"https://api.binance.com/api/v3/depth"
            params = {"symbol": symbol, "limit": 100}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    bids = [(float(p), float(s)) for p, s in data.get("bids", [])]
                    asks = [(float(p), float(s)) for p, s in data.get("asks", [])]
        except Exception:
            pass  # Fallback to synthetic data
        
        # If no real data (geo-block or error), generate synthetic orderbook
        if not bids or not asks:
            # Generate synthetic orderbook for demo purposes
            base_price = 69900.0 if "BTC" in symbol else 100.0
            
            # Generate bids (below mid price)
            for i in range(50):
                price = base_price - (i * 10) - random.uniform(0, 10)
                size = random.uniform(0.05, 2.0) * (1.0 + random.random() * 3 if i % 7 == 0 else 1.0)  # Occasional walls
                bids.append((price, size))
            
            # Generate asks (above mid price)
            for i in range(50):
                price = base_price + (i * 10) + random.uniform(0, 10)
                size = random.uniform(0.05, 2.0) * (1.0 + random.random() * 3 if i % 5 == 0 else 1.0)  # Occasional walls
                asks.append((price, size))
        
        bucket_size = 50.0 if "BTC" in symbol else 1.0
        
        heatmap = aggregate_orderbook(
            bids=bids,
            asks=asks,
            bucket_size=bucket_size,
        )
        
        bid_rows = heatmap["bids"]
        ask_rows = heatmap["asks"]
        
        # Calculate mid price
        mid_price = None
        if bids and asks:
            mid_price = (float(bids[0][0]) + float(asks[0][0])) / 2.0
        
        return {
            "ok": True,
            "symbol": symbol,
            "mid_price": mid_price,
            "buckets": heatmap,
            "summary": {
                "top_bid_wall": bid_rows[0]["price"] if bid_rows else None,
                "top_ask_wall": ask_rows[0]["price"] if ask_rows else None,
                "nearest_bid_liquidity": bid_rows[0]["price"] if bid_rows else None,
                "nearest_ask_liquidity": ask_rows[0]["price"] if ask_rows else None,
            },
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[Routes] Heatmap error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }

