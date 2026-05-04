"""
PHASE 3.2 — Policy Guard Layer

Prevents system from over-adapting or self-destructing.
Controls adaptation velocity and scope.

Modules:
- policy_config: Policy configuration and limits
- policy_evaluator: Evaluates actions against policies
- policy_guard: Main orchestrator
"""

from .policy_guard import PolicyGuard
from .policy_evaluator import PolicyEvaluator
from .policy_config import PolicyConfig, DEFAULT_POLICY_CONFIG

__all__ = [
    "PolicyGuard",
    "PolicyEvaluator",
    "PolicyConfig",
    "DEFAULT_POLICY_CONFIG",
]
