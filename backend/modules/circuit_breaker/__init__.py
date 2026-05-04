"""
Circuit Breaker Module

PHASE 41.4 — Circuit Breaker Engine

Automatic risk-control system that triggers protective actions
based on predefined rules (drawdown, slippage, loss streak).

Actions:
- Reduce position size
- Block new entries
- Switch to LIMIT only
- Pause strategy
- Trigger kill switch
"""

from .breaker_types import (
    BreakerState,
    BreakerRuleType,
    BreakerAction,
    BreakerSeverity,
    BreakerRule,
    BreakerEvent,
    BreakerStatus,
    BreakerConfig,
    BreakerCheckResult,
)

from .breaker_engine import (
    CircuitBreakerEngine,
    get_circuit_breaker,
)

from .breaker_routes import router as breaker_router

__all__ = [
    "BreakerState",
    "BreakerRuleType",
    "BreakerAction",
    "BreakerSeverity",
    "BreakerRule",
    "BreakerEvent",
    "BreakerStatus",
    "BreakerConfig",
    "BreakerCheckResult",
    "CircuitBreakerEngine",
    "get_circuit_breaker",
    "breaker_router",
]
