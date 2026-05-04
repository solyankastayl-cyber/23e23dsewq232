"""
Step 12 — Decision Intelligence Layer.

Final analytical layer that converts:
    scenarios + engines + interaction + temporal_intelligence
into:
    primary scenario + decision confidence + risk + explanation

Hard rules (locked):
  * Does NOT mutate scenarios, engines, calibration, temporal context.
  * Does NOT call ML, does NOT use random, does NOT hit MetaBrain or trading.
  * Pure, deterministic, read-only observer.
  * On empty / missing inputs → primary="none", confidence=0, strength="no_edge".
"""
from __future__ import annotations

from .decision_builder import build_decision_intelligence
from .types import DecisionIntelligenceContext

__all__ = ["build_decision_intelligence", "DecisionIntelligenceContext"]
