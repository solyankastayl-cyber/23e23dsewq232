"""
Strategy Diagnostics Module (STR4)
===================================

Observability layer for Strategy System.

Components:
- diagnostics_types: Type definitions
- health_analyzer: Strategy health evaluation
- performance_aggregator: Performance metrics
- risk_aggregator: Risk metrics
- diagnostics_service: Main service
- diagnostics_routes: API endpoints
"""

from .diagnostics_types import (
    HealthStatus,
    WarningType,
    StrategyState,
    StrategyHealthState,
    PerformanceSummary,
    RiskSummary,
    StrategyDiagnosticsSnapshot,
    StrategyWarning,
    SwitchTrace
)

from .health_analyzer import (
    HealthAnalyzer,
    health_analyzer
)

from .performance_aggregator import (
    PerformanceAggregator,
    performance_aggregator
)

from .risk_aggregator import (
    RiskAggregator,
    risk_aggregator
)

from .diagnostics_service import (
    StrategyDiagnosticsService,
    strategy_diagnostics_service
)

__all__ = [
    # Types
    "HealthStatus",
    "WarningType",
    "StrategyState",
    "StrategyHealthState",
    "PerformanceSummary",
    "RiskSummary",
    "StrategyDiagnosticsSnapshot",
    "StrategyWarning",
    "SwitchTrace",
    # Analyzers
    "HealthAnalyzer",
    "health_analyzer",
    "PerformanceAggregator",
    "performance_aggregator",
    "RiskAggregator",
    "risk_aggregator",
    # Service
    "StrategyDiagnosticsService",
    "strategy_diagnostics_service"
]
