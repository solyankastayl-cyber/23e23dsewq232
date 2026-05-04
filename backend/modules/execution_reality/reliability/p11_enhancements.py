"""
P1.1 Final Enhancements - Fund-Grade Retry Safety

CRITICAL FIXES:
1. Pre-retry check to prevent double-submit
2. Budget exhaustion → event emission to Risk Guard  
3. READ/WRITE operation separation
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BudgetExhaustedEvent:
    """Event emitted when retry budget exhausted"""
    
    def __init__(
        self,
        timestamp: str,
        global_retries: int,
        max_retries: int,
        exhaustion_count: int,
        severity: str = "CRITICAL"
    ):
        self.timestamp = timestamp
        self.global_retries = global_retries
        self.max_retries = max_retries
        self.exhaustion_count = exhaustion_count
        self.severity = severity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": "RETRY_BUDGET_EXHAUSTED",
            "timestamp": self.timestamp,
            "global_retries": self.global_retries,
            "max_retries": self.max_retries,
            "exhaustion_count": self.exhaustion_count,
            "severity": self.severity,
            "action_required": "Risk Guard should throttle/pause execution"
        }


async def check_order_exists_before_retry(
    context: Dict[str, Any],
    order_projection
) -> Optional[Dict[str, Any]]:
    """
    P1.1 CRITICAL: Pre-retry safety check.
    
    Prevents double-submit when:
    - submit → timeout
    - BUT order actually went through
    - retry → double order
    
    Args:
        context: Contains client_order_id
        order_projection: Order state projection
    
    Returns:
        Existing order if found, None otherwise
    """
    client_order_id = context.get("client_order_id")
    if not client_order_id:
        return None
    
    try:
        existing = await order_projection.get_order(client_order_id)
        
        if existing and existing.get("status") in ["ACKNOWLEDGED", "PARTIAL", "FILLED"]:
            logger.info(
                f"✅ PRE-RETRY CHECK: Order already exists | "
                f"client_order_id={client_order_id} | "
                f"status={existing.get('status')} | "
                f"SKIPPING RETRY (safety)"
            )
            return existing
        
        return None
    
    except Exception as e:
        logger.warning(f"⚠️ Pre-retry check failed: {e} (continuing)")
        return None


def emit_budget_exhausted_event(
    event_emitter: Optional[callable],
    global_retries: int,
    max_retries: int,
    exhaustion_count: int
):
    """
    P1.1: Emit event when retry budget exhausted.
    
    Risk Guard should listen to this and:
    - Set system health to WARNING/CRITICAL
    - Throttle new submissions
    - Potentially pause execution
    
    Args:
        event_emitter: Event emitter function
        global_retries: Current retry count
        max_retries: Maximum allowed
        exhaustion_count: How many times exhausted
    """
    if not event_emitter:
        logger.warning("⚠️ No event emitter configured for budget exhaustion")
        return
    
    from datetime import datetime, timezone
    
    event = BudgetExhaustedEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        global_retries=global_retries,
        max_retries=max_retries,
        exhaustion_count=exhaustion_count
    )
    
    try:
        event_emitter(event.to_dict())
        logger.critical(
            f"🔥 RETRY_BUDGET_EXHAUSTED event emitted | "
            f"retries={global_retries}/{max_retries} | "
            f"count={exhaustion_count}"
        )
    except Exception as e:
        logger.error(f"❌ Failed to emit budget exhaustion event: {e}")


def get_max_attempts_for_operation(
    operation_type: str,
    default_max_attempts: int
) -> int:
    """
    P1.1: Separate retry limits for READ vs WRITE.
    
    READ operations (safe):
    - get_ticker, get_position, get_order_status
    - Can retry aggressively (5+ attempts)
    
    WRITE operations (dangerous):
    - submit_order, cancel_order, modify_order
    - Must retry conservatively (1-2 attempts)
    - Rely on idempotency for safety
    
    Args:
        operation_type: "READ" or "WRITE"
        default_max_attempts: Default retry limit
    
    Returns:
        Adjusted max attempts
    """
    if operation_type == "WRITE":
        # WRITE = dangerous, strict retry
        return min(2, default_max_attempts)
    elif operation_type == "READ":
        # READ = safe, aggressive retry
        return max(5, default_max_attempts)
    else:
        return default_max_attempts
