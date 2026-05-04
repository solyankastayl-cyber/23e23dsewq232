"""
Trading Terminal - Portfolio Module (TR2)
=========================================

Unified Portfolio Monitor - aggregates data from all exchanges.

Components:
- portfolio_types: Type definitions
- portfolio_aggregator: Data aggregation
- portfolio_service: Main service
- portfolio_routes: API endpoints
"""

from .portfolio_types import (
    UnifiedPortfolioState,
    PortfolioBalance,
    PortfolioPosition,
    PortfolioMetrics,
    ExposureBreakdown,
    PortfolioSnapshot
)

from .portfolio_aggregator import (
    PortfolioAggregator,
    portfolio_aggregator
)

from .portfolio_service import (
    PortfolioService,
    portfolio_service
)

__all__ = [
    # Types
    "UnifiedPortfolioState",
    "PortfolioBalance",
    "PortfolioPosition",
    "PortfolioMetrics",
    "ExposureBreakdown",
    "PortfolioSnapshot",
    # Services
    "PortfolioAggregator",
    "portfolio_aggregator",
    "PortfolioService",
    "portfolio_service"
]
