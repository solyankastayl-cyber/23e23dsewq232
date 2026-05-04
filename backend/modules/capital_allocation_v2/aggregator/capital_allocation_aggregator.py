"""
PHASE 21.3 — Capital Allocation Aggregator
==========================================
Main aggregator for Capital Allocation Layer.

Combines:
- Core Allocator (PHASE 21.1)
- Budget Constraints (PHASE 21.2)

Into unified Capital Allocation Layer.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from modules.capital_allocation_v2.aggregator.capital_allocation_layer_types import (
    CapitalAllocationLayerState,
    AllocationState,
    ALLOCATION_STATE_THRESHOLDS,
)
from modules.capital_allocation_v2.aggregator.capital_allocation_registry import (
    get_capital_allocation_registry,
    CapitalAllocationRegistry,
)

# Import sub-engines
from modules.capital_allocation_v2.capital_router_engine import (
    get_capital_router_engine,
    CapitalRouterEngine,
)
from modules.capital_allocation_v2.budget_constraints.capital_budget_engine import (
    get_capital_budget_engine,
    CapitalBudgetEngine,
)
from modules.capital_allocation_v2.budget_constraints.capital_budget_types import (
    BudgetState,
)


class CapitalAllocationAggregator:
    """
    Capital Allocation Aggregator - PHASE 21.3
    
    Unified Capital Allocation Layer combining:
    - Core Allocator: Strategy/Factor/Asset/Cluster routing
    - Budget Engine: Constraints, reserves, dry powder
    
    Outputs unified state for Trading Product integration.
    """
    
    def __init__(self):
        """Initialize aggregator."""
        self.registry = get_capital_allocation_registry()
        self.allocator = get_capital_router_engine()
        self.budget_engine = get_capital_budget_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════
    
    def compute_layer_state(
        self,
        total_capital: float = 1.0,
        market_regime: Optional[str] = None,
        btc_dominance: Optional[float] = None,
        regime_confidence: float = 0.7,
        portfolio_state: str = "NORMAL",
        risk_state: str = "NORMAL",
        loop_state: str = "HEALTHY",
        volatility_state: str = "NORMAL",
        portfolio_capital_modifier: float = 1.0,
        loop_capital_modifier: float = 1.0,
    ) -> CapitalAllocationLayerState:
        """
        Compute unified Capital Allocation Layer state.
        
        Returns CapitalAllocationLayerState with all integrated data.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Get Core Allocator state
        allocator_state = self.allocator.compute_allocation(
            total_capital=total_capital,
            market_regime=market_regime,
            btc_dominance=btc_dominance,
            regime_confidence=regime_confidence,
            portfolio_modifier=portfolio_capital_modifier,
            research_modifier=loop_capital_modifier,
        )
        
        # 2. Get Budget state
        budget_state = self.budget_engine.compute_budget(
            total_capital=total_capital,
            regime=market_regime or "MIXED",
            portfolio_state=portfolio_state,
            risk_state=risk_state,
            loop_state=loop_state,
            volatility_state=volatility_state,
            regime_confidence=regime_confidence,
            allocation_confidence=allocator_state.allocation_confidence,
            portfolio_capital_modifier=portfolio_capital_modifier,
            loop_capital_modifier=loop_capital_modifier,
        )
        
        # 3. Calculate capital efficiency
        capital_efficiency = self._calculate_capital_efficiency(
            deployable_capital=budget_state.deployable_capital,
            allocation_confidence=allocator_state.allocation_confidence,
            concentration_score=allocator_state.concentration_score,
        )
        
        # 4. Calculate combined modifiers
        confidence_modifier, capital_modifier = self._calculate_combined_modifiers(
            allocator_confidence_mod=allocator_state.confidence_modifier,
            allocator_capital_mod=allocator_state.capital_modifier,
            budget_confidence_mod=budget_state.confidence_modifier,
            budget_capital_mod=budget_state.capital_modifier,
        )
        
        # 5. Determine allocation state
        allocation_state = self._determine_allocation_state(
            budget_state=budget_state.budget_state,
            capital_efficiency=capital_efficiency,
            allocation_confidence=allocator_state.allocation_confidence,
            concentration_score=allocator_state.concentration_score,
        )
        
        # 6. Build reason
        reason = self._build_reason(
            allocation_state=allocation_state,
            allocator_state=allocator_state,
            budget_state=budget_state,
            capital_efficiency=capital_efficiency,
        )
        
        return CapitalAllocationLayerState(
            total_capital=total_capital,
            deployable_capital=budget_state.deployable_capital,
            reserve_capital=budget_state.reserve_capital,
            dry_powder=budget_state.dry_powder,
            
            strategy_allocations=allocator_state.strategy_allocations,
            factor_allocations=allocator_state.factor_allocations,
            asset_allocations=allocator_state.asset_allocations,
            cluster_allocations=allocator_state.cluster_allocations,
            
            dominant_route=allocator_state.dominant_route.value,
            routing_regime=allocator_state.routing_regime.value,
            
            budget_state=budget_state.budget_state.value,
            budget_multiplier=budget_state.final_budget_multiplier,
            
            allocation_confidence=allocator_state.allocation_confidence,
            concentration_score=allocator_state.concentration_score,
            capital_efficiency=capital_efficiency,
            
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            
            allocation_state=allocation_state,
            
            reason=reason,
            timestamp=now,
        )
    
    def recompute(self) -> CapitalAllocationLayerState:
        """
        Recompute layer state and record to registry.
        """
        state = self.compute_layer_state()
        self.registry.record_state(state)
        return state
    
    def get_current_state(self) -> Optional[CapitalAllocationLayerState]:
        """Get current state from registry."""
        return self.registry.get_current_state()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get layer summary."""
        state = self.compute_layer_state()
        return state.to_summary()
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get detailed state information."""
        state = self.compute_layer_state()
        return {
            "allocation_state": state.allocation_state.value,
            "budget_state": state.budget_state,
            "capital_efficiency": round(state.capital_efficiency, 4),
            "deployable_capital": round(state.deployable_capital, 4),
            "confidence_modifier": round(state.confidence_modifier, 4),
            "capital_modifier": round(state.capital_modifier, 4),
            "reason": state.reason,
        }
    
    # ═══════════════════════════════════════════════════════════
    # INTERNAL METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_capital_efficiency(
        self,
        deployable_capital: float,
        allocation_confidence: float,
        concentration_score: float,
    ) -> float:
        """
        Calculate capital efficiency.
        
        Formula:
        capital_efficiency = deployable_capital × allocation_confidence × (1 - concentration_score)
        
        Normalized to 0..1.
        """
        efficiency = (
            deployable_capital *
            allocation_confidence *
            (1.0 - concentration_score)
        )
        
        return max(0.0, min(1.0, efficiency))
    
    def _calculate_combined_modifiers(
        self,
        allocator_confidence_mod: float,
        allocator_capital_mod: float,
        budget_confidence_mod: float,
        budget_capital_mod: float,
    ) -> Tuple[float, float]:
        """
        Calculate combined modifiers from allocator and budget.
        
        confidence_modifier = allocator × budget
        capital_modifier = allocator × budget
        
        Bounded: confidence [0.75, 1.20], capital [0.70, 1.15]
        """
        confidence_modifier = allocator_confidence_mod * budget_confidence_mod
        capital_modifier = allocator_capital_mod * budget_capital_mod
        
        # Bound to reasonable ranges
        confidence_modifier = max(0.75, min(1.20, confidence_modifier))
        capital_modifier = max(0.70, min(1.15, capital_modifier))
        
        return round(confidence_modifier, 4), round(capital_modifier, 4)
    
    def _determine_allocation_state(
        self,
        budget_state: BudgetState,
        capital_efficiency: float,
        allocation_confidence: float,
        concentration_score: float,
    ) -> AllocationState:
        """
        Determine overall allocation state.
        
        OPTIMAL: budget OPEN, high confidence, low concentration
        BALANCED: budget THROTTLED, normal confidence
        CONSTRAINED: budget DEFENSIVE or high concentration
        STRESSED: budget EMERGENCY or very low efficiency
        """
        thresholds = ALLOCATION_STATE_THRESHOLDS
        
        # STRESSED conditions
        if budget_state == BudgetState.EMERGENCY:
            return AllocationState.STRESSED
        
        if capital_efficiency < thresholds["efficiency_stressed"]:
            return AllocationState.STRESSED
        
        # CONSTRAINED conditions
        if budget_state == BudgetState.DEFENSIVE:
            return AllocationState.CONSTRAINED
        
        if concentration_score > thresholds["concentration_high"]:
            return AllocationState.CONSTRAINED
        
        # OPTIMAL conditions
        if budget_state == BudgetState.OPEN:
            if (allocation_confidence >= thresholds["confidence_high"] and
                capital_efficiency >= thresholds["efficiency_optimal"]):
                return AllocationState.OPTIMAL
        
        # BALANCED is the default
        if capital_efficiency >= thresholds["efficiency_balanced"]:
            return AllocationState.BALANCED
        
        # Low efficiency but not stressed
        return AllocationState.CONSTRAINED
    
    def _build_reason(
        self,
        allocation_state: AllocationState,
        allocator_state,
        budget_state,
        capital_efficiency: float,
    ) -> str:
        """Build human-readable reason."""
        parts = []
        
        # Routing regime
        parts.append(f"{allocator_state.routing_regime.value.lower()} regime")
        
        # Budget state
        budget_desc = {
            BudgetState.OPEN: "open budget",
            BudgetState.THROTTLED: "throttled budget",
            BudgetState.DEFENSIVE: "defensive budget",
            BudgetState.EMERGENCY: "emergency budget",
        }
        parts.append(budget_desc.get(budget_state.budget_state, "unknown budget"))
        
        # Allocation quality
        if allocation_state == AllocationState.OPTIMAL:
            parts.append("optimal allocations")
        elif allocation_state == AllocationState.BALANCED:
            parts.append("balanced allocations")
        elif allocation_state == AllocationState.CONSTRAINED:
            parts.append("constrained allocations")
        else:
            parts.append("stressed allocations")
        
        # Efficiency note
        if capital_efficiency > 0.5:
            parts.append(f"high efficiency ({capital_efficiency:.0%})")
        elif capital_efficiency < 0.2:
            parts.append(f"low efficiency ({capital_efficiency:.0%})")
        
        return " with ".join(parts[:3])


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_aggregator: Optional[CapitalAllocationAggregator] = None


def get_capital_allocation_aggregator() -> CapitalAllocationAggregator:
    """Get singleton aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = CapitalAllocationAggregator()
    return _aggregator
