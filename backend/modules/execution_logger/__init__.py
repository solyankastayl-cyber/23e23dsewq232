"""
Execution Logger — P1.4 Debug Layer

Tracks:
- Signals generated
- Decisions made
- Orders placed
- Rejections

Provides visibility into Signal → Decision → Execution pipeline
"""

from .repository import ExecutionEventRepository

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ExecutionLogger:
    """
    Centralized execution event logger.
    
    Stores events in MongoDB for ZAP Tab visibility.
    """
    
    def __init__(self, db):
        self.db = db
        self.events_collection = db.execution_events
        self.signals_collection = db.execution_signals
        self.decisions_collection = db.execution_decisions
        
        logger.info("[ExecutionLogger] Initialized")
    
    async def log_signal(self, signal: Dict[str, Any]):
        """Log a generated signal."""
        event = {
            "type": "SIGNAL",
            "symbol": signal.get("symbol"),
            "side": signal.get("side"),
            "confidence": signal.get("confidence"),
            "strategy": signal.get("strategy"),
            "timestamp": datetime.now(timezone.utc),
        }
        
        await self.signals_collection.insert_one(signal.copy())
        await self.events_collection.insert_one(event)
        
        logger.debug(f"[ExecutionLogger] Signal: {signal['symbol']} {signal['side']} ({signal['strategy']})")
    
    async def log_decision(self, decision: Dict[str, Any]):
        """Log a risk decision."""
        event = {
            "type": "DECISION",
            "symbol": decision.get("symbol"),
            "approved": decision.get("approved"),
            "reason": decision.get("reason"),
            "confidence": decision.get("confidence"),
            "timestamp": datetime.now(timezone.utc),
        }
        
        await self.decisions_collection.insert_one(decision.copy())
        await self.events_collection.insert_one(event)
        
        status = "APPROVED" if decision["approved"] else "REJECTED"
        logger.info(f"[ExecutionLogger] Decision: {decision['symbol']} {status} ({decision.get('reason', 'N/A')})")
    
    async def log_rejection(self, symbol: str, reason: str, signal: Dict[str, Any] = None):
        """Log a rejected signal."""
        rejection = {
            "symbol": symbol,
            "reason": reason,
            "confidence": signal.get("confidence") if signal else None,
            "strategy": signal.get("strategy") if signal else None,
            "timestamp": datetime.now(timezone.utc),
        }
        
        await self.db.strategy_rejections.insert_one(rejection.copy())
        
        event = {
            "type": "REJECT",
            "symbol": symbol,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc),
        }
        
        await self.events_collection.insert_one(event)
        
        logger.warning(f"[ExecutionLogger] Rejection: {symbol} → {reason}")
    
    async def log_order(self, order: Dict[str, Any]):
        """Log an order placement."""
        event = {
            "type": "ORDER",
            "symbol": order.get("symbol"),
            "side": order.get("side"),
            "status": order.get("status"),
            "order_id": order.get("order_id"),
            "timestamp": datetime.now(timezone.utc),
        }
        
        await self.events_collection.insert_one(event)
        
        logger.info(f"[ExecutionLogger] Order: {order['symbol']} {order['side']} → {order['status']}")
    
    async def log_fill(self, fill: Dict[str, Any]):
        """Log an order fill."""
        event = {
            "type": "FILL",
            "symbol": fill.get("symbol"),
            "side": fill.get("side"),
            "qty": fill.get("qty"),
            "price": fill.get("price"),
            "pnl": fill.get("pnl"),
            "timestamp": datetime.now(timezone.utc),
        }
        
        await self.events_collection.insert_one(event)
        
        logger.info(f"[ExecutionLogger] Fill: {fill['symbol']} {fill['qty']} @ ${fill['price']}")
    
    async def log_event(self, event: Dict[str, Any]):
        """Log a generic event."""
        from datetime import datetime, timezone
        from uuid import uuid4
        import time
        
        # Ensure required fields
        if "event_id" not in event:
            event["event_id"] = str(uuid4())
        
        if "timestamp" not in event:
            event["timestamp"] = int(time.time() * 1000)
        
        if "timestamp_dt" not in event:
            event["timestamp_dt"] = datetime.now(timezone.utc)
        
        await self.events_collection.insert_one(event.copy())
        
        logger.debug(f"[ExecutionLogger] Event: {event.get('type', 'UNKNOWN')}")
        
        # WS-1: Broadcast to execution.feed channel
        try:
            from modules.ws_hub.service_locator import get_ws_broadcaster
            
            broadcaster = get_ws_broadcaster()
            event_type = event.get("type") or event.get("event_type") or "UNKNOWN_EVENT"
            
            await broadcaster.broadcast_event(
                channel="execution.feed",
                event=event_type,
                data={
                    "symbol": event.get("symbol"),
                    "side": event.get("side"),
                    "reason": event.get("reason"),
                    "strategy": event.get("strategy"),
                    "order_id": event.get("order_id"),
                    "qty": event.get("qty"),
                    "price": event.get("price"),
                    "status": event.get("status"),
                    "confidence": event.get("confidence"),
                    "approved": event.get("approved"),
                },
            )
        except Exception as e:
            # WS must never break execution logger
            logger.debug(f"[ExecutionLogger] WS broadcast failed (non-critical): {e}")
            pass
    
    async def get_feed(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Get recent execution feed.
        
        Returns unified feed of all events (signals, decisions, orders, fills)
        """
        events = await self.events_collection.find(
            {},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(length=limit)
        
        return events


# Singleton
_execution_logger = None


def init_execution_logger(db):
    """Initialize execution logger singleton."""
    global _execution_logger
    _execution_logger = ExecutionLogger(db)
    logger.info("[ExecutionLogger] Singleton initialized")


def get_execution_logger() -> ExecutionLogger:
    """Get execution logger singleton."""
    if _execution_logger is None:
        raise RuntimeError("ExecutionLogger not initialized. Call init_execution_logger() first.")
    return _execution_logger
