"""
TR6 Dashboard Service
=====================

Main service for unified trading dashboard.

Aggregates data from all system layers:
- Accounts (TR1)
- Portfolio (TR2) + Capital Flow (OPS4)
- Trades (TR3)
- Risk (TR4)
- Strategy (TR5 + STG4 + STG5)
- Regime Engine
- Reconciliation
- Connection Safety (SEC3)
- Event Ledger
"""

import os
import time
import threading
import random
from typing import Dict, List, Optional, Any

from .dashboard_types import (
    UnifiedDashboardState,
    AccountsWidget,
    PortfolioWidget,
    TradesWidget,
    RiskWidget,
    StrategyWidget,
    RegimeWidget,
    ReconciliationWidget,
    ConnectionsWidget,
    EventsWidget,
    SystemHealthStatus
)


class DashboardService:
    """
    Main service for TR6 Unified Dashboard.
    
    Aggregates all trading system data into unified view.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Cache
        self._state_cache: Optional[UnifiedDashboardState] = None
        self._cache_timestamp: int = 0
        self._cache_ttl_ms: int = 2000  # 2 seconds
        
        # Base values for mock
        self._base_equity = 50000.0
        
        self._initialized = True
        print("[DashboardService] Initialized (TR6)")
    
    # ===========================================
    # Main State
    # ===========================================
    
    def get_dashboard_state(self) -> UnifiedDashboardState:
        """
        Get complete unified dashboard state.
        """
        
        # Check cache
        now = int(time.time() * 1000)
        if self._state_cache and (now - self._cache_timestamp) < self._cache_ttl_ms:
            return self._state_cache
        
        # Build fresh state
        state = UnifiedDashboardState()
        
        # Aggregate all widgets
        state.accounts = self._get_accounts_widget()
        state.portfolio = self._get_portfolio_widget()
        state.trades = self._get_trades_widget()
        state.risk = self._get_risk_widget()
        state.strategy = self._get_strategy_widget()
        state.regime = self._get_regime_widget()
        state.reconciliation = self._get_reconciliation_widget()
        state.connections = self._get_connections_widget()
        state.events = self._get_events_widget()
        
        # Compute system health
        state.system_health, state.health_details = self._compute_system_health(state)
        
        # Cache
        self._state_cache = state
        self._cache_timestamp = now
        
        return state
    
    # ===========================================
    # Individual Widgets
    # ===========================================
    
    def get_accounts_widget(self) -> AccountsWidget:
        """Get accounts widget"""
        return self._get_accounts_widget()
    
    def get_portfolio_widget(self) -> PortfolioWidget:
        """Get portfolio widget"""
        return self._get_portfolio_widget()
    
    def get_trades_widget(self) -> TradesWidget:
        """Get trades widget"""
        return self._get_trades_widget()
    
    def get_risk_widget(self) -> RiskWidget:
        """Get risk widget"""
        return self._get_risk_widget()
    
    def get_strategy_widget(self) -> StrategyWidget:
        """Get strategy widget"""
        return self._get_strategy_widget()
    
    def get_regime_widget(self) -> RegimeWidget:
        """Get regime widget"""
        return self._get_regime_widget()
    
    def get_reconciliation_widget(self) -> ReconciliationWidget:
        """Get reconciliation widget"""
        return self._get_reconciliation_widget()
    
    def get_connections_widget(self) -> ConnectionsWidget:
        """Get connections widget"""
        return self._get_connections_widget()
    
    def get_events_widget(self) -> EventsWidget:
        """Get events widget"""
        return self._get_events_widget()
    
    # ===========================================
    # System Health
    # ===========================================
    
    def _compute_system_health(
        self,
        state: UnifiedDashboardState
    ) -> tuple:
        """
        Compute overall system health.
        
        Logic:
        - CRITICAL if kill switch, critical risk, quarantine with exposure
        - DEGRADED if risk/accounts/connection/recon problems
        - WARNING if minor issues in any block
        - HEALTHY otherwise
        """
        
        details = {}
        
        # Check for CRITICAL conditions
        if state.strategy and state.strategy.kill_switch_active:
            return SystemHealthStatus.CRITICAL, {"reason": "kill_switch_active"}
        
        if state.risk and state.risk.critical_alerts > 0:
            return SystemHealthStatus.CRITICAL, {"reason": "critical_risk_alerts"}
        
        if state.connections and state.connections.quarantined_exchanges > 0:
            details["connections"] = "quarantined_exchanges"
            if state.portfolio and state.portfolio.open_positions > 0:
                return SystemHealthStatus.CRITICAL, {
                    "reason": "quarantine_with_exposure",
                    **details
                }
        
        # Check for DEGRADED conditions
        if state.risk and state.risk.risk_level == "CRITICAL":
            return SystemHealthStatus.DEGRADED, {"reason": "critical_risk_level"}
        
        if state.reconciliation and state.reconciliation.critical_mismatches > 0:
            return SystemHealthStatus.DEGRADED, {"reason": "critical_recon_mismatches"}
        
        if state.connections and state.connections.degraded_exchanges > 1:
            return SystemHealthStatus.DEGRADED, {"reason": "multiple_degraded_exchanges"}
        
        # Check for WARNING conditions
        if state.risk and state.risk.active_alerts > 0:
            details["risk"] = f"{state.risk.active_alerts}_active_alerts"
        
        if state.connections and state.connections.degraded_exchanges > 0:
            details["connections"] = f"{state.connections.degraded_exchanges}_degraded"
        
        if state.reconciliation and state.reconciliation.mismatch_count > 0:
            details["reconciliation"] = f"{state.reconciliation.mismatch_count}_mismatches"
        
        if state.strategy and state.strategy.trading_paused:
            details["strategy"] = "trading_paused"
        
        if details:
            return SystemHealthStatus.WARNING, details
        
        return SystemHealthStatus.HEALTHY, {}
    
    # ===========================================
    # Widget Implementations (Mock)
    # ===========================================
    
    def _get_accounts_widget(self) -> AccountsWidget:
        """Build accounts widget"""
        
        # Try to get from actual services
        try:
            from modules.security.connection_safety import connection_safety_service
            summary = connection_safety_service.get_summary()
            
            return AccountsWidget(
                connected_exchanges=summary.total_exchanges,
                healthy=summary.healthy_count,
                degraded=summary.degraded_count,
                quarantined=summary.quarantined_count,
                total_equity=self._base_equity + random.uniform(-2000, 5000),
                total_balance=self._base_equity * 1.1
            )
        except Exception:
            pass
        
        # Mock fallback
        return AccountsWidget(
            connected_exchanges=3,
            healthy=2,
            degraded=1,
            quarantined=0,
            total_equity=round(self._base_equity + random.uniform(-2000, 5000), 2),
            total_balance=round(self._base_equity * 1.1, 2)
        )
    
    def _get_portfolio_widget(self) -> PortfolioWidget:
        """Build portfolio widget"""
        
        # Try OPS4 Capital Flow
        try:
            from modules.trading_terminal.operations.capital import capital_flow_service
            state = capital_flow_service.get_capital_state()
            
            return PortfolioWidget(
                total_equity=state.total_equity,
                used_margin=state.used_margin,
                free_margin=state.free_margin,
                unrealized_pnl=state.unrealized_pnl,
                realized_pnl=state.realized_pnl,
                total_pnl=state.total_pnl,
                daily_pnl=random.uniform(-500, 1500),
                daily_pnl_pct=random.uniform(-0.02, 0.04),
                exposure_usd=state.exposure_usd,
                exposure_pct=state.exposure_pct,
                open_positions=state.open_positions
            )
        except Exception:
            pass
        
        # Mock fallback
        equity = self._base_equity + random.uniform(-2000, 5000)
        used_margin = equity * random.uniform(0.2, 0.4)
        
        return PortfolioWidget(
            total_equity=round(equity, 2),
            used_margin=round(used_margin, 2),
            free_margin=round(equity - used_margin, 2),
            unrealized_pnl=round(random.uniform(-500, 1500), 2),
            realized_pnl=round(random.uniform(100, 2500), 2),
            total_pnl=round(random.uniform(-200, 3000), 2),
            daily_pnl=round(random.uniform(-500, 1500), 2),
            daily_pnl_pct=round(random.uniform(-0.02, 0.04), 4),
            exposure_usd=round(used_margin * random.uniform(2, 4), 2),
            exposure_pct=round(used_margin / equity, 4),
            open_positions=random.randint(3, 8)
        )
    
    def _get_trades_widget(self) -> TradesWidget:
        """Build trades widget"""
        
        return TradesWidget(
            recent_orders=random.randint(5, 25),
            recent_fills=random.randint(3, 15),
            recent_closed=random.randint(5, 20),
            trades_today=random.randint(2, 12),
            trades_week=random.randint(15, 60),
            win_rate=round(random.uniform(0.52, 0.68), 4),
            profit_factor=round(random.uniform(1.2, 2.5), 4),
            avg_trade_pnl=round(random.uniform(15, 85), 2),
            last_trade_at=int(time.time() * 1000) - random.randint(60000, 3600000)
        )
    
    def _get_risk_widget(self) -> RiskWidget:
        """Build risk widget"""
        
        risk_score = random.uniform(0.2, 0.7)
        
        if risk_score > 0.6:
            risk_level = "HIGH"
        elif risk_score > 0.4:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"
        
        return RiskWidget(
            risk_level=risk_level,
            risk_score=round(risk_score, 4),
            drawdown_pct=round(random.uniform(0.02, 0.12), 4),
            max_drawdown_pct=round(random.uniform(0.08, 0.20), 4),
            daily_loss_pct=round(random.uniform(0, 0.03), 4),
            daily_loss_limit_pct=0.05,
            daily_limit_used_pct=round(random.uniform(0, 0.6), 4),
            leverage=round(random.uniform(1, 5), 2),
            max_concentration_pct=round(random.uniform(0.15, 0.40), 4),
            var_95=round(random.uniform(-0.10, -0.20), 4),
            cvar_95=round(random.uniform(-0.15, -0.25), 4),
            active_alerts=random.randint(0, 3),
            critical_alerts=0
        )
    
    def _get_strategy_widget(self) -> StrategyWidget:
        """Build strategy widget"""
        
        profiles = ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]
        strategies = ["MOMENTUM_BREAKOUT", "TREND_FOLLOWING", "MEAN_REVERSION", "CHANNEL_BREAKOUT"]
        
        return StrategyWidget(
            active_profile=random.choice(profiles),
            active_config="config_v1",
            selected_strategy=random.choice(strategies),
            strategy_health="HEALTHY" if random.random() > 0.2 else "WARNING",
            trading_paused=random.random() < 0.05,
            kill_switch_active=False,
            recent_switches=random.randint(0, 3),
            active_overrides=[],
            strategies_available=len(strategies),
            strategies_active=random.randint(2, 4)
        )
    
    def _get_regime_widget(self) -> RegimeWidget:
        """Build regime widget"""
        
        regimes = ["TRENDING", "RANGE", "HIGH_VOLATILITY", "LOW_VOLATILITY", "TRANSITION"]
        current = random.choice(regimes)
        previous = random.choice([r for r in regimes if r != current])
        
        return RegimeWidget(
            current_regime=current,
            regime_confidence=round(random.uniform(0.65, 0.95), 4),
            regime_stability=round(random.uniform(0.5, 0.9), 4),
            transition_risk=round(random.uniform(0.1, 0.4), 4),
            previous_regime=previous,
            regime_duration_hours=round(random.uniform(2, 48), 1)
        )
    
    def _get_reconciliation_widget(self) -> ReconciliationWidget:
        """Build reconciliation widget"""
        
        has_mismatch = random.random() < 0.1
        
        return ReconciliationWidget(
            status="MISMATCH" if has_mismatch else "OK",
            last_check_at=int(time.time() * 1000) - random.randint(60000, 300000),
            mismatch_count=random.randint(1, 3) if has_mismatch else 0,
            critical_mismatches=0,
            frozen_symbols=[],
            quarantined_exchanges=[],
            position_synced=True,
            balance_synced=True,
            orders_synced=not has_mismatch
        )
    
    def _get_connections_widget(self) -> ConnectionsWidget:
        """Build connections widget"""
        
        # Try SEC3
        try:
            from modules.security.connection_safety import connection_safety_service
            summary = connection_safety_service.get_summary()
            
            return ConnectionsWidget(
                total_exchanges=summary.total_exchanges,
                healthy_exchanges=summary.healthy_count,
                degraded_exchanges=summary.degraded_count,
                quarantined_exchanges=summary.quarantined_count,
                active_incidents=summary.active_incidents,
                latency_warnings=0,
                overall_health=summary.overall_health,
                exchange_status=summary.exchanges
            )
        except Exception:
            pass
        
        # Mock fallback
        degraded = 1 if random.random() < 0.3 else 0
        
        return ConnectionsWidget(
            total_exchanges=3,
            healthy_exchanges=3 - degraded,
            degraded_exchanges=degraded,
            quarantined_exchanges=0,
            active_incidents=random.randint(0, 2),
            latency_warnings=random.randint(0, 1),
            overall_health="DEGRADED" if degraded > 0 else "HEALTHY",
            exchange_status=[
                {"exchange": "BINANCE", "status": "HEALTHY", "healthScore": 0.95},
                {"exchange": "BYBIT", "status": "DEGRADED" if degraded > 0 else "HEALTHY", "healthScore": 0.65 if degraded > 0 else 0.88},
                {"exchange": "HYPERLIQUID", "status": "HEALTHY", "healthScore": 0.92}
            ]
        )
    
    def _get_events_widget(self) -> EventsWidget:
        """Build events widget"""
        
        events = [
            {"type": "TRADE_CLOSED", "severity": "INFO", "message": "Position closed with profit", "timestamp": int(time.time() * 1000) - 120000},
            {"type": "REGIME_CHANGED", "severity": "INFO", "message": "Regime changed to TRENDING", "timestamp": int(time.time() * 1000) - 300000},
            {"type": "RISK_ALERT", "severity": "WARNING", "message": "Drawdown approaching threshold", "timestamp": int(time.time() * 1000) - 600000}
        ]
        
        return EventsWidget(
            recent_critical=0,
            recent_warnings=random.randint(1, 4),
            recent_info=random.randint(5, 15),
            latest_events=events,
            risk_alerts=random.randint(0, 2),
            profile_switches=random.randint(0, 2),
            recon_incidents=0,
            connection_incidents=random.randint(0, 1)
        )
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "TR6 Unified Dashboard",
            "status": "healthy",
            "version": "1.0.0",
            "cached": self._state_cache is not None,
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
dashboard_service = DashboardService()
