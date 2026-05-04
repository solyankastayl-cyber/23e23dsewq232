"""
Account Types (TR1)
===================

Type definitions for Account/Key Manager.

Entities:
- ExchangeConnection: Exchange API connection
- AccountState: Account balances/positions
- AccountHealthCheck: Health status
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# Enums
# ===========================================

class ExchangeType(Enum):
    """Supported exchanges"""
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"
    HYPERLIQUID = "HYPERLIQUID"
    COINBASE = "COINBASE"
    OKX = "OKX"
    MOCK = "MOCK"  # For testing


class ConnectionStatus(Enum):
    """Connection status"""
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ERROR = "ERROR"
    VALIDATING = "VALIDATING"


class AccountHealthStatus(Enum):
    """Account health levels"""
    HEALTHY = 1
    WARNING = 2
    DEGRADED = 3
    ERROR = 4


class Permission(Enum):
    """API key permissions"""
    READ = "READ"
    SPOT_TRADE = "SPOT_TRADE"
    FUTURES_TRADE = "FUTURES_TRADE"
    WITHDRAW = "WITHDRAW"
    MARGIN = "MARGIN"


# ===========================================
# AccountBalance
# ===========================================

@dataclass
class AccountBalance:
    """Single asset balance"""
    asset: str = ""
    free: float = 0.0
    locked: float = 0.0
    total: float = 0.0
    usd_value: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset": self.asset,
            "free": round(self.free, 8),
            "locked": round(self.locked, 8),
            "total": round(self.total, 8),
            "usd_value": round(self.usd_value, 2)
        }


# ===========================================
# AccountPosition
# ===========================================

@dataclass
class AccountPosition:
    """Open position"""
    symbol: str = ""
    side: str = "LONG"  # LONG / SHORT
    size: float = 0.0
    entry_price: float = 0.0
    mark_price: float = 0.0
    unrealized_pnl: float = 0.0
    leverage: float = 1.0
    margin_type: str = "CROSS"  # CROSS / ISOLATED
    liquidation_price: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "size": round(self.size, 8),
            "entry_price": round(self.entry_price, 8),
            "mark_price": round(self.mark_price, 8),
            "unrealized_pnl": round(self.unrealized_pnl, 4),
            "leverage": round(self.leverage, 1),
            "margin_type": self.margin_type,
            "liquidation_price": round(self.liquidation_price, 2)
        }


# ===========================================
# ExchangeConnection
# ===========================================

@dataclass
class ExchangeConnection:
    """
    Exchange API connection configuration.
    
    Stores credentials and connection state.
    """
    connection_id: str = field(default_factory=lambda: f"conn_{uuid.uuid4().hex[:8]}")
    
    # Exchange info
    exchange: ExchangeType = ExchangeType.MOCK
    label: str = ""
    description: str = ""
    
    # Credentials (encrypted in storage)
    api_key: str = ""
    api_secret: str = ""
    passphrase: str = ""  # For some exchanges
    
    # Permissions detected
    permissions: List[str] = field(default_factory=list)
    
    # Status
    status: ConnectionStatus = ConnectionStatus.DISABLED
    last_error: str = ""
    
    # Trading settings
    is_testnet: bool = False
    default_leverage: float = 1.0
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_validated_at: Optional[datetime] = None
    created_by: str = "admin"
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        result = {
            "connection_id": self.connection_id,
            "exchange": self.exchange.value,
            "label": self.label,
            "description": self.description,
            "permissions": self.permissions,
            "status": self.status.value,
            "last_error": self.last_error,
            "is_testnet": self.is_testnet,
            "default_leverage": self.default_leverage,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_validated_at": self.last_validated_at.isoformat() if self.last_validated_at else None,
            "created_by": self.created_by
        }
        
        if include_secrets:
            result["api_key"] = self.api_key
            result["api_secret"] = "***" if self.api_secret else ""
        else:
            result["api_key"] = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "***"
        
        return result
    
    def to_storage_dict(self) -> Dict[str, Any]:
        """For MongoDB storage"""
        return {
            "connection_id": self.connection_id,
            "exchange": self.exchange.value,
            "label": self.label,
            "description": self.description,
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "passphrase": self.passphrase,
            "permissions": self.permissions,
            "status": self.status.value,
            "last_error": self.last_error,
            "is_testnet": self.is_testnet,
            "default_leverage": self.default_leverage,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_validated_at": self.last_validated_at,
            "created_by": self.created_by
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ExchangeConnection":
        return ExchangeConnection(
            connection_id=data.get("connection_id", ""),
            exchange=ExchangeType(data.get("exchange", "MOCK")),
            label=data.get("label", ""),
            description=data.get("description", ""),
            api_key=data.get("api_key", ""),
            api_secret=data.get("api_secret", ""),
            passphrase=data.get("passphrase", ""),
            permissions=data.get("permissions", []),
            status=ConnectionStatus(data.get("status", "DISABLED")),
            last_error=data.get("last_error", ""),
            is_testnet=data.get("is_testnet", False),
            default_leverage=data.get("default_leverage", 1.0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_validated_at=data.get("last_validated_at"),
            created_by=data.get("created_by", "admin")
        )


# ===========================================
# AccountState
# ===========================================

@dataclass
class AccountState:
    """
    Current account state from exchange.
    
    Contains balances, positions, equity.
    """
    connection_id: str = ""
    exchange: str = ""
    
    # Balances
    balances: List[AccountBalance] = field(default_factory=list)
    total_balance_usd: float = 0.0
    
    # Positions
    positions: List[AccountPosition] = field(default_factory=list)
    total_unrealized_pnl: float = 0.0
    
    # Equity
    equity: float = 0.0
    available_margin: float = 0.0
    used_margin: float = 0.0
    
    # Metadata
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "exchange": self.exchange,
            "balances": [b.to_dict() for b in self.balances],
            "total_balance_usd": round(self.total_balance_usd, 2),
            "positions": [p.to_dict() for p in self.positions],
            "total_unrealized_pnl": round(self.total_unrealized_pnl, 4),
            "equity": round(self.equity, 2),
            "available_margin": round(self.available_margin, 2),
            "used_margin": round(self.used_margin, 2),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# ===========================================
# AccountHealthCheck
# ===========================================

@dataclass
class AccountHealthCheck:
    """
    Health check result for an account.
    """
    connection_id: str = ""
    
    status: AccountHealthStatus = AccountHealthStatus.HEALTHY
    status_reason: str = ""
    
    # Checks
    auth_check: bool = True
    balance_check: bool = True
    permission_check: bool = True
    
    # Performance
    latency_ms: float = 0.0
    
    # Warnings
    warnings: List[str] = field(default_factory=list)
    
    # Timestamp
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "status": self.status.name,
            "status_reason": self.status_reason,
            "checks": {
                "auth": self.auth_check,
                "balance": self.balance_check,
                "permission": self.permission_check
            },
            "latency_ms": round(self.latency_ms, 2),
            "warnings": self.warnings,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None
        }
