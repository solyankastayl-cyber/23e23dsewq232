"""
Execution Queue Feature Flags (P1.3.1)
=======================================

Feature flags для безопасного rollout execution queue.

Флаги:
- EXECUTION_QUEUE_SHADOW_ENABLED: Dual-write mode (enqueue + direct submit)
- EXECUTION_QUEUE_ROUTE_ENABLED: Queue routing mode (только queue)
- EXECUTION_QUEUE_BLOCK_ON_DISPATCH_FAILURE: Блокировать execution если enqueue упал

Rollout sequence:
1. SHADOW=true, ROUTE=false → shadow integration (P1.3.1)
2. Worker dry-run запущен → worker validates queue (P1.3.2)
3. ROUTE=true, CANARY=10% → partial routing (P1.3.3)
4. CANARY=100% → full migration
"""

import os
import logging

logger = logging.getLogger(__name__)


def is_execution_queue_shadow_enabled() -> bool:
    """
    Check if shadow integration is enabled.
    
    Shadow mode:
    - approved decision → enqueue job (NEW)
    - approved decision → direct submit (OLD)
    
    Both paths execute. Queue receives real traffic for validation.
    """
    value = os.getenv("EXECUTION_QUEUE_SHADOW_ENABLED", "false").lower()
    return value in ("true", "1", "yes")


def is_execution_queue_route_enabled() -> bool:
    """
    Check if queue routing is enabled.
    
    Route mode:
    - approved decision → enqueue job (NEW)
    - approved decision → NO direct submit (OLD path disabled)
    
    Only queue executes. Legacy path disabled.
    """
    value = os.getenv("EXECUTION_QUEUE_ROUTE_ENABLED", "false").lower()
    return value in ("true", "1", "yes")


def is_execution_queue_block_on_dispatch_failure() -> bool:
    """
    Check if dispatch failure should block execution.
    
    If True:
    - enqueue failure → BLOCKS execution (raises exception)
    
    If False:
    - enqueue failure → logs error, execution continues via legacy path
    
    Recommended: False for P1.3.1 (shadow mode)
    """
    value = os.getenv("EXECUTION_QUEUE_BLOCK_ON_DISPATCH_FAILURE", "false").lower()
    return value in ("true", "1", "yes")


def get_execution_queue_canary_percent() -> float:
    """
    Get canary routing percentage (P1.3.3).
    
    Returns:
        Float between 0.0 and 1.0 (e.g., 0.1 = 10%)
    """
    try:
        value = float(os.getenv("EXECUTION_QUEUE_CANARY_PERCENT", "0.0"))
        return max(0.0, min(1.0, value))  # Clamp to [0.0, 1.0]
    except ValueError:
        logger.error("Invalid EXECUTION_QUEUE_CANARY_PERCENT, defaulting to 0.0")
        return 0.0


def log_feature_flags():
    """Log current feature flag values (for debugging)."""
    logger.info(
        f"[P1.3.1 Feature Flags] "
        f"SHADOW={is_execution_queue_shadow_enabled()}, "
        f"ROUTE={is_execution_queue_route_enabled()}, "
        f"BLOCK_ON_FAILURE={is_execution_queue_block_on_dispatch_failure()}, "
        f"CANARY={get_execution_queue_canary_percent()}"
    )
