"""
Exchange Sync Types

PHASE 43.2 — Order + Position Sync Engine

Types for exchange synchronization layer.
Exchange is the source of truth.

Sync tasks:
- positions sync (every 10-15 sec)
- balances sync
- open orders sync
- recent fills sync
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


class SyncStatus(str, Enum):
    """Sync status"""
    IDLE = "IDLE"
    SYNCING = "SYNCING"
    SYNCED = "SYNCED"
    ERROR = "ERROR"
    STALE = "STALE"


class SyncType(str, Enum):
    """Types of sync operations"""
    POSITIONS = "POSITIONS"
    BALANCES = "BALANCES"
    OPEN_ORDERS = "OPEN_ORDERS"
    RECENT_FILLS = "RECENT_FILLS"
    FULL = "FULL"


class ExchangePositionSync(BaseModel):
    """Synced position from exchange."""
    sync_id: str = Field(default_factory=lambda: f"pos_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    # Exchange info
    exchange: str
    symbol: str
    exchange_symbol: str
    
    # Position data
    side: str  # LONG, SHORT
    size: float  # In base asset
    size_usd: float  # In USD
    entry_price: float
    mark_price: float
    liquidation_price: Optional[float] = None
    
    # PnL
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    realized_pnl: float = 0.0
    
    # Margin
    leverage: int = 1
    margin_mode: str = "CROSS"
    margin_used: float = 0.0
    
    # Timestamps
    synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    exchange_update_time: Optional[datetime] = None


class ExchangeBalanceSync(BaseModel):
    """Synced balance from exchange."""
    sync_id: str = Field(default_factory=lambda: f"bal_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    exchange: str
    asset: str
    
    # Balances
    total: float
    available: float
    locked: float
    
    # USD value
    usd_value: Optional[float] = None
    
    synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExchangeOrderSync(BaseModel):
    """Synced order from exchange."""
    sync_id: str = Field(default_factory=lambda: f"ord_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    exchange: str
    exchange_order_id: str
    client_order_id: Optional[str] = None
    
    symbol: str
    side: str  # BUY, SELL
    order_type: str  # MARKET, LIMIT, etc.
    status: str
    
    # Sizes
    original_size: float
    filled_size: float
    remaining_size: float
    
    # Prices
    price: Optional[float] = None
    avg_fill_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExchangeFillSync(BaseModel):
    """Synced fill/trade from exchange."""
    sync_id: str = Field(default_factory=lambda: f"fill_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    exchange: str
    trade_id: str
    order_id: str
    
    symbol: str
    side: str
    
    # Fill details
    size: float
    price: float
    value: float
    fee: float
    fee_asset: str
    
    # Timestamps
    filled_at: datetime
    synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SyncState(BaseModel):
    """Overall sync state for an exchange."""
    exchange: str
    
    # Status per type
    positions_status: SyncStatus = SyncStatus.IDLE
    balances_status: SyncStatus = SyncStatus.IDLE
    orders_status: SyncStatus = SyncStatus.IDLE
    fills_status: SyncStatus = SyncStatus.IDLE
    
    # Last sync times
    positions_last_sync: Optional[datetime] = None
    balances_last_sync: Optional[datetime] = None
    orders_last_sync: Optional[datetime] = None
    fills_last_sync: Optional[datetime] = None
    
    # Counts
    positions_count: int = 0
    balances_count: int = 0
    open_orders_count: int = 0
    recent_fills_count: int = 0
    
    # Errors
    last_error: Optional[str] = None
    error_count: int = 0
    
    # Config
    sync_interval_seconds: int = 15
    stale_threshold_seconds: int = 60
    
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SyncConfig(BaseModel):
    """Sync engine configuration."""
    # Sync intervals
    positions_interval_seconds: int = 15
    balances_interval_seconds: int = 30
    orders_interval_seconds: int = 10
    fills_interval_seconds: int = 60
    
    # Stale thresholds
    stale_threshold_seconds: int = 60
    
    # Retry
    max_retries: int = 3
    retry_delay_seconds: int = 5
    
    # Exchanges to sync
    enabled_exchanges: List[str] = Field(default_factory=lambda: ["BINANCE", "BYBIT"])
    
    # MongoDB persistence
    persist_to_db: bool = True
    
    # Auto-start
    auto_start: bool = True
