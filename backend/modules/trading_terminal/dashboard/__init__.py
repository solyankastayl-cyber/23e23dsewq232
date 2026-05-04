"""TR6 Unified Trading Dashboard Module"""

from .dashboard_types import (
    UnifiedDashboardState,
    DashboardWidget,
    AccountsWidget,
    PortfolioWidget,
    TradesWidget,
    RiskWidget,
    StrategyWidget,
    RegimeWidget,
    ConnectionsWidget,
    EventsWidget,
    SystemHealthStatus
)
from .dashboard_service import dashboard_service

__all__ = [
    'UnifiedDashboardState',
    'DashboardWidget',
    'AccountsWidget',
    'PortfolioWidget',
    'TradesWidget',
    'RiskWidget',
    'StrategyWidget',
    'RegimeWidget',
    'ConnectionsWidget',
    'EventsWidget',
    'SystemHealthStatus',
    'dashboard_service'
]
