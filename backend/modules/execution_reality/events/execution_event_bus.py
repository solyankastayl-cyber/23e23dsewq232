"""Execution Event Bus

In-process pub/sub для событий исполнения.
Подписчики (projections) получают события синхронно.
"""

from typing import Callable, List
from .execution_event_types import ExecutionEvent
import logging

logger = logging.getLogger(__name__)


class ExecutionEventBus:
    """In-process event bus"""

    def __init__(self, audit_repo=None):
        self._subscribers: List[Callable[[ExecutionEvent], None]] = []
        self.audit_repo = audit_repo  # P0.7 Audit hook

    def subscribe(self, handler: Callable[[ExecutionEvent], None]) -> None:
        """Подписаться на события"""
        self._subscribers.append(handler)
        logger.info(f"Subscribed handler: {handler.__name__}")

    async def publish(self, event: ExecutionEvent) -> None:
        """Опубликовать событие всем подписчикам"""
        logger.info(f"Publishing event: {event.event_type} | order={event.client_order_id}")
        
        # P0.7 AUDIT HOOK - Log execution event
        if self.audit_repo:
            try:
                await self.audit_repo.insert({
                    "event_type": event.event_type,
                    "client_order_id": event.client_order_id,
                    "exchange_order_id": event.exchange_order_id,
                    "symbol": event.symbol,
                    "exchange": event.exchange,
                    "timestamp": event.timestamp,
                    "trace_id": event.trace_id,  # P0.7 CRITICAL: trace ID
                    "payload": event.payload
                })
            except Exception as e:
                # CRITICAL: Audit failure MUST NOT break execution
                logger.error(f"Execution audit failed (non-blocking): {e}")
        
        for handler in self._subscribers:
            try:
                # Вызываем синхронно (для простоты Milestone A)
                # В будущем можно сделать async handlers
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler {handler.__name__}: {e}")
