"""
Trading Terminal Module
=======================

Admin Trading Terminal backend.

Components:
- TR1: Account/Key Manager
- TR2: Portfolio Monitor
- TR3: Trade Monitor
"""

# TR1 - Account Manager
from .accounts import (
    account_service,
    account_health_service,
    ExchangeConnection,
    AccountState,
    AccountHealthCheck
)

# TR2 - Portfolio Monitor
from .portfolio import (
    portfolio_service,
    portfolio_aggregator,
    UnifiedPortfolioState,
    PortfolioBalance,
    PortfolioPosition
)

# TR3 - Trade Monitor
from .trades import (
    trade_service,
    order_service,
    trade_aggregator,
    Order,
    Fill,
    Trade
)

__all__ = [
    # TR1
    "account_service",
    "account_health_service",
    "ExchangeConnection",
    "AccountState",
    "AccountHealthCheck",
    # TR2
    "portfolio_service",
    "portfolio_aggregator",
    "UnifiedPortfolioState",
    "PortfolioBalance",
    "PortfolioPosition",
    # TR3
    "trade_service",
    "order_service",
    "trade_aggregator",
    "Order",
    "Fill",
    "Trade"
]
