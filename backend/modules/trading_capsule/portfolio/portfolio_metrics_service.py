"""
Portfolio Metrics Service (S4.3)
================================

Service for calculating portfolio-level metrics.

Features:
- Portfolio Sharpe, Sortino, Calmar
- Correlation matrix between strategies
- Equity curve
- Risk contribution analysis
- Diversification metrics
"""

import threading
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import defaultdict

from .portfolio_types import PortfolioState
from .portfolio_broker_types import PortfolioTrade
from .portfolio_metrics_types import (
    PortfolioMetrics,
    StrategyMetrics,
    CorrelationMatrix,
    EquityCurvePoint,
    RiskContribution
)
from .portfolio_repository import portfolio_repository
from .portfolio_broker_service import portfolio_broker_service


# ===========================================
# Statistical Helpers
# ===========================================

def calculate_mean(values: List[float]) -> float:
    """Calculate mean of values"""
    if not values:
        return 0.0
    return sum(values) / len(values)


def calculate_std(values: List[float]) -> float:
    """Calculate standard deviation"""
    if len(values) < 2:
        return 0.0
    mean = calculate_mean(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def calculate_downside_std(values: List[float], threshold: float = 0.0) -> float:
    """Calculate downside standard deviation"""
    downside = [min(0, x - threshold) for x in values]
    if len(downside) < 2:
        return 0.0
    mean = calculate_mean(downside)
    variance = sum((x - mean) ** 2 for x in downside) / (len(downside) - 1)
    return math.sqrt(variance)


def calculate_correlation(x: List[float], y: List[float]) -> float:
    """Calculate Pearson correlation between two series"""
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / (n - 1)
    std_x = calculate_std(x)
    std_y = calculate_std(y)
    
    if std_x == 0 or std_y == 0:
        return 0.0
    
    return cov / (std_x * std_y)


def annualize_return(total_return: float, days: int) -> float:
    """Annualize a return"""
    if days <= 0:
        return 0.0
    years = days / 365.0
    if years <= 0:
        return 0.0
    return (1 + total_return) ** (1 / years) - 1


def annualize_volatility(daily_vol: float) -> float:
    """Annualize daily volatility"""
    return daily_vol * math.sqrt(252)


# ===========================================
# Portfolio Metrics Service
# ===========================================

class PortfolioMetricsService:
    """
    Service for calculating portfolio metrics.
    
    Thread-safe singleton.
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
        self._metrics_cache: Dict[str, PortfolioMetrics] = {}
        self._correlation_cache: Dict[str, CorrelationMatrix] = {}
        
        self._initialized = True
        print("[PortfolioMetricsService] Initialized")
    
    # ===========================================
    # Portfolio Metrics
    # ===========================================
    
    def calculate_portfolio_metrics(
        self,
        simulation_id: str,
        force_recalculate: bool = False
    ) -> Optional[PortfolioMetrics]:
        """
        Calculate comprehensive portfolio metrics.
        """
        # Check cache
        if not force_recalculate and simulation_id in self._metrics_cache:
            return self._metrics_cache[simulation_id]
        
        simulation = portfolio_repository.get_simulation(simulation_id)
        if not simulation:
            return None
        
        current_state = portfolio_repository.get_latest_state(simulation_id)
        if not current_state:
            return None
        
        state_history = portfolio_repository.get_state_history(simulation_id)
        slots = portfolio_repository.get_slots_by_simulation(simulation_id)
        
        # Get all trades
        trades = portfolio_broker_service.get_all_trades(simulation_id, closed_only=True)
        
        # Calculate returns from state history
        returns = self._calculate_returns_from_states(state_history)
        
        # Basic metrics
        initial_capital = simulation.total_capital_usd
        final_equity = current_state.equity_usd
        total_return = final_equity - initial_capital
        total_return_pct = total_return / initial_capital if initial_capital > 0 else 0
        
        # Calculate simulation days
        sim_days = 1
        if state_history and len(state_history) > 1:
            first_state = state_history[-1]
            last_state = state_history[0]
            if first_state.timestamp and last_state.timestamp:
                delta = last_state.timestamp - first_state.timestamp
                sim_days = max(1, delta.days)
        
        # Volatility (annualized)
        daily_vol = calculate_std(returns) if returns else 0
        volatility = annualize_volatility(daily_vol)
        
        # Max drawdown
        max_dd_pct = self._calculate_max_drawdown(state_history)
        max_dd_usd = initial_capital * max_dd_pct
        
        # Average drawdown
        drawdowns = [s.drawdown_pct for s in state_history if s.drawdown_pct > 0]
        avg_dd_pct = calculate_mean(drawdowns) if drawdowns else 0
        
        # Risk-adjusted returns
        risk_free_rate = 0.02 / 252  # Daily risk-free rate
        excess_return = calculate_mean(returns) - risk_free_rate if returns else 0
        
        sharpe = excess_return / daily_vol * math.sqrt(252) if daily_vol > 0 else 0
        
        downside_vol = calculate_downside_std(returns)
        sortino = excess_return / downside_vol * math.sqrt(252) if downside_vol > 0 else 0
        
        ann_return = annualize_return(total_return_pct, sim_days)
        calmar = ann_return / max_dd_pct if max_dd_pct > 0 else 0
        
        # Trade stats
        winning_trades = [t for t in trades if t.realized_pnl_usd > 0]
        losing_trades = [t for t in trades if t.realized_pnl_usd < 0]
        
        gross_profit = sum(t.realized_pnl_usd for t in winning_trades)
        gross_loss = abs(sum(t.realized_pnl_usd for t in losing_trades))
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (9999.99 if gross_profit > 0 else 0)
        
        win_rate = len(winning_trades) / len(trades) if trades else 0
        expectancy = total_return / len(trades) if trades else 0
        
        # Diversification
        weights = [s.current_weight for s in slots if s.enabled]
        effective_n = 1.0 / sum(w ** 2 for w in weights) if weights and sum(w ** 2 for w in weights) > 0 else 0
        diversification_ratio = effective_n / len(slots) if slots else 0
        
        # Build metrics
        metrics = PortfolioMetrics(
            simulation_id=simulation_id,
            initial_capital_usd=initial_capital,
            final_equity_usd=final_equity,
            total_return_usd=total_return,
            total_return_pct=total_return_pct,
            annualized_return_pct=ann_return,
            volatility=volatility,
            max_drawdown_usd=max_dd_usd,
            max_drawdown_pct=max_dd_pct,
            avg_drawdown_pct=avg_dd_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            gross_profit_usd=gross_profit,
            gross_loss_usd=gross_loss,
            profit_factor=profit_factor,
            expectancy_usd=expectancy,
            num_strategies=len(slots),
            effective_num_strategies=effective_n,
            diversification_ratio=diversification_ratio,
            simulation_days=sim_days
        )
        
        # Cache
        self._metrics_cache[simulation_id] = metrics
        
        return metrics
    
    def _calculate_returns_from_states(
        self,
        states: List[PortfolioState]
    ) -> List[float]:
        """Calculate daily returns from state history"""
        if len(states) < 2:
            return []
        
        # States are sorted descending by time
        states = sorted(states, key=lambda s: s.timestamp)
        
        returns = []
        for i in range(1, len(states)):
            prev_equity = states[i - 1].equity_usd
            curr_equity = states[i].equity_usd
            if prev_equity > 0:
                ret = (curr_equity - prev_equity) / prev_equity
                returns.append(ret)
        
        return returns
    
    def _calculate_max_drawdown(
        self,
        states: List[PortfolioState]
    ) -> float:
        """Calculate maximum drawdown from state history"""
        if not states:
            return 0.0
        
        max_dd = max(s.drawdown_pct for s in states)
        return max_dd
    
    # ===========================================
    # Strategy Metrics
    # ===========================================
    
    def calculate_strategy_metrics(
        self,
        simulation_id: str,
        slot_id: str
    ) -> Optional[StrategyMetrics]:
        """Calculate metrics for a single strategy slot"""
        broker = portfolio_broker_service.get_slot_broker(simulation_id, slot_id)
        if not broker:
            return None
        
        slot = portfolio_repository.get_slot(slot_id)
        if not slot:
            return None
        
        # Get trades
        trades = [t for t in broker.trades if t.is_closed]
        winning = [t for t in trades if t.realized_pnl_usd > 0]
        losing = [t for t in trades if t.realized_pnl_usd < 0]
        
        # Returns
        initial_capital = slot.allocated_capital_usd
        current_equity = broker.get_equity()
        total_return = current_equity - initial_capital
        total_return_pct = total_return / initial_capital if initial_capital > 0 else 0
        
        # PnL stats
        total_pnl = sum(t.realized_pnl_usd for t in trades)
        avg_win = calculate_mean([t.realized_pnl_usd for t in winning]) if winning else 0
        avg_loss = calculate_mean([abs(t.realized_pnl_usd) for t in losing]) if losing else 0
        
        gross_profit = sum(t.realized_pnl_usd for t in winning)
        gross_loss = abs(sum(t.realized_pnl_usd for t in losing))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (9999.99 if gross_profit > 0 else 0)
        
        win_rate = len(winning) / len(trades) if trades else 0
        expectancy = total_pnl / len(trades) if trades else 0
        
        return StrategyMetrics(
            strategy_id=slot.strategy_id,
            slot_id=slot_id,
            total_return_pct=total_return_pct,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            total_pnl_usd=total_pnl,
            avg_win_usd=avg_win,
            avg_loss_usd=avg_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            current_weight=slot.current_weight,
            target_weight=slot.target_weight
        )
    
    def calculate_all_strategy_metrics(
        self,
        simulation_id: str
    ) -> List[StrategyMetrics]:
        """Calculate metrics for all strategies"""
        slots = portfolio_repository.get_slots_by_simulation(simulation_id)
        metrics = []
        
        for slot in slots:
            m = self.calculate_strategy_metrics(simulation_id, slot.slot_id)
            if m:
                metrics.append(m)
        
        return metrics
    
    # ===========================================
    # Correlation Matrix
    # ===========================================
    
    def calculate_correlation_matrix(
        self,
        simulation_id: str,
        force_recalculate: bool = False
    ) -> Optional[CorrelationMatrix]:
        """
        Calculate correlation matrix between strategies.
        
        Based on daily returns of each strategy.
        """
        # Check cache
        if not force_recalculate and simulation_id in self._correlation_cache:
            return self._correlation_cache[simulation_id]
        
        brokers = portfolio_broker_service.get_all_slot_brokers(simulation_id)
        if not brokers:
            return None
        
        # Collect daily returns per strategy
        strategy_returns: Dict[str, List[float]] = {}
        strategy_ids = []
        
        for slot_id, broker in brokers.items():
            slot = portfolio_repository.get_slot(slot_id)
            if not slot:
                continue
            
            # Simple returns from trades
            returns = []
            trades = [t for t in broker.trades if t.is_closed]
            for trade in trades:
                if trade.entry_notional_usd > 0:
                    ret = trade.realized_pnl_usd / trade.entry_notional_usd
                    returns.append(ret)
            
            if returns:
                strategy_returns[slot.strategy_id] = returns
                strategy_ids.append(slot.strategy_id)
        
        if len(strategy_ids) < 2:
            # Can't calculate correlation with less than 2 strategies
            return CorrelationMatrix(
                simulation_id=simulation_id,
                strategy_ids=strategy_ids,
                correlations={},
                avg_correlation=0.0,
                max_correlation=0.0,
                min_correlation=0.0
            )
        
        # Calculate pairwise correlations
        correlations = {}
        corr_values = []
        
        for i, strat_a in enumerate(strategy_ids):
            for j, strat_b in enumerate(strategy_ids):
                if i >= j:
                    continue
                
                returns_a = strategy_returns[strat_a]
                returns_b = strategy_returns[strat_b]
                
                # Align lengths
                min_len = min(len(returns_a), len(returns_b))
                if min_len < 2:
                    corr = 0.0
                else:
                    corr = calculate_correlation(returns_a[:min_len], returns_b[:min_len])
                
                key = f"{strat_a}:{strat_b}"
                correlations[key] = corr
                corr_values.append(corr)
        
        # Stats
        avg_corr = calculate_mean(corr_values) if corr_values else 0
        max_corr = max(corr_values) if corr_values else 0
        min_corr = min(corr_values) if corr_values else 0
        
        matrix = CorrelationMatrix(
            simulation_id=simulation_id,
            strategy_ids=strategy_ids,
            correlations=correlations,
            avg_correlation=avg_corr,
            max_correlation=max_corr,
            min_correlation=min_corr
        )
        
        # Cache
        self._correlation_cache[simulation_id] = matrix
        
        return matrix
    
    # ===========================================
    # Equity Curve
    # ===========================================
    
    def get_equity_curve(
        self,
        simulation_id: str,
        limit: int = 1000
    ) -> List[EquityCurvePoint]:
        """Get equity curve data points"""
        simulation = portfolio_repository.get_simulation(simulation_id)
        if not simulation:
            return []
        
        states = portfolio_repository.get_state_history(simulation_id, limit)
        if not states:
            return []
        
        initial_capital = simulation.total_capital_usd
        
        # States are sorted descending, reverse for chronological
        states = sorted(states, key=lambda s: s.timestamp)
        
        points = []
        for state in states:
            pnl = state.equity_usd - initial_capital
            pnl_pct = pnl / initial_capital if initial_capital > 0 else 0
            
            point = EquityCurvePoint(
                timestamp=state.timestamp,
                equity_usd=state.equity_usd,
                cash_usd=state.cash_usd,
                pnl_usd=pnl,
                pnl_pct=pnl_pct,
                drawdown_usd=state.drawdown_usd,
                drawdown_pct=state.drawdown_pct
            )
            points.append(point)
        
        return points
    
    # ===========================================
    # Risk Contribution
    # ===========================================
    
    def calculate_risk_contributions(
        self,
        simulation_id: str
    ) -> List[RiskContribution]:
        """Calculate risk contribution per strategy"""
        slots = portfolio_repository.get_slots_by_simulation(simulation_id)
        if not slots:
            return []
        
        contributions = []
        total_risk = 0.0
        
        # First pass: calculate individual volatilities
        slot_vols = {}
        for slot in slots:
            metrics = self.calculate_strategy_metrics(simulation_id, slot.slot_id)
            vol = metrics.volatility if metrics else 0.1  # Default 10%
            slot_vols[slot.slot_id] = vol
            total_risk += slot.current_weight * vol
        
        # Second pass: calculate contributions
        for slot in slots:
            vol = slot_vols.get(slot.slot_id, 0.1)
            weight = slot.current_weight
            
            marginal = vol  # Simplified: marginal contribution = vol
            component = weight * vol
            pct_contrib = component / total_risk if total_risk > 0 else 0
            
            contributions.append(RiskContribution(
                strategy_id=slot.strategy_id,
                slot_id=slot.slot_id,
                weight=weight,
                volatility=vol,
                marginal_contribution=marginal,
                component_contribution=component,
                pct_contribution=pct_contrib
            ))
        
        return contributions
    
    # ===========================================
    # Clear Cache
    # ===========================================
    
    def clear_cache(self, simulation_id: Optional[str] = None) -> None:
        """Clear metrics cache"""
        if simulation_id:
            self._metrics_cache.pop(simulation_id, None)
            self._correlation_cache.pop(simulation_id, None)
        else:
            self._metrics_cache.clear()
            self._correlation_cache.clear()
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "service": "PortfolioMetricsService",
            "status": "healthy",
            "version": "s4.3",
            "cached_metrics": len(self._metrics_cache),
            "cached_correlations": len(self._correlation_cache)
        }


# Global singleton
portfolio_metrics_service = PortfolioMetricsService()
