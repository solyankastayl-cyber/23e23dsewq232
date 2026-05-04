"""
PHASE 22.1 — Institutional Risk Module
=====================================
Institutional Risk Fabric.

Sub-modules:
- var_engine: VaR Engine (PHASE 22.1)
"""

from modules.institutional_risk.var_engine import (
    VaRState,
    RiskState,
    RecommendedAction,
    VaRAggregator,
    get_var_aggregator,
)

__all__ = [
    "VaRState",
    "RiskState",
    "RecommendedAction",
    "VaRAggregator",
    "get_var_aggregator",
]
