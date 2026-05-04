"""
Strategy Switch Module (STR3)
=============================

Strategy Switching & Policy Logic for trading profile management.

Components:
- switch_types: Type definitions
- switch_policy_registry: Standard policies
- switch_policy_engine: Policy evaluation
- switch_scheduler: Scheduled switches
- switch_service: Main service
- switch_routes: API endpoints
"""

from .switch_types import (
    SwitchTriggerType,
    SwitchPolicy,
    SwitchContext,
    SwitchEvent,
    SwitchDecision,
    ActiveProfileState,
    PolicyCondition,
    ScheduleConfig
)

from .switch_policy_registry import (
    POLICY_REGISTRY,
    get_policy,
    get_all_policies,
    register_policy
)

from .switch_policy_engine import (
    SwitchPolicyEngine,
    switch_policy_engine
)

from .switch_scheduler import (
    SwitchScheduler,
    switch_scheduler
)

from .switch_service import (
    StrategySwitchService,
    strategy_switch_service
)

__all__ = [
    # Types
    "SwitchTriggerType",
    "SwitchPolicy",
    "SwitchContext",
    "SwitchEvent",
    "SwitchDecision",
    "ActiveProfileState",
    "PolicyCondition",
    "ScheduleConfig",
    # Registry
    "POLICY_REGISTRY",
    "get_policy",
    "get_all_policies",
    "register_policy",
    # Engine
    "SwitchPolicyEngine",
    "switch_policy_engine",
    # Scheduler
    "SwitchScheduler",
    "switch_scheduler",
    # Service
    "StrategySwitchService",
    "strategy_switch_service"
]
