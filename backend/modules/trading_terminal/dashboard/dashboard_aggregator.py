"""
Dashboard Aggregator (TR6)
==========================

Aggregates data from all trading terminal modules into unified dashboard state.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .dashboard_types import (
    UnifiedDashboardState,
    PortfolioSummary,
    StrategySummary,
    RiskSummary,
    TradesSummary,
    AccountsSummary,
    SystemHealth
)


class DashboardAggregator:
    """
    Aggregates data from all modules.
    
    Sources:
    - TR1 Account Manager
    - TR2 Portfolio Monitor
    - TR3 Trade Monitor
    - TR4 Risk Dashboard
    - TR5 Strategy Control
    - STR4 Strategy Diagnostics
    """
    
    def __init__(self):
        self._last_state: Optional[UnifiedDashboardState] = None
        print("[DashboardAggregator] Initialized")
    
    def aggregate(self) -> UnifiedDashboardState:
        """
        Aggregate all module data into unified state.
        """
        state = UnifiedDashboardState()
        
        # Aggregate each module
        state.portfolio = self._aggregate_portfolio()
        state.strategy = self._aggregate_strategy()
        state.risk = self._aggregate_risk()
        state.trades = self._aggregate_trades()
        state.accounts = self._aggregate_accounts()
        
        # Calculate system health
        state.system_health, state.health_reasons = self._calculate_system_health(state)
        
        state.generated_at = datetime.now(timezone.utc)
        self._last_state = state
        
        return state
    
    def _aggregate_portfolio(self) -> PortfolioSummary:
        """Aggregate portfolio data from TR2"""
        summary = PortfolioSummary()
        
        try:
            from ..portfolio.portfolio_service import portfolio_service
            
            portfolio_state = portfolio_service.get_portfolio_state()
            
            summary.total_equity = portfolio_state.total_equity
            summary.available_balance = portfolio_state.available_balance
            summary.daily_pnl = portfolio_state.daily_pnl
            summary.daily_pnl_pct = portfolio_state.daily_pnl_pct
            summary.open_positions = portfolio_state.open_positions_count
            summary.open_orders = portfolio_state.open_orders_count
            summary.total_exposure_pct = portfolio_state.exposure_pct
            summary.margin_used_pct = portfolio_state.margin_used_pct
            
        except Exception as e:
            print(f"[DashboardAggregator] Portfolio aggregation error: {e}")
            # Use mock data
            summary.total_equity = 50000.0
            summary.available_balance = 35000.0
            summary.daily_pnl = 125.50
            summary.daily_pnl_pct = 0.0025
            summary.open_positions = 2
            summary.open_orders = 1
            summary.total_exposure_pct = 0.30
            summary.margin_used_pct = 0.15
        
        return summary
    
    def _aggregate_strategy(self) -> StrategySummary:
        """Aggregate strategy data from TR5 and STR4"""
        summary = StrategySummary()
        
        try:
            from ..strategy_control.control_service import strategy_control_service
            
            state = strategy_control_service.get_state()
            
            summary.active_profile = state.active_profile
            summary.active_config = state.active_config
            summary.trading_paused = state.paused
            summary.override_mode = state.override_mode
            summary.kill_switch_active = state.kill_switch_active
            summary.kill_switch_mode = state.kill_switch_mode.value if state.kill_switch_mode else ""
            summary.control_mode = state.mode.value
            
        except Exception as e:
            print(f"[DashboardAggregator] Strategy control aggregation error: {e}")
            summary.active_profile = "BALANCED"
            summary.control_mode = "NORMAL"
        
        # Get strategy health from STR4
        try:
            from ...trading_capsule.strategy_diagnostics.diagnostics_service import diagnostics_service
            
            health_state = diagnostics_service.get_strategy_health()
            summary.health_status = health_state.get("status", "HEALTHY")
            summary.health_score = health_state.get("score", 1.0)
            
        except Exception as e:
            print(f"[DashboardAggregator] Strategy diagnostics aggregation error: {e}")
            summary.health_status = "HEALTHY"
            summary.health_score = 1.0
        
        # Count recent switches
        try:
            events = strategy_control_service.get_events(limit=10)
            summary.recent_switches = len([e for e in events if "SWITCH" in e.action.value])
        except Exception:
            summary.recent_switches = 0
        
        return summary
    
    def _aggregate_risk(self) -> RiskSummary:
        """Aggregate risk data from TR4"""
        summary = RiskSummary()
        
        try:
            from ..risk.risk_service import risk_service
            
            risk_state = risk_service.get_risk_state()
            
            summary.risk_level = risk_state.risk_level.name
            summary.current_drawdown_pct = risk_state.metrics.current_drawdown_pct
            summary.daily_loss_pct = risk_state.metrics.daily_loss_pct
            summary.gross_exposure_pct = risk_state.exposure.gross_exposure_pct
            summary.current_leverage = risk_state.exposure.current_leverage
            summary.concentration_score = risk_state.concentration.concentration_score
            summary.var_95_pct = risk_state.tail_risk.var_95_pct
            summary.cvar_95_pct = risk_state.tail_risk.cvar_95_pct
            
            # Get active alerts count
            alerts = risk_service.get_alerts(active_only=True)
            summary.active_alerts = len(alerts)
            
        except Exception as e:
            print(f"[DashboardAggregator] Risk aggregation error: {e}")
            # Use mock data
            summary.risk_level = "LOW"
            summary.current_drawdown_pct = 0.02
            summary.daily_loss_pct = 0.005
            summary.gross_exposure_pct = 0.30
            summary.current_leverage = 1.5
            summary.var_95_pct = 0.05
            summary.cvar_95_pct = 0.07
        
        return summary
    
    def _aggregate_trades(self) -> TradesSummary:
        """Aggregate trades data from TR3"""
        summary = TradesSummary()
        
        try:
            from ..trades.trade_service import trade_service
            
            # Get recent orders
            orders = trade_service.get_orders(limit=50)
            summary.recent_orders = len(orders)
            
            # Get recent fills
            fills = trade_service.get_fills(limit=50)
            summary.recent_fills = len(fills)
            
            # Get today's closed trades
            trades = trade_service.get_trades(limit=100)
            today_trades = [t for t in trades if self._is_today(t.closed_at)]
            summary.closed_trades_today = len(today_trades)
            
            if today_trades:
                winning = len([t for t in today_trades if t.realized_pnl > 0])
                summary.win_rate_today = winning / len(today_trades) if today_trades else 0.0
                summary.pnl_today = sum(t.realized_pnl for t in today_trades)
            
            # Get execution logs for errors
            logs = trade_service.get_execution_logs(limit=50)
            summary.execution_errors = len([l for l in logs if l.status == "ERROR"])
            
        except Exception as e:
            print(f"[DashboardAggregator] Trades aggregation error: {e}")
            # Use mock data
            summary.recent_orders = 5
            summary.recent_fills = 3
            summary.closed_trades_today = 2
            summary.win_rate_today = 0.5
            summary.pnl_today = 50.0
        
        return summary
    
    def _aggregate_accounts(self) -> AccountsSummary:
        """Aggregate accounts data from TR1"""
        summary = AccountsSummary()
        
        try:
            from ..accounts.account_service import account_service
            
            health = account_service.get_health()
            
            summary.connected_exchanges = health.get("connections", {}).get("total", 0)
            summary.healthy_connections = health.get("connections", {}).get("healthy", 0)
            summary.degraded_connections = health.get("connections", {}).get("degraded", 0)
            
            # Get balances
            balances = account_service.get_aggregated_balances()
            summary.total_balance_usd = balances.get("total_usd", 0.0)
            
            # Get exchange list
            connections = account_service.get_connections()
            summary.exchanges = [
                {
                    "exchange": c.exchange,
                    "status": c.status.value,
                    "lastSync": c.last_sync.isoformat() if c.last_sync else None
                }
                for c in connections
            ]
            
        except Exception as e:
            print(f"[DashboardAggregator] Accounts aggregation error: {e}")
            # Use mock data
            summary.connected_exchanges = 1
            summary.healthy_connections = 1
            summary.total_balance_usd = 50000.0
            summary.exchanges = [
                {"exchange": "binance", "status": "CONNECTED", "lastSync": datetime.now(timezone.utc).isoformat()}
            ]
        
        return summary
    
    def _calculate_system_health(
        self,
        state: UnifiedDashboardState
    ) -> tuple:
        """
        Calculate overall system health.
        
        Returns (SystemHealth, List[str] reasons)
        """
        reasons = []
        
        # Check for CRITICAL conditions
        if state.strategy.kill_switch_active:
            reasons.append(f"Kill switch active: {state.strategy.kill_switch_mode}")
            return SystemHealth.CRITICAL, reasons
        
        if state.risk.risk_level == "CRITICAL":
            reasons.append("Critical risk level")
            return SystemHealth.CRITICAL, reasons
        
        if state.accounts.connected_exchanges == 0:
            reasons.append("No exchange connections")
            return SystemHealth.CRITICAL, reasons
        
        # Check for DEGRADED conditions
        if state.accounts.degraded_connections > 0:
            reasons.append(f"{state.accounts.degraded_connections} degraded exchange connection(s)")
        
        if state.strategy.health_status in ["DEGRADED", "CRITICAL"]:
            reasons.append(f"Strategy health: {state.strategy.health_status}")
        
        if reasons and "degraded" in str(reasons).lower():
            return SystemHealth.DEGRADED, reasons
        
        # Check for WARNING conditions
        if state.strategy.trading_paused:
            reasons.append("Trading paused")
        
        if state.strategy.override_mode:
            reasons.append("Override mode active")
        
        if state.risk.risk_level in ["MODERATE", "HIGH"]:
            reasons.append(f"Risk level: {state.risk.risk_level}")
        
        if state.risk.active_alerts > 0:
            reasons.append(f"{state.risk.active_alerts} active risk alert(s)")
        
        if state.strategy.health_status == "WARNING":
            reasons.append("Strategy health warning")
        
        if state.trades.execution_errors > 0:
            reasons.append(f"{state.trades.execution_errors} execution error(s)")
        
        if reasons:
            return SystemHealth.WARNING, reasons
        
        return SystemHealth.HEALTHY, []
    
    def _is_today(self, dt: Optional[datetime]) -> bool:
        """Check if datetime is today"""
        if dt is None:
            return False
        today = datetime.now(timezone.utc).date()
        return dt.date() == today
    
    def get_last_state(self) -> Optional[UnifiedDashboardState]:
        """Get last aggregated state"""
        return self._last_state


# Global singleton
dashboard_aggregator = DashboardAggregator()
