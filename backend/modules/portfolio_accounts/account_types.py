"""
Account Types - PHASE 5.4
=========================

Unified types for portfolio account management.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AccountStatus(str, Enum):
    """Account connection status"""
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    MAINTENANCE = "MAINTENANCE"


class AccountType(str, Enum):
    """Account type"""
    SPOT = "SPOT"
    MARGIN = "MARGIN"
    FUTURES = "FUTURES"
    UNIFIED = "UNIFIED"


class MarginMode(str, Enum):
    """Margin mode for positions"""
    CROSS = "CROSS"
    ISOLATED = "ISOLATED"


class PositionSide(str, Enum):
    """Position side"""
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"


# ============================================
# Core Portfolio Types
# ============================================

class PortfolioAccount(BaseModel):
    """Unified account representation"""
    exchange: str
    account_id: str
    status: AccountStatus = AccountStatus.DISCONNECTED
    account_type: AccountType = AccountType.UNIFIED
    equity: float = 0.0
    free_balance: float = 0.0
    used_margin: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    leverage: float = 1.0
    margin_ratio: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PortfolioBalance(BaseModel):
    """Unified balance representation"""
    exchange: str
    asset: str
    free: float = 0.0
    locked: float = 0.0
    total: float = 0.0
    usd_value: float = 0.0
    avg_price: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def locked_pct(self) -> float:
        if self.total > 0:
            return (self.locked / self.total) * 100
        return 0.0


class PortfolioPosition(BaseModel):
    """Unified position representation"""
    exchange: str
    symbol: str
    side: PositionSide
    size: float = 0.0
    entry_price: float = 0.0
    mark_price: float = 0.0
    liquidation_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    leverage: float = 1.0
    margin_mode: MarginMode = MarginMode.CROSS
    margin_used: float = 0.0
    notional_value: float = 0.0
    roe_pct: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def pnl_pct(self) -> float:
        if self.entry_price > 0 and self.size > 0:
            if self.side == PositionSide.LONG:
                return ((self.mark_price - self.entry_price) / self.entry_price) * 100
            else:
                return ((self.entry_price - self.mark_price) / self.entry_price) * 100
        return 0.0


class MarginInfo(BaseModel):
    """Margin information"""
    exchange: str
    total_margin: float = 0.0
    used_margin: float = 0.0
    free_margin: float = 0.0
    margin_ratio: float = 0.0
    margin_utilization: float = 0.0
    maintenance_margin: float = 0.0
    initial_margin: float = 0.0
    leverage_exposure: float = 0.0
    is_at_risk: bool = False
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExposureInfo(BaseModel):
    """Position exposure information"""
    symbol: str
    total_long_size: float = 0.0
    total_short_size: float = 0.0
    net_exposure: float = 0.0
    gross_exposure: float = 0.0
    long_notional: float = 0.0
    short_notional: float = 0.0
    net_notional: float = 0.0
    exchanges_long: List[str] = Field(default_factory=list)
    exchanges_short: List[str] = Field(default_factory=list)
    avg_long_entry: float = 0.0
    avg_short_entry: float = 0.0
    total_unrealized_pnl: float = 0.0


class PortfolioState(BaseModel):
    """Complete portfolio state snapshot"""
    total_equity: float = 0.0
    total_free_balance: float = 0.0
    total_used_margin: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    total_notional: float = 0.0
    exchange_count: int = 0
    positions_count: int = 0
    balances_count: int = 0
    long_positions_count: int = 0
    short_positions_count: int = 0
    margin_utilization: float = 0.0
    leverage_exposure: float = 0.0
    risk_level: str = "LOW"
    accounts: List[PortfolioAccount] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================
# Aggregation Types
# ============================================

class AggregatedBalance(BaseModel):
    """Balance aggregated across exchanges"""
    asset: str
    total_free: float = 0.0
    total_locked: float = 0.0
    total_amount: float = 0.0
    total_usd_value: float = 0.0
    exchange_breakdown: Dict[str, float] = Field(default_factory=dict)
    exchange_count: int = 0


class AggregatedPosition(BaseModel):
    """Position aggregated across exchanges"""
    symbol: str
    total_long_size: float = 0.0
    total_short_size: float = 0.0
    net_size: float = 0.0
    total_long_notional: float = 0.0
    total_short_notional: float = 0.0
    net_notional: float = 0.0
    avg_long_entry: float = 0.0
    avg_short_entry: float = 0.0
    total_unrealized_pnl: float = 0.0
    positions_by_exchange: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    exchange_count: int = 0


class PortfolioHistoryEntry(BaseModel):
    """Portfolio state history entry"""
    total_equity: float
    total_pnl: float
    positions_count: int
    timestamp: datetime


# ============================================
# Request/Response Models
# ============================================

class RefreshAccountsRequest(BaseModel):
    """Request to refresh account data"""
    exchanges: List[str] = Field(default_factory=lambda: ["BINANCE", "BYBIT", "OKX"])
    force: bool = False


class PortfolioFilterRequest(BaseModel):
    """Filter for portfolio queries"""
    exchanges: Optional[List[str]] = None
    assets: Optional[List[str]] = None
    symbols: Optional[List[str]] = None
    min_value: Optional[float] = None
