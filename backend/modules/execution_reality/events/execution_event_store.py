"""Execution Event Store

Иммутабельное хранилище событий в MongoDB.
Записываем события, читаем для replay/debug.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Optional
import os
import logging
from .execution_event_types import ExecutionEvent

logger = logging.getLogger(__name__)


class ExecutionEventStore:
    """Event Store для execution events"""

    def __init__(self):
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client["trading_os"]
        self.collection = self.db["execution_events"]

    async def append(self, event: ExecutionEvent) -> None:
        """
        Записать событие (иммутабельно) с idempotency защитой.
        Если event_id уже существует — skip (безопасно игнорируем дубли).
        """
        try:
            await self.collection.insert_one(event.dict())
        except Exception as e:
            # Duplicate key error (event_id unique constraint) — это нормально, skip
            if "duplicate key" in str(e).lower() or "E11000" in str(e):
                logger.debug(f"Idempotency: skipping duplicate event_id={event.event_id}")
                return
            else:
                # Другая ошибка — пробрасываем
                logger.error(f"Failed to append event: {e}")
                raise

    async def list_last(
        self,
        limit: int = 5,
        symbol: Optional[str] = None,
        client_order_id: Optional[str] = None
    ) -> List[ExecutionEvent]:
        """Получить последние события (для debug/UI)"""
        query = {}
        if symbol:
            query["symbol"] = symbol
        if client_order_id:
            query["client_order_id"] = client_order_id

        cursor = self.collection.find(query).sort("timestamp", -1).limit(limit)
        events = await cursor.to_list(length=limit)
        return [ExecutionEvent(**event) for event in events]

    async def get_events_for_order(self, client_order_id: str) -> List[ExecutionEvent]:
        """Получить все события для конкретного ордера (для replay)"""
        cursor = self.collection.find({"client_order_id": client_order_id}).sort("timestamp", 1)
        events = await cursor.to_list(length=None)
        return [ExecutionEvent(**event) for event in events]

    async def list_all_for_rebuild(self, limit: int = 100000) -> List[ExecutionEvent]:
        """
        Получить ВСЕ события в хронологическом порядке (для boot restore).
        
        Args:
            limit: максимум событий (защита от OOM)
        
        Returns:
            Список всех событий, отсортированных по timestamp
        """
        cursor = self.collection.find({}).sort("timestamp", 1).limit(limit)
        events = await cursor.to_list(length=limit)
        logger.info(f"Loaded {len(events)} events for rebuild")
        
        # Filter out invalid events (legacy data from pre-schema migrations)
        valid_events = []
        for event in events:
            try:
                valid_events.append(ExecutionEvent(**event))
            except Exception as e:
                logger.warning(f"Skipping invalid event {event.get('_id')}: {e}")
                continue
        
        logger.info(f"✅ Validated {len(valid_events)}/{len(events)} events (skipped {len(events) - len(valid_events)} invalid)")
        return valid_events

    async def ensure_indexes(self):
        """Создать необходимые индексы (в том числе unique event_id для idempotency)"""
        try:
            # Unique index на event_id (для idempotency)
            await self.collection.create_index("event_id", unique=True)
            logger.info("✅ Created unique index on event_id (idempotency)")
            
            # Index на timestamp (для сортировки)
            await self.collection.create_index("timestamp")
            
            # Index на client_order_id (для быстрого поиска по ордеру)
            await self.collection.create_index("client_order_id")
            
            logger.info("✅ Execution event store indexes ensured")
        except Exception as e:
            logger.warning(f"Index creation warning (may already exist): {e}")
