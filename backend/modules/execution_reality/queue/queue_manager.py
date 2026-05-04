"""
In-Memory Priority Queue Manager (P1.1)
=======================================

Thread-safe priority queue with delayed retry scheduling.
Designed for easy migration to Redis in P1.1B.
"""

import asyncio
import heapq
import logging
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from .queue_models import QueueItem, QueueStatus, QueueMetrics

logger = logging.getLogger(__name__)


class InMemoryQueueManager:
    """
    In-memory priority queue with delayed retry scheduling.
    
    Features:
    - Priority-based dequeue (P0 > P1 > P2)
    - Delayed retry scheduling (next_retry_at)
    - Thread/async safety via asyncio.Lock
    - Idempotency checking (duplicate client_order_id + action_type)
    - Metrics tracking
    
    Architecture:
    - heap: priority queue for ready items
    - retry_queue: delayed items waiting for next_retry_at
    - processing: items currently being processed
    - done: completed items (for metrics)
    """
    
    def __init__(self):
        self._lock = asyncio.Lock()
        
        # Main priority queue: (priority, created_at, queue_item_id, QueueItem)
        self._heap: List[tuple] = []
        
        # Retry queue: items waiting for next_retry_at
        self._retry_queue: List[QueueItem] = []
        
        # Processing: {queue_item_id: QueueItem}
        self._processing: Dict[str, QueueItem] = {}
        
        # Done items (for metrics) — limited retention
        self._done: List[QueueItem] = []
        self._max_done_retention = 1000
        
        # Idempotency tracking: (client_order_id, action_type) → queue_item_id
        self._active_items: Dict[tuple, str] = {}
        
        # Metrics
        self._retry_count = 0
        self._wait_times_ms: List[float] = []
        self._processing_times_ms: List[float] = []
        
        logger.info("✅ InMemoryQueueManager initialized")
    
    async def enqueue(self, item: QueueItem) -> Dict[str, any]:
        """
        Enqueue a new item.
        
        Returns:
            {
                "accepted": bool,
                "queue_item_id": str,
                "reason": str (if rejected)
            }
        """
        async with self._lock:
            # Idempotency check
            idempotency_key = (item.client_order_id, item.action_type)
            if idempotency_key in self._active_items:
                existing_id = self._active_items[idempotency_key]
                logger.warning(
                    f"⚠️ Duplicate enqueue rejected: client_order_id={item.client_order_id}, "
                    f"action_type={item.action_type}, existing_queue_item_id={existing_id}"
                )
                return {
                    "accepted": False,
                    "queue_item_id": item.queue_item_id,
                    "reason": f"Duplicate: already queued as {existing_id}"
                }
            
            # Add to priority queue
            heap_entry = (
                item.priority,
                item.created_at.timestamp(),
                item.queue_item_id,
                item
            )
            heapq.heappush(self._heap, heap_entry)
            
            # Track for idempotency
            self._active_items[idempotency_key] = item.queue_item_id
            
            logger.info(
                f"✅ Enqueued: queue_item_id={item.queue_item_id}, "
                f"client_order_id={item.client_order_id}, "
                f"action_type={item.action_type}, priority={item.priority}, "
                f"trace_id={item.trace_id}"
            )
            
            return {
                "accepted": True,
                "queue_item_id": item.queue_item_id,
            }
    
    async def dequeue_ready(self) -> Optional[QueueItem]:
        """
        Dequeue the highest-priority ready item.
        
        Also moves items from retry_queue to heap if next_retry_at has passed.
        """
        async with self._lock:
            # First, move ready retry items back to heap
            await self._promote_ready_retries()
            
            # Dequeue from heap
            if not self._heap:
                return None
            
            _, _, queue_item_id, item = heapq.heappop(self._heap)
            
            # Move to processing
            item.status = "PROCESSING"
            item.updated_at = datetime.now(timezone.utc)
            self._processing[queue_item_id] = item
            
            # Track wait time
            wait_ms = (datetime.now(timezone.utc) - item.created_at).total_seconds() * 1000
            self._wait_times_ms.append(wait_ms)
            if len(self._wait_times_ms) > 100:
                self._wait_times_ms.pop(0)
            
            logger.debug(f"🔄 Dequeued: queue_item_id={queue_item_id}, wait_ms={wait_ms:.1f}")
            
            return item
    
    async def mark_processing(self, queue_item_id: str) -> None:
        """Mark item as processing (already done in dequeue_ready)."""
        pass  # No-op, status already set in dequeue_ready
    
    async def mark_done(self, queue_item_id: str) -> None:
        """Mark item as successfully completed."""
        async with self._lock:
            item = self._processing.pop(queue_item_id, None)
            if not item:
                logger.warning(f"⚠️ mark_done: item not found in processing: {queue_item_id}")
                return
            
            item.status = "DONE"
            item.updated_at = datetime.now(timezone.utc)
            
            # Track processing time
            if item.updated_at:
                processing_ms = (item.updated_at - item.created_at).total_seconds() * 1000
                self._processing_times_ms.append(processing_ms)
                if len(self._processing_times_ms) > 100:
                    self._processing_times_ms.pop(0)
            
            # Add to done list (limited retention)
            self._done.append(item)
            if len(self._done) > self._max_done_retention:
                self._done.pop(0)
            
            # Remove from idempotency tracking
            idempotency_key = (item.client_order_id, item.action_type)
            self._active_items.pop(idempotency_key, None)
            
            logger.info(f"✅ Marked done: queue_item_id={queue_item_id}")
    
    async def mark_retry(
        self,
        queue_item_id: str,
        retry_after_seconds: float,
        error: str
    ) -> None:
        """
        Mark item for retry with exponential backoff.
        
        Args:
            queue_item_id: Item ID
            retry_after_seconds: Delay before next retry
            error: Error message
        """
        async with self._lock:
            item = self._processing.pop(queue_item_id, None)
            if not item:
                logger.warning(f"⚠️ mark_retry: item not found in processing: {queue_item_id}")
                return
            
            item.attempt += 1
            item.status = "RETRYING"
            item.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=retry_after_seconds)
            item.updated_at = datetime.now(timezone.utc)
            
            # Add to retry queue
            self._retry_queue.append(item)
            self._retry_count += 1
            
            logger.warning(
                f"🔄 Marked retry: queue_item_id={queue_item_id}, "
                f"attempt={item.attempt}/{item.max_attempts}, "
                f"retry_after={retry_after_seconds}s, error={error}"
            )
    
    async def mark_failed_to_dlq(
        self,
        queue_item_id: str,
        error: str,
        classification: str
    ) -> None:
        """
        Mark item as failed and remove from queue (DLQ handled externally).
        
        Args:
            queue_item_id: Item ID
            error: Final error message
            classification: DLQ classification
        """
        async with self._lock:
            item = self._processing.pop(queue_item_id, None)
            if not item:
                logger.warning(f"⚠️ mark_failed_to_dlq: item not found in processing: {queue_item_id}")
                return
            
            item.status = "FAILED_DLQ"
            item.updated_at = datetime.now(timezone.utc)
            
            # Remove from idempotency tracking
            idempotency_key = (item.client_order_id, item.action_type)
            self._active_items.pop(idempotency_key, None)
            
            logger.error(
                f"❌ Marked DLQ: queue_item_id={queue_item_id}, "
                f"classification={classification}, error={error}"
            )
    
    async def _promote_ready_retries(self) -> None:
        """Move items from retry_queue to heap if next_retry_at has passed."""
        now = datetime.now(timezone.utc)
        ready_items = []
        pending_items = []
        
        for item in self._retry_queue:
            if item.next_retry_at and item.next_retry_at <= now:
                # Reset status and add back to heap
                item.status = "QUEUED"
                item.next_retry_at = None
                heap_entry = (
                    item.priority,
                    item.created_at.timestamp(),
                    item.queue_item_id,
                    item
                )
                heapq.heappush(self._heap, heap_entry)
                ready_items.append(item.queue_item_id)
            else:
                pending_items.append(item)
        
        self._retry_queue = pending_items
        
        if ready_items:
            logger.debug(f"♻️ Promoted {len(ready_items)} items from retry queue")
    
    async def get_metrics(self) -> QueueMetrics:
        """Get current queue metrics."""
        async with self._lock:
            avg_wait_ms = sum(self._wait_times_ms) / len(self._wait_times_ms) if self._wait_times_ms else 0.0
            avg_processing_ms = (
                sum(self._processing_times_ms) / len(self._processing_times_ms)
                if self._processing_times_ms else 0.0
            )
            
            return QueueMetrics(
                queue_depth=len(self._heap),
                processing_count=len(self._processing),
                retry_count=len(self._retry_queue),
                dlq_count=0,  # DLQ count comes from Mongo (external)
                avg_wait_ms=avg_wait_ms,
                avg_processing_ms=avg_processing_ms,
                workers_active=0,  # Updated by worker pool
                workers_total=0,   # Updated by worker pool
                timestamp=datetime.now(timezone.utc)
            )
    
    async def get_queue_depth(self) -> int:
        """Get current queue depth."""
        async with self._lock:
            return len(self._heap)
    
    async def get_processing_count(self) -> int:
        """Get count of items currently being processed."""
        async with self._lock:
            return len(self._processing)
