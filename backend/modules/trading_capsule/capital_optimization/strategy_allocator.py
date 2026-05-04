"""
Strategy Allocator
==================

PHASE 3.4 - Manages capital allocation across strategies.
"""

import time
from typing import Dict, List, Optional, Any

from .capital_types import (
    StrategyAllocation,
    StrategyPerformance,
    AllocationStatus,
    PerformanceGrade,
    RebalanceAction,
    RebalanceRecommendation,
    RebalancePlan
)


class StrategyAllocator:
    """
    Manages strategy allocations:
    - Base allocations
    - Dynamic adjustments based on performance
    - Regime-based adjustments
    - Rebalancing recommendations
    """
    
    def __init__(self):
        # Default strategies and base allocations
        self._default_allocations = {
            "TREND_CONFIRMATION": 25.0,
            "MEAN_REVERSION": 20.0,
            "MOMENTUM": 20.0,
            "BREAKOUT": 15.0,
            "SCALPING": 10.0,
            "SWING": 10.0
        }
        
        # Performance adjustment factors
        self._performance_adjustments = {
            PerformanceGrade.EXCELLENT: 1.3,
            PerformanceGrade.GOOD: 1.15,
            PerformanceGrade.AVERAGE: 1.0,
            PerformanceGrade.BELOW: 0.8,
            PerformanceGrade.POOR: 0.5
        }
        
        # Regime adjustments
        self._regime_adjustments = {
            "TRENDING": {
                "TREND_CONFIRMATION": 1.2,
                "MOMENTUM": 1.15,
                "MEAN_REVERSION": 0.8,
                "BREAKOUT": 1.1
            },
            "RANGE": {
                "TREND_CONFIRMATION": 0.85,
                "MEAN_REVERSION": 1.25,
                "MOMENTUM": 0.9,
                "SCALPING": 1.1
            },
            "HIGH_VOLATILITY": {
                "TREND_CONFIRMATION": 0.9,
                "BREAKOUT": 1.2,
                "SCALPING": 0.7,
                "SWING": 0.85
            }
        }
        
        # Allocation limits
        self._limits = {
            "min_allocation_pct": 5.0,
            "max_allocation_pct": 40.0,
            "max_adjustment_per_period": 10.0  # Max 10% change per rebalance
        }
        
        # Strategy allocations
        self._allocations: Dict[str, StrategyAllocation] = {}
        
        # Initialize default allocations
        self._initialize_defaults()
        
        print("[StrategyAllocator] Initialized (PHASE 3.4)")
    
    def _initialize_defaults(self):
        """Initialize default strategy allocations"""
        for strategy, base in self._default_allocations.items():
            self._allocations[strategy] = StrategyAllocation(
                strategy_id=strategy,
                strategy_name=strategy.replace("_", " ").title(),
                base_allocation_pct=base,
                current_allocation_pct=base,
                min_allocation_pct=self._limits["min_allocation_pct"],
                max_allocation_pct=self._limits["max_allocation_pct"],
                status=AllocationStatus.ACTIVE
            )
    
    def get_allocation(self, strategy_id: str) -> Optional[StrategyAllocation]:
        """Get allocation for a strategy"""
        return self._allocations.get(strategy_id)
    
    def get_all_allocations(self) -> List[StrategyAllocation]:
        """Get all allocations"""
        return list(self._allocations.values())
    
    def update_allocation(
        self,
        strategy_id: str,
        performance: Optional[StrategyPerformance] = None,
        regime: str = "RANGE",
        risk_factor: float = 1.0,
        total_capital: float = 1000000.0
    ) -> StrategyAllocation:
        """Update allocation based on performance and market conditions"""
        
        if strategy_id not in self._allocations:
            # Create new allocation
            self._allocations[strategy_id] = StrategyAllocation(
                strategy_id=strategy_id,
                strategy_name=strategy_id.replace("_", " ").title(),
                base_allocation_pct=10.0,  # Default
                current_allocation_pct=10.0,
                min_allocation_pct=self._limits["min_allocation_pct"],
                max_allocation_pct=self._limits["max_allocation_pct"],
                status=AllocationStatus.ACTIVE
            )
        
        alloc = self._allocations[strategy_id]
        
        # Performance adjustment
        if performance:
            alloc.performance = performance
            alloc.performance_adjustment = self._performance_adjustments.get(
                performance.grade, 1.0
            )
        
        # Regime adjustment
        regime_adj = self._regime_adjustments.get(regime, {})
        alloc.regime_adjustment = regime_adj.get(strategy_id, 1.0)
        
        # Risk adjustment
        alloc.risk_adjustment = risk_factor
        
        # Calculate new allocation
        combined = alloc.performance_adjustment * alloc.regime_adjustment * alloc.risk_adjustment
        new_allocation = alloc.base_allocation_pct * combined
        
        # Apply limits
        new_allocation = max(alloc.min_allocation_pct, min(alloc.max_allocation_pct, new_allocation))
        
        # Limit change per period
        max_change = self._limits["max_adjustment_per_period"]
        change = new_allocation - alloc.current_allocation_pct
        if abs(change) > max_change:
            change = max_change if change > 0 else -max_change
            new_allocation = alloc.current_allocation_pct + change
        
        # Update allocation
        alloc.current_allocation_pct = new_allocation
        alloc.allocated_capital = total_capital * (new_allocation / 100)
        
        # Update status based on allocation
        if new_allocation < self._limits["min_allocation_pct"] * 1.5:
            alloc.status = AllocationStatus.REDUCED
        elif performance and performance.grade == PerformanceGrade.POOR:
            alloc.status = AllocationStatus.SUSPENDED
        else:
            alloc.status = AllocationStatus.ACTIVE
        
        alloc.last_adjustment_at = int(time.time() * 1000)
        alloc.adjustment_reason = f"Performance: {alloc.performance_adjustment:.2f}x, Regime: {alloc.regime_adjustment:.2f}x"
        
        return alloc
    
    def generate_rebalance_plan(
        self,
        performances: Dict[str, StrategyPerformance],
        regime: str = "RANGE",
        total_capital: float = 1000000.0
    ) -> RebalancePlan:
        """Generate a rebalancing plan based on current performance"""
        
        plan = RebalancePlan(
            created_at=int(time.time() * 1000),
            valid_until=int(time.time() * 1000) + 24 * 3600 * 1000  # Valid for 24h
        )
        
        total_target = 0.0
        
        for strategy_id, alloc in self._allocations.items():
            perf = performances.get(strategy_id)
            
            # Calculate target allocation
            if perf:
                perf_adj = self._performance_adjustments.get(perf.grade, 1.0)
            else:
                perf_adj = 1.0
            
            regime_adj = self._regime_adjustments.get(regime, {}).get(strategy_id, 1.0)
            
            target = alloc.base_allocation_pct * perf_adj * regime_adj
            target = max(self._limits["min_allocation_pct"], min(self._limits["max_allocation_pct"], target))
            
            total_target += target
            
            change = target - alloc.current_allocation_pct
            
            # Create recommendation
            rec = RebalanceRecommendation(
                strategy_id=strategy_id,
                strategy_name=alloc.strategy_name,
                current_allocation_pct=alloc.current_allocation_pct,
                target_allocation_pct=target,
                change_pct=change,
                performance_grade=perf.grade if perf else PerformanceGrade.AVERAGE
            )
            
            # Determine action
            if change > 5:
                rec.action = RebalanceAction.INCREASE
                rec.priority = 2 if change > 10 else 3
                rec.reasons.append(f"Strong performance ({perf.grade.value if perf else 'N/A'})")
                plan.strategies_to_increase += 1
            elif change < -5:
                rec.action = RebalanceAction.DECREASE
                rec.priority = 2 if change < -10 else 3
                rec.reasons.append(f"Underperformance ({perf.grade.value if perf else 'N/A'})")
                plan.strategies_to_decrease += 1
            else:
                rec.action = RebalanceAction.MAINTAIN
                rec.priority = 5
                rec.reasons.append("Allocation within target range")
            
            if perf and perf.grade == PerformanceGrade.POOR:
                rec.action = RebalanceAction.SUSPEND
                rec.priority = 1
                rec.reasons.append("Poor performance - suspension recommended")
                plan.strategies_to_suspend += 1
            
            # Impact calculation
            rec.capital_change = (change / 100) * total_capital
            if perf and perf.expectancy != 0:
                rec.expected_improvement = rec.capital_change * (perf.expectancy / 1000)
            
            plan.recommendations.append(rec)
            plan.total_reallocation += abs(change)
        
        # Normalize to 100% if needed
        if abs(total_target - 100) > 1:
            scale = 100 / total_target
            for rec in plan.recommendations:
                rec.target_allocation_pct *= scale
                rec.change_pct = rec.target_allocation_pct - rec.current_allocation_pct
        
        # Sort by priority
        plan.recommendations.sort(key=lambda x: x.priority)
        
        # Execution recommendation
        if plan.total_reallocation > 20:
            plan.recommended_execution = "GRADUAL"
            plan.execution_steps = 3
        elif plan.total_reallocation > 10:
            plan.recommended_execution = "GRADUAL"
            plan.execution_steps = 2
        else:
            plan.recommended_execution = "IMMEDIATE"
            plan.execution_steps = 1
        
        # Expected outcomes
        plan.expected_efficiency_gain = sum(
            r.expected_improvement for r in plan.recommendations if r.expected_improvement > 0
        )
        plan.expected_risk_reduction = plan.strategies_to_suspend * 2 + plan.strategies_to_decrease * 0.5
        
        return plan
    
    def apply_rebalance(
        self,
        plan: RebalancePlan,
        step: int = 1,
        total_capital: float = 1000000.0
    ) -> Dict[str, Any]:
        """Apply a rebalancing plan (or step of it)"""
        
        results = []
        fraction = step / plan.execution_steps if plan.execution_steps > 0 else 1.0
        
        for rec in plan.recommendations:
            if rec.action == RebalanceAction.MAINTAIN:
                continue
            
            alloc = self._allocations.get(rec.strategy_id)
            if not alloc:
                continue
            
            # Calculate partial change for this step
            change = rec.change_pct * fraction
            new_alloc = alloc.current_allocation_pct + change
            
            # Apply
            alloc.current_allocation_pct = new_alloc
            alloc.allocated_capital = total_capital * (new_alloc / 100)
            alloc.last_adjustment_at = int(time.time() * 1000)
            alloc.adjustment_reason = f"Rebalance step {step}/{plan.execution_steps}"
            
            if rec.action == RebalanceAction.SUSPEND:
                alloc.status = AllocationStatus.SUSPENDED
            
            results.append({
                "strategyId": rec.strategy_id,
                "previousAllocation": round(alloc.current_allocation_pct - change, 1),
                "newAllocation": round(new_alloc, 1),
                "change": round(change, 1),
                "status": alloc.status.value
            })
        
        return {
            "step": step,
            "totalSteps": plan.execution_steps,
            "results": results,
            "timestamp": int(time.time() * 1000)
        }
    
    def set_allocation(
        self,
        strategy_id: str,
        allocation_pct: float,
        total_capital: float = 1000000.0
    ) -> StrategyAllocation:
        """Manually set allocation for a strategy"""
        
        if strategy_id not in self._allocations:
            self._allocations[strategy_id] = StrategyAllocation(
                strategy_id=strategy_id,
                strategy_name=strategy_id.replace("_", " ").title(),
                base_allocation_pct=allocation_pct,
                min_allocation_pct=self._limits["min_allocation_pct"],
                max_allocation_pct=self._limits["max_allocation_pct"],
                status=AllocationStatus.ACTIVE
            )
        
        alloc = self._allocations[strategy_id]
        alloc.base_allocation_pct = allocation_pct
        alloc.current_allocation_pct = allocation_pct
        alloc.allocated_capital = total_capital * (allocation_pct / 100)
        alloc.last_adjustment_at = int(time.time() * 1000)
        alloc.adjustment_reason = "Manual adjustment"
        
        return alloc
    
    def suspend_strategy(self, strategy_id: str, reason: str = "") -> bool:
        """Suspend a strategy"""
        if strategy_id in self._allocations:
            self._allocations[strategy_id].status = AllocationStatus.SUSPENDED
            self._allocations[strategy_id].adjustment_reason = reason or "Manually suspended"
            self._allocations[strategy_id].last_adjustment_at = int(time.time() * 1000)
            return True
        return False
    
    def activate_strategy(self, strategy_id: str) -> bool:
        """Reactivate a suspended strategy"""
        if strategy_id in self._allocations:
            self._allocations[strategy_id].status = AllocationStatus.ACTIVE
            self._allocations[strategy_id].adjustment_reason = "Reactivated"
            self._allocations[strategy_id].last_adjustment_at = int(time.time() * 1000)
            return True
        return False
    
    def get_total_allocation(self) -> float:
        """Get total allocation across all strategies"""
        return sum(a.current_allocation_pct for a in self._allocations.values() if a.status != AllocationStatus.SUSPENDED)
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        active = sum(1 for a in self._allocations.values() if a.status == AllocationStatus.ACTIVE)
        suspended = sum(1 for a in self._allocations.values() if a.status == AllocationStatus.SUSPENDED)
        
        return {
            "engine": "StrategyAllocator",
            "version": "1.0.0",
            "phase": "3.4",
            "status": "active",
            "strategies": {
                "total": len(self._allocations),
                "active": active,
                "suspended": suspended
            },
            "totalAllocation": round(self.get_total_allocation(), 1),
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
strategy_allocator = StrategyAllocator()
