"""
Decision Engine Module
======================

V2 Architecture:
  decision = f(mtf_context, structure_context, primary_pattern)

Priority weights:
  MTF Context        45%
  Structure Context  35%
  Pattern Evidence   20%
"""

from .decision_engine import (
    compute_final_bias,
    compute_alignment,
    detect_market_state,
    build_decision,
    decision_engine
)

# V2 — New Decision Layer (Structure-First)
from .decision_engine_v2 import (
    DecisionEngineV2,
    get_decision_engine_v2,
    decision_engine_v2
)

__all__ = [
    # V1 (legacy compatibility)
    "compute_final_bias",
    "compute_alignment", 
    "detect_market_state",
    "build_decision",
    "decision_engine",
    # V2 (new architecture)
    "DecisionEngineV2",
    "get_decision_engine_v2",
    "decision_engine_v2",
]
