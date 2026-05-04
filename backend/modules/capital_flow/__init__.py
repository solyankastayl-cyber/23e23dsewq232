"""
Capital Flow Module

PHASE 42 — Capital Flow Engine
PHASE 42.4 — Capital Flow Integration

Inter-asset capital rotation intelligence layer.

Buckets: BTC, ETH, ALTS, CASH

Components:
- 42.1 Flow Snapshot Engine
- 42.2 Rotation Detection Engine
- 42.3 Flow Scoring Engine
- 42.4 Capital Flow Integration (Hypothesis/Portfolio/Simulation)
"""

from .flow_types import (
    FlowBucket,
    FlowState,
    FlowBias,
    RotationType,
    CapitalFlowSnapshot,
    RotationState,
    FlowScore,
    CapitalFlowResult,
    CapitalFlowConfig,
)

from .flow_snapshot_engine import FlowSnapshotEngine
from .flow_rotation_engine import RotationDetectionEngine
from .flow_scoring_engine import FlowScoringEngine
from .flow_registry import FlowRegistry, get_flow_registry
from .flow_integration import CapitalFlowIntegration, get_capital_flow_integration
from .flow_routes import router as capital_flow_router

__all__ = [
    "FlowBucket",
    "FlowState",
    "FlowBias",
    "RotationType",
    "CapitalFlowSnapshot",
    "RotationState",
    "FlowScore",
    "CapitalFlowResult",
    "CapitalFlowConfig",
    "FlowSnapshotEngine",
    "RotationDetectionEngine",
    "FlowScoringEngine",
    "FlowRegistry",
    "get_flow_registry",
    "CapitalFlowIntegration",
    "get_capital_flow_integration",
    "capital_flow_router",
]
