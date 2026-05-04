"""
Live Execution Routes

PHASE 43 — Live Exchange Integration

Consolidated routes for:
- Exchange Sync (43.2)
- Pilot Mode (43.3)
- Trade Throttle (43.4)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/live-execution", tags=["Live Execution"])


# ══════════════════════════════════════════════════════════════
# Exchange Sync Routes (PHASE 43.2)
# ══════════════════════════════════════════════════════════════

@router.get("/sync/summary")
async def get_sync_summary():
    """Get exchange sync summary."""
    from modules.exchange_sync import get_exchange_sync_engine
    engine = get_exchange_sync_engine()
    return engine.get_summary()


@router.get("/sync/positions")
async def get_synced_positions(exchange: Optional[str] = None):
    """Get synced positions from exchanges."""
    from modules.exchange_sync import get_exchange_sync_engine
    engine = get_exchange_sync_engine()
    positions = engine.get_positions(exchange)
    
    return {
        "count": len(positions),
        "positions": [p.model_dump() for p in positions],
    }


@router.get("/sync/balances")
async def get_synced_balances(exchange: Optional[str] = None):
    """Get synced balances from exchanges."""
    from modules.exchange_sync import get_exchange_sync_engine
    engine = get_exchange_sync_engine()
    balances = engine.get_balances(exchange)
    
    return {
        "count": len(balances),
        "balances": [b.model_dump() for b in balances],
    }


@router.get("/sync/orders")
async def get_synced_orders(exchange: Optional[str] = None):
    """Get synced open orders from exchanges."""
    from modules.exchange_sync import get_exchange_sync_engine
    engine = get_exchange_sync_engine()
    orders = engine.get_open_orders(exchange)
    
    return {
        "count": len(orders),
        "orders": [o.model_dump() for o in orders],
    }


@router.post("/sync/start")
async def start_sync():
    """Start exchange sync engine."""
    from modules.exchange_sync import get_exchange_sync_engine
    engine = get_exchange_sync_engine()
    await engine.start()
    return {"status": "started"}


@router.post("/sync/stop")
async def stop_sync():
    """Stop exchange sync engine."""
    from modules.exchange_sync import get_exchange_sync_engine
    engine = get_exchange_sync_engine()
    await engine.stop()
    return {"status": "stopped"}


@router.post("/sync/refresh")
async def refresh_sync(exchange: str = Query(default="BINANCE")):
    """Manually trigger sync for an exchange."""
    from modules.exchange_sync import get_exchange_sync_engine
    engine = get_exchange_sync_engine()
    
    positions = await engine.sync_positions(exchange)
    balances = await engine.sync_balances(exchange)
    orders = await engine.sync_orders(exchange)
    
    return {
        "exchange": exchange,
        "positions_synced": len(positions),
        "balances_synced": len(balances),
        "orders_synced": len(orders),
    }


# ══════════════════════════════════════════════════════════════
# Pilot Mode Routes (PHASE 43.3)
# ══════════════════════════════════════════════════════════════

@router.get("/pilot/summary")
async def get_pilot_summary():
    """Get pilot mode summary."""
    from modules.pilot_mode import get_pilot_mode_engine
    engine = get_pilot_mode_engine()
    return engine.get_summary()


@router.get("/pilot/state")
async def get_pilot_state():
    """Get pilot mode state."""
    from modules.pilot_mode import get_pilot_mode_engine
    engine = get_pilot_mode_engine()
    return engine.get_state().model_dump()


@router.get("/pilot/constraints")
async def get_pilot_constraints():
    """Get pilot mode constraints."""
    from modules.pilot_mode import get_pilot_mode_engine
    engine = get_pilot_mode_engine()
    return engine.get_constraints().model_dump()


@router.post("/pilot/check")
async def check_pilot_constraints(
    symbol: str = Query(...),
    size_usd: float = Query(...),
    side: str = Query(default="BUY"),
):
    """Check if trade meets pilot constraints."""
    from modules.pilot_mode import get_pilot_mode_engine
    engine = get_pilot_mode_engine()
    result = engine.check_constraints(symbol, size_usd, side)
    return result.model_dump()


@router.post("/pilot/set-mode")
async def set_pilot_mode(mode: str = Query(...)):
    """Set trading mode (PAPER, PILOT, LIVE, MAINTENANCE)."""
    from modules.pilot_mode import get_pilot_mode_engine, TradingMode
    
    try:
        trading_mode = TradingMode(mode.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")
    
    engine = get_pilot_mode_engine()
    engine.set_mode(trading_mode)
    
    return {
        "status": "ok",
        "mode": trading_mode.value,
    }


# ══════════════════════════════════════════════════════════════
# Trade Throttle Routes (PHASE 43.4)
# ══════════════════════════════════════════════════════════════

@router.get("/throttle/summary")
async def get_throttle_summary():
    """Get trade throttle summary."""
    from modules.trade_throttle import get_trade_throttle_engine
    engine = get_trade_throttle_engine()
    return engine.get_summary()


@router.get("/throttle/state")
async def get_throttle_state():
    """Get trade throttle state."""
    from modules.trade_throttle import get_trade_throttle_engine
    engine = get_trade_throttle_engine()
    return engine.get_state().model_dump()


@router.get("/throttle/config")
async def get_throttle_config():
    """Get trade throttle configuration."""
    from modules.trade_throttle import get_trade_throttle_engine
    engine = get_trade_throttle_engine()
    return engine.get_config().model_dump()


@router.post("/throttle/check")
async def check_throttle(
    symbol: str = Query(...),
    side: str = Query(default="BUY"),
    size_usd: float = Query(...),
    strategy: str = Query(default="default"),
):
    """Check if trade would be throttled."""
    from modules.trade_throttle import get_trade_throttle_engine
    engine = get_trade_throttle_engine()
    result = engine.check_throttle(symbol, side, size_usd, strategy)
    return result.model_dump()


@router.post("/throttle/emergency-block")
async def set_emergency_block(enabled: bool = Query(...)):
    """Enable/disable emergency block."""
    from modules.trade_throttle import get_trade_throttle_engine
    engine = get_trade_throttle_engine()
    engine.set_emergency_block(enabled)
    
    return {
        "status": "ok",
        "emergency_block": enabled,
    }


@router.post("/throttle/reset-daily")
async def reset_daily_stats():
    """Reset daily throttle statistics."""
    from modules.trade_throttle import get_trade_throttle_engine
    engine = get_trade_throttle_engine()
    engine.reset_daily_stats()
    return {"status": "reset"}


# ══════════════════════════════════════════════════════════════
# Combined Health Check
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def live_execution_health():
    """Health check for live execution layer."""
    from modules.exchange_sync import get_exchange_sync_engine
    from modules.pilot_mode import get_pilot_mode_engine
    from modules.trade_throttle import get_trade_throttle_engine
    
    sync_engine = get_exchange_sync_engine()
    pilot_engine = get_pilot_mode_engine()
    throttle_engine = get_trade_throttle_engine()
    
    return {
        "status": "ok",
        "phase": "43",
        "components": {
            "exchange_sync": {
                "running": sync_engine._running,
                "exchanges": list(sync_engine._sync_states.keys()),
            },
            "pilot_mode": {
                "mode": pilot_engine.get_mode().value,
                "constraints_active": True,
            },
            "trade_throttle": {
                "level": throttle_engine.get_state().throttle_level.value,
                "emergency_block": throttle_engine._config.emergency_block_enabled,
            },
        },
        "default_config": {
            "execution_mode": "APPROVAL",
            "capital_mode": "PILOT",
            "kill_switch": "ON",
            "circuit_breaker": "ON",
            "trade_throttle": "REQUIRED",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
