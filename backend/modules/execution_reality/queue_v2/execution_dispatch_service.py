"""
Execution Dispatch Service (P1.3)
==================================

Перехватывает решение после FinalGate и создаёт ExecutionJob в очереди.

Integration Point:
FinalGate → ExecutionDispatchService → execution_jobs.enqueue()

Feature Flag:
- USE_EXECUTION_QUEUE = true → enqueue job
- USE_EXECUTION_QUEUE = false → direct submit (old path)
"""

import logging
import hashlib
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .execution_queue_repository import ExecutionQueueRepository
from .execution_job_models import get_priority_for_action

logger = logging.getLogger(__name__)


# P1.3.1D: Failure Injection Support
def is_dispatch_failure_forced() -> bool:
    """Check if dispatch failure is forced (for testing)."""
    return os.getenv("EXECUTION_QUEUE_FORCE_DISPATCH_FAILURE", "false").lower() == "true"


# P1.3.1D: Action Filtering Guard
# Только эти actions разрешены для enqueue в execution_jobs
ALLOWED_EXECUTION_ACTIONS = {
    "OPEN_LONG",
    "OPEN_SHORT",
    "CLOSE",
    "REDUCE",
    "STOP_LOSS",
    "TAKE_PROFIT",
    "HEDGE",
    "RISK_REDUCTION",
    # Legacy/generic actions
    "GO_FULL",
    "GO_AGGRESSIVE",
    "GO_NORMAL",
}

# Actions которые НЕ должны попадать в queue
NON_EXECUTION_ACTIONS = {
    "WAIT",
    "HOLD",
    "BLOCK",
    "SKIP",
    "NO_ACTION",
    "WAIT_RETEST",  # Временно блокируем
}


def build_semantic_idempotency_key(
    exchange: str,
    account_id: str,
    trace_id: Optional[str],
    symbol: str,
    side: str,
    reason: str
) -> str:
    """
    Build semantic idempotency key для защиты от duplicate decisions.
    
    Правка 1 (перед P1.3.1): Усиление idempotency protection.
    
    Args:
        exchange: Exchange name (e.g., 'binance')
        account_id: Account identifier
        trace_id: Causal trace ID
        symbol: Trading symbol
        side: BUY/SELL
        reason: Decision reason (action или другой unique identifier)
    
    Returns:
        Semantic idempotency key
    
    Example:
        binance:acc123:trace-001:BTCUSDT:BUY:GO_FULL
    """
    # Base semantic key
    parts = [
        exchange,
        account_id or "default",
        trace_id or "no-trace",
        symbol,
        side or "UNKNOWN",
        reason or "UNKNOWN"
    ]
    
    semantic_key = ":".join(parts)
    
    # Для очень длинных ключей можно использовать hash
    # Но пока оставляем читаемым для debugging
    if len(semantic_key) > 200:
        # Используем hash для очень длинных ключей
        hash_suffix = hashlib.sha256(semantic_key.encode()).hexdigest()[:16]
        return f"{exchange}:{account_id}:{symbol}:{side}:hash-{hash_suffix}"
    
    return semantic_key


