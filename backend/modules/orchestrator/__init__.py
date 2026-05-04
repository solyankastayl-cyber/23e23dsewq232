"""
Orchestrator Module
===================

Pre-execution orchestration layer (ORCH-1 + ORCH-2 + ORCH-3).
"""

from .final_gate import FinalGate, get_final_gate
from .execution import (
    ExecutionController,
    ExecutionIntent,
    RoutingResult
)
from .integration import (
    OverrideRegistry,
    get_override_registry,
    OrchestratorIntegrationEngine,
    get_integration_engine
)

__all__ = [
    "FinalGate",
    "get_final_gate",
    "ExecutionController",
    "ExecutionIntent",
    "RoutingResult",
    "OverrideRegistry",
    "get_override_registry",
    "OrchestratorIntegrationEngine",
    "get_integration_engine",
]
