"""
System Control Module

PHASE 33 — System Control Layer

Top-level control layer for Market Intelligence OS.

Components:
- Decision Engine: Market state and strategy recommendations
- Risk Engine: Risk assessment and control
- Alert Engine: System alerts and notifications
- Cockpit State: Aggregated UI state
"""

from .decision_engine import (
    MarketDecisionEngine,
    get_decision_engine,
)

from .risk_engine import (
    RiskEngine,
    get_risk_engine,
)

from .alert_engine import (
    AlertEngine,
    get_alert_engine,
)

from .cockpit_state import (
    CockpitStateAggregator,
    get_cockpit_aggregator,
)

from .control_types import (
    MarketDecisionState,
    RiskState,
    Alert,
    CockpitState,
    ControlSummary,
    MARKET_STATES,
    RISK_LEVELS,
    ALERT_TYPES,
)

from .control_routes import router as control_router

__all__ = [
    "MarketDecisionEngine",
    "get_decision_engine",
    "RiskEngine",
    "get_risk_engine",
    "AlertEngine",
    "get_alert_engine",
    "CockpitStateAggregator",
    "get_cockpit_aggregator",
    "MarketDecisionState",
    "RiskState",
    "Alert",
    "CockpitState",
    "ControlSummary",
    "MARKET_STATES",
    "RISK_LEVELS",
    "ALERT_TYPES",
    "control_router",
]
