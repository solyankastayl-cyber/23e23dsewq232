"""
P1.2 - Latency Repository

Persists latency events to MongoDB for historical analysis.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class LatencyRepository:
    """Persist latency events"""
    
    def __init__(self, motor_db):
        self.collection = motor_db["latency_events"]
    
    async def insert(self, event_dict: Dict[str, Any]):
        """Insert latency event"""
        try:
            await self.collection.insert_one(event_dict)
            logger.debug(f"✅ Latency event persisted: {event_dict.get('client_order_id')}")
        except Exception as e:
            logger.error(f"❌ Failed to persist latency event: {e}")
    
    async def get_by_order_id(self, client_order_id: str) -> Optional[Dict[str, Any]]:
        """Get latency event by order ID"""
        try:
            event = await self.collection.find_one({"client_order_id": client_order_id})
            if event:
                event.pop("_id", None)
            return event
        except Exception as e:
            logger.error(f"❌ Failed to fetch latency event: {e}")
            return None
    
    async def get_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get all latency events for a trace ID"""
        try:
            cursor = self.collection.find({"trace_id": trace_id})
            events = await cursor.to_list(length=100)
            for event in events:
                event.pop("_id", None)
            return events
        except Exception as e:
            logger.error(f"❌ Failed to fetch latency events by trace: {e}")
            return []
    
    async def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent latency events"""
        try:
            cursor = self.collection.find().sort("fill_ts", -1).limit(limit)
            events = await cursor.to_list(length=limit)
            for event in events:
                event.pop("_id", None)
            return events
        except Exception as e:
            logger.error(f"❌ Failed to fetch recent latency events: {e}")
            return []
    
    async def get_stats(self, last_n: int = 100) -> Dict[str, Any]:
        """Calculate percentile stats from DB"""
        try:
            pipeline = [
                {"$sort": {"fill_ts": -1}},
                {"$limit": last_n},
                {"$group": {
                    "_id": None,
                    "count": {"$sum": 1},
                    "latencies": {"$push": "$total_latency_ms"}
                }}
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(length=1)
            
            if not result or not result[0].get("latencies"):
                return {"count": 0}
            
            latencies = sorted(result[0]["latencies"])
            count = len(latencies)
            
            def percentile(data, p):
                index = int(len(data) * p / 100)
                return data[min(index, len(data) - 1)]
            
            return {
                "count": count,
                "p50_ms": percentile(latencies, 50),
                "p95_ms": percentile(latencies, 95),
                "p99_ms": percentile(latencies, 99)
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to calculate latency stats: {e}")
            return {"count": 0}
