"""
Execution Safety Layer (SEC1)
=============================

Protects against:
- Duplicate orders
- Runaway execution
- Position limits
- Stale orders
- Exchange desync

Safety Gate between Strategy Runtime and OMS.
"""

from .safety_types import (
    SafetyDecision,
    SafetyDecisionResult,
    SafetyConfig,
    SafetyEventType,
    SafetyEvent,
    OrderValidationRequest,
    PositionGuardConfig,
    RateGuardConfig,
    DuplicateGuardConfig,
    StaleOrderConfig,
    ExchangeSyncConfig
)

from .safety_service import safety_service

__all__ = [
    'safety_service',
    'SafetyDecision',
    'SafetyDecisionResult',
    'SafetyConfig',
    'SafetyEventType',
    'SafetyEvent',
    'OrderValidationRequest',
    'PositionGuardConfig',
    'RateGuardConfig',
    'DuplicateGuardConfig',
    'StaleOrderConfig',
    'ExchangeSyncConfig'
]
