"""Execution Reality Controller

Главный контроллер для event-driven execution.
Оркестрирует: event bus + event store + adapters + projections.

P1.1: Async order queue integration.
P1.5: STOP_LOSS safety mechanisms.
"""

import uuid
import logging
import asyncio
from typing import Dict, Any, Optional
from collections import deque
from .events.execution_event_types import create_event, EXECUTION_EVENT_TYPES, ExecutionEvent
from .events.execution_event_store import ExecutionEventStore
from .events.execution_event_bus import ExecutionEventBus
from .adapters.binance_rest_adapter import BinanceRestAdapter
from .adapters.binance_mapper import BinanceMapper
from .state.order_projection import OrderProjection
from .state.position_projection import PositionProjection

logger = logging.getLogger(__name__)


class ExecutionRealityController:
    """Контроллер execution reality (Milestone A + P1.1 Queue)"""

    def __init__(self, audit_repo=None, persistent_queue=None, dlq_repository=None):
        # Core components
        self.event_store = ExecutionEventStore()
        self.event_bus = ExecutionEventBus(audit_repo=audit_repo)  # P0.7 Audit hook

        # Adapters
        self.binance_adapter = BinanceRestAdapter(use_real=False)  # mock для Milestone A
        self.binance_mapper = BinanceMapper()

        # Projections
        self.order_projection = OrderProjection()
        self.position_projection = PositionProjection()
        
        # PnL Projection (P0.5)
        from .pnl.pnl_projection import PnLProjection
        self.pnl_projection = PnLProjection()

        # Risk Guard (P0.6)
        from .risk.health_model import SystemHealth
        from .risk.risk_guard_engine import RiskGuardEngine
        self.health_model = SystemHealth()
        self.risk_guard = RiskGuardEngine()

        # P1.1B: Persistent Queue (Mongo-backed) + DLQ
        self.persistent_queue = persistent_queue
        self.dlq_repository = dlq_repository
        
        # P1-A: Latency tracking + Execution metrics
        from .latency.latency_tracker import LatencyTracker
        from .latency.execution_metrics_store import ExecutionMetricsStore
        self.latency_tracker = LatencyTracker(window_size=100)
        self.metrics_store = ExecutionMetricsStore(window_size=100)
        
        # P1-B: Rate Limiting + Circuit Breakers
        from .rate_limit.token_bucket import BinanceRateLimiter
        from .rate_limit.circuit_breaker import CircuitBreaker
        from .guards.queue_pressure_guard import QueuePressureGuard
        
        self.rate_limiter = BinanceRateLimiter(market_type="spot")  # 1200 weight/min
        self.circuit_breaker = CircuitBreaker(
            name="execution",
            latency_threshold_ms=2000.0,
            reject_rate_threshold=0.15,
            timeout_rate_threshold=0.1
        )
        self.queue_pressure_guard = QueuePressureGuard(
            max_inflight=20,
            max_queue_depth=50,
            max_latency_ms=2000.0
        )

        # Подписываем projections на события
        self.event_bus.subscribe(self._apply_to_order_projection)
        self.event_bus.subscribe(self._apply_to_position_projection)
        self.event_bus.subscribe(self._apply_to_pnl_projection)
        self.event_bus.subscribe(self._track_latency)  # P1-A: Latency tracking
        
        # P1.5.3: Execution locks (prevent simultaneous STOP_LOSS per symbol)
        self._execution_locks: Dict[str, asyncio.Lock] = {}

        logger.info(
            "✅ ExecutionRealityController initialized "
            "(P1-A: latency | P1-B: rate limit + circuit breaker + queue pressure guard | "
            "P1.5: STOP_LOSS safety + execution locks)"
        )

    async def initialize(self):
        """
        Инициализация контроллера (КРИТИЧНО):
        1. Создать индексы (idempotency)
        2. Boot restore (восстановить projections из events)
        3. P1.1: Ensure DLQ indexes
        """
        # 1. Ensure indexes (unique event_id для idempotency)
        await self.event_store.ensure_indexes()

        # 2. Boot restore: восстанавливаем projections из всех событий
        await self.rebuild_from_events()

        # 3. P1.1: DLQ indexes
        if self.dlq_repository:
            await self.dlq_repository.ensure_indexes()

        logger.info("✅ ExecutionRealityController fully initialized (boot restore complete)")

    async def rebuild_from_events(self):
        """
        Boot restore: восстановить projections строго из persisted events.
        Вызывается при старте приложения.
        """
        logger.info("🔄 Rebuilding projections from event store...")

        # Получаем ВСЕ события в хронологическом порядке
        events = await self.event_store.list_all_for_rebuild(limit=100000)

        if not events:
            logger.info("No events found, projections are empty (fresh start)")
            return

        # Replay events через projections
        for event in events:
            self.order_projection.apply(event)
            self.position_projection.apply(event)
            self.pnl_projection.apply(event)  # P0.5

        logger.info(f"✅ Rebuilt projections from {len(events)} events")
        logger.info(f"   Orders: {len(self.order_projection.list_orders())}")
        logger.info(f"   Positions: {len(self.position_projection.list_positions())}")
        logger.info(f"   Trades (PnL ledger): {len(self.pnl_projection.ledger.get_all_trades())}")

    def _apply_to_order_projection(self, event: ExecutionEvent) -> None:
        """Применить событие к order projection"""
        self.order_projection.apply(event)

    def _apply_to_position_projection(self, event: ExecutionEvent) -> None:
        """Применить событие к position projection"""
        self.position_projection.apply(event)

    def _apply_to_pnl_projection(self, event: ExecutionEvent) -> None:
        """Применить событие к PnL projection (P0.5)"""
        self.pnl_projection.apply(event)
    
    def _track_latency(self, event: ExecutionEvent) -> None:
        """
        P1-A: Track execution latencies (submit → ACK → fill).
        
        Tracks two critical latency metrics:
        - submit_to_ack_ms: Time from ORDER_SUBMIT_REQUESTED to ORDER_ACKNOWLEDGED
        - submit_to_fill_ms: Time from ORDER_SUBMIT_REQUESTED to ORDER_FILL_RECORDED
        
        Also updates ExecutionMetricsStore counters for health monitoring.
        """
        coid = event.client_order_id
        
        # Track submit
        if event.event_type == "ORDER_SUBMIT_REQUESTED":
            self.latency_tracker.mark_submit_requested(coid, event.timestamp)
            self.metrics_store.record_submit()
        
        # Track ACK
        elif event.event_type == "ORDER_ACKNOWLEDGED":
            self.latency_tracker.mark_ack_received(coid, event.timestamp)
            self.metrics_store.record_ack()
        
        # Track reject
        elif event.event_type == "ORDER_REJECTED":
            self.metrics_store.record_reject()
            # Clean up inflight tracking
            if coid in self.latency_tracker._inflight:
                del self.latency_tracker._inflight[coid]
        
        # Track first fill
        elif event.event_type == "ORDER_FILL_RECORDED":
            self.latency_tracker.mark_first_fill(coid, event.timestamp)
            self.metrics_store.record_fill()
        
        # Track full fill (order completely filled)
        elif event.event_type == "ORDER_FULLY_FILLED":
            self.latency_tracker.mark_full_fill(coid, event.timestamp)
        
        # Periodic snapshots for queue depth and inflight count
        # (снимаем snapshot каждые N событий для оценки avg queue depth)
        if hasattr(self, 'persistent_queue') and self.persistent_queue:
            # Snapshot queue depth periodically (every 10th event for efficiency)
            import random
            if random.random() < 0.1:  # 10% sampling rate
                # Async call is not allowed in sync subscriber, so we skip for now
                # Will be tracked via separate periodic task in production
                pass
        
        # Snapshot inflight count
        inflight_count = self.latency_tracker.get_inflight_count()
        self.metrics_store.snapshot_inflight_count(inflight_count)

    async def test_submit_limit(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        trace_id: str = None  # P0.7.1: Audit trace ID
    ) -> Dict[str, Any]:
        """
        Test submit LIMIT order (Milestone A use-case).
        
        Flow:
        1. Создаём client_order_id
        2. Пишем ORDER_SUBMIT_REQUESTED
        3. Вызываем adapter (mock Binance)
        4. Пишем ORDER_ACKNOWLEDGED или ORDER_REJECTED
        5. Возвращаем результат
        """
        # 1. Генерируем client_order_id
        client_order_id = str(uuid.uuid4())

        logger.info(f"=== EXECUTION REALITY FLOW START | {client_order_id} | trace={trace_id} ===")

        # 2. ORDER_SUBMIT_REQUESTED event
        submit_event = create_event(
            event_type=EXECUTION_EVENT_TYPES["ORDER_SUBMIT_REQUESTED"],
            exchange="binance",
            symbol=symbol,
            client_order_id=client_order_id,
            trace_id=trace_id,  # P0.7.1: Propagate trace_id
            payload={
                "side": side,
                "qty": qty,
                "price": price,
                "order_type": "LIMIT"
            }
        )

        # Записываем в event store
        await self.event_store.append(submit_event)
        # Публикуем в event bus
        await self.event_bus.publish(submit_event)

        logger.info(f"✅ ORDER_SUBMIT_REQUESTED | {client_order_id}")

        # 3. Вызываем adapter
        try:
            binance_response = await self.binance_adapter.submit_limit_order(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price
            )

            # 4. Маппим ответ в событие
            ack_or_reject_event = self.binance_mapper.map_order_response_to_event(
                binance_response=binance_response,
                client_order_id=client_order_id
            )
            
            # P0.7.1: Propagate trace_id to ACK/REJECT event
            ack_or_reject_event.trace_id = trace_id

            # Записываем в event store
            await self.event_store.append(ack_or_reject_event)
            # Публикуем в event bus
            await self.event_bus.publish(ack_or_reject_event)

            logger.info(f"✅ {ack_or_reject_event.event_type} | {client_order_id}")

            # 5. Возвращаем результат
            order = self.order_projection.get_order(client_order_id)

            logger.info(f"=== EXECUTION REALITY FLOW END | status={order.status if order else 'NOT_FOUND'} ===")

            return {
                "success": True,
                "client_order_id": client_order_id,
                "status": order.status if order else "UNKNOWN",
                "exchange_order_id": order.exchange_order_id if order else None,
                "order": order.dict() if order else None
            }

        except Exception as e:
            logger.error(f"❌ Error in test_submit_limit: {e}")
            # Пишем ORDER_REJECTED
            reject_event = create_event(
                event_type=EXECUTION_EVENT_TYPES["ORDER_REJECTED"],
                exchange="binance",
                symbol=symbol,
                client_order_id=client_order_id,
                payload={"reason": str(e)}
            )
            await self.event_store.append(reject_event)
            await self.event_bus.publish(reject_event)

            return {
                "success": False,
                "client_order_id": client_order_id,
                "status": "REJECTED",
                "error": str(e)
            }

    async def _execute_immediately(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        client_order_id: str,
        trace_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        intent_type: str = "STOP_LOSS"
    ) -> Dict[str, Any]:
        """
        P1.5: Immediate execution for CRITICAL intents (STOP_LOSS, CLOSE).
        
        BYPASSES:
        - Queue
        - Circuit breaker (partial - logs warning but proceeds)
        - Rate limiter (partial - logs warning but proceeds)
        - Queue pressure guard
        
        PRESERVES:
        - Event sourcing (all events still published)
        - Audit trail
        - PnL tracking
        
        P1.5.3: EXECUTION LOCK per symbol (prevents simultaneous STOP_LOSS)
        
        Critical Rule: STOP_LOSS НИКОГДА НЕ ЖДЁТ
        
        Returns:
            {
                "accepted": bool,
                "client_order_id": str,
                "exchange_order_id": str (if success),
                "status": "executed_immediately" | "failed",
                "latency_ms": float
            }
        """
        import time
        start_time = time.time()
        
        # P1.5.3: Acquire execution lock for symbol (prevents parallel STOP_LOSS)
        if symbol not in self._execution_locks:
            self._execution_locks[symbol] = asyncio.Lock()
        
        lock = self._execution_locks[symbol]
        
        # Try to acquire lock with timeout (prevent deadlock)
        try:
            acquired = await asyncio.wait_for(lock.acquire(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.critical(
                f"🔥 Execution lock timeout | "
                f"symbol={symbol} | intent={intent_type} | "
                f"Another STOP_LOSS already executing, BLOCKING to prevent position flip"
            )
            return {
                "accepted": False,
                "client_order_id": client_order_id,
                "trace_id": trace_id,
                "status": "rejected_lock_timeout",
                "reason": "Execution lock held by another STOP_LOSS",
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
        
        try:
            logger.info(
                f"🔒 Execution lock ACQUIRED | "
                f"symbol={symbol} | intent={intent_type} | "
                f"client_order_id={client_order_id}"
            )
            
            # Emit ORDER_SUBMIT_REQUESTED event (event sourcing preserved!)
            submit_event = create_event(
                "ORDER_SUBMIT_REQUESTED",
                client_order_id=client_order_id,
                exchange_order_id=None,
                symbol=symbol,
                exchange="binance",
                trace_id=trace_id,
                payload={
                    "side": side,
                    "qty": qty,
                    "price": price,
                    "order_type": "LIMIT",
                    "strategy_id": strategy_id,
                    "intent_type": intent_type,
                    "immediate_execution": True  # Flag for monitoring
                }
            )
            
            self.event_bus.publish(submit_event)
            await self.event_store.append(submit_event)
            
            # CRITICAL RULE: STOP_LOSS = MARKET order (не LIMIT!)
            # MARKET гарантирует execution, LIMIT может не исполниться
            use_market = intent_type in ["STOP_LOSS", "CLOSE", "CLOSE_POSITION"]
            
            # Retry logic ONLY for STOP_LOSS (max 2 attempts)
            max_attempts = 2 if intent_type == "STOP_LOSS" else 1
            order_result = None
            
            for attempt in range(max_attempts):
                try:
                    # P1.5: Idempotency check before retry
                    if attempt > 0:
                        existing = self.order_projection.get_order(client_order_id)
                        if existing and existing.status in ["ACKNOWLEDGED", "FILLED", "PARTIALLY_FILLED", "PARTIAL"]:
                            logger.warning(
                                f"⚠️ Retry SKIPPED - order already exists | "
                                f"client_order_id={client_order_id} | "
                                f"status={existing.status}"
                            )
                            # Return existing order as success (idempotent)
                            elapsed_ms = (time.time() - start_time) * 1000
                            return {
                                "accepted": True,
                                "client_order_id": client_order_id,
                                "exchange_order_id": existing.exchange_order_id,
                                "trace_id": trace_id,
                                "status": "executed_immediately",
                                "order_type": "MARKET" if use_market else "LIMIT",
                                "fill_status": existing.status,
                                "latency_ms": round(elapsed_ms, 2),
                                "idempotent": True
                            }
                    
                    # Direct execution via adapter (bypass queue)
                    if use_market:
                        logger.info(
                            f"🔴 MARKET order execution (attempt {attempt + 1}/{max_attempts}) | "
                            f"intent={intent_type} | client_order_id={client_order_id}"
                        )
                        order_result = await self.binance_adapter.submit_market_order(
                            symbol=symbol,
                            side=side,
                            qty=qty,
                            client_order_id=client_order_id
                        )
                    else:
                        order_result = await self.binance_adapter.submit_limit_order(
                            symbol=symbol,
                            side=side,
                            qty=qty,
                            price=price,
                            client_order_id=client_order_id
                        )
                    
                    # Success - break retry loop
                    break
                    
                except Exception as e:
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"⚠️ Immediate execution attempt {attempt + 1} FAILED, retrying | "
                            f"error={e}"
                        )
                        await asyncio.sleep(0.05)  # 50ms delay before retry
                    else:
                        # Final attempt failed
                        raise e
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Emit ACK or FILLED event
            if order_result["status"] in ["ACK", "FILLED"]:
                ack_event = create_event(
                    "ORDER_ACKNOWLEDGED",
                    client_order_id=client_order_id,
                    exchange_order_id=order_result.get("exchange_order_id"),
                    symbol=symbol,
                    exchange="binance",
                    trace_id=trace_id,
                    payload={
                        "exchange_order_id": order_result.get("exchange_order_id"),
                        "latency_ms": latency_ms
                    }
                )
                
                self.event_bus.publish(ack_event)
                await self.event_store.append(ack_event)
                
                logger.info(
                    f"✅ Immediate execution SUCCESS | "
                    f"intent={intent_type} | latency={latency_ms:.1f}ms | "
                    f"client_order_id={client_order_id}"
                )
                
                return {
                    "accepted": True,
                    "client_order_id": client_order_id,
                    "exchange_order_id": order_result.get("exchange_order_id"),
                    "trace_id": trace_id,
                    "status": "executed_immediately",
                    "latency_ms": round(latency_ms, 2)
                }
            
            # Emit REJECTED event
            else:
                reject_event = create_event(
                    "ORDER_REJECTED",
                    client_order_id=client_order_id,
                    exchange_order_id=None,
                    symbol=symbol,
                    exchange="binance",
                    trace_id=trace_id,
                    payload={
                        "reason": order_result.get("error", "Unknown rejection"),
                        "latency_ms": latency_ms
                    }
                )
                
                self.event_bus.publish(reject_event)
                await self.event_store.append(reject_event)
                
                logger.error(
                    f"❌ Immediate execution REJECTED | "
                    f"intent={intent_type} | reason={order_result.get('error')} | "
                    f"client_order_id={client_order_id}"
                )
                
                return {
                    "accepted": False,
                    "client_order_id": client_order_id,
                    "trace_id": trace_id,
                    "status": "rejected",
                    "reason": order_result.get("error", "Exchange rejected"),
                    "latency_ms": round(latency_ms, 2)
                }
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.exception(
                f"🔥 Immediate execution FAILED | "
                f"intent={intent_type} | error={e} | "
                f"client_order_id={client_order_id}"
            )
            
            # P1.5: LAST RESORT - Forced close for STOP_LOSS
            if intent_type == "STOP_LOSS":
                logger.critical(
                    f"🔥 Triggering FORCED CLOSE (last resort) | "
                    f"symbol={symbol} | qty={qty}"
                )
                
                forced_success = await self._forced_close_position(
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    trace_id=trace_id
                )
                
                if forced_success:
                    return {
                        "accepted": True,
                        "client_order_id": client_order_id,
                        "trace_id": trace_id,
                        "status": "forced_close_success",
                        "latency_ms": round(latency_ms, 2)
                    }
            
            # Emit FAILED event
            failed_event = create_event(
                "ORDER_FAILED",
                client_order_id=client_order_id,
                exchange_order_id=None,
                symbol=symbol,
                exchange="binance",
                trace_id=trace_id,
                payload={
                    "error": str(e),
                    "latency_ms": latency_ms
                }
            )
            
            self.event_bus.publish(failed_event)
            await self.event_store.append(failed_event)
            
            return {
                "accepted": False,
                "client_order_id": client_order_id,
                "trace_id": trace_id,
                "status": "failed",
                "error": str(e),
                "latency_ms": round(latency_ms, 2)
            }
        
        finally:
            # P1.5.3: Always release lock
            lock.release()
            logger.info(
                f"🔓 Execution lock RELEASED | "
                f"symbol={symbol} | client_order_id={client_order_id}"
            )
    
    async def _forced_close_position(
        self,
        symbol: str,
        side: str,
        qty: float,
        trace_id: Optional[str] = None
    ) -> bool:
        """
        P1.5.2: Adaptive forced close with size reduction + spread protection.
        
        Last resort when normal STOP_LOSS fails.
        
        CRITICAL UPGRADES:
        - Iterative size reduction (size *= 0.7) to avoid dumping full qty into thin book
        - Spread threshold check (pause if bid/ask too wide to prevent catastrophic slippage)
        - Exponential backoff between attempts
        
        Args:
            symbol: Symbol to close
            side: SELL (close LONG) or BUY (close SHORT)
            qty: Initial quantity to close
            trace_id: Audit trace ID
        
        Returns:
            True if successfully closed, False if all attempts failed
        """
        logger.critical(
            f"🔥 FORCED CLOSE INITIATED (LAST RESORT) | "
            f"symbol={symbol} | side={side} | initial_qty={qty}"
        )
        
        # P1.5.2: Adaptive parameters
        MAX_ATTEMPTS = 10
        SPREAD_THRESHOLD_BPS = 100  # 1% spread = too wide, pause
        SIZE_REDUCTION_FACTOR = 0.7
        
        current_qty = qty
        
        for attempt in range(MAX_ATTEMPTS):
            try:
                # P1.5.2: Spread check (prevent dumping into empty book)
                try:
                    ticker = await self.binance_adapter.get_ticker(symbol)
                    bid = float(ticker.get("bidPrice", 0))
                    ask = float(ticker.get("askPrice", 0))
                    mid = (bid + ask) / 2
                    spread_bps = ((ask - bid) / mid) * 10000 if mid > 0 else 9999
                    
                    if spread_bps > SPREAD_THRESHOLD_BPS:
                        logger.warning(
                            f"⚠️ Forced close attempt {attempt + 1}: spread too wide, pausing | "
                            f"spread={spread_bps:.1f}bps | threshold={SPREAD_THRESHOLD_BPS}bps"
                        )
                        await asyncio.sleep(0.5 * (attempt + 1))  # Longer pause for wide spread
                        continue  # Skip this attempt, wait for spread to tighten
                except Exception as e:
                    logger.warning(f"Spread check failed: {e}, proceeding anyway")
                
                # Generate new client_order_id for each attempt
                client_order_id = f"forced-close-{attempt}-{str(uuid.uuid4())[:8]}"
                
                logger.critical(
                    f"🔥 Forced close attempt {attempt + 1}/{MAX_ATTEMPTS} | "
                    f"qty={current_qty:.4f} | client_order_id={client_order_id}"
                )
                
                result = await self.binance_adapter.submit_market_order(
                    symbol=symbol,
                    side=side,
                    qty=current_qty,
                    client_order_id=client_order_id
                )
                
                if result.get("status") in ["FILLED", "ACK"]:
                    logger.critical(
                        f"✅ FORCED CLOSE SUCCESS (attempt {attempt + 1}) | "
                        f"client_order_id={client_order_id} | "
                        f"qty={current_qty:.4f}"
                    )
                    
                    # Emit event for audit
                    event = create_event(
                        "ORDER_FULLY_FILLED" if result["status"] == "FILLED" else "ORDER_ACKNOWLEDGED",
                        client_order_id=client_order_id,
                        exchange_order_id=result.get("exchange_order_id"),
                        symbol=symbol,
                        exchange="binance",
                        trace_id=trace_id,
                        payload={
                            "forced_close": True,
                            "attempt": attempt + 1,
                            "adaptive_qty": current_qty
                        }
                    )
                    self.event_bus.publish(event)
                    await self.event_store.append(event)
                    
                    return True
                
            except Exception as e:
                logger.error(
                    f"⚠️ Forced close attempt {attempt + 1}/{MAX_ATTEMPTS} FAILED | "
                    f"qty={current_qty:.4f} | error={e}"
                )
                
                # P1.5.2: Reduce size for next attempt (avoid repeatedly dumping full qty)
                if attempt < MAX_ATTEMPTS - 1:
                    current_qty = current_qty * SIZE_REDUCTION_FACTOR
                    logger.warning(
                        f"📉 Reducing order size for next attempt | "
                        f"new_qty={current_qty:.4f} (factor={SIZE_REDUCTION_FACTOR})"
                    )
                
                await asyncio.sleep(0.2 * (attempt + 1))  # Exponential backoff
        
        # All attempts failed - CRITICAL SYSTEM RISK
        logger.critical(
            f"🔥🔥🔥 FORCED CLOSE FAILED AFTER {MAX_ATTEMPTS} ATTEMPTS | "
            f"symbol={symbol} | final_qty={current_qty:.4f} | "
            f"CRITICAL SYSTEM RISK | MANUAL INTERVENTION REQUIRED"
        )
        
        # Emit CRITICAL event
        critical_event = create_event(
            "SYSTEM_CRITICAL_RISK",
            client_order_id=None,
            exchange_order_id=None,
            symbol=symbol,
            exchange="binance",
            trace_id=trace_id,
            payload={
                "risk_type": "FAILED_FORCED_CLOSE",
                "symbol": symbol,
                "qty": qty,
                "final_qty": current_qty,
                "message": f"Unable to close position after {MAX_ATTEMPTS} attempts (adaptive sizing + spread protection)"
            }
        )
        self.event_bus.publish(critical_event)
        await self.event_store.append(critical_event)
        
        return False
    
    async def _wait_for_fill_confirmation(
        self,
        client_order_id: str,
        symbol: str,
        base_timeout_ms: float = 300.0,
        spike_timeout_ms: float = 1000.0
    ) -> bool:
        """
        P1.5.1: Dynamic fill confirmation with adaptive timeout + REST fallback.
        
        CRITICAL for STOP_LOSS to prevent "ghost fills" AND duplicate CLOSES:
        - Order submitted
        - ACK received  
        - But fill delayed due to Binance stream lag
        
        Dynamic Timeout Strategy:
        1. Base: 300ms (normal conditions)
        2. Spike: 800-1200ms (if circuit breaker recently opened or latency high)
        3. REST Fallback: Check order/position status via REST if no stream confirm
        
        Args:
            client_order_id: Order to wait for
            symbol: Trading symbol (for REST fallback)
            base_timeout_ms: Normal timeout (default 300ms)
            spike_timeout_ms: Extended timeout during degradation (default 1000ms)
        
        Returns:
            True if FILLED or PARTIAL confirmed (stream OR REST), False otherwise
        """
        import time
        start = time.time()
        
        # P1.5.1: Adaptive timeout selection
        # Use spike timeout if circuit breaker recently opened or p95 latency high
        latency_stats = self.latency_tracker.get_stats()
        p95_latency = latency_stats.get("p95_network_ms") or 0.0
        cb_state = self.circuit_breaker.get_state()
        
        use_spike_mode = (
            cb_state["state"] in ["OPEN", "HALF_OPEN"] or
            p95_latency > 800.0  # High latency indicator
        )
        
        timeout_ms = spike_timeout_ms if use_spike_mode else base_timeout_ms
        
        logger.info(
            f"⏱️ Fill confirmation wait starting | "
            f"client_order_id={client_order_id} | "
            f"timeout={timeout_ms:.0f}ms | "
            f"mode={'SPIKE' if use_spike_mode else 'NORMAL'} | "
            f"p95_latency={p95_latency:.1f}ms | "
            f"cb_state={cb_state['state']}"
        )
        
        # Poll projection (stream-based fills)
        while (time.time() - start) * 1000 < timeout_ms:
            order = self.order_projection.get_order(client_order_id)
            
            if order and order.status in ["FILLED", "PARTIAL", "PARTIALLY_FILLED"]:
                logger.info(
                    f"✅ Fill confirmed (stream) | "
                    f"client_order_id={client_order_id} | "
                    f"status={order.status} | "
                    f"wait_time={(time.time() - start) * 1000:.1f}ms"
                )
                return True
            
            await asyncio.sleep(0.02)  # 20ms poll interval
        
        # P1.5.1: REST Fallback
        # Stream didn't confirm in time → check REST to prevent duplicate execution
        logger.warning(
            f"⚠️ Stream confirmation timeout, attempting REST fallback | "
            f"client_order_id={client_order_id}"
        )
        
        try:
            # Check order status via REST
            rest_status = await self.binance_adapter.get_order_status(
                symbol=symbol,
                client_order_id=client_order_id
            )
            
            if rest_status and rest_status.get("status") in ["FILLED", "PARTIALLY_FILLED"]:
                logger.info(
                    f"✅ Fill confirmed (REST fallback) | "
                    f"client_order_id={client_order_id} | "
                    f"rest_status={rest_status.get('status')} | "
                    f"total_wait={(time.time() - start) * 1000:.1f}ms"
                )
                return True
            
            # Check position to see if it changed (indirect confirmation)
            position = self.position_projection.get_position(symbol)
            if position and position.size == 0.0:
                logger.info(
                    f"✅ Position closed (REST fallback position check) | "
                    f"client_order_id={client_order_id} | "
                    f"symbol={symbol}"
                )
                return True
                
        except Exception as e:
            logger.error(
                f"❌ REST fallback failed | "
                f"client_order_id={client_order_id} | "
                f"error={e}"
            )
        
        logger.error(
            f"❌ Fill confirmation FAILED (stream + REST) | "
            f"client_order_id={client_order_id} | "
            f"timeout={timeout_ms}ms | "
            f"total_wait={(time.time() - start) * 1000:.1f}ms"
        )
        return False

    async def submit_limit_async(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        trace_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        intent_type: str = "ENTRY"  # P1.5: Intent type for priority
    ) -> Dict[str, Any]:
        """
        P1.1B: Async submit LIMIT order via persistent queue.
        P1-B: With rate limiting + circuit breaker protection.
        
        NEW SEMANTICS:
        - Returns "accepted_for_processing" (NOT exchange-accepted)
        - Order is enqueued in Mongo and will be processed by worker pool
        - Workers emit execution events asynchronously
        - Queue survives restart
        
        Flow:
        1. P1-B: Check circuit breaker
        2. P1-B: Check rate limiter
        3. Generate client_order_id
        4. Enqueue task to Mongo persistent queue
        5. Return accepted_for_processing response
        
        Args:
            symbol: Trading symbol
            side: BUY or SELL
            qty: Quantity
            price: Limit price
            trace_id: P0.7.1 trace ID
            strategy_id: Strategy identifier
        
        Returns:
            {
                "accepted": bool,
                "task_id": str,
                "client_order_id": str,
                "trace_id": str,
                "status": "accepted_for_processing" | "rejected",
                "reason": str (if rejected)
            }
        """
        if not self.persistent_queue:
            raise RuntimeError("Persistent queue not initialized (P1.1B not enabled)")
        
        # === P1.5: CRITICAL BYPASS FOR STOP_LOSS ===
        # STOP_LOSS НИКОГДА НЕ ЖДЁТ В ОЧЕРЕДИ
        from .queue.intent_priority import is_critical_intent, get_intent_priority
        import time
        
        if is_critical_intent(intent_type):
            logger.critical(
                f"🔴 CRITICAL INTENT BYPASS: {intent_type} | "
                f"IMMEDIATE EXECUTION (bypassing queue) | "
                f"symbol={symbol} | trace_id={trace_id}"
            )
            
            # Generate client_order_id
            client_order_id = str(uuid.uuid4())
            
            # Execute immediately (bypass queue, guards, everything)
            start_time = time.time()
            result = await self._execute_immediately(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                client_order_id=client_order_id,
                trace_id=trace_id,
                strategy_id=strategy_id,
                intent_type=intent_type
            )
            
            latency_ms = (time.time() - start_time) * 1000
            logger.critical(
                f"🔴 CRITICAL INTENT COMPLETED: {intent_type} | "
                f"latency={latency_ms:.1f}ms | "
                f"client_order_id={client_order_id}"
            )
            
            return result
        
        priority = get_intent_priority(intent_type)
        
        # === P1-B: EXECUTION GUARD LAYER ===
        
        # 1. Circuit Breaker Check
        if self.circuit_breaker.is_open():
            logger.error(
                f"🔥 Order BLOCKED by circuit breaker | "
                f"symbol={symbol} | trace_id={trace_id}"
            )
            return {
                "accepted": False,
                "task_id": None,
                "client_order_id": None,
                "trace_id": trace_id,
                "status": "rejected",
                "reason": "circuit_breaker_open"
            }
        
        # 2. Rate Limiter Check
        if not self.rate_limiter.consume_order_new():
            logger.warning(
                f"⚠️ Order THROTTLED by rate limiter | "
                f"symbol={symbol} | trace_id={trace_id}"
            )
            
            # Check wait time
            wait_time = self.rate_limiter.bucket.wait_time(tokens=1.0)
            
            return {
                "accepted": False,
                "task_id": None,
                "client_order_id": None,
                "trace_id": trace_id,
                "status": "rejected",
                "reason": f"rate_limit_exceeded (retry in {wait_time:.1f}s)"
            }
        
        # 3. Queue Pressure Guard Check
        inflight_count = self.latency_tracker.get_inflight_count()
        latency_stats = self.latency_tracker.get_stats()
        avg_latency = latency_stats.get("p50_network_ms") or 0.0
        
        # Get queue depth
        queue_depth = 0
        if self.persistent_queue:
            try:
                queue_metrics = await self.persistent_queue.get_metrics()
                queue_depth = queue_metrics.get("pending_count", 0) + queue_metrics.get("processing_count", 0)
            except Exception:
                pass
        
        pressure_eval = self.queue_pressure_guard.evaluate(
            inflight_orders=inflight_count,
            queue_depth=queue_depth,
            avg_latency_ms=avg_latency
        )
        
        if pressure_eval["should_block"]:
            logger.error(
                f"🔥 Order BLOCKED by queue pressure guard | "
                f"pressure={pressure_eval['pressure']:.2f} | "
                f"reason={pressure_eval['reason']} | "
                f"symbol={symbol} | trace_id={trace_id}"
            )
            return {
                "accepted": False,
                "task_id": None,
                "client_order_id": None,
                "trace_id": trace_id,
                "status": "rejected",
                "reason": f"queue_pressure_critical ({pressure_eval['reason']})",
                "pressure_metrics": pressure_eval
            }
        
        # Apply size multiplier if pressure elevated
        if pressure_eval["size_multiplier"] < 1.0:
            original_qty = qty
            qty = qty * pressure_eval["size_multiplier"]
            logger.warning(
                f"⚠️ Order size REDUCED by queue pressure guard | "
                f"pressure={pressure_eval['pressure']:.2f} | "
                f"size_mult={pressure_eval['size_multiplier']} | "
                f"qty: {original_qty} → {qty} | "
                f"symbol={symbol}"
            )
        
        # === P1.1B: ORIGINAL QUEUE LOGIC ===
        
        # 4. Generate client_order_id
        client_order_id = str(uuid.uuid4())
        
        logger.info(
            f"=== P1.1B ASYNC SUBMIT | client_order_id={client_order_id} | "
            f"symbol={symbol} | trace_id={trace_id} ==="
        )
        
        # 2. Enqueue task to Mongo persistent queue (P1.5: with priority)
        enqueue_result = await self.persistent_queue.enqueue(
            task_type="SUBMIT_ORDER",
            priority=priority,  # P1.5: Priority-based execution
            payload={
                "exchange": "binance",
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "price": price,
                "order_type": "LIMIT",
                "strategy_id": strategy_id,
                "client_order_id": client_order_id,
                "intent_type": intent_type  # P1.5: For monitoring
            },
            trace_id=trace_id
        )
        
        if not enqueue_result["accepted"]:
            logger.warning(
                f"⚠️ Order rejected by queue: {enqueue_result.get('reason')}"
            )
            return {
                "accepted": False,
                "task_id": enqueue_result["task_id"],
                "client_order_id": client_order_id,
                "trace_id": trace_id,
                "status": "rejected",
                "reason": enqueue_result.get("reason", "Queue rejected")
            }
        
        # 3. Return accepted_for_processing
        from .queue.intent_priority import get_priority_label
        
        logger.info(
            f"✅ Order accepted for processing | "
            f"priority={get_priority_label(priority)} | "
            f"task_id={enqueue_result['task_id']} | "
            f"client_order_id={client_order_id}"
        )
        
        return {
            "accepted": True,
            "task_id": enqueue_result["task_id"],
            "client_order_id": client_order_id,
            "trace_id": trace_id,
            "status": "accepted_for_processing"
        }

    async def get_execution_health(self) -> Dict[str, Any]:
        """
        P1-A/P1-B: Get execution health metrics with circuit breaker and rate limiter status.
        
        Returns comprehensive execution health including:
        - Latencies (p50, p95): submit_to_ack_ms, submit_to_fill_ms
        - Queue metrics: depth, inflight_orders
        - Reject/timeout rates
        - P1-B: Circuit breaker state
        - P1-B: Rate limiter metrics
        - Overall health status: HEALTHY / WARNING / CRITICAL
        
        Returns:
            {
                "status": "HEALTHY" | "WARNING" | "CRITICAL",
                "latency": {...},
                "queue": {...},
                "execution": {...},
                "circuit_breaker": {
                    "state": "CLOSED" | "OPEN" | "HALF_OPEN",
                    "consecutive_failures": int,
                    "consecutive_successes": int
                },
                "rate_limiter": {
                    "available_tokens": float,
                    "capacity": float,
                    "utilization": float
                },
                "timestamp": str
            }
        """
        import statistics
        from datetime import datetime, timezone
        
        # Get latency stats from LatencyTracker
        latency_stats = self.latency_tracker.get_stats()
        
        # Calculate p50 (median) from raw data
        def calc_p50(data: deque) -> float:
            if not data:
                return 0.0
            return statistics.median(data) if len(data) > 0 else 0.0
        
        # Use new LatencyTracker API (network_latencies = submit_to_ack)
        p50_ack = calc_p50(self.latency_tracker._network_latencies_ms)
        p50_fill = calc_p50(self.latency_tracker._execution_latencies_ms)
        
        # Get execution metrics from ExecutionMetricsStore
        exec_metrics = self.metrics_store.get_metrics()
        
        # Get current queue depth (if queue available)
        queue_depth = 0
        if self.persistent_queue:
            # Get pending + processing tasks count
            try:
                queue_metrics = await self.persistent_queue.get_metrics()
                queue_depth = queue_metrics.get("pending_count", 0) + queue_metrics.get("processing_count", 0)
                self.metrics_store.snapshot_queue_depth(queue_depth)
            except Exception as e:
                logger.warning(f"Failed to get queue metrics: {e}")
        
        # P1-B: Evaluate circuit breaker with current metrics
        circuit_breaker_metrics = {
            "latency_p95_ms": latency_stats.get("p95_network_ms") or 0.0,  # network = submit_to_ack
            "reject_rate": exec_metrics["reject_rate"],
            "timeout_rate": exec_metrics["timeout_rate"],
            "sample_count": exec_metrics["total_submits"]
        }
        self.circuit_breaker.evaluate(circuit_breaker_metrics)
        
        # Get health status (may be overridden by circuit breaker)
        health_status = self.metrics_store.get_health_status()
        
        # Override if circuit breaker is OPEN
        if self.circuit_breaker.is_open():
            health_status = "CRITICAL"
        
        # P1-B: Get circuit breaker state
        cb_state = self.circuit_breaker.get_state()
        
        # P1-B: Get rate limiter metrics
        rl_metrics = self.rate_limiter.get_metrics()
        
        # P1: Get queue pressure evaluation
        pressure_eval = self.queue_pressure_guard.evaluate(
            inflight_orders=len(self.latency_tracker._inflight),
            queue_depth=queue_depth,
            avg_latency_ms=latency_stats.get("p50_network_ms") or 0.0  # Use p50 network latency, handle None
        )
        
        # Override health if queue pressure critical
        if pressure_eval["should_block"]:
            health_status = "CRITICAL"
        
        return {
            "status": health_status,
            "latency": {
                "avg_submit_to_ack_ms": round(latency_stats.get("p50_network_ms") or 0.0, 2),
                "p50_submit_to_ack_ms": round(p50_ack, 2),
                "p95_submit_to_ack_ms": round(latency_stats.get("p95_network_ms") or 0.0, 2),
                "avg_submit_to_fill_ms": round(latency_stats.get("p50_total_ms") or 0.0, 2),
                "p50_submit_to_fill_ms": round(p50_fill, 2),
                "p95_submit_to_fill_ms": round(latency_stats.get("p95_total_ms") or 0.0, 2)
            },
            "queue": {
                "queue_depth": queue_depth,
                "inflight_orders": len(self.latency_tracker._inflight),
                "avg_queue_depth": exec_metrics["avg_queue_depth"],
                "pressure": pressure_eval["pressure"],
                "pressure_level": pressure_eval["level"]
            },
            "execution": {
                "total_submits": exec_metrics["total_submits"],
                "total_acks": exec_metrics["total_acks"],
                "total_fills": exec_metrics["total_fills"],
                "total_rejects": exec_metrics["total_rejects"],
                "total_timeouts": exec_metrics["total_timeouts"],
                "reject_rate": exec_metrics["reject_rate"],
                "timeout_rate": exec_metrics["timeout_rate"]
            },
            "circuit_breaker": {
                "state": cb_state["state"],
                "consecutive_failures": cb_state["consecutive_failures"],
                "consecutive_successes": cb_state["consecutive_successes"],
                "last_state_change": cb_state["last_state_change"]
            },
            "rate_limiter": {
                "available_tokens": rl_metrics["available_tokens"],
                "capacity": rl_metrics["capacity"],
                "utilization": rl_metrics["utilization"],
                "refill_rate_per_min": round(rl_metrics["refill_rate"] * 60, 2)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_system_health(self, current_prices: Dict[str, float] | None = None) -> Dict[str, Any]:
        """
        Оценить здоровье системы (P0.6 — Protection Layer).
        
        Args:
            current_prices: {symbol: price} для расчёта unrealized pnl
        
        Returns:
            {
                "status": "HEALTHY" | "WARNING" | "CRITICAL",
                "metrics": {...},
                "actions": [...]
            }
        """
        # Собираем metrics
        current_prices = current_prices or {}
        
        # 1. PnL metrics
        all_pnl = {}
        symbols = set(t["symbol"] for t in self.pnl_projection.ledger.get_all_trades())
        for symbol in symbols:
            price = current_prices.get(symbol, 0.0)
            pnl = self.pnl_projection.get_symbol_pnl(symbol, price, current_prices)
            all_pnl[symbol] = pnl
        
        # Aggregate PnL
        total_realized = sum(p["realized_pnl"] for p in all_pnl.values())
        total_unrealized = sum(p["unrealized_pnl"] for p in all_pnl.values())
        total_pnl = total_realized + total_unrealized
        total_fees = sum(p["fees_usdt"] for p in all_pnl.values())
        net_pnl = total_pnl - total_fees
        
        # Daily PnL % (упрощённо: предполагаем starting equity = 10000 USDT)
        starting_equity = 10000.0
        daily_pnl_pct = net_pnl / starting_equity if starting_equity > 0 else 0.0
        
        # Drawdown % (упрощённо: от starting equity)
        drawdown_pct = min(0.0, daily_pnl_pct)  # если убыток, то это drawdown
        
        # 2. Execution metrics
        # Reject rate: кол-во ORDER_REJECTED / total orders
        all_events = await self.event_store.list_last(limit=1000)
        rejected_count = sum(1 for e in all_events if e.event_type == "ORDER_REJECTED")
        total_submit = sum(1 for e in all_events if e.event_type == "ORDER_SUBMIT_REQUESTED")
        reject_rate = rejected_count / total_submit if total_submit > 0 else 0.0
        
        # Latency (placeholder)
        latency_ms = 0
        
        # 3. Reconciliation critical mismatches
        recon_critical = sum(
            1 for e in all_events
            if e.event_type == "RECONCILIATION_MISMATCH"
            and e.payload.get("severity") == "CRITICAL"
        )
        
        # Update health model
        self.health_model.update_metrics({
            "daily_pnl_pct": daily_pnl_pct,
            "drawdown_pct": drawdown_pct,
            "reject_rate": reject_rate,
            "latency_ms": latency_ms,
            "reconciliation_critical": recon_critical
        })
        
        # Evaluate
        health_status = self.health_model.evaluate()
        guard_actions = self.risk_guard.evaluate(health_status)
        
        return {
            "status": health_status,
            "metrics": self.health_model.metrics,
            "actions": guard_actions
        }

    async def close_all_positions(self, reason: str = "risk_guard_critical") -> Dict[str, Any]:
        """
        KILL SWITCH: Закрыть все открытые позиции (P0.6).
        
        Вызывается когда Risk Guard выдаёт CLOSE_ALL action.
        В production это создаст MARKET ордера на закрытие.
        
        Args:
            reason: Причина закрытия (для аудита)
        
        Returns:
            {
                "success": bool,
                "positions_closed": int,
                "events_created": List[str]
            }
        """
        logger.critical(f"🔥 KILL SWITCH TRIGGERED: close_all_positions | reason={reason}")
        
        # Получаем все открытые позиции
        positions = self.position_projection.list_positions()
        open_positions = [p for p in positions if p.size != 0]
        
        if not open_positions:
            logger.info("No open positions to close")
            return {
                "success": True,
                "positions_closed": 0,
                "events_created": []
            }
        
        events_created = []
        
        # Создаём события закрытия для каждой позиции
        for position in open_positions:
            # В production здесь будет вызов binance_adapter.submit_market_order
            # Для P0.6 создаём событие POSITION_CLOSE_REQUESTED
            close_event = create_event(
                event_type="POSITION_CLOSE_REQUESTED",
                exchange=position.exchange,
                symbol=position.symbol,
                client_order_id=str(uuid.uuid4()),
                payload={
                    "reason": reason,
                    "size": abs(position.size),
                    "side": "SELL" if position.size > 0 else "BUY",
                    "urgency": "IMMEDIATE"
                }
            )
            
            await self.event_store.append(close_event)
            await self.event_bus.publish(close_event)
            
            events_created.append(close_event.event_id)
            
            logger.warning(
                f"   Position close requested: {position.symbol} | "
                f"size={position.size} | event_id={close_event.event_id}"
            )
        
        logger.critical(
            f"✅ KILL SWITCH EXECUTED: {len(open_positions)} positions closed | "
            f"reason={reason}"
        )
        
        return {
            "success": True,
            "positions_closed": len(open_positions),
            "events_created": events_created
        }

    async def manual_record_fill(
        self,
        client_order_id: str,
        fill_qty: float,
        fill_price: float
    ) -> Dict[str, Any]:
        """
        Вручную записать ORDER_FILL_RECORDED событие (для DoD Test 3).
        В production это будет приходить через WebSocket user stream.
        """
        order = self.order_projection.get_order(client_order_id)
        if not order:
            return {"success": False, "error": "Order not found"}

        fill_event = create_event(
            event_type=EXECUTION_EVENT_TYPES["ORDER_FILL_RECORDED"],
            exchange=order.exchange,
            symbol=order.symbol,
            client_order_id=client_order_id,
            exchange_order_id=order.exchange_order_id,
            payload={
                "fill_qty": fill_qty,
                "fill_price": fill_price,
                "side": order.side
            }
        )

        await self.event_store.append(fill_event)
        await self.event_bus.publish(fill_event)

        logger.info(f"✅ ORDER_FILL_RECORDED (manual) | {client_order_id} | qty={fill_qty}")

        # Возвращаем обновлённый order + position
        updated_order = self.order_projection.get_order(client_order_id)
        position = self.position_projection.get_position(order.symbol)

        return {
            "success": True,
            "order": updated_order.dict() if updated_order else None,
            "position": position.dict() if position else None
        }
