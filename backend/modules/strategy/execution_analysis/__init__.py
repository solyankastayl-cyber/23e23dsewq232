"""
Execution Analysis Module
=========================

Phase 3.1: Execution Validation Layer

Purpose:
  Prove that execution layer does NOT corrupt decision quality.
  Compare shadow_trades (ideal) vs paper_positions (real execution).

Architecture:
  shadow_trades (discovery truth)
    ↕
  execution_comparator (matching + delta calculation)
    ↓
  execution_quality_service (metrics aggregation)
    ↓
  execution_quality_rules (gates + verdict)
    ↓
  API endpoint (decision support)

Components:
  - execution_comparator: Match shadow ↔ paper by snapshot_id
  - execution_quality_service: Aggregate metrics
  - execution_quality_rules: 6 gates + verdict
"""

from .execution_comparator import ExecutionComparator
from .execution_quality_service import ExecutionQualityService
from .execution_quality_rules import ExecutionQualityRules

__all__ = [
    "ExecutionComparator",
    "ExecutionQualityService",
    "ExecutionQualityRules",
]
