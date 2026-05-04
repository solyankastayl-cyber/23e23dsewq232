"""
Execution Debug Routes — P1.4 Visibility Layer
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging

from modules.execution_logger import get_execution_logger

logger = logging.getLogger(__name__)

router = APIRouter()


class TestOrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: float
    type: str = "MARKET"
    price: float = None


@router.post("/api/execution/test-order")
async def test_order(request: TestOrderRequest):
    """Direct order execution test with step-by-step tracing."""
    import asyncio
    import traceback as tb
    import time
    
    exec_logger = get_execution_logger()
    
    try:
        # STEP 1
        await exec_logger.log_event({
            "type": "STEP_1_TEST_ORDER_START",
            "symbol": request.symbol,
            "side": request.side,
            "quantity": request.quantity
        })
        
        from modules.exchange.order_builder import build_order_request
        from modules.exchange.service_v2 import get_exchange_service
        from modules.exchange.order_manager import OrderManager
        from modules.portfolio.service import get_portfolio_service
        
        # STEP 2
        await exec_logger.log_event({
            "type": "STEP_2_IMPORTS_DONE"
        })
        
        # Build order
        order = build_order_request(
            symbol=request.symbol,
            side=request.side,
            qty=request.quantity,
            order_type=request.type,
            price=request.price
        )
        
        # STEP 3
        await exec_logger.log_event({
            "type": "STEP_3_ORDER_BUILT",
            "symbol": order["symbol"],
            "side": order["side"],
            "order_type": order["type"],
            "quantity": order["quantity"]
        })
        
        # Get services
        exchange_service = get_exchange_service()
        adapter = exchange_service.get_adapter()
        portfolio = get_portfolio_service()
        
        # Create OrderManager
        order_mgr = OrderManager(adapter, portfolio.db)
        
        # STEP 4
        await exec_logger.log_event({
            "type": "STEP_4_ORDER_MANAGER_CREATED"
        })
        
        # Execute with timeout
        result = await asyncio.wait_for(
            order_mgr.place_order(order),
            timeout=5.0
        )
        
        # STEP 5
        await exec_logger.log_event({
            "type": "STEP_5_AFTER_PLACE_ORDER",
            "result": str(result)[:200]
        })
        
        # Success
        await exec_logger.log_event({
            "type": "TEST_ORDER_SUCCESS",
            "symbol": request.symbol
        })
        
        return {
            "ok": True,
            "result": result if isinstance(result, dict) else str(result)
        }
    
    except asyncio.TimeoutError:
        await exec_logger.log_event({
            "type": "TEST_ORDER_TIMEOUT",
            "symbol": request.symbol,
            "message": "place_order timed out after 5s"
        })
        
        return {
            "ok": False,
            "error": "TEST_ORDER_TIMEOUT",
            "message": "Order placement timed out after 5 seconds"
        }
    
    except Exception as e:
        error_trace = tb.format_exc()
        
        await exec_logger.log_event({
            "type": "TEST_ORDER_FAILED",
            "symbol": request.symbol,
            "error": str(e),
            "traceback": error_trace[:500]
        })
        
        return {
            "ok": False,
            "error": str(e),
            "traceback": error_trace[:500]
        }


@router.get("/api/execution/feed")
async def get_execution_feed(limit: int = 30):
    """
    Get unified execution feed.
    
    Returns all events (signals, decisions, orders, fills) in chronological order.
    """
    try:
        exec_logger = get_execution_logger()
        feed = await exec_logger.get_feed(limit=limit)
        
        return {
            "ok": True,
            "feed": feed
        }
    except Exception as e:
        logger.error(f"[ExecutionRoutes] Feed failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/api/execution/debug")
async def debug_events():
    """
    Debug endpoint - returns raw events from MongoDB.
    """
    try:
        exec_logger = get_execution_logger()
        
        # Get last 20 events
        events = await exec_logger.events_collection.find({}).sort("timestamp", -1).limit(20).to_list(length=20)
        
        # Convert to JSON-serializable format
        for e in events:
            if "_id" in e:
                e["_id"] = str(e["_id"])
            if "timestamp_dt" in e and hasattr(e["timestamp_dt"], "isoformat"):
                e["timestamp_dt"] = e["timestamp_dt"].isoformat()
        
        return {
            "ok": True,
            "count": len(events),
            "events": events
        }
    except Exception as e:
        logger.error(f"[Debug] Failed: {e}")
        return {
            "ok": False,
            "error": str(e)
        }


@router.get("/api/execution/signals")
async def get_signals(limit: int = 50):
    """Get recent signals."""
    try:
        exec_logger = get_execution_logger()
        
        signals = await exec_logger.signals_collection.find(
            {},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        return {
            "ok": True,
            "signals": signals
        }
    except Exception as e:
        logger.error(f"[ExecutionRoutes] Signals failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/execution/decisions")
async def get_decisions(limit: int = 50):
    """Get recent decisions."""
    try:
        exec_logger = get_execution_logger()
        
        decisions = await exec_logger.decisions_collection.find(
            {},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        return {
            "ok": True,
            "decisions": decisions
        }
    except Exception as e:
        logger.error(f"[ExecutionRoutes] Decisions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
