"""
PHASE 21.2 — Sleeve Limit Engine
================================
Sub-engine for sleeve-level capital limits.

Ensures no single category captures entire budget.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from modules.capital_allocation_v2.budget_constraints.capital_budget_types import (
    DEFAULT_SLEEVE_LIMITS,
    SleeveLimitState,
)


class SleeveLimitEngine:
    """
    Sleeve Limit Sub-Engine.
    
    Manages maximum allocation limits per sleeve:
    - Strategy sleeve
    - Factor sleeve
    - Asset sleeve
    - Cluster sleeve
    """
    
    def __init__(self):
        """Initialize engine."""
        self._limits = DEFAULT_SLEEVE_LIMITS.copy()
    
    def get_limits(self) -> Dict[str, float]:
        """Get current sleeve limits."""
        return self._limits.copy()
    
    def set_limit(self, sleeve: str, limit: float):
        """Set limit for a sleeve."""
        if sleeve in self._limits:
            self._limits[sleeve] = max(0.1, min(1.0, limit))
    
    def check_sleeve_limits(
        self,
        strategy_allocations: Dict[str, float],
        factor_allocations: Dict[str, float],
        asset_allocations: Dict[str, float],
        cluster_allocations: Dict[str, float],
    ) -> Dict[str, SleeveLimitState]:
        """
        Check all sleeve limits against current allocations.
        
        Returns dict of sleeve name -> SleeveLimitState.
        """
        results = {}
        
        # Strategy sleeve
        max_strategy = max(strategy_allocations.values()) if strategy_allocations else 0
        results["strategy"] = self._create_sleeve_state(
            "strategy", self._limits["strategy"], max_strategy
        )
        
        # Factor sleeve
        max_factor = max(factor_allocations.values()) if factor_allocations else 0
        results["factor"] = self._create_sleeve_state(
            "factor", self._limits["factor"], max_factor
        )
        
        # Asset sleeve
        max_asset = max(asset_allocations.values()) if asset_allocations else 0
        results["asset"] = self._create_sleeve_state(
            "asset", self._limits["asset"], max_asset
        )
        
        # Cluster sleeve
        max_cluster = max(cluster_allocations.values()) if cluster_allocations else 0
        results["cluster"] = self._create_sleeve_state(
            "cluster", self._limits["cluster"], max_cluster
        )
        
        return results
    
    def _create_sleeve_state(
        self,
        sleeve_name: str,
        max_limit: float,
        current_allocation: float,
    ) -> SleeveLimitState:
        """Create sleeve limit state."""
        utilization = current_allocation / max_limit if max_limit > 0 else 0
        headroom = max(0, max_limit - current_allocation)
        is_breached = current_allocation > max_limit
        
        return SleeveLimitState(
            sleeve_name=sleeve_name,
            max_limit=max_limit,
            current_allocation=current_allocation,
            utilization=utilization,
            headroom=headroom,
            is_breached=is_breached,
        )
    
    def get_breached_sleeves(
        self,
        sleeve_states: Dict[str, SleeveLimitState],
    ) -> List[str]:
        """Get list of breached sleeves."""
        return [name for name, state in sleeve_states.items() if state.is_breached]
    
    def get_utilization_score(
        self,
        sleeve_states: Dict[str, SleeveLimitState],
    ) -> float:
        """Calculate average sleeve utilization."""
        if not sleeve_states:
            return 0.0
        
        utilizations = [state.utilization for state in sleeve_states.values()]
        return sum(utilizations) / len(utilizations)


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[SleeveLimitEngine] = None


def get_sleeve_limit_engine() -> SleeveLimitEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = SleeveLimitEngine()
    return _engine
