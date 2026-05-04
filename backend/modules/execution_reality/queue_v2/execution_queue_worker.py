"""
Execution Queue Worker (P1.3.2)
===============================

Основной worker loop: lease → process → ack cycle.
"""

import logging
import asyncio
import uuid
from typing import Optional
from datetime import datetime, timezone

from .execution_queue_repository import ExecutionQueueRepository
from .execution_worker_heartbeat import ExecutionWorkerHeartbeatWriter
from .execution_submit_simulator import ExecutionSubmitSimulator
from .execution_worker_config import ExecutionWorkerConfig
from .execution_handler import ExecutionHandler

logger = logging.getLogger(__name__)


class ExecutionQueueWorker:
    """
    Execution Queue Worker.
    
    P1.3.2: Single-worker, dry-run, deterministic.
    """
    
    def __init__(
        self,
        queue_repo: ExecutionQueueRepository,
        heartbeat_writer: ExecutionWorkerHeartbeatWriter,
        submit_simulator: ExecutionSubmitSimulator,
        config: ExecutionWorkerConfig,
        audit_logger=None,
        order_manager=None  # Sprint A2.3: для REAL execution mode
    ):
        """
        Args:
            queue_repo: ExecutionQueueRepository instance
            heartbeat_writer: ExecutionWorkerHeartbeatWriter instance
            submit_simulator: ExecutionSubmitSimulator instance
            config: ExecutionWorkerConfig instance
            audit_logger: ExecutionQueueAuditLogger (optional)
            order_manager: OrderManager instance (required for REAL mode)
        """
        self.queue_repo = queue_repo
        self.heartbeat = heartbeat_writer
        self.simulator = submit_simulator
        self.config = config
        self.audit_logger = audit_logger
        self.order_manager = order_manager
        
        # Worker ID
        self.worker_id = heartbeat_writer.worker_id
        
        # Sprint A2.3: ExecutionHandler для DRY_RUN/REAL switch
        self.execution_handler = ExecutionHandler(
            simulator=submit_simulator,
            order_manager=order_manager
        )
        
        # Control
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(
            f"✅ ExecutionQueueWorker initialized: worker_id={self.worker_id}, "
            f"mode={self.execution_handler.get_mode()}"
        )
    
    async def start(self):
        """Start worker loop."""
        if self._running:
            logger.warning(f"[Worker] Already running: {self.worker_id}")
            return
        
        self._running = True
        
        # Start heartbeat
        await self.heartbeat.start()
        await self.heartbeat.update_status("healthy")
        
        # Start worker loop
        self._worker_task = asyncio.create_task(self._worker_loop())
        
        logger.info(f"🔄 [Worker] Started: {self.worker_id}")
    
    async def stop(self):
        """Stop worker loop (drain and shutdown)."""
        if not self._running:
            return
        
        logger.info(f"⏹️ [Worker] Stopping: {self.worker_id}")
        
        # Enter draining state
        await self.heartbeat.update_status("draining")
        
        # Stop accepting new jobs
        self._running = False
        
        # Wait for current job to finish (graceful)
        if self._worker_task:
            try:
                await asyncio.wait_for(
                    self._worker_task,
                    timeout=self.config.graceful_shutdown_timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"[Worker] Graceful shutdown timeout, cancelling: {self.worker_id}"
                )
                self._worker_task.cancel()
                try:
                    await self._worker_task
                except asyncio.CancelledError:
                    pass
        
        # Stop heartbeat
        await self.heartbeat.stop()
        
        logger.info(f"✅ [Worker] Stopped: {self.worker_id}")
    
    async def _worker_loop(self):
        """Main worker loop."""
        logger.info(f"🔄 [Worker] Loop started: {self.worker_id}")
        
        try:
            while self._running:
                # Update status: healthy (waiting for jobs)
                await self.heartbeat.update_status("healthy")
                
                # Try to lease next job
                job = await self.queue_repo.lease_next()
                
                if job is None:
                    # No jobs available, sleep and retry
                    await asyncio.sleep(self.config.poll_interval_seconds)
                    continue
                
                # Process job
                await self._process_job(job)
        
        except asyncio.CancelledError:
            logger.debug(f"[Worker] Loop cancelled: {self.worker_id}")
        except Exception as e:
            logger.error(f"[Worker] Loop error: {e}", exc_info=True)
    
    async def _process_job(self, job):
        """Process single job."""
        try:
            # Update status: busy
            await self.heartbeat.update_status("busy")
            self.heartbeat.set_current_job(job.jobId)
            
            logger.info(
                f"🔄 [Worker] Processing job: job_id={job.jobId}, "
                f"symbol={job.symbol}, priority={job.priority}, "
                f"trace_id={job.traceId}"
            )
            
            # Mark job as in_flight
            success = await self.queue_repo.mark_in_flight(
                job_id=job.jobId,
                lease_token=job.leaseToken
            )
            
            if not success:
                logger.error(
                    f"❌ [Worker] Failed to mark in_flight: job_id={job.jobId}"
                )
                return
            
            # Submit order (DRY-RUN or REAL based on EXECUTION_MODE)
            # P1.3.4 CRITICAL: Use idempotencyKey as clientOrderId (exchange-level dedup)
            client_order_id = job.idempotencyKey or f"job-{job.jobId}"
            
            # Sprint A2.3: ExecutionHandler handles DRY_RUN vs REAL
            result = await self.execution_handler.execute_order(
                job_id=job.jobId,
                trace_id=job.traceId,
                payload={
                    **job.payload,
                    "clientOrderId": client_order_id  # CRITICAL: Exchange idempotency
                }
            )
            
            if result.get("success"):
                # Paper Trading Integration: Create Position after FILLED
                await self._handle_fill(job, result)
                
                # Success: mark acked
                ack_success = await self.queue_repo.mark_acked(
                    job_id=job.jobId,
                    lease_token=job.leaseToken
                )
                
                if ack_success:
                    logger.info(
                        f"✅ [Worker] Job acked: job_id={job.jobId}, "
                        f"order_id={result.get('order_id')}"
                    )
                    
                    # Increment counter
                    self.heartbeat.increment_jobs_processed()
                else:
                    logger.error(
                        f"❌ [Worker] Failed to mark acked: job_id={job.jobId}"
                    )
            else:
                # Failure: schedule retry (P1.3.2B)
                error = result.get("error", "Unknown error")
                logger.warning(
                    f"⚠️ [Worker] Submit failed: job_id={job.jobId}, error={error}, "
                    f"attemptCount={job.attemptCount}"
                )
                
                # Check if retry allowed (maxAttempts)
                max_attempts = 3  # P1.3.2B: hardcoded для testing
                
                if job.attemptCount < max_attempts:
                    # Schedule retry
                    backoff_seconds = 30.0  # 30s backoff
                    
                    retry_success = await self.queue_repo.mark_retry_wait(
                        job_id=job.jobId,
                        lease_token=job.leaseToken,
                        error=error,
                        backoff_seconds=backoff_seconds
                    )
                    
                    if retry_success:
                        logger.info(
                            f"🔄 [Worker] Job scheduled for retry: job_id={job.jobId}, "
                            f"next_retry_in={backoff_seconds}s"
                        )
                    else:
                        logger.error(
                            f"❌ [Worker] Failed to schedule retry: job_id={job.jobId}"
                        )
                else:
                    # Max attempts reached: mark as failed_terminal
                    logger.error(
                        f"❌ [Worker] Max attempts reached: job_id={job.jobId}, "
                        f"attemptCount={job.attemptCount}"
                    )
                    
                    await self.queue_repo.mark_failed_terminal(
                        job_id=job.jobId,
                        lease_token=job.leaseToken,
                        error=f"Max attempts ({max_attempts}) reached: {error}"
                    )
        
        except Exception as e:
            logger.error(
                f"❌ [Worker] Job processing error: job_id={job.jobId}, error={e}",
                exc_info=True
            )
        
        finally:
            # Clear current job
            self.heartbeat.set_current_job(None)
    
    async def _handle_fill(self, job, execution_result):
        """
        Handle filled order: create Position and write execution events.
        
        Paper Trading Integration Point.
        """
        try:
            # Get TradingCaseService
            from modules.trading_cases.service import get_trading_case_service
            from modules.trading_cases.models import CaseCreateRequest
            from modules.execution_logger import get_execution_logger
            
            trading_case_service = get_trading_case_service()
            execution_logger = get_execution_logger()
            
            # Extract decision_id from payload
            decision_id = job.payload.get("decision_id")
            strategy = job.payload.get("strategy", "QUEUE_EXECUTION")
            timeframe = job.payload.get("timeframe", "1h")
            
            # STEP 1.5.3: Extract experiment_id from payload (safe fallback)
            experiment_id = job.payload.get("experiment_id", "baseline_btc")
            
            # Parse execution result
            filled_qty = execution_result.get("filled_qty", job.payload.get("quantity", 0.001))
            fill_price = execution_result.get("avg_price", job.payload.get("price", 0.0))
            order_id = execution_result.get("order_id")
            
            # Calculate size_usd
            size_usd = filled_qty * fill_price
            
            # Create Trading Case (Position)
            case_request = CaseCreateRequest(
                symbol=job.symbol,
                side="LONG" if job.payload.get("side") == "BUY" else "SHORT",
                entry_price=fill_price,
                qty=filled_qty,
                size_usd=size_usd,
                strategy=strategy,
                trading_tf=timeframe,
                thesis=f"Execution via job {job.jobId}",
                decision_id=decision_id,
                experiment_id=experiment_id  # STEP 1.5.4: Pass experiment_id to case
            )
            
            try:
                case = await trading_case_service.create_case(case_request)
            except Exception as create_error:
                raise
            
            logger.info(
                f"✅ [Worker] Position created: case_id={case.case_id}, "
                f"symbol={job.symbol}, qty={filled_qty}, price=${fill_price:.2f}"
            )
            
            # Write execution events
            await execution_logger.log_event({
                "type": "ORDER_SUBMITTED",
                "symbol": job.symbol,
                "side": job.payload.get("side"),
                "job_id": job.jobId,
                "order_id": order_id,
                "decision_id": decision_id
            })
            
            await execution_logger.log_event({
                "type": "ORDER_FILLED",
                "symbol": job.symbol,
                "order_id": order_id,
                "filled_qty": filled_qty,
                "avg_price": fill_price,
                "size_usd": size_usd,
                "case_id": case.case_id,
                "decision_id": decision_id
            })
            
            logger.info(
                f"✅ [Worker] Execution events logged for job_id={job.jobId}"
            )
            
        except Exception as e:
            logger.error(
                f"⚠️ [Worker] Failed to create position for job {job.jobId}: {e}",
                exc_info=True
            )
            # Don't fail the job if position creation fails (execution succeeded)
