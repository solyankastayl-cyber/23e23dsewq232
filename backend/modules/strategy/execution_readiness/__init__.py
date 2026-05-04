"""
Execution Readiness Module
===========================

Phase 2.9: Execution gate based on system health.

Architecture:
  Observability → Readiness → Execution

States:
  - READY: Full execution allowed
  - LIMITED: Restricted execution (majors only, reduced positions)
  - BLOCKED: Execution prohibited

Components:
  - readiness_rules: State determination logic
  - execution_readiness_service: Core service
  - readiness_storage: Decision logging (optional)
"""

from .execution_readiness_service import (
    ExecutionReadinessService,
    get_execution_readiness_service
)
from .readiness_rules import ReadinessRules, ReadinessState

__all__ = [
    "ExecutionReadinessService",
    "get_execution_readiness_service",
    "ReadinessRules",
    "ReadinessState",
]
