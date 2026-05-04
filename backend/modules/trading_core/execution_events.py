"""Execution Events Service — Week 3

Tracks execution events for live feed:
- SIGNAL_DETECTED
- DECISION_MADE
- ORDER_SUBMITTED
- ORDER_FILLED
- POSITION_OPENED
- POSITION_CLOSED
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)


class ExecutionEventsService:
    """Service for tracking and retrieving execution events."""
    
    def __init__(self, db_client: AsyncIOMotorClient):
        self.db = db_client.trading_db
    
    async def log_event(
        self,
        event_type: str,
        symbol: str,
        data: Dict[str, Any] = None
    ):
        """Log execution event.
        
        Args:
            event_type: SIGNAL_DETECTED, DECISION_MADE, ORDER_SUBMITTED, ORDER_FILLED, etc.
            symbol: Trading symbol
            data: Additional event data
        """
        event = {
            "event_type": event_type,
            "symbol": symbol,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc),
        }
        
        await self.db.execution_events.insert_one(event)
        
        logger.debug(f"[ExecutionEvents] {event_type}: {symbol}")
    
    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent execution events.
        
        Args:
            limit: Max events to return
        
        Returns:
            List of events (newest first)
        """
        events = await self.db.execution_events.find().sort(
            "timestamp", -1
        ).limit(limit).to_list(length=limit)
        
        # Remove _id
        for event in events:
            event.pop("_id", None)
            # Format timestamp
            if isinstance(event.get("timestamp"), datetime):
                event["timestamp"] = event["timestamp"].isoformat()
        
        return events


# Global instance
_events_service = None


def init_events_service(db_client: AsyncIOMotorClient):
    """Initialize global events service."""
    global _events_service
    _events_service = ExecutionEventsService(db_client)
    return _events_service


def get_events_service():
    """Get global events service instance."""
    if _events_service is None:
        raise ValueError("Events service not initialized")
    return _events_service
