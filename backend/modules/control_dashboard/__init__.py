"""
Control Dashboard Module

PHASE 40 — Real-Time Control Dashboard

Trading cockpit for system control and monitoring.

Components:
- Dashboard State Engine (aggregates system state)
- Approval Queue Engine (decision support workflow)
- Alerts Engine (system alerts)
- Audit Engine (action logging)

Modes:
- PAPER: Simulated execution for testing
- APPROVAL: Human approval required (Decision Support)
- LIVE: Real execution with safeguards
"""

from .dashboard_types import (
    DashboardState,
    MarketOverview,
    HypothesisState,
    PortfolioState,
    RiskState,
    PnLState,
    ExecutionState,
    PositionSummary,
    OrderSummary,
    FillSummary,
    PendingExecution,
    ApprovalAction,
    ApprovalResult,
    DashboardAlert,
    DashboardAuditLog,
    DashboardConfig,
    MultiSymbolDashboard,
)

from .dashboard_engine import (
    DashboardStateEngine,
    get_dashboard_engine,
)

from .approval_engine import (
    ApprovalQueueEngine,
    get_approval_engine,
)

from .alerts_engine import (
    AlertsEngine,
    get_alerts_engine,
)

from .audit_engine import (
    AuditEngine,
    get_audit_engine,
)

from .dashboard_routes import router as dashboard_router

__all__ = [
    # Types
    "DashboardState",
    "MarketOverview",
    "HypothesisState",
    "PortfolioState",
    "RiskState",
    "PnLState",
    "ExecutionState",
    "PositionSummary",
    "OrderSummary",
    "FillSummary",
    "PendingExecution",
    "ApprovalAction",
    "ApprovalResult",
    "DashboardAlert",
    "DashboardAuditLog",
    "DashboardConfig",
    "MultiSymbolDashboard",
    # Engines
    "DashboardStateEngine",
    "get_dashboard_engine",
    "ApprovalQueueEngine",
    "get_approval_engine",
    "AlertsEngine",
    "get_alerts_engine",
    "AuditEngine",
    "get_audit_engine",
    # Router
    "dashboard_router",
]
