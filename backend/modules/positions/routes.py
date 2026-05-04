"""
Position Routes
Sprint A5: API for position tracking, sync, and close
"""

import logging
from fastapi import APIRouter, HTTPException

from modules.positions.service_locator import get_position_sync_service
from modules.exchange.service_v2 import get_exchange_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/positions", tags=["positions"])

# DB will be accessed via service_locator pattern
_db = None

def init_positions_db(db):
    global _db
    _db = db

def get_db():
    if _db is None:
        raise RuntimeError("Positions DB not initialized")
    return _db


@router.get("")
async def get_positions():
    """
    Get all open positions.
    
    Phase closing-loop.3 (2026-04-23): unified view across both collections.
    Historically this endpoint only read `portfolio_positions[status=OPEN]`,
    but the live paper-trading flow writes to `trading_cases[status=ACTIVE]`
    (via trading_case_service when execution_jobs are processed). The UI
    hook usePositions() polls this endpoint every 2s and was permanently
    empty because no component ever wrote to `portfolio_positions`.
    
    Architect directive: "UI обязан показать живые позиции."
    
    Resolution: UNION both collections, normalize trading_case docs to the
    same outward shape (symbol / side / entry_price / qty / size_usd / etc.).
    No logic change to either producer — pure read-side compat.
    
    Returns:
        List[dict] — merged open positions from portfolio_positions and
        trading_cases. Each dict is JSON-serializable (no _id).
    """
    try:
        db = get_db()
        merged: list = []

        # Source 1: legacy portfolio_positions (status=OPEN)
        try:
            rows_pp = await db.portfolio_positions.find({"status": "OPEN"}).to_list(length=200)
            for r in rows_pp:
                r.pop("_id", None)
                # Tag source so UI can distinguish if needed
                r.setdefault("source", "portfolio_positions")
                merged.append(r)
        except Exception as e:
            logger.warning(f"[PositionRoutes] portfolio_positions read failed: {e}")

        # Source 2: trading_cases (status=ACTIVE) — where live paper flow
        # actually lands. Normalize shape to match what PositionsWorkspace +
        # usePositions expect (symbol, side, entry_price, qty, size_usd, ...).
        try:
            rows_tc = await db.trading_cases.find({"status": "ACTIVE"}).to_list(length=200)
            for r in rows_tc:
                r.pop("_id", None)
                # Strip heavy arrays that the list view does not need
                for heavy in ("events_log", "snapshots", "thesis_history", "fills", "order_ids"):
                    r.pop(heavy, None)
                # Datetime fields -> ISO strings for JSON safety
                for dt_field in ("opened_at", "closed_at", "created_at", "updated_at"):
                    v = r.get(dt_field)
                    if hasattr(v, "isoformat"):
                        r[dt_field] = v.isoformat()
                # Provide stable outward status so UI can treat identically
                r["status"] = "OPEN"  # remap ACTIVE -> OPEN for frontend uniformity
                r.setdefault("source", "trading_cases")
                # Common aliases the UI looks for
                r.setdefault("position_id", r.get("case_id"))
                # Phase closing-loop.B.UI: PositionCard reads `mark_price`
                # but the backend writes `current_price` in trading_cases.
                # Provide an alias so Entry and Mark are both populated in UI.
                r.setdefault("mark_price", r.get("current_price", 0.0))
                # leverage default — UI renders "{leverage}x"
                r.setdefault("leverage", 1)
                merged.append(r)
        except Exception as e:
            logger.warning(f"[PositionRoutes] trading_cases read failed: {e}")

        return merged
    except Exception as e:
        logger.error(f"[PositionRoutes] Get positions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_positions():
    """
    Manually trigger position sync from exchange.
    
    Returns:
        {"ok": bool, "count": int}
    """
    try:
        service = get_position_sync_service()
        result = await service.sync_positions()
        return result
    except Exception as e:
        logger.error(f"[PositionRoutes] Sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{symbol}/close")
async def close_position(symbol: str):
    """
    Close position for symbol (MARKET order).
    
    Returns:
        {"ok": bool, "exchange_order_id": str, "status": str}
    """
    try:
        exchange_service = get_exchange_service()
        adapter = exchange_service.adapter
        
        result = adapter.close_position(symbol)
        
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Close failed"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PositionRoutes] Close position failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
