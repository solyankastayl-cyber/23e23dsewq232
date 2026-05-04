"""
Trading Terminal - Accounts Module (TR1)
========================================

Account/Key Manager for exchange connections.

Components:
- account_types: Type definitions
- account_service: Main service
- account_health_service: Health monitoring
- account_validator: Key validation
- account_routes: API endpoints
"""

from .account_types import (
    ExchangeType,
    ConnectionStatus,
    AccountHealthStatus,
    ExchangeConnection,
    AccountState,
    AccountHealthCheck,
    AccountBalance,
    AccountPosition
)

from .account_service import (
    AccountService,
    account_service
)

from .account_health_service import (
    AccountHealthService,
    account_health_service
)

__all__ = [
    # Types
    "ExchangeType",
    "ConnectionStatus",
    "AccountHealthStatus",
    "ExchangeConnection",
    "AccountState",
    "AccountHealthCheck",
    "AccountBalance",
    "AccountPosition",
    # Services
    "AccountService",
    "account_service",
    "AccountHealthService",
    "account_health_service"
]
