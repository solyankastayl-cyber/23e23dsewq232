"""
Dead Letter Queue Repository (P1.1)
===================================

Mongo persistence for failed queue items.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from .queue_models import DLQItem, QueueItem, DLQClassification

logger = logging.getLogger(__name__)


class DLQRepository:
    """Repository for dead letter queue (failed orders)."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["failed_order_queue"]
        logger.info("✅ DLQRepository initialized")
    
    async def ensure_indexes(self):
        """Create indexes for DLQ collection."""
        await self.collection.create_index("queue_item_id", unique=True)
        await self.collection.create_index("client_order_id")
        await self.collection.create_index("trace_id")
        await self.collection.create_index("failed_at")
        await self.collection.create_index("classification")
        logger.info("✅ DLQ indexes created")
    
    async def add(
        self,
        queue_item: QueueItem,
        final_error: str,
        classification: DLQClassification
    ) -> None:
        """
        Add item to DLQ.
        
        Args:
            queue_item: Failed queue item
            final_error: Error message
            classification: Failure classification
        """
        dlq_item = DLQItem(
            queue_item_id=queue_item.queue_item_id,
            trace_id=queue_item.trace_id,
            client_order_id=queue_item.client_order_id,
            strategy_id=queue_item.payload.get("strategy_id"),
            action_type=queue_item.action_type,
            payload=queue_item.payload,
            attempts=queue_item.attempt,
            final_error=final_error,
            failed_at=datetime.now(timezone.utc),
            classification=classification
        )
        
        await self.collection.insert_one(dlq_item.dict())
        
        logger.error(
            f"❌ DLQ added: queue_item_id={queue_item.queue_item_id}, "
            f"client_order_id={queue_item.client_order_id}, "
            f"classification={classification}, trace_id={queue_item.trace_id}"
        )
    
    async def list_recent(self, limit: int = 100) -> List[DLQItem]:
        """Get recent DLQ items."""
        cursor = self.collection.find().sort("failed_at", -1).limit(limit)
        items = await cursor.to_list(length=limit)
        return [DLQItem(**item) for item in items]
    
    async def count(self) -> int:
        """Get total DLQ count."""
        return await self.collection.count_documents({})
    
    async def get_by_trace_id(self, trace_id: str) -> List[DLQItem]:
        """Get DLQ items by trace_id."""
        cursor = self.collection.find({"trace_id": trace_id})
        items = await cursor.to_list(length=None)
        return [DLQItem(**item) for item in items]

    
    async def list_dlq(self, limit: int = 100) -> list:
        """
        P1 Product Layer: List recent DLQ items for UI.
        
        Args:
            limit: Max items to return
        
        Returns:
            List of DLQ items (most recent first)
        """
        cursor = self.collection.find().sort("failed_at", -1).limit(limit)
        items = await cursor.to_list(length=limit)
        
        # Convert to dict and make _id JSON-serializable
        result = []
        for item in items:
            item["_id"] = str(item["_id"])
            result.append(item)
        
        return result

