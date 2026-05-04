"""
Worker Pool v2 (P1.1C)
======================

Production-grade worker pool with:
- Idempotency (client_order_id)
- Exponential backoff retry
- Rate limiting (Binance semaphore)
- Duplicate order handling
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone

from .persistent_queue_repository import PersistentQueueRepository
from .persistent_queue_models import PersistentQueueTask
from .retry_classifier import RetryClassifier
from .dlq_repository import DLQRepository
from ..events.execution_event_types import create_event, EXECUTION_EVENT_TYPES
from ..events.execution_event_store import ExecutionEventStore
from ..events.execution_event_bus import ExecutionEventBus
from ..adapters.binance_rest_adapter import BinanceRestAdapter
from ..adapters.binance_mapper import BinanceMapper

logger = logging.getLogger(__name__)


class WorkerPoolV2:
    """
    Production-grade worker pool (P1.1C).
    
    Safety Features:
    - Idempotency: client_order_id prevents duplicates
    - Rate limiting: global semaphore for Binance calls
    - Smart retry: exponential backoff with error classification
    - Duplicate handling: -2010 treated as success
    """
    
    # P1.1C: Global rate limiter for Binance API
    # Limit concurrent exchange calls to avoid 429
    _binance_semaphore = asyncio.Semaphore(5)
    
    def __init__(
        self,
        persistent_queue: PersistentQueueRepository,
        dlq_repository: DLQRepository,
        event_store: ExecutionEventStore,
        event_bus: ExecutionEventBus,
        binance_adapter: BinanceRestAdapter,
        binance_mapper: BinanceMapper,
        num_workers: int = 3
    ):
        self.persistent_queue = persistent_queue
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
        
        logger.info(f"✅ WorkerPoolV2 initialized (workers={num_workers}, P1.1C safety)")
    
    async def start(self):
        """Start worker pool."""
        if self._running:
            logger.warning("⚠️ WorkerPoolV2 already running")
            return
        
        self._running = True
        
        # Spawn workers
        for i in range(self.num_workers):
            task = asyncio.create_task(self._worker_loop(worker_id=i))
            self._workers.append(task)
        
        logger.info(f"✅ WorkerPoolV2 started ({self.num_workers} workers)")
    
    async def stop(self):
        """Stop worker pool gracefully."""
        if not self._running:
            return
        
        self._running = False
        
        logger.info("🛑 Stopping WorkerPoolV2...")
        
        for task in self._workers:
            task.cancel()
        
        await asyncio.gather(*self._workers, return_exceptions=True)
        
        self._workers.clear()
        
        logger.info("✅ WorkerPoolV2 stopped")
    
    async def _worker_loop(self, worker_id: int):
        """Main worker loop."""
        logger.info(f"🟢 Worker {worker_id} started")
        
        while self._running:
            try:
                # Dequeue task (atomic with lease locking)
                task = await self.persistent_queue.dequeue()
                
                if task is None:
                    # No tasks ready, sleep briefly
                    await asyncio.sleep(0.5)
                    continue
                
                # Process task
                self._workers_active += 1
                try:
                    await self._process_task(task, worker_id)
                finally:
                    self._workers_active -= 1
            
            except asyncio.CancelledError:
                logger.info(f"🛑 Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Worker {worker_id} unexpected error: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info(f"🔴 Worker {worker_id} stopped")
    
    async def _process_task(self, task: PersistentQueueTask, worker_id: int):
        """
        Process a single task (P1.1C production-safe).
        
        Flow:
        1. Emit ORDER_SUBMIT_REQUESTED event
        2. Execution-level idempotency check
        3. Submit to exchange (with rate limiting)
        4. Handle duplicate order as success
        5. Emit ACK/REJECT event
        6. Mark done OR retry (with backoff) OR DLQ
        """
        logger.info(
            f"[Worker {worker_id}] Processing: task_id={task.task_id}, "
            f"type={task.type}, attempt={task.attempt + 1}, trace_id={task.trace_id}"
        )
        
        start_time = datetime.now(timezone.utc)
        
        # Extract client_order_id (P1.1C: idempotency key)
        client_order_id = task.payload.get("client_order_id")
        if not client_order_id:
            logger.error(
                f"[Worker {worker_id}] ❌ Missing client_order_id in payload"
            )
            await self._move_to_dlq(task, "Missing client_order_id", "malformed", worker_id)
            return
        
        try:
            # 1. Emit ORDER_SUBMIT_REQUESTED event
            submit_event = create_event(
                event_type=EXECUTION_EVENT_TYPES["ORDER_SUBMIT_REQUESTED"],
                exchange=task.payload.get("exchange", "binance"),
                symbol=task.payload.get("symbol"),
                client_order_id=client_order_id,
                trace_id=task.trace_id,
                payload={
                    "task_type": task.type,
                    "task_id": task.task_id,
                    **task.payload
                }
            )
            await self.event_store.append(submit_event)
            await self.event_bus.publish(submit_event)
            
            # 2. Execution-level idempotency check
            existing_event = await self._check_existing_submission(client_order_id)
            if existing_event:
                logger.warning(
                    f"[Worker {worker_id}] ⚠️ Idempotency: client_order_id already processed, "
                    f"existing_event={existing_event['event_type']}, treating as success"
                )
                await self.persistent_queue.mark_done(task.task_id)
                return
            
            # 3. Submit to exchange (P1.1C: rate limited)
            async with self._binance_semaphore:
                binance_response = await self._submit_to_exchange(task)
            
            # 4. Map response to ACK/REJECT event
            ack_or_reject_event = self.binance_mapper.map_order_response_to_event(
                binance_response=binance_response,
                client_order_id=client_order_id
            )
            ack_or_reject_event.trace_id = task.trace_id
            
            await self.event_store.append(ack_or_reject_event)
            await self.event_bus.publish(ack_or_reject_event)
            
            # 5. Mark done
            await self.persistent_queue.mark_done(task.task_id)
            
            processing_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.info(
                f"[Worker {worker_id}] ✅ Completed: task_id={task.task_id}, "
                f"event_type={ack_or_reject_event.event_type}, processing_ms={processing_ms:.1f}"
            )
        
        except Exception as e:
            # Handle error: classify → retry (with backoff) or DLQ
            await self._handle_error(task, e, worker_id)
    
    async def _submit_to_exchange(self, task: PersistentQueueTask) -> dict:
        """Submit order to exchange based on task type."""
        task_type = task.type
        payload = task.payload
        
        if task_type == "SUBMIT_ORDER":
            return await self.binance_adapter.submit_limit_order(
                symbol=payload["symbol"],
                side=payload["side"],
                qty=payload["qty"],
                price=payload["price"]
            )
        
        elif task_type == "CLOSE_POSITION":
            raise NotImplementedError("CLOSE_POSITION not yet implemented")
        
        elif task_type == "CANCEL_ORDER":
            raise NotImplementedError("CANCEL_ORDER not yet implemented")
        
        else:
            raise ValueError(f"Unsupported task_type: {task_type}")
    
    async def _handle_error(self, task: PersistentQueueTask, error: Exception, worker_id: int):
        """
        Handle processing error (P1.1C production-safe).
        
        Logic:
        1. Extract Binance error code (if available)
        2. Classify error (retryable / non-retryable / duplicate_success)
        3. Handle duplicate as success (idempotency)
        4. If retryable: schedule retry with exponential backoff
        5. Otherwise: move to DLQ
        """
        error_str = str(error)
        
        # Extract Binance error code (if present)
        error_code = self._extract_binance_error_code(error)
        
        # Classify error (P1.1C: Binance-aware)
        classification, dlq_classification = self.retry_classifier.classify(
            error=error,
            error_code=error_code
        )
        
        # Handle duplicate order as SUCCESS (idempotency)
        if classification == "duplicate_success":
            logger.info(
                f"[Worker {worker_id}] ✅ Duplicate order → treating as SUCCESS: "
                f"task_id={task.task_id}, error_code={error_code}"
            )
            await self.persistent_queue.mark_done(task.task_id)
            return
        
        # Non-retryable → DLQ immediately
        if classification == "non_retryable":
            await self._move_to_dlq(task, error_str, dlq_classification, worker_id)
            return
        
        # Retryable → check attempts
        if task.attempt + 1 >= task.max_attempts:
            # Max attempts exceeded → DLQ
            await self._move_to_dlq(task, error_str, "retry_exhausted", worker_id)
            return
        
        # Retry with exponential backoff (P1.1C)
        backoff_seconds = self.retry_classifier.get_backoff_seconds(task.attempt)
        
        await self.persistent_queue.mark_failed(
            task_id=task.task_id,
            error=error_str,
            retry=True,
            backoff_seconds=backoff_seconds
        )
        
        logger.warning(
            f"[Worker {worker_id}] 🔄 Retry scheduled: task_id={task.task_id}, "
            f"attempt={task.attempt + 1}/{task.max_attempts}, "
            f"backoff={backoff_seconds}s, error={error_str}"
        )
    
    def _extract_binance_error_code(self, error: Exception) -> Optional[int]:
        """
        Extract Binance error code from exception.
        
        Returns:
            Error code (e.g., -2010) or None
        """
        error_str = str(error)
        
        # Try to parse error code from error message
        # Typical format: "APIError(code=-2010): ..."
        try:
            if "code=" in error_str:
                code_str = error_str.split("code=")[1].split(")")[0].split(":")[0].strip()
                return int(code_str)
        except Exception:
            pass
        
        return None
    
    async def _move_to_dlq(
        self,
        task: PersistentQueueTask,
        error: str,
        classification: str,
        worker_id: int
    ):
        """Move task to Dead Letter Queue."""
        # Convert PersistentQueueTask to QueueItem for DLQ
        from .queue_models import QueueItem
        
        queue_item = QueueItem(
            queue_item_id=task.task_id,
            trace_id=task.trace_id,
            client_order_id=task.payload.get("client_order_id", "unknown"),
            priority=task.priority,
            action_type=task.type,  # Map task_type to action_type
            payload=task.payload,
            attempt=task.attempt,
            max_attempts=task.max_attempts,
            created_at=task.created_at
        )
        
        # Add to DLQ
        await self.dlq_repository.add(
            queue_item=queue_item,
            final_error=error,
            classification=classification
        )
        
        # Mark task as FAILED in queue
        await self.persistent_queue.mark_failed(
            task_id=task.task_id,
            error=error,
            retry=False
        )
        
        logger.error(
            f"[Worker {worker_id}] ❌ Moved to DLQ: task_id={task.task_id}, "
            f"classification={classification}, error={error}"
        )
    
    async def _check_existing_submission(self, client_order_id: str) -> Optional[dict]:
        """Execution-level idempotency check."""
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
