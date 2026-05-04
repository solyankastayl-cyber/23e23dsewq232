"""
Capital Optimizer
=================

PHASE 3.4 - Core capital optimization engine.
"""

import time
from typing import Dict, List, Optional, Any

from .capital_types import (
    PortfolioCapital,
    StrategyPerformance,
    StrategyAllocation,
    CapitalEfficiency,
    RebalancePlan,
    PerformanceGrade,
    AllocationStatus
)
from .strategy_allocator import strategy_allocator
from .capital_efficiency_engine import capital_efficiency_engine


class CapitalOptimizer:
    """
    Capital Optimization Engine:
    - Portfolio capital management
    - Strategy allocation optimization
    - Performance-based rebalancing
    - Capital efficiency maximization
    """
    
    def __init__(self):
        # Portfolio configuration
        self._config = {
            "total_capital": 1000000.0,      # Default $1M
            "reserve_pct": 10.0,             # 10% reserve
            "max_drawdown_threshold": 20.0,  # 20% max DD
            "rebalance_threshold": 5.0,      # 5% drift triggers rebalance
            "min_trade_capital": 100.0       # Minimum per trade
        }
        
        # Portfolio state
        self._portfolio = PortfolioCapital(
            total_capital=self._config["total_capital"],
            reserved_capital=self._config["total_capital"] * self._config["reserve_pct"] / 100
        )
        
        # Strategy performances
        self._performances: Dict[str, StrategyPerformance] = {}
        
        # Strategy efficiencies
        self._efficiencies: Dict[str, CapitalEfficiency] = {}
        
        # Current regime
        self._current_regime = "RANGE"
        
        print("[CapitalOptimizer] Initialized (PHASE 3.4)")
    
    def set_total_capital(self, capital: float):
        """Set total portfolio capital"""
        self._config["total_capital"] = capital
        self._portfolio.total_capital = capital
        self._portfolio.reserved_capital = capital * self._config["reserve_pct"] / 100
        self._update_portfolio()
    
    def get_portfolio(self) -> PortfolioCapital:
        """Get current portfolio state"""
        self._update_portfolio()
        return self._portfolio
    
    def update_strategy_performance(
        self,
        strategy_id: str,
        trades: List[Dict[str, Any]],
        evaluation_days: int = 30
    ) -> StrategyPerformance:
        """Update performance metrics for a strategy"""
        
        perf = capital_efficiency_engine.calculate_performance(
            strategy_id=strategy_id,
            strategy_name=strategy_id.replace("_", " ").title(),
            trades=trades,
            evaluation_days=evaluation_days
        )
        
        self._performances[strategy_id] = perf
        
        # Update allocation with new performance
        strategy_allocator.update_allocation(
            strategy_id=strategy_id,
            performance=perf,
            regime=self._current_regime,
            total_capital=self._config["total_capital"]
        )
        
        # Calculate efficiency
        alloc = strategy_allocator.get_allocation(strategy_id)
        if alloc:
            efficiency = capital_efficiency_engine.calculate_efficiency(
                strategy_id=strategy_id,
                performance=perf,
                allocated_capital=alloc.allocated_capital,
                utilized_capital=alloc.utilized_capital,
                risk_taken=alloc.allocated_capital * 0.1  # Assume 10% risk
            )
            self._efficiencies[strategy_id] = efficiency
        
        self._update_portfolio()
        
        return perf
    
    def get_strategy_performance(self, strategy_id: str) -> Optional[StrategyPerformance]:
        """Get performance for a strategy"""
        return self._performances.get(strategy_id)
    
    def get_all_performances(self) -> List[StrategyPerformance]:
        """Get all strategy performances"""
        return list(self._performances.values())
    
    def get_strategy_efficiency(self, strategy_id: str) -> Optional[CapitalEfficiency]:
        """Get efficiency for a strategy"""
        return self._efficiencies.get(strategy_id)
    
    def get_all_efficiencies(self) -> List[CapitalEfficiency]:
        """Get all strategy efficiencies"""
        return list(self._efficiencies.values())
    
    def set_regime(self, regime: str):
        """Set current market regime"""
        self._current_regime = regime
        
        # Update all allocations
        for strategy_id in strategy_allocator.get_all_allocations():
            perf = self._performances.get(strategy_id.strategy_id)
            strategy_allocator.update_allocation(
                strategy_id=strategy_id.strategy_id,
                performance=perf,
                regime=regime,
                total_capital=self._config["total_capital"]
            )
        
        self._update_portfolio()
    
    def get_allocations(self) -> List[StrategyAllocation]:
        """Get all current allocations"""
        return strategy_allocator.get_all_allocations()
    
    def optimize_allocations(self) -> RebalancePlan:
        """Generate optimized allocation plan"""
        
        plan = strategy_allocator.generate_rebalance_plan(
            performances=self._performances,
            regime=self._current_regime,
            total_capital=self._config["total_capital"]
        )
        
        return plan
    
    def apply_rebalance(self, plan: RebalancePlan, step: int = 1) -> Dict[str, Any]:
        """Apply rebalancing plan"""
        
        result = strategy_allocator.apply_rebalance(
            plan=plan,
            step=step,
            total_capital=self._config["total_capital"]
        )
        
        self._update_portfolio()
        
        return result
    
    def get_capital_for_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """Get available capital for a strategy"""
        
        alloc = strategy_allocator.get_allocation(strategy_id)
        
        if not alloc or alloc.status == AllocationStatus.SUSPENDED:
            return {
                "strategyId": strategy_id,
                "available": 0.0,
                "reason": "Strategy suspended or not found",
                "canTrade": False
            }
        
        available = alloc.allocated_capital - alloc.utilized_capital
        can_trade = available >= self._config["min_trade_capital"]
        
        return {
            "strategyId": strategy_id,
            "allocated": round(alloc.allocated_capital, 2),
            "utilized": round(alloc.utilized_capital, 2),
            "available": round(max(0, available), 2),
            "canTrade": can_trade,
            "minTrade": self._config["min_trade_capital"]
        }
    
    def reserve_capital(
        self,
        strategy_id: str,
        amount: float,
        position_id: str
    ) -> Dict[str, Any]:
        """Reserve capital for a new position"""
        
        alloc = strategy_allocator.get_allocation(strategy_id)
        
        if not alloc:
            return {
                "success": False,
                "reason": "Strategy not found",
                "reserved": 0.0
            }
        
        if alloc.status == AllocationStatus.SUSPENDED:
            return {
                "success": False,
                "reason": "Strategy is suspended",
                "reserved": 0.0
            }
        
        available = alloc.allocated_capital - alloc.utilized_capital
        
        if amount > available:
            return {
                "success": False,
                "reason": f"Insufficient capital. Available: {available:.2f}",
                "reserved": 0.0
            }
        
        alloc.utilized_capital += amount
        alloc.available_capital = alloc.allocated_capital - alloc.utilized_capital
        
        self._update_portfolio()
        
        return {
            "success": True,
            "positionId": position_id,
            "reserved": round(amount, 2),
            "remaining": round(alloc.available_capital, 2)
        }
    
    def release_capital(
        self,
        strategy_id: str,
        amount: float,
        position_id: str,
        pnl: float = 0.0
    ) -> Dict[str, Any]:
        """Release capital when position closes"""
        
        alloc = strategy_allocator.get_allocation(strategy_id)
        
        if not alloc:
            return {
                "success": False,
                "reason": "Strategy not found"
            }
        
        alloc.utilized_capital = max(0, alloc.utilized_capital - amount)
        alloc.available_capital = alloc.allocated_capital - alloc.utilized_capital
        
        # Update PnL
        self._portfolio.total_pnl += pnl
        self._portfolio.daily_pnl += pnl
        
        self._update_portfolio()
        
        return {
            "success": True,
            "positionId": position_id,
            "released": round(amount, 2),
            "pnl": round(pnl, 2),
            "available": round(alloc.available_capital, 2)
        }
    
    def _update_portfolio(self):
        """Update portfolio state from allocations"""
        
        allocations = strategy_allocator.get_all_allocations()
        
        # Reset
        self._portfolio.allocated_capital = 0
        self._portfolio.utilized_capital = 0
        self._portfolio.strategy_allocations.clear()
        self._portfolio.strategy_utilizations.clear()
        
        for alloc in allocations:
            if alloc.status != AllocationStatus.SUSPENDED:
                self._portfolio.allocated_capital += alloc.allocated_capital
                self._portfolio.utilized_capital += alloc.utilized_capital
                self._portfolio.strategy_allocations[alloc.strategy_id] = alloc.current_allocation_pct
                self._portfolio.strategy_utilizations[alloc.strategy_id] = alloc.utilized_capital
        
        # Calculate metrics
        self._portfolio.available_capital = (
            self._portfolio.total_capital - 
            self._portfolio.utilized_capital - 
            self._portfolio.reserved_capital
        )
        
        if self._portfolio.total_capital > 0:
            self._portfolio.utilization_pct = (
                self._portfolio.utilized_capital / self._portfolio.total_capital * 100
            )
            self._portfolio.at_risk_pct = (
                self._portfolio.allocated_capital / self._portfolio.total_capital * 100
            )
            self._portfolio.portfolio_return_pct = (
                self._portfolio.total_pnl / self._portfolio.total_capital * 100
            )
        
        self._portfolio.updated_at = int(time.time() * 1000)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete optimization summary"""
        
        self._update_portfolio()
        
        # Strategy rankings
        rankings = []
        for perf in self._performances.values():
            eff = self._efficiencies.get(perf.strategy_id)
            alloc = strategy_allocator.get_allocation(perf.strategy_id)
            
            rankings.append({
                "strategyId": perf.strategy_id,
                "grade": perf.grade.value,
                "profitFactor": round(perf.profit_factor, 2),
                "winRate": round(perf.win_rate, 1),
                "efficiency": round(eff.efficiency_score, 1) if eff else 0,
                "allocation": round(alloc.current_allocation_pct, 1) if alloc else 0
            })
        
        rankings.sort(key=lambda x: x["efficiency"], reverse=True)
        
        return {
            "portfolio": self._portfolio.to_dict(),
            "rankings": rankings,
            "config": self._config,
            "regime": self._current_regime,
            "engines": {
                "allocator": strategy_allocator.get_health(),
                "efficiency": capital_efficiency_engine.get_health()
            },
            "timestamp": int(time.time() * 1000)
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        return {
            "engine": "CapitalOptimizer",
            "version": "1.0.0",
            "phase": "3.4",
            "status": "active",
            "portfolio": {
                "totalCapital": round(self._portfolio.total_capital, 0),
                "utilizationPct": round(self._portfolio.utilization_pct, 1),
                "pnl": round(self._portfolio.total_pnl, 2)
            },
            "strategies": {
                "tracked": len(self._performances),
                "withEfficiency": len(self._efficiencies)
            },
            "regime": self._current_regime,
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
capital_optimizer = CapitalOptimizer()