class ExecutionDispatchService:
    """
    Execution Dispatch Service (P1.3).
    
    Responsibilities:
    - Convert FinalGate result → ExecutionJob payload
    - Enqueue job to execution_jobs
    - Return dispatch confirmation (NOT exchange confirmation!)
    """
    
    def __init__(self, execution_queue_repo: ExecutionQueueRepository):
        """
        Args:
            execution_queue_repo: ExecutionQueueRepository instance
        """
        self.execution_queue_repo = execution_queue_repo
        logger.info("✅ ExecutionDispatchService initialized (P1.3)")
    
    async def dispatch(
        self,
        symbol: str,
        gate_result: Dict[str, Any],
        execution_plan: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatch execution job to queue.
        
        Args:
            symbol: Trading symbol
            gate_result: FinalGate evaluation result
            execution_plan: Raw execution plan
            trace_id: P0.7 causal graph trace ID
        
        Returns:
            {
                "dispatched": bool,
                "jobId": str,
                "traceId": str,
                "priority": int,
                "reason": str (if rejected)
            }
        """
        # Check if decision blocked by FinalGate
        if gate_result.get("blocked"):
            logger.info(
                f"[P1.3 Dispatch] Decision blocked by FinalGate: {gate_result.get('block_reason')}, "
                f"NOT dispatching job"
            )
            return {
                "dispatched": False,
                "reason": f"blocked_by_final_gate: {gate_result.get('block_reason')}"
            }
        
        # Extract decision
        decision_enforced = gate_result.get("decision_enforced", {})
        action = decision_enforced.get("action", "WAIT")
        confidence = decision_enforced.get("confidence", 0.5)
        
        # P1.3.1D: Action Filtering Guard
        # Проверяем, что action разрешён для execution
        if action in NON_EXECUTION_ACTIONS:
            logger.info(
                f"[P1.3.1D Filter] Action '{action}' is NON_EXECUTION_ACTION, "
                f"NOT dispatching job for {symbol}"
            )
            
            # Audit event: skipped non-execution action
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type="EXECUTION_QUEUE_SKIPPED_NON_EXECUTION_ACTION",
                    job_id=None,
                    trace_id=trace_id,
                    status="skipped",
                    metadata={
                        "symbol": symbol,
                        "action": action,
                        "reason": "non_execution_action"
                    }
                )
            
            return {
                "dispatched": False,
                "reason": f"non_execution_action: {action}"
            }
        
        # Дополнительная проверка: action должен быть в whitelist
        if action not in ALLOWED_EXECUTION_ACTIONS:
            logger.warning(
                f"[P1.3.1D Filter] Action '{action}' NOT in ALLOWED_EXECUTION_ACTIONS, "
                f"dispatching anyway (might be new action type)"
            )
            
            # Audit event: unknown action (warning, но не блокируем)
            if self.audit_logger:
                await self.audit_logger.log_event(
                    event_type="EXECUTION_QUEUE_UNKNOWN_ACTION_WARNING",
                    job_id=None,
                    trace_id=trace_id,
                    status="warning",
                    metadata={
                        "symbol": symbol,
                        "action": action,
                        "reason": "action_not_in_whitelist_but_not_blocked"
                    }
                )
        
        # Build execution payload
        payload = self._build_payload(
            symbol=symbol,
            decision_enforced=decision_enforced,
            execution_plan=execution_plan,
            gate_result=gate_result
        )
        
        # Determine priority
        priority = get_priority_for_action(action, confidence)
        
        # Правка 1: Semantic idempotency key
        # Защищает от duplicate decisions на бизнес-уровне
        side = decision_enforced.get("direction", "NEUTRAL")  # LONG/SHORT/NEUTRAL
        if side == "LONG":
            side = "BUY"
        elif side == "SHORT":
            side = "SELL"
        else:
            side = "UNKNOWN"
        
        # Build semantic idempotency key
        idempotency_key = build_semantic_idempotency_key(
            exchange="binance",  # TODO: получать из конфига
            account_id=execution_plan.get("account_id", "default"),
            trace_id=trace_id,
            symbol=symbol,
            side=side,
            reason=action  # Action как reason
        )
        
        # Enqueue job
        try:
            # P1.3.1D: Failure Injection (для testing)
            if is_dispatch_failure_forced():
                logger.warning(
                    f"[P1.3.1D Failure] FORCED_DISPATCH_FAILURE triggered for testing: "
                    f"symbol={symbol}, trace_id={trace_id}"
                )
                raise RuntimeError("FORCED_DISPATCH_FAILURE (test mode)")
            
            result = await self.execution_queue_repo.enqueue(
                symbol=symbol,
                exchange="binance",  # TODO: получать из конфига
                action=action,
                payload=payload,
                trace_id=trace_id,
                priority=priority,
                idempotency_key=idempotency_key,
                confidence=confidence
            )
            
            if result.get("accepted"):
                logger.info(
                    f"✅ [P1.3 Dispatch] Job dispatched: jobId={result['jobId']}, "
                    f"symbol={symbol}, action={action}, priority={priority}, "
                    f"trace_id={trace_id}"
                )
                return {
                    "dispatched": True,
                    "jobId": result["jobId"],
                    "traceId": trace_id,
                    "priority": priority
                }
            else:
                logger.warning(
                    f"⚠️ [P1.3 Dispatch] Job rejected: {result.get('reason')}"
                )
                return {
                    "dispatched": False,
                    "reason": result.get("reason")
                }
        
        except Exception as e:
            logger.error(
                f"❌ [P1.3 Dispatch] Dispatch error: {e}", exc_info=True
            )
            return {
                "dispatched": False,
                "reason": f"dispatch_error: {str(e)}"
            }
    
    def _build_payload(
        self,
        symbol: str,
        decision_enforced: Dict[str, Any],
        execution_plan: Dict[str, Any],
        gate_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build execution job payload from decision and execution plan.
        
        Args:
            symbol: Trading symbol
            decision_enforced: Enforced decision from FinalGate
            execution_plan: Raw execution plan
            gate_result: Full FinalGate result
        
        Returns:
            Payload dict for ExecutionJob
        """
        # Extract core execution parameters
        action = decision_enforced.get("action", "WAIT")
        direction = decision_enforced.get("direction", "NEUTRAL")
        size_multiplier = gate_result.get("size_multiplier", 1.0)
        forced_mode = gate_result.get("forced_execution_mode")
        
        # Extract execution plan details
        base_size = execution_plan.get("size", 0.0)
        entry_price = execution_plan.get("entry")
        stop_price = execution_plan.get("stop")
        target_price = execution_plan.get("target")
        
        # Calculate final size (with FinalGate multiplier)
        final_size = base_size * size_multiplier
        
        # Determine side
        side = "BUY" if direction == "LONG" else "SELL" if direction == "SHORT" else None
        
        payload = {
            # Core execution
            "symbol": symbol,
            "action": action,
            "side": side,
            "direction": direction,
            
            # Sizing
            "base_size": base_size,
            "size_multiplier": size_multiplier,
            "final_size": final_size,
            
            # Prices
            "entry_price": entry_price,
            "stop_price": stop_price,
            "target_price": target_price,
            
            # Mode
            "execution_mode": forced_mode or execution_plan.get("mode", "PASSIVE_LIMIT"),
            
            # FinalGate context
            "reason_chain": gate_result.get("reason_chain", []),
            
            # Metadata
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return payload


# Global singleton instance (опционально, для удобства)
_dispatch_service: Optional[ExecutionDispatchService] = None


def get_execution_dispatch_service() -> Optional[ExecutionDispatchService]:
    """Get singleton ExecutionDispatchService instance (if initialized)."""
    global _dispatch_service
    return _dispatch_service


def set_execution_dispatch_service(service: ExecutionDispatchService):
    """Set singleton ExecutionDispatchService instance."""
    global _dispatch_service
    _dispatch_service = service
    logger.info("✅ ExecutionDispatchService singleton set")
