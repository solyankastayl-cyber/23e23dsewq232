"""
Security Module
===============

SEC1: Execution Safety Layer
SEC2: API Key Security / Vault Abstraction (planned)
SEC3: Connection Safety (planned)
SEC4: Action Audit Layer (planned)
"""

from .execution_safety import (
    safety_service,
    SafetyDecision,
    SafetyConfig,
    SafetyEventType
)

__all__ = [
    'safety_service',
    'SafetyDecision',
    'SafetyConfig',
    'SafetyEventType'
]
