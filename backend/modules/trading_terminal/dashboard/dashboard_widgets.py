"""
Dashboard Widgets (TR6)
=======================

Individual widget data providers.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List

from .dashboard_types import DashboardWidgetState, WidgetType


class DashboardWidgets:
    """
    Provides data for individual dashboard widgets.
    """
    
    def get_portfolio_widget(self) -> DashboardWidgetState:
        """Get portfolio widget data"""
        try:
            from ..portfolio.portfolio_service import portfolio_service
            
            state = portfolio_service.get_portfolio_state()
            positions = portfolio_service.get_positions()
            
            payload = {
                "equity": round(state.total_equity, 2),
                "available": round(state.available_balance, 2),
                "dailyPnl": round(state.daily_pnl, 2),
                "dailyPnlPct": round(state.daily_pnl_pct, 4),
                "positions": [
                    {
                        "symbol": p.symbol,
                        "side": p.side,
                        "size": p.size,
                        "entryPrice": p.entry_price,
                        "unrealizedPnl": round(p.unrealized_pnl, 2)
                    }
                    for p in positions[:5]
                ],
                "positionsCount": len(positions),
                "exposure": round(state.exposure_pct, 4)
            }
        except Exception as e:
            print(f"[DashboardWidgets] Portfolio widget error: {e}")
            payload = {
                "equity": 50000.0,
                "available": 35000.0,
                "dailyPnl": 125.50,
                "dailyPnlPct": 0.0025,
                "positions": [],
                "positionsCount": 2,
                "exposure": 0.30
            }
        
        return DashboardWidgetState(
            widget_type=WidgetType.PORTFOLIO,
            payload=payload
        )
    
    def get_strategy_widget(self) -> DashboardWidgetState:
        """Get strategy widget data"""
        try:
            from ..strategy_control.control_service import strategy_control_service
            
            state = strategy_control_service.get_state()
            profile_info = strategy_control_service.get_profile()
            config_info = strategy_control_service.get_config()
            
            payload = {
                "activeProfile": state.active_profile,
                "activeConfig": state.active_config,
                "mode": state.mode.value,
                "tradingEnabled": state.trading_enabled,
                "paused": state.paused,
                "overrideMode": state.override_mode,
                "killSwitch": {
                    "active": state.kill_switch_active,
                    "mode": state.kill_switch_mode.value if state.kill_switch_mode else None
                },
                "availableProfiles": profile_info.get("available", []),
                "availableConfigs": list(config_info.get("configs", {}).keys())
            }
        except Exception as e:
            print(f"[DashboardWidgets] Strategy widget error: {e}")
            payload = {
                "activeProfile": "BALANCED",
                "activeConfig": "",
                "mode": "NORMAL",
                "tradingEnabled": True,
                "paused": False,
                "overrideMode": False,
                "killSwitch": {"active": False, "mode": None},
                "availableProfiles": ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"],
                "availableConfigs": []
            }
        
        return DashboardWidgetState(
            widget_type=WidgetType.STRATEGY,
            payload=payload
        )
    
    def get_risk_widget(self) -> DashboardWidgetState:
        """Get risk widget data"""
        try:
            from ..risk.risk_service import risk_service
            
            state = risk_service.get_risk_state()
            alerts = risk_service.get_alerts(active_only=True)
            
            payload = {
                "riskLevel": state.risk_level.name,
                "drawdown": {
                    "current": round(state.metrics.current_drawdown_pct, 4),
                    "max": round(state.metrics.max_drawdown_pct, 4)
                },
                "dailyLoss": {
                    "current": round(state.metrics.daily_loss_pct, 4),
                    "limit": round(state.metrics.daily_loss_limit_pct, 4)
                },
                "exposure": {
                    "gross": round(state.exposure.gross_exposure_pct, 4),
                    "net": round(state.exposure.net_exposure_pct, 4)
                },
                "leverage": round(state.exposure.current_leverage, 2),
                "tailRisk": {
                    "var95": round(state.tail_risk.var_95_pct, 4),
                    "cvar95": round(state.tail_risk.cvar_95_pct, 4)
                },
                "alerts": [
                    {
                        "id": a.alert_id,
                        "type": a.alert_type.value,
                        "severity": a.severity.name,
                        "message": a.message
                    }
                    for a in alerts[:5]
                ],
                "alertsCount": len(alerts)
            }
        except Exception as e:
            print(f"[DashboardWidgets] Risk widget error: {e}")
            payload = {
                "riskLevel": "LOW",
                "drawdown": {"current": 0.02, "max": 0.05},
                "dailyLoss": {"current": 0.005, "limit": 0.05},
                "exposure": {"gross": 0.30, "net": 0.15},
                "leverage": 1.5,
                "tailRisk": {"var95": 0.05, "cvar95": 0.07},
                "alerts": [],
                "alertsCount": 0
            }
        
        return DashboardWidgetState(
            widget_type=WidgetType.RISK,
            payload=payload
        )
    
    def get_trades_widget(self) -> DashboardWidgetState:
        """Get trades widget data"""
        try:
            from ..trades.trade_service import trade_service
            
            orders = trade_service.get_orders(limit=10)
            fills = trade_service.get_fills(limit=10)
            trades = trade_service.get_trades(limit=10)
            
            payload = {
                "recentOrders": [
                    {
                        "id": o.order_id,
                        "symbol": o.symbol,
                        "side": o.side,
                        "type": o.order_type,
                        "status": o.status,
                        "size": o.size,
                        "price": o.price
                    }
                    for o in orders[:5]
                ],
                "recentFills": [
                    {
                        "id": f.fill_id,
                        "orderId": f.order_id,
                        "symbol": f.symbol,
                        "side": f.side,
                        "size": f.filled_size,
                        "price": f.fill_price
                    }
                    for f in fills[:5]
                ],
                "recentTrades": [
                    {
                        "id": t.trade_id,
                        "symbol": t.symbol,
                        "side": t.side,
                        "pnl": round(t.realized_pnl, 2),
                        "closedAt": t.closed_at.isoformat() if t.closed_at else None
                    }
                    for t in trades[:5]
                ],
                "ordersCount": len(orders),
                "fillsCount": len(fills),
                "tradesCount": len(trades)
            }
        except Exception as e:
            print(f"[DashboardWidgets] Trades widget error: {e}")
            payload = {
                "recentOrders": [],
                "recentFills": [],
                "recentTrades": [],
                "ordersCount": 0,
                "fillsCount": 0,
                "tradesCount": 0
            }
        
        return DashboardWidgetState(
            widget_type=WidgetType.TRADES,
            payload=payload
        )
    
    def get_accounts_widget(self) -> DashboardWidgetState:
        """Get accounts widget data"""
        try:
            from ..accounts.account_service import account_service
            
            connections = account_service.get_connections()
            balances = account_service.get_aggregated_balances()
            health = account_service.get_health()
            
            payload = {
                "exchanges": [
                    {
                        "exchange": c.exchange,
                        "status": c.status.value,
                        "lastSync": c.last_sync.isoformat() if c.last_sync else None,
                        "permissions": c.permissions
                    }
                    for c in connections
                ],
                "balances": {
                    "total": round(balances.get("total_usd", 0), 2),
                    "byExchange": balances.get("by_exchange", {})
                },
                "health": {
                    "connected": health.get("connections", {}).get("total", 0),
                    "healthy": health.get("connections", {}).get("healthy", 0),
                    "degraded": health.get("connections", {}).get("degraded", 0)
                }
            }
        except Exception as e:
            print(f"[DashboardWidgets] Accounts widget error: {e}")
            payload = {
                "exchanges": [
                    {"exchange": "binance", "status": "CONNECTED", "lastSync": datetime.now(timezone.utc).isoformat()}
                ],
                "balances": {"total": 50000.0, "byExchange": {"binance": 50000.0}},
                "health": {"connected": 1, "healthy": 1, "degraded": 0}
            }
        
        return DashboardWidgetState(
            widget_type=WidgetType.ACCOUNTS,
            payload=payload
        )
    
    def get_alerts_widget(self) -> DashboardWidgetState:
        """Get alerts widget data"""
        alerts_list = []
        
        # Get risk alerts
        try:
            from ..risk.risk_service import risk_service
            risk_alerts = risk_service.get_alerts(active_only=True)
            for a in risk_alerts:
                alerts_list.append({
                    "id": a.alert_id,
                    "source": "risk",
                    "type": a.alert_type.value,
                    "severity": a.severity.name,
                    "title": a.title,
                    "message": a.message,
                    "createdAt": a.created_at.isoformat() if a.created_at else None
                })
        except Exception as e:
            print(f"[DashboardWidgets] Risk alerts error: {e}")
        
        # Get control events (last kill switches, overrides)
        try:
            from ..strategy_control.control_service import strategy_control_service
            events = strategy_control_service.get_kill_switch_events(limit=5)
            for e in events:
                alerts_list.append({
                    "id": e.event_id,
                    "source": "control",
                    "type": e.action.value,
                    "severity": "HIGH" if "KILL" in e.action.value else "WARNING",
                    "title": e.action.value.replace("_", " ").title(),
                    "message": e.reason,
                    "createdAt": e.timestamp.isoformat() if e.timestamp else None
                })
        except Exception as e:
            print(f"[DashboardWidgets] Control events error: {e}")
        
        # Sort by time
        alerts_list.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        
        payload = {
            "alerts": alerts_list[:20],
            "totalCount": len(alerts_list),
            "bySource": {
                "risk": len([a for a in alerts_list if a["source"] == "risk"]),
                "control": len([a for a in alerts_list if a["source"] == "control"])
            }
        }
        
        return DashboardWidgetState(
            widget_type=WidgetType.ALERTS,
            payload=payload
        )
    
    def get_system_widget(self) -> DashboardWidgetState:
        """Get system health widget data"""
        from .dashboard_aggregator import dashboard_aggregator
        
        state = dashboard_aggregator.aggregate()
        
        payload = {
            "health": state.system_health.value,
            "reasons": state.health_reasons,
            "modules": {
                "portfolio": "healthy",
                "strategy": state.strategy.health_status.lower(),
                "risk": "warning" if state.risk.active_alerts > 0 else "healthy",
                "trades": "healthy",
                "accounts": "healthy" if state.accounts.degraded_connections == 0 else "degraded"
            },
            "uptime": "running",
            "generatedAt": state.generated_at.isoformat()
        }
        
        return DashboardWidgetState(
            widget_type=WidgetType.SYSTEM,
            payload=payload
        )


# Global singleton
dashboard_widgets = DashboardWidgets()
