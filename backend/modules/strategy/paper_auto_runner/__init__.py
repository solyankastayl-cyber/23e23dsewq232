"""
Paper Auto Runner Module
=========================

Phase 3.0B: Controlled Autonomy

Purpose:
  Enable automated paper execution with strict guards and safety limits.

Architecture:
  scheduler (10 min interval)
    → readiness check (must be READY)
    → execution quality check (must be > -0.002)
    → position limits check (max 3 open)
    → rate limiting (max 4 runs/hour)
    → if all guards pass → run_once()

Components:
  - auto_runner_state: State management (paused/resumed, counters, auto-disabled)
  - auto_runner_rules: Guard rules evaluation
  - paper_auto_runner: Main controlled loop
"""

from .auto_runner_state import AutoRunnerState
from .auto_runner_rules import AutoRunnerRules
from .paper_auto_runner import PaperAutoRunner

__all__ = [
    "AutoRunnerState",
    "AutoRunnerRules",
    "PaperAutoRunner",
]
