"""
Allocation Repository
=====================

PHASE 3.4 - Data persistence for capital optimization.
"""

import time
from typing import Dict, List, Optional, Any

from .capital_types import (
    PortfolioCapital,
    StrategyPerformance,
    StrategyAllocation,
    CapitalEfficiency,
    RebalancePlan
)


class AllocationRepository:
    """
    Repository for capital optimization data:
    - Portfolio snapshots
    - Performance history
    - Allocation history
    - Rebalance history
    """
    
    def __init__(self):
        self._portfolio_snapshots: List[Dict[str, Any]] = []
        self._performance_history: Dict[str, List[StrategyPerformance]] = {}
        self._allocation_history: Dict[str, List[StrategyAllocation]] = {}
        self._efficiency_history: Dict[str, List[CapitalEfficiency]] = {}
        self._rebalance_history: List[RebalancePlan] = []
        
        print("[AllocationRepository] Initialized (PHASE 3.4)")
    
    # Portfolio snapshots
    def save_portfolio_snapshot(self, portfolio: PortfolioCapital):
        """Save portfolio snapshot"""
        self._portfolio_snapshots.append(portfolio.to_dict())
        if len(self._portfolio_snapshots) > 100:
            self._portfolio_snapshots = self._portfolio_snapshots[-100:]
    
    def get_portfolio_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get portfolio history"""
        return self._portfolio_snapshots[-limit:]
    
    # Performance history
    def save_performance(self, performance: StrategyPerformance):
        """Save performance snapshot"""
        strategy_id = performance.strategy_id
        if strategy_id not in self._performance_history:
            self._performance_history[strategy_id] = []
        
        self._performance_history[strategy_id].append(performance)
        
        if len(self._performance_history[strategy_id]) > 50:
            self._performance_history[strategy_id] = self._performance_history[strategy_id][-50:]
    
    def get_performance_history(self, strategy_id: str, limit: int = 20) -> List[StrategyPerformance]:
        """Get performance history for strategy"""
        history = self._performance_history.get(strategy_id, [])
        return history[-limit:]
    
    # Allocation history
    def save_allocation(self, allocation: StrategyAllocation):
        """Save allocation snapshot"""
        strategy_id = allocation.strategy_id
        if strategy_id not in self._allocation_history:
            self._allocation_history[strategy_id] = []
        
        self._allocation_history[strategy_id].append(allocation)
        
        if len(self._allocation_history[strategy_id]) > 50:
            self._allocation_history[strategy_id] = self._allocation_history[strategy_id][-50:]
    
    def get_allocation_history(self, strategy_id: str, limit: int = 20) -> List[StrategyAllocation]:
        """Get allocation history for strategy"""
        history = self._allocation_history.get(strategy_id, [])
        return history[-limit:]
    
    # Efficiency history
    def save_efficiency(self, efficiency: CapitalEfficiency):
        """Save efficiency snapshot"""
        strategy_id = efficiency.strategy_id
        if strategy_id not in self._efficiency_history:
            self._efficiency_history[strategy_id] = []
        
        self._efficiency_history[strategy_id].append(efficiency)
        
        if len(self._efficiency_history[strategy_id]) > 50:
            self._efficiency_history[strategy_id] = self._efficiency_history[strategy_id][-50:]
    
    def get_efficiency_history(self, strategy_id: str, limit: int = 20) -> List[CapitalEfficiency]:
        """Get efficiency history for strategy"""
        history = self._efficiency_history.get(strategy_id, [])
        return history[-limit:]
    
    # Rebalance history
    def save_rebalance(self, plan: RebalancePlan):
        """Save rebalance plan"""
        self._rebalance_history.append(plan)
        if len(self._rebalance_history) > 20:
            self._rebalance_history = self._rebalance_history[-20:]
    
    def get_rebalance_history(self, limit: int = 10) -> List[RebalancePlan]:
        """Get rebalance history"""
        return self._rebalance_history[-limit:]
    
    def get_last_rebalance(self) -> Optional[RebalancePlan]:
        """Get most recent rebalance plan"""
        return self._rebalance_history[-1] if self._rebalance_history else None
    
    # Clear
    def clear(self):
        """Clear all data"""
        self._portfolio_snapshots.clear()
        self._performance_history.clear()
        self._allocation_history.clear()
        self._efficiency_history.clear()
        self._rebalance_history.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        return {
            "portfolioSnapshots": len(self._portfolio_snapshots),
            "strategiesTracked": len(self._performance_history),
            "performanceRecords": sum(len(h) for h in self._performance_history.values()),
            "allocationRecords": sum(len(h) for h in self._allocation_history.values()),
            "efficiencyRecords": sum(len(h) for h in self._efficiency_history.values()),
            "rebalances": len(self._rebalance_history),
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
allocation_repository = AllocationRepository()
