"""
TR6 Dashboard Types
===================

Data structures for unified trading dashboard.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time
import uuid


class SystemHealthStatus(str, Enum):
    """System-wide health status"""
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


@dataclass
class AccountsWidget:
    """
    Dashboard widget for accounts summary.
    """
    connected_exchanges: int = 0
    healthy: int = 0
    degraded: int = 0
    quarantined: int = 0
    
    total_equity: float = 0.0
    total_balance: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "connectedExchanges": self.connected_exchanges,
            "healthy": self.healthy,
            "degraded": self.degraded,
            "quarantined": self.quarantined,
            "totalEquity": round(self.total_equity, 2),
            "totalBalance": round(self.total_balance, 2)
        }


@dataclass
class PortfolioWidget:
    """
    Dashboard widget for portfolio summary.
    """
    total_equity: float = 0.0
    used_margin: float = 0.0
    free_margin: float = 0.0
    
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    
    exposure_usd: float = 0.0
    exposure_pct: float = 0.0
    
    open_positions: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "totalEquity": round(self.total_equity, 2),
            "usedMargin": round(self.used_margin, 2),
            "freeMargin": round(self.free_margin, 2),
            "pnl": {
                "unrealized": round(self.unrealized_pnl, 2),
                "realized": round(self.realized_pnl, 2),
                "total": round(self.total_pnl, 2),
                "daily": round(self.daily_pnl, 2),
                "dailyPct": round(self.daily_pnl_pct, 4)
            },
            "exposure": {
                "usd": round(self.exposure_usd, 2),
                "pct": round(self.exposure_pct, 4)
            },
            "openPositions": self.open_positions
        }


@dataclass
class TradesWidget:
    """
    Dashboard widget for trades summary.
    """
    recent_orders: int = 0
    recent_fills: int = 0
    recent_closed: int = 0
    
    trades_today: int = 0
    trades_week: int = 0
    
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_trade_pnl: float = 0.0
    
    last_trade_at: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "recentOrders": self.recent_orders,
            "recentFills": self.recent_fills,
            "recentClosed": self.recent_closed,
            "tradesToday": self.trades_today,
            "tradesWeek": self.trades_week,
            "performance": {
                "winRate": round(self.win_rate, 4),
                "profitFactor": round(self.profit_factor, 4),
                "avgTradePnl": round(self.avg_trade_pnl, 2)
            },
            "lastTradeAt": self.last_trade_at
        }


@dataclass
class RiskWidget:
    """
    Dashboard widget for risk summary.
    """
    risk_level: str = "MODERATE"  # LOW, MODERATE, HIGH, CRITICAL
    risk_score: float = 0.0
    
    drawdown_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    
    daily_loss_pct: float = 0.0
    daily_loss_limit_pct: float = 0.0
    daily_limit_used_pct: float = 0.0
    
    leverage: float = 0.0
    max_concentration_pct: float = 0.0
    
    var_95: float = 0.0
    cvar_95: float = 0.0
    
    active_alerts: int = 0
    critical_alerts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "riskLevel": self.risk_level,
            "riskScore": round(self.risk_score, 4),
            "drawdown": {
                "current": round(self.drawdown_pct, 4),
                "max": round(self.max_drawdown_pct, 4)
            },
            "dailyLoss": {
                "current": round(self.daily_loss_pct, 4),
                "limit": round(self.daily_loss_limit_pct, 4),
                "limitUsedPct": round(self.daily_limit_used_pct, 4)
            },
            "leverage": round(self.leverage, 2),
            "maxConcentrationPct": round(self.max_concentration_pct, 4),
            "var95": round(self.var_95, 4),
            "cvar95": round(self.cvar_95, 4),
            "alerts": {
                "active": self.active_alerts,
                "critical": self.critical_alerts
            }
        }


@dataclass
class StrategyWidget:
    """
    Dashboard widget for strategy summary.
    """
    active_profile: str = ""
    active_config: str = ""
    selected_strategy: str = ""
    
    strategy_health: str = "HEALTHY"  # HEALTHY, WARNING, DEGRADED
    
    trading_paused: bool = False
    kill_switch_active: bool = False
    
    recent_switches: int = 0
    active_overrides: List[str] = field(default_factory=list)
    
    strategies_available: int = 0
    strategies_active: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "activeProfile": self.active_profile,
            "activeConfig": self.active_config,
            "selectedStrategy": self.selected_strategy,
            "health": self.strategy_health,
            "controls": {
                "tradingPaused": self.trading_paused,
                "killSwitchActive": self.kill_switch_active
            },
            "recentSwitches": self.recent_switches,
            "activeOverrides": self.active_overrides,
            "strategies": {
                "available": self.strategies_available,
                "active": self.strategies_active
            }
        }


@dataclass
class RegimeWidget:
    """
    Dashboard widget for market regime.
    """
    current_regime: str = ""
    regime_confidence: float = 0.0
    regime_stability: float = 0.0
    transition_risk: float = 0.0
    
    previous_regime: str = ""
    regime_duration_hours: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current": self.current_regime,
            "confidence": round(self.regime_confidence, 4),
            "stability": round(self.regime_stability, 4),
            "transitionRisk": round(self.transition_risk, 4),
            "previousRegime": self.previous_regime,
            "durationHours": round(self.regime_duration_hours, 1)
        }


@dataclass
class ReconciliationWidget:
    """
    Dashboard widget for reconciliation status.
    """
    status: str = "OK"  # OK, WARNING, MISMATCH, ERROR
    last_check_at: Optional[int] = None
    
    mismatch_count: int = 0
    critical_mismatches: int = 0
    
    frozen_symbols: List[str] = field(default_factory=list)
    quarantined_exchanges: List[str] = field(default_factory=list)
    
    position_synced: bool = True
    balance_synced: bool = True
    orders_synced: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "lastCheckAt": self.last_check_at,
            "mismatches": {
                "total": self.mismatch_count,
                "critical": self.critical_mismatches
            },
            "frozenSymbols": self.frozen_symbols,
            "quarantinedExchanges": self.quarantined_exchanges,
            "synced": {
                "positions": self.position_synced,
                "balances": self.balance_synced,
                "orders": self.orders_synced
            }
        }


@dataclass
class ConnectionsWidget:
    """
    Dashboard widget for connection safety.
    """
    total_exchanges: int = 0
    healthy_exchanges: int = 0
    degraded_exchanges: int = 0
    quarantined_exchanges: int = 0
    
    active_incidents: int = 0
    latency_warnings: int = 0
    
    overall_health: str = "HEALTHY"
    
    exchange_status: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "totalExchanges": self.total_exchanges,
            "healthyExchanges": self.healthy_exchanges,
            "degradedExchanges": self.degraded_exchanges,
            "quarantinedExchanges": self.quarantined_exchanges,
            "activeIncidents": self.active_incidents,
            "latencyWarnings": self.latency_warnings,
            "overallHealth": self.overall_health,
            "exchanges": self.exchange_status
        }


@dataclass
class EventsWidget:
    """
    Dashboard widget for recent events.
    """
    recent_critical: int = 0
    recent_warnings: int = 0
    recent_info: int = 0
    
    latest_events: List[Dict[str, Any]] = field(default_factory=list)
    
    risk_alerts: int = 0
    profile_switches: int = 0
    recon_incidents: int = 0
    connection_incidents: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "counts": {
                "critical": self.recent_critical,
                "warnings": self.recent_warnings,
                "info": self.recent_info
            },
            "latestEvents": self.latest_events,
            "breakdown": {
                "riskAlerts": self.risk_alerts,
                "profileSwitches": self.profile_switches,
                "reconIncidents": self.recon_incidents,
                "connectionIncidents": self.connection_incidents
            }
        }


@dataclass
class DashboardWidget:
    """
    Generic dashboard widget.
    """
    widget_type: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    updated_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "widgetType": self.widget_type,
            "data": self.data,
            "updatedAt": self.updated_at
        }


@dataclass
class UnifiedDashboardState:
    """
    Complete unified dashboard state.
    Main entity for TR6.
    """
    dashboard_id: str = field(default_factory=lambda: f"dash_{uuid.uuid4().hex[:8]}")
    
    # Widgets
    accounts: Optional[AccountsWidget] = None
    portfolio: Optional[PortfolioWidget] = None
    trades: Optional[TradesWidget] = None
    risk: Optional[RiskWidget] = None
    strategy: Optional[StrategyWidget] = None
    regime: Optional[RegimeWidget] = None
    reconciliation: Optional[ReconciliationWidget] = None
    connections: Optional[ConnectionsWidget] = None
    events: Optional[EventsWidget] = None
    
    # System health
    system_health: SystemHealthStatus = SystemHealthStatus.HEALTHY
    health_details: Dict[str, str] = field(default_factory=dict)
    
    # Timestamps
    generated_at: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dashboardId": self.dashboard_id,
            "accounts": self.accounts.to_dict() if self.accounts else None,
            "portfolio": self.portfolio.to_dict() if self.portfolio else None,
            "trades": self.trades.to_dict() if self.trades else None,
            "risk": self.risk.to_dict() if self.risk else None,
            "strategy": self.strategy.to_dict() if self.strategy else None,
            "regime": self.regime.to_dict() if self.regime else None,
            "reconciliation": self.reconciliation.to_dict() if self.reconciliation else None,
            "connections": self.connections.to_dict() if self.connections else None,
            "events": self.events.to_dict() if self.events else None,
            "systemHealth": self.system_health.value,
            "healthDetails": self.health_details,
            "generatedAt": self.generated_at
        }
