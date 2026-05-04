"""
Dashboard State Engine

PHASE 40.1 — Dashboard State Aggregator

Aggregates data from all system modules into unified dashboard state.

Data sources:
- Hypothesis Engine
- Simulation Engine
- Portfolio Manager
- Risk Budget Engine
- Execution Gateway
- Reflexivity Engine
- Regime Graph Engine
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta

from .dashboard_types import (
    DashboardState,
    MarketOverview,
    HypothesisState,
    PortfolioState,
    RiskState,
    PnLState,
    ExecutionState,
    PositionSummary,
    OrderSummary,
    FillSummary,
    DashboardAlert,
    MultiSymbolDashboard,
    DashboardConfig,
)


# ══════════════════════════════════════════════════════════════
# Dashboard State Engine
# ══════════════════════════════════════════════════════════════

class DashboardStateEngine:
    """
    Dashboard State Engine — PHASE 40.1
    
    Aggregates data from all modules into unified dashboard state.
    """
    
    def __init__(self, config: Optional[DashboardConfig] = None):
        self._config = config or DashboardConfig()
        self._state_cache: Dict[str, DashboardState] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Tracked symbols
        self._symbols = ["BTC", "ETH", "SOL", "AVAX"]
    
    # ═══════════════════════════════════════════════════════════
    # 1. Build Dashboard State
    # ═══════════════════════════════════════════════════════════
    
    def build_dashboard_state(self, symbol: str = "PORTFOLIO") -> DashboardState:
        """
        Build aggregated dashboard state.
        
        Collects data from all modules.
        """
        start_time = datetime.now(timezone.utc)
        
        # Check cache
        if self._is_cache_valid(symbol):
            return self._state_cache[symbol]
        
        # Get execution mode
        execution_mode = self._get_execution_mode()
        
        # Aggregate from modules
        market = self._get_market_overview(symbol)
        hypothesis = self._get_hypothesis_state(symbol)
        portfolio = self._get_portfolio_state()
        risk = self._get_risk_state()
        pnl = self._get_pnl_state()
        execution = self._get_execution_state()
        alerts = self._get_alerts(symbol)
        
        # Build state
        state = DashboardState(
            symbol=symbol,
            execution_mode=execution_mode,
            market=market,
            hypothesis=hypothesis,
            portfolio=portfolio,
            risk=risk,
            pnl=pnl,
            execution=execution,
            alerts=alerts,
            alert_count=len(alerts),
            critical_alert_count=sum(1 for a in alerts if a.severity == "CRITICAL"),
            last_updated=datetime.now(timezone.utc),
            data_freshness_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
        )
        
        # Cache
        self._state_cache[symbol] = state
        self._cache_timestamps[symbol] = datetime.now(timezone.utc)
        
        return state
    
    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached state is still valid."""
        if symbol not in self._state_cache:
            return False
        
        if symbol not in self._cache_timestamps:
            return False
        
        age = (datetime.now(timezone.utc) - self._cache_timestamps[symbol]).total_seconds()
        return age < self._config.state_cache_ttl_seconds
    
    def invalidate_cache(self, symbol: Optional[str] = None):
        """Invalidate cache."""
        if symbol:
            self._state_cache.pop(symbol, None)
            self._cache_timestamps.pop(symbol, None)
        else:
            self._state_cache.clear()
            self._cache_timestamps.clear()
    
    # ═══════════════════════════════════════════════════════════
    # 2. Market Overview
    # ═══════════════════════════════════════════════════════════
    
    def _get_market_overview(self, symbol: str) -> MarketOverview:
        """Get market state from regime and reflexivity engines."""
        overview = MarketOverview()
        
        # Regime Engine
        try:
            from modules.regime_intelligence_v2 import get_regime_engine_v2
            engine = get_regime_engine_v2()
            regime = engine.get_current_regime(symbol)
            if regime:
                overview.regime = regime.get("regime", "UNKNOWN")
                overview.regime_confidence = regime.get("confidence", 0.0)
        except Exception:
            pass
        
        # Reflexivity Engine
        try:
            from modules.reflexivity_engine import get_reflexivity_engine
            engine = get_reflexivity_engine()
            state = engine.get_state()
            overview.reflexivity_state = state.get("dominant_loop", "STABLE")
        except Exception:
            pass
        
        # Fractal bias
        try:
            from modules.fractal_intelligence import get_fractal_engine
            engine = get_fractal_engine()
            analysis = engine.analyze(symbol)
            if analysis:
                overview.fractal_bias = analysis.get("bias", "NEUTRAL")
                overview.trend_strength = analysis.get("trend_strength", 0.0)
        except Exception:
            pass
        
        return overview
    
    # ═══════════════════════════════════════════════════════════
    # 3. Hypothesis State
    # ═══════════════════════════════════════════════════════════
    
    def _get_hypothesis_state(self, symbol: str) -> HypothesisState:
        """Get hypothesis state from Hypothesis Engine."""
        state = HypothesisState()
        
        try:
            from modules.hypothesis_engine_v2 import get_hypothesis_engine
            engine = get_hypothesis_engine()
            
            # Get top hypothesis
            hypotheses = engine.get_active_hypotheses(symbol=symbol, limit=5)
            
            if hypotheses:
                top = hypotheses[0]
                state.top_hypothesis = top.get("description", "")
                state.top_hypothesis_id = top.get("hypothesis_id", "")
                state.confidence = top.get("confidence", 0.0)
                state.reliability = top.get("reliability", 0.0)
                state.competing_count = len(hypotheses) - 1
        except Exception:
            pass
        
        # Simulation
        try:
            from modules.market_simulation import get_simulation_engine
            engine = get_simulation_engine()
            scenarios = engine.get_scenarios(symbol)
            if scenarios:
                state.top_scenario = scenarios[0].get("name", "")
        except Exception:
            pass
        
        return state
    
    # ═══════════════════════════════════════════════════════════
    # 4. Portfolio State
    # ═══════════════════════════════════════════════════════════
    
    def _get_portfolio_state(self) -> PortfolioState:
        """Get portfolio state from Portfolio Manager."""
        state = PortfolioState()
        
        try:
            from modules.portfolio_manager import get_portfolio_engine
            engine = get_portfolio_engine()
            
            portfolio = engine.get_portfolio_state()
            
            state.total_capital = portfolio.total_value
            state.deployed_capital = portfolio.deployed_capital
            state.available_capital = portfolio.cash_available
            
            state.long_exposure = portfolio.long_exposure
            state.short_exposure = portfolio.short_exposure
            state.net_exposure = portfolio.net_exposure
            state.gross_exposure = portfolio.gross_exposure
            
            state.position_count = portfolio.position_count
            
            # Convert positions
            for pos in portfolio.positions:
                state.active_positions.append(PositionSummary(
                    symbol=pos.symbol,
                    side="LONG" if pos.size > 0 else "SHORT",
                    size_base=abs(pos.size),
                    size_usd=pos.market_value,
                    entry_price=pos.avg_entry_price,
                    current_price=pos.current_price,
                    unrealized_pnl=pos.unrealized_pnl,
                    unrealized_pnl_pct=pos.unrealized_pnl_pct,
                    strategy=pos.strategy,
                ))
            
            # Concentration
            if state.active_positions:
                max_pos = max(state.active_positions, key=lambda p: p.size_usd)
                state.concentration_top = max_pos.size_usd / state.total_capital if state.total_capital > 0 else 0
            
        except Exception:
            # Default values
            state.total_capital = 1000000.0
            state.available_capital = 950000.0
        
        return state
    
    # ═══════════════════════════════════════════════════════════
    # 5. Risk State
    # ═══════════════════════════════════════════════════════════
    
    def _get_risk_state(self) -> RiskState:
        """Get risk state from Risk Budget Engine."""
        state = RiskState()
        
        try:
            from modules.risk_budget import get_risk_budget_engine
            engine = get_risk_budget_engine()
            
            portfolio_risk = engine.get_portfolio_risk_budget()
            
            state.portfolio_risk = portfolio_risk.total_risk
            state.portfolio_risk_limit = portfolio_risk.total_risk_limit
            state.risk_utilization = portfolio_risk.risk_utilization
            state.vol_scale_factor = portfolio_risk.vol_scale_factor
            state.risk_state = portfolio_risk.risk_state
            state.risk_budget_remaining = 1 - state.risk_utilization
            
            # VaR estimates (simplified)
            state.var_95 = state.portfolio_risk * 1.65  # ~95% confidence
            state.var_99 = state.portfolio_risk * 2.33  # ~99% confidence
            
        except Exception:
            pass
        
        return state
    
    # ═══════════════════════════════════════════════════════════
    # 6. PnL State
    # ═══════════════════════════════════════════════════════════
    
    def _get_pnl_state(self) -> PnLState:
        """Get PnL state."""
        state = PnLState()
        
        try:
            from modules.portfolio_manager import get_portfolio_engine
            engine = get_portfolio_engine()
            
            portfolio = engine.get_portfolio_state()
            
            state.unrealized_pnl = portfolio.total_unrealized_pnl
            state.realized_pnl = portfolio.total_realized_pnl
            state.total_pnl = state.realized_pnl + state.unrealized_pnl
            
        except Exception:
            pass
        
        # Fill stats for slippage
        try:
            from modules.execution_gateway import get_gateway_repository
            repo = get_gateway_repository()
            
            stats = repo.get_fill_statistics(hours_back=24)
            state.avg_slippage_bps = stats.get("avg_slippage_bps", 0.0)
            state.total_fees = stats.get("total_fees_usd", 0.0)
            state.daily_pnl = stats.get("total_volume_usd", 0.0) * 0.001  # Rough estimate
            
        except Exception:
            pass
        
        return state
    
    # ═══════════════════════════════════════════════════════════
    # 7. Execution State
    # ═══════════════════════════════════════════════════════════
    
    def _get_execution_state(self) -> ExecutionState:
        """Get execution state from Execution Gateway."""
        state = ExecutionState()
        
        try:
            from modules.execution_gateway import get_execution_gateway
            gateway = get_execution_gateway()
            
            config = gateway.get_config()
            state.mode = config.execution_mode.value
            
            # Pending approvals
            pending = gateway.get_pending_approvals()
            state.pending_count = len(pending)
            
            for p in pending[:10]:
                state.pending_orders.append(OrderSummary(
                    order_id=p.order_id,
                    symbol=p.symbol,
                    side=p.side.value,
                    size_usd=p.size_usd,
                    order_type=p.order_type.value,
                    status="AWAITING_APPROVAL",
                    exchange=p.exchange,
                    created_at=p.created_at,
                ))
            
            # Recent fills
            fills = gateway.get_fills()
            state.fill_count_today = len(fills)
            
            for f in fills[:10]:
                state.recent_fills.append(FillSummary(
                    fill_id=f.fill_id,
                    symbol=f.symbol,
                    side=f.side.value,
                    filled_size=f.filled_size,
                    avg_price=f.avg_price,
                    slippage_bps=f.slippage_bps,
                    fee=f.fee,
                    filled_at=f.filled_at,
                ))
            
            # Daily stats
            daily_stats = gateway.get_daily_stats()
            state.daily_volume = daily_stats.get("daily_volume_usd", 0.0)
            
            # Connected exchanges
            state.connected_exchanges = ["BINANCE", "BYBIT"]
            
        except Exception:
            pass
        
        return state
    
    # ═══════════════════════════════════════════════════════════
    # 8. Alerts
    # ═══════════════════════════════════════════════════════════
    
    def _get_alerts(self, symbol: str) -> List[DashboardAlert]:
        """Get active alerts."""
        alerts = []
        
        try:
            from .alerts_engine import get_alerts_engine
            engine = get_alerts_engine()
            alerts = engine.get_active_alerts(symbol=symbol, limit=self._config.max_alerts_displayed)
        except Exception:
            pass
        
        # Generate alerts from current state
        risk = self._get_risk_state()
        
        if risk.portfolio_risk > self._config.risk_critical_threshold:
            alerts.append(DashboardAlert(
                symbol="PORTFOLIO",
                severity="CRITICAL",
                title="Portfolio Risk Critical",
                message=f"Portfolio risk {risk.portfolio_risk*100:.1f}% exceeds critical threshold {self._config.risk_critical_threshold*100:.0f}%",
                source="RiskBudgetEngine",
                category="RISK",
                value=risk.portfolio_risk,
                threshold=self._config.risk_critical_threshold,
            ))
        elif risk.portfolio_risk > self._config.risk_warning_threshold:
            alerts.append(DashboardAlert(
                symbol="PORTFOLIO",
                severity="WARNING",
                title="Portfolio Risk Elevated",
                message=f"Portfolio risk {risk.portfolio_risk*100:.1f}% approaching limit",
                source="RiskBudgetEngine",
                category="RISK",
                value=risk.portfolio_risk,
                threshold=self._config.risk_warning_threshold,
            ))
        
        return alerts
    
    # ═══════════════════════════════════════════════════════════
    # 9. Execution Mode
    # ═══════════════════════════════════════════════════════════
    
    def _get_execution_mode(self) -> str:
        """Get current execution mode."""
        try:
            from modules.execution_gateway import get_execution_gateway
            gateway = get_execution_gateway()
            return gateway.get_config().execution_mode.value
        except Exception:
            return "PAPER"
    
    # ═══════════════════════════════════════════════════════════
    # 10. Multi-Symbol Dashboard
    # ═══════════════════════════════════════════════════════════
    
    def build_multi_dashboard(self, symbols: Optional[List[str]] = None) -> MultiSymbolDashboard:
        """Build dashboard for multiple symbols."""
        symbols = symbols or self._symbols
        
        result = MultiSymbolDashboard(symbols=symbols)
        
        # Build state for each symbol
        for symbol in symbols:
            state = self.build_dashboard_state(symbol)
            result.symbol_states[symbol] = state
        
        # Aggregated states (portfolio level)
        result.portfolio = self._get_portfolio_state()
        result.risk = self._get_risk_state()
        result.pnl = self._get_pnl_state()
        result.execution = self._get_execution_state()
        
        # Collect all alerts
        all_alerts = []
        for state in result.symbol_states.values():
            all_alerts.extend(state.alerts)
        result.alerts = sorted(all_alerts, key=lambda a: a.created_at, reverse=True)[:50]
        
        result.timestamp = datetime.now(timezone.utc)
        
        return result
    
    # ═══════════════════════════════════════════════════════════
    # 11. Specific Getters
    # ═══════════════════════════════════════════════════════════
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary for API."""
        state = self._get_portfolio_state()
        return {
            "total_capital": state.total_capital,
            "deployed_capital": state.deployed_capital,
            "available_capital": state.available_capital,
            "long_exposure": state.long_exposure,
            "short_exposure": state.short_exposure,
            "net_exposure": state.net_exposure,
            "gross_exposure": state.gross_exposure,
            "position_count": state.position_count,
            "concentration_top": state.concentration_top,
        }
    
    def get_risk_summary(self) -> Dict:
        """Get risk summary for API."""
        state = self._get_risk_state()
        return {
            "portfolio_risk": state.portfolio_risk,
            "portfolio_risk_limit": state.portfolio_risk_limit,
            "risk_utilization": state.risk_utilization,
            "var_95": state.var_95,
            "var_99": state.var_99,
            "risk_state": state.risk_state,
            "vol_scale_factor": state.vol_scale_factor,
            "risk_budget_remaining": state.risk_budget_remaining,
        }
    
    def get_execution_summary(self) -> Dict:
        """Get execution summary for API."""
        state = self._get_execution_state()
        return {
            "mode": state.mode,
            "pending_count": state.pending_count,
            "active_count": state.active_count,
            "fill_count_today": state.fill_count_today,
            "daily_volume": state.daily_volume,
            "connected_exchanges": state.connected_exchanges,
        }


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_dashboard_engine: Optional[DashboardStateEngine] = None


def get_dashboard_engine() -> DashboardStateEngine:
    """Get singleton instance."""
    global _dashboard_engine
    if _dashboard_engine is None:
        _dashboard_engine = DashboardStateEngine()
    return _dashboard_engine
