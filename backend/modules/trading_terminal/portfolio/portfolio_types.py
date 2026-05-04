"""
Portfolio Types (TR2)
=====================

Type definitions for Unified Portfolio Monitor.

Key entities:
- UnifiedPortfolioState: Aggregated portfolio state
- PortfolioBalance: System-wide balance
- PortfolioPosition: Aggregated position
- PortfolioMetrics: Performance metrics
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid


# ===========================================
# PortfolioBalance
# ===========================================

@dataclass
class PortfolioBalance:
    """
    Aggregated balance across all exchanges.
    """
    asset: str = ""
    
    # Totals across all exchanges
    total_amount: float = 0.0
    total_free: float = 0.0
    total_locked: float = 0.0
    
    # USD value
    usd_value: float = 0.0
    
    # Per-exchange breakdown
    by_exchange: Dict[str, float] = field(default_factory=dict)
    
    # Portfolio weight
    weight_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset": self.asset,
            "total_amount": round(self.total_amount, 8),
            "total_free": round(self.total_free, 8),
            "total_locked": round(self.total_locked, 8),
            "usd_value": round(self.usd_value, 2),
            "by_exchange": {k: round(v, 8) for k, v in self.by_exchange.items()},
            "weight_pct": round(self.weight_pct, 4)
        }


# ===========================================
# PortfolioPosition
# ===========================================

@dataclass
class PortfolioPosition:
    """
    Position aggregated from an exchange.
    """
    position_id: str = field(default_factory=lambda: f"pos_{uuid.uuid4().hex[:6]}")
    
    # Identity
    symbol: str = ""
    exchange: str = ""
    connection_id: str = ""
    
    # Position details
    side: str = "LONG"  # LONG / SHORT
    size: float = 0.0
    entry_price: float = 0.0
    mark_price: float = 0.0
    
    # PnL
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    # Risk
    leverage: float = 1.0
    margin_type: str = "CROSS"
    liquidation_price: float = 0.0
    
    # Notional
    notional_value: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "connection_id": self.connection_id,
            "side": self.side,
            "size": round(self.size, 8),
            "entry_price": round(self.entry_price, 8),
            "mark_price": round(self.mark_price, 8),
            "unrealized_pnl": round(self.unrealized_pnl, 4),
            "unrealized_pnl_pct": round(self.unrealized_pnl_pct, 4),
            "leverage": round(self.leverage, 1),
            "margin_type": self.margin_type,
            "liquidation_price": round(self.liquidation_price, 2),
            "notional_value": round(self.notional_value, 2)
        }


# ===========================================
# ExposureBreakdown
# ===========================================

@dataclass
class ExposureBreakdown:
    """
    Exposure analysis by asset/category.
    """
    # By asset
    by_asset: Dict[str, float] = field(default_factory=dict)
    
    # By category (STABLECOIN, BTC, ETH, ALTCOIN)
    by_category: Dict[str, float] = field(default_factory=dict)
    
    # By exchange
    by_exchange: Dict[str, float] = field(default_factory=dict)
    
    # Concentration
    max_asset_weight: float = 0.0
    max_asset: str = ""
    
    # Long/Short
    long_exposure: float = 0.0
    short_exposure: float = 0.0
    net_exposure: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "by_asset": {k: round(v, 4) for k, v in self.by_asset.items()},
            "by_category": {k: round(v, 4) for k, v in self.by_category.items()},
            "by_exchange": {k: round(v, 4) for k, v in self.by_exchange.items()},
            "concentration": {
                "max_asset": self.max_asset,
                "max_weight": round(self.max_asset_weight, 4)
            },
            "directional": {
                "long_exposure": round(self.long_exposure, 4),
                "short_exposure": round(self.short_exposure, 4),
                "net_exposure": round(self.net_exposure, 4)
            }
        }


# ===========================================
# PortfolioMetrics
# ===========================================

@dataclass
class PortfolioMetrics:
    """
    Portfolio performance metrics.
    """
    # PnL
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    weekly_pnl: float = 0.0
    weekly_pnl_pct: float = 0.0
    total_realized_pnl: float = 0.0
    total_unrealized_pnl: float = 0.0
    
    # Leverage
    portfolio_leverage: float = 1.0
    max_leverage: float = 1.0
    
    # Risk
    portfolio_var_95: Optional[float] = None
    portfolio_cvar_95: Optional[float] = None
    
    # Performance
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pnl": {
                "daily": round(self.daily_pnl, 2),
                "daily_pct": round(self.daily_pnl_pct, 4),
                "weekly": round(self.weekly_pnl, 2),
                "weekly_pct": round(self.weekly_pnl_pct, 4),
                "total_realized": round(self.total_realized_pnl, 2),
                "total_unrealized": round(self.total_unrealized_pnl, 2)
            },
            "leverage": {
                "current": round(self.portfolio_leverage, 2),
                "max": round(self.max_leverage, 2)
            },
            "risk": {
                "var_95": round(self.portfolio_var_95, 4) if self.portfolio_var_95 else None,
                "cvar_95": round(self.portfolio_cvar_95, 4) if self.portfolio_cvar_95 else None
            },
            "performance": {
                "sharpe_ratio": round(self.sharpe_ratio, 2) if self.sharpe_ratio else None,
                "sortino_ratio": round(self.sortino_ratio, 2) if self.sortino_ratio else None
            }
        }


# ===========================================
# UnifiedPortfolioState
# ===========================================

@dataclass
class UnifiedPortfolioState:
    """
    Complete aggregated portfolio state.
    
    This is the main entity - shows unified view across all exchanges.
    """
    portfolio_id: str = field(default_factory=lambda: f"pf_{uuid.uuid4().hex[:8]}")
    
    # Equity
    total_equity: float = 0.0
    available_margin: float = 0.0
    used_margin: float = 0.0
    
    # Balances
    balances: List[PortfolioBalance] = field(default_factory=list)
    total_balance_usd: float = 0.0
    
    # Positions
    positions: List[PortfolioPosition] = field(default_factory=list)
    positions_count: int = 0
    
    # Exposure
    exposure: ExposureBreakdown = field(default_factory=ExposureBreakdown)
    
    # Metrics
    metrics: PortfolioMetrics = field(default_factory=PortfolioMetrics)
    
    # Source info
    exchanges_connected: List[str] = field(default_factory=list)
    accounts_count: int = 0
    
    # Timestamp
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "equity": {
                "total": round(self.total_equity, 2),
                "available_margin": round(self.available_margin, 2),
                "used_margin": round(self.used_margin, 2)
            },
            "balances": [b.to_dict() for b in self.balances],
            "total_balance_usd": round(self.total_balance_usd, 2),
            "positions": [p.to_dict() for p in self.positions],
            "positions_count": self.positions_count,
            "exposure": self.exposure.to_dict(),
            "metrics": self.metrics.to_dict(),
            "sources": {
                "exchanges": self.exchanges_connected,
                "accounts_count": self.accounts_count
            },
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_dashboard_dict(self) -> Dict[str, Any]:
        """Compact dashboard format"""
        return {
            "equity": round(self.total_equity, 2),
            "dailyPnl": round(self.metrics.daily_pnl, 2),
            "dailyPnlPct": round(self.metrics.daily_pnl_pct, 4),
            "unrealizedPnl": round(self.metrics.total_unrealized_pnl, 2),
            "positionsCount": self.positions_count,
            "exposure": {
                "long": round(self.exposure.long_exposure, 4),
                "short": round(self.exposure.short_exposure, 4),
                "net": round(self.exposure.net_exposure, 4)
            },
            "leverage": round(self.metrics.portfolio_leverage, 2),
            "exchangesConnected": len(self.exchanges_connected),
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None
        }


# ===========================================
# PortfolioSnapshot
# ===========================================

@dataclass
class PortfolioSnapshot:
    """
    Point-in-time snapshot for history.
    """
    snapshot_id: str = field(default_factory=lambda: f"snap_{uuid.uuid4().hex[:8]}")
    
    equity: float = 0.0
    total_pnl: float = 0.0
    positions_count: int = 0
    net_exposure: float = 0.0
    leverage: float = 1.0
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "equity": round(self.equity, 2),
            "total_pnl": round(self.total_pnl, 2),
            "positions_count": self.positions_count,
            "net_exposure": round(self.net_exposure, 4),
            "leverage": round(self.leverage, 2),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
