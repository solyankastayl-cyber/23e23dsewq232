"""
Weight Allocator (S3.2)
=======================

Calculates allocation weights for eligible strategies.

Allocation Score Formula:
0.40 * ranking_score
0.30 * robustness_score
0.15 * calmar_norm
0.15 * low_dd_norm

Then normalize: weight_i = score_i / sum(scores)

Applies caps:
- max_weight_per_strategy
- min_weight_per_strategy
- max_strategies
"""

from typing import List, Dict, Any
import threading

from .allocation_types import (
    EligibleStrategy,
    StrategyAllocation,
    AllocationPolicy
)


class WeightAllocator:
    """
    Calculates and normalizes allocation weights.
    
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
        
        self._initialized = True
        print("[WeightAllocator] Initialized")
    
    # ===========================================
    # Calculate Weights
    # ===========================================
    
    def calculate_weights(
        self,
        eligible_strategies: List[EligibleStrategy],
        total_capital_usd: float,
        policy: AllocationPolicy
    ) -> List[StrategyAllocation]:
        """
        Calculate allocation weights for eligible strategies.
        
        Args:
            eligible_strategies: List of eligible strategies
            total_capital_usd: Total capital to allocate
            policy: Allocation policy
            
        Returns:
            List of StrategyAllocation with weights
        """
        if not eligible_strategies:
            return []
        
        # Step 1: Take only top N strategies
        top_strategies = eligible_strategies[:policy.max_strategies]
        
        # Step 2: Calculate allocation scores
        allocations = []
        for strategy in top_strategies:
            allocation = self._calculate_allocation_score(strategy, policy)
            allocations.append(allocation)
        
        # Step 3: Normalize to get raw weights
        self._normalize_weights(allocations)
        
        # Step 4: Apply caps
        self._apply_caps(allocations, policy)
        
        # Step 5: Calculate target capital
        for alloc in allocations:
            alloc.target_capital_usd = total_capital_usd * alloc.target_weight
        
        print(f"[WeightAllocator] Allocated {len(allocations)} strategies")
        return allocations
    
    def _calculate_allocation_score(
        self,
        strategy: EligibleStrategy,
        policy: AllocationPolicy
    ) -> StrategyAllocation:
        """
        Calculate allocation score for a strategy.
        
        Score = weighted combination of:
        - ranking_score
        - robustness_score
        - calmar (normalized)
        - low_dd (normalized)
        """
        # Normalize calmar (scale 0-3 to 0-1)
        calmar_norm = min(1.0, max(0.0, strategy.calmar_ratio / 3.0))
        
        # Normalize drawdown (lower is better, scale 0-35% to 1-0)
        dd_pct = strategy.max_drawdown_pct / 100.0 if strategy.max_drawdown_pct > 1 else strategy.max_drawdown_pct
        low_dd_norm = max(0.0, 1.0 - (dd_pct / 0.35))
        
        # Calculate allocation score
        allocation_score = (
            policy.weight_ranking * strategy.ranking_score +
            policy.weight_robustness * strategy.robustness_score +
            policy.weight_calmar * calmar_norm +
            policy.weight_low_dd * low_dd_norm
        )
        
        return StrategyAllocation(
            strategy_id=strategy.strategy_id,
            allocation_score=allocation_score,
            ranking_score=strategy.ranking_score,
            robustness_score=strategy.robustness_score,
            calmar_ratio=strategy.calmar_ratio,
            max_drawdown_pct=strategy.max_drawdown_pct,
            warnings=strategy.warnings.copy()
        )
    
    def _normalize_weights(self, allocations: List[StrategyAllocation]):
        """
        Normalize allocation scores to weights (sum = 1).
        """
        if not allocations:
            return
        
        total_score = sum(a.allocation_score for a in allocations)
        
        if total_score <= 0:
            # Equal weights if no valid scores
            equal_weight = 1.0 / len(allocations)
            for alloc in allocations:
                alloc.raw_weight = equal_weight
                alloc.target_weight = equal_weight
        else:
            for alloc in allocations:
                alloc.raw_weight = alloc.allocation_score / total_score
                alloc.target_weight = alloc.raw_weight
    
    def _apply_caps(
        self,
        allocations: List[StrategyAllocation],
        policy: AllocationPolicy
    ):
        """
        Apply weight caps and redistribute excess.
        """
        if not allocations:
            return
        
        max_weight = policy.max_weight_per_strategy
        min_weight = policy.min_weight_per_strategy
        
        # Track total capped
        iterations = 0
        max_iterations = 10
        
        while iterations < max_iterations:
            excess = 0.0
            uncapped_count = 0
            
            for alloc in allocations:
                if not alloc.capped:
                    if alloc.target_weight > max_weight:
                        excess += alloc.target_weight - max_weight
                        alloc.target_weight = max_weight
                        alloc.capped = True
                        alloc.cap_reason = f"Max cap applied ({max_weight*100:.0f}%)"
                    elif alloc.target_weight < min_weight:
                        # Check if strategy has enough score to justify min weight
                        if alloc.allocation_score > 0:
                            deficit = min_weight - alloc.target_weight
                            # This will be adjusted in redistribution
                            alloc.target_weight = min_weight
                            alloc.capped = True
                            alloc.cap_reason = f"Min cap applied ({min_weight*100:.0f}%)"
                        else:
                            alloc.enabled = False
                            alloc.target_weight = 0
                    else:
                        uncapped_count += 1
            
            # Redistribute excess to uncapped strategies
            if excess > 0 and uncapped_count > 0:
                redistribution = excess / uncapped_count
                for alloc in allocations:
                    if not alloc.capped and alloc.enabled:
                        alloc.target_weight += redistribution
            else:
                break
            
            iterations += 1
        
        # Final normalization to ensure sum = 1
        total_weight = sum(a.target_weight for a in allocations if a.enabled)
        if total_weight > 0 and abs(total_weight - 1.0) > 0.001:
            for alloc in allocations:
                if alloc.enabled:
                    alloc.target_weight /= total_weight


# Global singleton
weight_allocator = WeightAllocator()
