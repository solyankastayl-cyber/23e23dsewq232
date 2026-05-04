"""
Execution Queue Integration Module (P1.3.1)
============================================

Shadow integration layer для безопасного rollout execution queue.
"""

from .execution_queue_feature_flags import (
    is_execution_queue_shadow_enabled,
    is_execution_queue_route_enabled,
    is_execution_queue_block_on_dispatch_failure,
    get_execution_queue_canary_percent,
    log_feature_flags
)

from .execution_queue_integration import (
    ExecutionQueueIntegrationService,
    get_execution_queue_integration_service,
    set_execution_queue_integration_service
)

__all__ = [
    "is_execution_queue_shadow_enabled",
    "is_execution_queue_route_enabled",
    "is_execution_queue_block_on_dispatch_failure",
    "get_execution_queue_canary_percent",
    "log_feature_flags",
    "ExecutionQueueIntegrationService",
    "get_execution_queue_integration_service",
    "set_execution_queue_integration_service",
]
