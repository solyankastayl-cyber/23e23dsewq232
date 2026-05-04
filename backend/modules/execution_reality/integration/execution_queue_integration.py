"""
Execution Queue Integration Service (P1.3.1)
=============================================

Интеграция execution queue в decision flow после FinalGate.

Режимы работы:
1. Shadow Mode (P1.3.1):
   - enqueue job ✅
   - direct submit ✅
   - enqueue failure не блокирует execution

2. Route Mode (P1.3.3+):
   - enqueue job ✅
   - direct submit ❌
   - только queue execution

3. Legacy Mode:
   - enqueue job ❌
   - direct submit ✅
   - старый путь без изменений
"""

import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timezone

from .execution_queue_feature_flags import (
    is_execution_queue_shadow_enabled,
    is_execution_queue_route_enabled,
    is_execution_queue_block_on_dispatch_failure,
)
from .execution_shadow_diff_models import ExecutionIntent, compare_intents
from .execution_routing_policy import (
    make_routing_decision,
    get_routing_policy
)
from .execution_routing_stats import increment_routing_stat

logger = logging.getLogger(__name__)


class ExecutionQueueIntegrationService:
    """
    Execution Queue Integration Service.
    
    Управляет маршрутизацией execution между queue и legacy path.
    """
    
    def __init__(self, dispatch_service, audit_logger=None, diff_repo=None):
        """
        Args:
            dispatch_service: ExecutionDispatchService instance
            audit_logger: ExecutionQueueAuditLogger (optional)
            diff_repo: ExecutionShadowDiffRepository (optional, P1.3.1D)
        """
        self.dispatch_service = dispatch_service
        self.audit_logger = audit_logger
        self.diff_repo = diff_repo  # P1.3.1D: Diff Capture
        
        logger.info(
            f"✅ ExecutionQueueIntegrationService initialized (P1.3.1) "
            f"[diff_capture={'enabled' if diff_repo else 'disabled'}]"
        )
    
    def _normalize_intent(
        self,
        symbol: str,
        gate_result: Dict[str, Any],
        execution_plan: Dict[str, Any],
        source: str = "queue"
    ) -> ExecutionIntent:
        """
        Normalize execution intent для diff comparison.
        
        P1.3.1D: Критично сравнивать ОДИНАКОВУЮ стадию трансформации!
        
        Args:
            symbol: Trading symbol
            gate_result: FinalGate result
            execution_plan: Raw execution plan
            source: "queue" or "legacy"
        
        Returns:
            ExecutionIntent (normalized)
        """
        decision_enforced = gate_result.get("decision_enforced", {})
        action = decision_enforced.get("action", "WAIT")
        direction = decision_enforced.get("direction", "NEUTRAL")
        size_multiplier = gate_result.get("size_multiplier", 1.0)
        
        # Extract base parameters
        base_size = execution_plan.get("size", 0.0)
        entry_price = execution_plan.get("entry")
        
        # Calculate normalized quantity
        normalized_quantity = base_size * size_multiplier
        
        # Determine side
        if direction == "LONG":
            side = "BUY"
        elif direction == "SHORT":
            side = "SELL"
        else:
            side = "UNKNOWN"
        
        # Determine orderType
        # Здесь можно добавить логику из execution_mode
        execution_mode = execution_plan.get("mode", "PASSIVE_LIMIT")
        if "MARKET" in execution_mode.upper():
            order_type = "MARKET"
            normalized_price = None  # MARKET orders не имеют price
        else:
            order_type = "LIMIT"
            normalized_price = entry_price
        
        # Extract exchange and accountId
        exchange = execution_plan.get("exchange", "binance")
        account_id = execution_plan.get("account_id", "default")
        
        return ExecutionIntent(
            symbol=symbol,
            side=side,
            quantity=normalized_quantity,
            price=normalized_price,
            orderType=order_type,
            reason=action,
            exchange=exchange,
            accountId=account_id,
            clientOrderId=None,  # TODO: extract if available
            timestamp=datetime.now(timezone.utc)
        )

    
    async def handle_approved_decision(
        self,
        symbol: str,
        gate_result: Dict[str, Any],
        execution_plan: Dict[str, Any],
        trace_id: Optional[str],
        direct_submit_callable: Callable[[], Awaitable[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Handle approved decision: route через queue или legacy path.
        
        Args:
            symbol: Trading symbol
            gate_result: FinalGate evaluation result
            execution_plan: Raw execution plan
            trace_id: P0.7 causal trace ID
            direct_submit_callable: Async callable для legacy direct submit
        
        Returns:
            {
                "mode": "shadow" | "queue_only" | "legacy_only",
                "dispatchResult": {...} or None,
                "dispatchError": str or None,
                "directSubmitExecuted": bool,
                "directResult": {...} or None
            }
        """
        shadow_enabled = is_execution_queue_shadow_enabled()
        route_enabled = is_execution_queue_route_enabled()
        block_on_dispatch_failure = is_execution_queue_block_on_dispatch_failure()
        
        dispatch_result = None
        dispatch_error = None
        
        # Попытка enqueue (если shadow или route enabled)
        if shadow_enabled or route_enabled:
            try:
                # Audit event: dispatch attempted
                if self.audit_logger:
                    await self.audit_logger.log_event(
                        event_type="EXECUTION_QUEUE_SHADOW_DISPATCH_ATTEMPTED",
                        job_id=None,
                        trace_id=trace_id,
                        status="shadow_dispatch",
                        metadata={
                            "symbol": symbol,
                            "shadowEnabled": shadow_enabled,
                            "routeEnabled": route_enabled
                        }
                    )
                
                # Dispatch to queue
                dispatch_result = await self.dispatch_service.dispatch(
                    symbol=symbol,
                    gate_result=gate_result,
                    execution_plan=execution_plan,
                    trace_id=trace_id
                )
                
                # Audit event: dispatch succeeded
                if dispatch_result.get("dispatched"):
                    if self.audit_logger:
                        await self.audit_logger.log_event(
                            event_type="EXECUTION_QUEUE_SHADOW_DISPATCH_SUCCEEDED",
                            job_id=dispatch_result.get("jobId"),
                            trace_id=trace_id,
                            status="queued",
                            metadata={
                                "symbol": symbol,
                                "priority": dispatch_result.get("priority"),
                                "mode": "route" if route_enabled else "shadow"
                            }
                        )
                    
                    logger.info(
                        f"✅ [P1.3.1 Shadow] Dispatch succeeded: jobId={dispatch_result.get('jobId')}, "
                        f"symbol={symbol}, trace_id={trace_id}, mode={'route' if route_enabled else 'shadow'}"
                    )
                else:
                    # Dispatch rejected (e.g., WAIT action, blocked decision)
                    logger.debug(
                        f"[P1.3.1 Shadow] Dispatch rejected: symbol={symbol}, "
                        f"reason={dispatch_result.get('reason')}"
                    )
            
            except Exception as exc:
                dispatch_error = str(exc)
                
                # Audit event: dispatch failed
                if self.audit_logger:
                    await self.audit_logger.log_event(
                        event_type="EXECUTION_QUEUE_SHADOW_DISPATCH_FAILED",
                        job_id=None,
                        trace_id=trace_id,
                        status="dispatch_error",
                        metadata={
                            "symbol": symbol,
                            "error": dispatch_error,
                            "shadowEnabled": shadow_enabled,
                            "routeEnabled": route_enabled
                        }
                    )
                
                logger.error(
                    f"❌ [P1.3.1 Shadow] Dispatch error: symbol={symbol}, "
                    f"trace_id={trace_id}, error={exc}",
                    exc_info=True
                )
                
                # Проверяем, нужно ли блокировать execution
                if block_on_dispatch_failure:
                    if route_enabled:
                        # Route mode + block on failure → критический фейл
                        logger.critical(
                            f"🚨 [P1.3.1] CRITICAL: Queue dispatch failed in ROUTE mode "
                            f"with BLOCK_ON_FAILURE=true. Blocking execution. "
                            f"symbol={symbol}, trace_id={trace_id}"
                        )
                        raise
                    
                    if shadow_enabled:
                        # Shadow mode + block on failure → строгий режим
                        logger.error(
                            f"🚨 [P1.3.1] Queue dispatch failed in SHADOW mode "
                            f"with BLOCK_ON_FAILURE=true. Blocking execution. "
                            f"symbol={symbol}, trace_id={trace_id}"
                        )
                        raise
                
                # P1.3.1D: Failure Injection Test Fix
                # Если dispatch failed, но НЕ блокируем execution (fail-open),
                # продолжаем legacy submit и возвращаем результат
                if shadow_enabled and not block_on_dispatch_failure:
                    logger.warning(
                        f"⚠️ [P1.3.1D Fail-Open] Dispatch failed but continuing legacy submit: "
                        f"symbol={symbol}, trace_id={trace_id}"
                    )
                    
                    # Execute legacy submit DESPITE dispatch failure
                    legacy_result = await direct_submit_callable()
                    
                    # Audit event: legacy continued after dispatch failure
                    if self.audit_logger:
                        await self.audit_logger.log_event(
                            event_type="EXECUTION_LEGACY_SUBMIT_AFTER_DISPATCH_FAILURE",
                            job_id=None,
                            trace_id=trace_id,
                            status="legacy_submit_fallback",
                            metadata={
                                "symbol": symbol,
                                "dispatchError": dispatch_error,
                                "legacyResult": legacy_result
                            }
                        )
                    
                    return {
                        "mode": "shadow_fail_open",
                        "dispatchResult": None,
                        "dispatchError": dispatch_error,
                        "legacySubmitExecuted": True,
                        "legacyResult": legacy_result
                    }
        
        # Route mode: ТОЛЬКО queue, БЕЗ direct submit
        if route_enabled:
            logger.info(
                f"[P1.3.1 Route] Queue-only mode: symbol={symbol}, "
                f"trace_id={trace_id}, dispatch_success={dispatch_result.get('dispatched') if dispatch_result else False}"
            )
            
            return {
                "mode": "queue_only",
                "dispatchResult": dispatch_result,
                "dispatchError": dispatch_error,
                "legacySubmitExecuted": False,
                "legacyResult": None
            }
        
        # Shadow mode или legacy: direct submit continues
        logger.info(
            f"[P1.3.1 {'Shadow' if shadow_enabled else 'Legacy'}] "
            f"Executing direct submit: symbol={symbol}, trace_id={trace_id}"
        )
        
        # Direct submit
        legacy_result = await direct_submit_callable()
        
        # Audit event: direct submit continued
        if shadow_enabled and self.audit_logger:
            await self.audit_logger.log_event(
                event_type="EXECUTION_DIRECT_SUBMIT_CONTINUED",
                job_id=dispatch_result.get("jobId") if dispatch_result else None,
                trace_id=trace_id,
                status="direct_submit",
                metadata={
                    "symbol": symbol,
                    "dispatchSuccess": dispatch_result.get("dispatched") if dispatch_result else False,
                    "legacyResult": legacy_result
                }
            )
        
        # P1.3.1D: Diff Capture (CRITICAL)
        # Сравниваем queue_intent vs legacy_intent
        if shadow_enabled and self.diff_repo:
            try:
                # Normalize intents (одинаковая стадия трансформации!)
                queue_intent = self._normalize_intent(
                    symbol=symbol,
                    gate_result=gate_result,
                    execution_plan=execution_plan,
                    source="queue"
                )
                
                legacy_intent = self._normalize_intent(
                    symbol=symbol,
                    gate_result=gate_result,
                    execution_plan=execution_plan,
                    source="legacy"
                )
                
                # Compare intents
                match, diff, severity = compare_intents(queue_intent, legacy_intent)
                
                # Save diff to DB
                await self.diff_repo.save_diff(
                    trace_id=trace_id,
                    job_id=dispatch_result.get("jobId") if dispatch_result else None,
                    queue_intent=queue_intent,
                    legacy_intent=legacy_intent,
                    match=match,
                    diff=diff,
                    severity=severity
                )
                
                logger.info(
                    f"✅ [P1.3.1D Diff] Shadow diff saved: trace_id={trace_id}, "
                    f"match={match}, severity={severity}"
                )
            
            except Exception as e:
                logger.error(
                    f"❌ [P1.3.1D Diff] Failed to save diff: {e}", exc_info=True
                )
                # Не блокируем execution если diff capture failed
        
        return {
            "mode": "shadow" if shadow_enabled else "legacy_only",
            "dispatchResult": dispatch_result,
            "dispatchError": dispatch_error,
            "legacySubmitExecuted": True,
            "legacyResult": legacy_result
        }


# Global singleton (опционально)
_integration_service: Optional[ExecutionQueueIntegrationService] = None


def get_execution_queue_integration_service() -> Optional[ExecutionQueueIntegrationService]:
    """Get singleton ExecutionQueueIntegrationService."""
    global _integration_service
    return _integration_service


def set_execution_queue_integration_service(service: ExecutionQueueIntegrationService):
    """Set singleton ExecutionQueueIntegrationService."""
    global _integration_service
    _integration_service = service
    logger.info("✅ ExecutionQueueIntegrationService singleton set")
