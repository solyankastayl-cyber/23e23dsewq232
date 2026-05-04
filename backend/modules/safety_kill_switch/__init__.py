"""
Safety Kill Switch Module

PHASE 41.3 — Kill Switch Engine

Emergency stop system for trading operations.

States:
- ACTIVE: Normal operation
- SAFE_MODE: Reduced operations
- DISABLED: All new operations blocked
- EMERGENCY_STOP: Immediate halt
"""

from .kill_switch_types import (
    KillSwitchState,
    KillSwitchTrigger,
    KillSwitchAction,
    KillSwitchStatus,
    KillSwitchEvent,
    KillSwitchConfig,
    KillSwitchCheckResult,
    ActivateKillSwitchRequest,
    DeactivateKillSwitchRequest,
)

from .kill_switch_engine import (
    KillSwitchEngine,
    get_kill_switch,
)

from .kill_switch_routes import router as kill_switch_router

__all__ = [
    "KillSwitchState",
    "KillSwitchTrigger",
    "KillSwitchAction",
    "KillSwitchStatus",
    "KillSwitchEvent",
    "KillSwitchConfig",
    "KillSwitchCheckResult",
    "ActivateKillSwitchRequest",
    "DeactivateKillSwitchRequest",
    "KillSwitchEngine",
    "get_kill_switch",
    "kill_switch_router",
]
