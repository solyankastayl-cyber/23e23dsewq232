"""
Paper Execution Bridge
======================

Phase 3.0A: Controlled bridge from discovery to paper execution.

Architecture:
  Discovery (selected_signals) 
    → Readiness Gate 
    → Policy Filter 
    → Paper Decisions 
    → Paper Positions 
    → Paper Outcomes

Critical principles:
  1. Readiness-first (BLOCKED → no execution)
  2. Paper-only (no real exchange)
  3. Isolated (baseline untouched)
  4. Deduplicated (snapshot_id + symbol)
  5. Audited (every decision logged)

Components:
  - paper_decision_repository: CRUD for paper_decisions
  - paper_position_repository: CRUD for paper_positions
  - paper_execution_policy: Readiness-based filtering
  - paper_bridge_service: Core execution logic
  - paper_close_worker: Background position closer
"""

from .paper_bridge_service import PaperBridgeService, get_paper_bridge_service
from .paper_execution_policy import PaperExecutionPolicy
from .paper_close_worker import PaperCloseWorker, get_paper_close_worker

__all__ = [
    "PaperBridgeService",
    "get_paper_bridge_service",
    "PaperExecutionPolicy",
    "PaperCloseWorker",
    "get_paper_close_worker",
]
