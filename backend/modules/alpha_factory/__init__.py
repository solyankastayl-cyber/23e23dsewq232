"""
AF1 - Alpha Factory Core
=========================
Self-improving layer that connects TT4 Forensics with Adaptive Layer.

Flow:
Trade outcomes → Forensics → Alpha Metrics → Edge Verdicts → Actions → Adaptive Apply

Components:
- AlphaMetricsEngine: Calculates metrics by scope (symbol, entry_mode)
- AlphaEvaluator: STRONG_EDGE / WEAK_EDGE / UNSTABLE_EDGE / NO_EDGE verdicts
- AlphaActionsEngine: Generates KEEP / REDUCE_RISK / DISABLE_SYMBOL / INCREASE_ALLOCATION
- AlphaFactoryEngine: Main orchestrator connecting all pieces
"""

from .alpha_routes import router

__all__ = ["router"]
