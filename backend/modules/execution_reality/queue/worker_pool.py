"""
Worker Pool (P1.1)
==================

In-process async worker pool for order queue processing.

Features:
- 2-4 configurable workers
- Graceful start/stop via FastAPI lifespan
- Worker health monitoring
- trace_id propagation
- Retry/DLQ handling
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone

from .queue_manager import InMemoryQueueManager
from .queue_models import QueueItem, DLQClassification
from .retry_classifier import RetryClassifier
from .dlq_repository import DLQRepository
from ..events.execution_event_types import create_event, EXECUTION_EVENT_TYPES
from ..events.execution_event_store import ExecutionEventStore
from ..events.execution_event_bus import ExecutionEventBus
from ..adapters.binance_rest_adapter import BinanceRestAdapter
from ..adapters.binance_mapper import BinanceMapper

logger = logging.getLogger(__name__)


class WorkerPool:
    """
    In-process worker pool for order queue.
    
    Each worker:
    1. Dequeues ready item
    2. Processes (submit to exchange)
    3. Emits execution events
    4. Handles retry/DLQ logic
    """
    
    def __init__(
        self,
        queue_manager: InMemoryQueueManager,
        dlq_repository: DLQRepository,
        event_store: ExecutionEventStore,
        event_bus: ExecutionEventBus,
        binance_adapter: BinanceRestAdapter,
        binance_mapper: BinanceMapper,
        num_workers: int = 3
    ):
        self.queue_manager = queue_manager
        self.dlq_repository = dlq_repository
        self.event_store = event_store
        self.event_bus = event_bus
        self.binance_adapter = binance_adapter
        self.binance_mapper = binance_mapper
        self.num_workers = num_workers
        
        self.retry_classifier = RetryClassifier()
        
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._workers_active = 0
        
        logger.info(f"✅ WorkerPool initialized (workers={num_workers})")
    
    async def start(self):
        """Start worker pool."""
        if self._running:
            logger.warning("⚠️ WorkerPool already running")
            return
        
        self._running = True
        
        # Spawn workers
        for i in range(self.num_workers):
            task = asyncio.create_task(self._worker_loop(worker_id=i))
            self._workers.append(task)
        
        logger.info(f"✅ WorkerPool started ({self.num_workers} workers)")
    
    async def stop(self):
        """Stop worker pool gracefully."""
        if not self._running:
            return
        
        self._running = False
        
        # Wait for workers to finish current items
        logger.info("🛑 Stopping WorkerPool...")
        
        for task in self._workers:
            task.cancel()
        
        await asyncio.gather(*self._workers, return_exceptions=True)
        
        self._workers.clear()
        
        logger.info("✅ WorkerPool stopped")
    
    async def _worker_loop(self, worker_id: int):
        """Main worker loop."""
        logger.info(f"🟢 Worker {worker_id} started")
        
        while self._running:
            try:
                # Dequeue ready item
                item = await self.queue_manager.dequeue_ready()
                
                if item is None:
                    # No items ready, sleep briefly
                    await asyncio.sleep(0.1)
                    continue
                
                # Process item
                self._workers_active += 1
                try:
                    await self._process_item(item, worker_id)
                finally:
                    self._workers_active -= 1
            
            except asyncio.CancelledError:
                logger.info(f"🛑 Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Worker {worker_id} unexpected error: {e}", exc_info=True)
                await asyncio.sleep(1)  # Brief pause before retry
        
        logger.info(f"🔴 Worker {worker_id} stopped")
    
    async def _process_item(self, item: QueueItem, worker_id: int):
        """
        Process a single queue item.
        
        Flow:
        1. Emit ORDER_SUBMIT_REQUESTED event
        2. Submit to exchange
        3. Emit ACK/REJECT event
        4. Mark done OR retry OR DLQ
        """
        logger.info(
            f"[Worker {worker_id}] Processing: queue_item_id={item.queue_item_id}, "
            f"client_order_id={item.client_order_id}, "
            f"action_type={item.action_type}, trace_id={item.trace_id}"
        )
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # 1. Emit ORDER_SUBMIT_REQUESTED event
            submit_event = create_event(
                event_type=EXECUTION_EVENT_TYPES["ORDER_SUBMIT_REQUESTED"],
                exchange=item.payload.get("exchange", "binance"),
                symbol=item.payload.get("symbol"),
                client_order_id=item.client_order_id,
                trace_id=item.trace_id,
                payload={
                    "action_type": item.action_type,
                    "queue_item_id": item.queue_item_id,
                    **item.payload
                }
            )
            await self.event_store.append(submit_event)
            await self.event_bus.publish(submit_event)
            
            # 1.5 Execution-level idempotency check
            # Check if this client_order_id was already submitted/ACKed
            existing_event = await self._check_existing_submission(item.client_order_id)
            if existing_event:
                logger.warning(
                    f"[Worker {worker_id}] ⚠️ Idempotency: client_order_id already processed, "
                    f"existing_event={existing_event['event_type']}, skipping submit"
                )
                # Mark done without re-submitting
                await self.queue_manager.mark_done(item.queue_item_id)
                return
            
            # 2. Submit to exchange
            binance_response = await self._submit_to_exchange(item)
            
            # 3. Map response to ACK/REJECT event
            ack_or_reject_event = self.binance_mapper.map_order_response_to_event(
                binance_response=binance_response,
                client_order_id=item.client_order_id
            )
            ack_or_reject_event.trace_id = item.trace_id
            
            await self.event_store.append(ack_or_reject_event)
            await self.event_bus.publish(ack_or_reject_event)
            
            # 4. Mark done
            await self.queue_manager.mark_done(item.queue_item_id)
            
            processing_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.info(
                f"[Worker {worker_id}] ✅ Completed: queue_item_id={item.queue_item_id}, "
                f"event_type={ack_or_reject_event.event_type}, processing_ms={processing_ms:.1f}"
            )
        
        except Exception as e:
            # Handle error: retry or DLQ
            await self._handle_error(item, e, worker_id)
    
    async def _submit_to_exchange(self, item: QueueItem) -> dict:
        """Submit order to exchange based on action_type."""
        action_type = item.action_type
        payload = item.payload
        
        if action_type == "OPEN_ORDER":
            # Submit LIMIT order
            return await self.binance_adapter.submit_limit_order(
                symbol=payload["symbol"],
                side=payload["side"],
                qty=payload["qty"],
                price=payload["price"]
            )
        
        elif action_type == "CLOSE_POSITION":
            # Submit MARKET order (close)
            # TODO: implement market order in adapter
            raise NotImplementedError("CLOSE_POSITION not yet implemented")
        
        elif action_type == "CANCEL_ORDER":
            # Cancel order
            # TODO: implement cancel in adapter
            raise NotImplementedError("CANCEL_ORDER not yet implemented")
        
        else:
            raise ValueError(f"Unsupported action_type: {action_type}")
    
    async def _handle_error(self, item: QueueItem, error: Exception, worker_id: int):
        """
        Handle processing error: retry or DLQ.
        
        Logic:
        1. Classify error (retryable vs non-retryable)
        2. If retryable and attempts < max: retry with backoff
        3. Otherwise: move to DLQ
        """
        error_str = str(error)
        
        # Classify error
        is_retryable, dlq_classification = self.retry_classifier.classify(error)
        
        # Non-retryable → DLQ immediately
        if not is_retryable:
            await self._move_to_dlq(item, error_str, dlq_classification, worker_id)
            return
        
        # Retryable → check attempts
        if item.attempt >= item.max_attempts:
            # Max attempts exceeded → DLQ
            await self._move_to_dlq(item, error_str, "retry_exhausted", worker_id)
            return
        
        # Retry with backoff
        backoff_seconds = self.retry_classifier.get_backoff_seconds(item.attempt)
        await self.queue_manager.mark_retry(
            queue_item_id=item.queue_item_id,
            retry_after_seconds=backoff_seconds,
            error=error_str
        )
        
        logger.warning(
            f"[Worker {worker_id}] 🔄 Retry scheduled: queue_item_id={item.queue_item_id}, "
            f"attempt={item.attempt + 1}/{item.max_attempts}, "
            f"backoff={backoff_seconds}s, error={error_str}"
        )
    
    async def _move_to_dlq(
        self,
        item: QueueItem,
        error: str,
        classification: DLQClassification,
        worker_id: int
    ):
        """Move item to Dead Letter Queue."""
        # Add to DLQ repository
        await self.dlq_repository.add(
            queue_item=item,
            final_error=error,
            classification=classification
        )
        
        # Mark in queue manager
        await self.queue_manager.mark_failed_to_dlq(
            queue_item_id=item.queue_item_id,
            error=error,
            classification=classification
        )
        
        logger.error(
            f"[Worker {worker_id}] ❌ Moved to DLQ: queue_item_id={item.queue_item_id}, "
            f"classification={classification}, error={error}"
        )
    
    async def _check_existing_submission(self, client_order_id: str) -> Optional[dict]:
        """
        Execution-level idempotency check.
        
        Check if this client_order_id was already submitted/ACKed.
        
        Returns:
            Existing event dict if found, None otherwise
        """
        # Query event store for any ACK/REJECT events with this client_order_id
        # (simplified: check last 1000 events)
        from ..events.execution_event_types import EXECUTION_EVENT_TYPES
        
        events = await self.event_store.list_last(limit=1000)
        
        for event in events:
            if (
                event.client_order_id == client_order_id
                and event.event_type in [
                    EXECUTION_EVENT_TYPES["ORDER_ACKNOWLEDGED"],
                    EXECUTION_EVENT_TYPES["ORDER_REJECTED"]
                ]
            ):
                return {
                    "event_type": event.event_type,
                    "event_id": event.event_id
                }
        
        return None
    
    def get_active_workers_count(self) -> int:
        """Get count of currently active workers."""
        return self._workers_active
    
    def get_total_workers_count(self) -> int:
        """Get total workers count."""
        return self.num_workers

