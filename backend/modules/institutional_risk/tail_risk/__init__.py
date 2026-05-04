"""
PHASE 22.2 — Tail Risk Engine Module
====================================
Tail Risk Engine for Institutional Risk Fabric.

Components:
- tail_risk_types: Type definitions
- tail_severity_engine: Tail loss severity and asymmetry
- crash_sensitivity_engine: Crash sensitivity calculation
- tail_concentration_engine: Tail concentration measurement
- tail_risk_aggregator: Main aggregator
- tail_risk_routes: API endpoints
"""

from modules.institutional_risk.tail_risk.tail_risk_types import (
    TailRiskState,
    TailRiskHistoryEntry,
    TailRiskLevel,
    TailRecommendedAction,
    TAIL_RISK_THRESHOLDS,
    CRASH_VOLATILITY_MULTIPLIERS,
    CRASH_CONCENTRATION_MULTIPLIERS,
    TAIL_RISK_MODIFIERS,
    TAIL_RISK_WEIGHTS,
)

from modules.institutional_risk.tail_risk.tail_risk_aggregator import (
    TailRiskAggregator,
    get_tail_risk_aggregator,
)

from modules.institutional_risk.tail_risk.tail_severity_engine import (
    TailSeverityEngine,
    get_tail_severity_engine,
)

from modules.institutional_risk.tail_risk.crash_sensitivity_engine import (
    CrashSensitivityEngine,
    get_crash_sensitivity_engine,
)

from modules.institutional_risk.tail_risk.tail_concentration_engine import (
    TailConcentrationEngine,
    get_tail_concentration_engine,
)

__all__ = [
    # Types
    "TailRiskState",
    "TailRiskHistoryEntry",
    "TailRiskLevel",
    "TailRecommendedAction",
    "TAIL_RISK_THRESHOLDS",
    "CRASH_VOLATILITY_MULTIPLIERS",
    "CRASH_CONCENTRATION_MULTIPLIERS",
    "TAIL_RISK_MODIFIERS",
    "TAIL_RISK_WEIGHTS",
    # Aggregator
    "TailRiskAggregator",
    "get_tail_risk_aggregator",
    # Sub-engines
    "TailSeverityEngine",
    "get_tail_severity_engine",
    "CrashSensitivityEngine",
    "get_crash_sensitivity_engine",
    "TailConcentrationEngine",
    "get_tail_concentration_engine",
]
