"""
PHASE 21.1 — Strategy Capital Engine
====================================
Sub-engine for strategy-level capital allocation.

Uses Strategy Brain allocations as baseline,
adjusted by regime confidence and portfolio constraints.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from modules.capital_allocation_v2.capital_allocation_types import (
    AllocationSlice,
    StrategyAllocationInput,
)


class StrategyCapitalEngine:
    """
    Strategy Capital Allocation Sub-Engine.
    
    Distributes capital across strategies based on:
    - Strategy Brain allocations (baseline)
    - Regime confidence
    - Portfolio constraint state
    - Research loop modifiers
    """
    
    def __init__(self):
        """Initialize engine."""
        self._base_allocations: Dict[str, float] = {}
        self._initialize_baseline()
    
    def _initialize_baseline(self):
        """Initialize baseline strategy allocations."""
        # Default allocations from Strategy Brain patterns
        self._base_allocations = {
            "mean_reversion": 0.26,
            "funding_arb": 0.13,
            "structure_reversal": 0.14,
            "trend_following": 0.15,
            "breakout": 0.12,
            "liquidation_capture": 0.10,
            "flow_following": 0.10,
        }
    
    def compute_allocations(
        self,
        regime_confidence: float = 0.7,
        portfolio_modifier: float = 1.0,
        research_modifier: float = 1.0,
        active_strategies: Optional[List[str]] = None,
        reduced_strategies: Optional[List[str]] = None,
        disabled_strategies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compute strategy allocations.
        
        Returns:
            {
                "allocations": {strategy: allocation},
                "slices": [AllocationSlice],
                "total": float,
                "concentration": float,
            }
        """
        if active_strategies is None:
            active_strategies = list(self._base_allocations.keys())
        if reduced_strategies is None:
            reduced_strategies = []
        if disabled_strategies is None:
            disabled_strategies = []
        
        allocations = {}
        slices = []
        
        for strategy, base_alloc in self._base_allocations.items():
            # Determine status
            if strategy in disabled_strategies:
                status = "DISABLED"
                multiplier = 0.0
            elif strategy in reduced_strategies:
                status = "REDUCED"
                multiplier = 0.5
            else:
                status = "ACTIVE"
                multiplier = 1.0
            
            # Calculate adjusted allocation
            adjusted = base_alloc * multiplier * portfolio_modifier * research_modifier
            
            # Apply regime confidence boost for trend strategies in trend regime
            if "trend" in strategy.lower() and regime_confidence > 0.7:
                adjusted *= 1.1
            elif "reversion" in strategy.lower() and regime_confidence < 0.5:
                adjusted *= 1.15
            
            allocations[strategy] = adjusted
            
            slices.append(AllocationSlice(
                name=strategy,
                allocation=adjusted,
                weight=base_alloc,
                confidence=regime_confidence * multiplier,
                status=status,
            ))
        
        # Normalize allocations to sum to 1.0
        total = sum(allocations.values())
        if total > 0:
            allocations = {k: v / total for k, v in allocations.items()}
            for slice in slices:
                slice.allocation = slice.allocation / total if total > 0 else 0
        
        # Calculate concentration (max allocation)
        concentration = max(allocations.values()) if allocations else 0.0
        
        return {
            "allocations": allocations,
            "slices": slices,
            "total": 1.0,
            "concentration": concentration,
        }
    
    def get_dominant_strategy(self, allocations: Dict[str, float]) -> str:
        """Get strategy with highest allocation."""
        if not allocations:
            return "none"
        return max(allocations, key=allocations.get)


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[StrategyCapitalEngine] = None


def get_strategy_capital_engine() -> StrategyCapitalEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = StrategyCapitalEngine()
    return _engine
