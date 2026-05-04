"""
PHASE 19.2 — Strategy Allocation Engine
=======================================
Main engine for strategy capital allocation.

Combines:
- Strategy State Engine (from PHASE 19.1)
- Weight Engine
- Capital Engine

Outputs:
- StrategyAllocationState for each strategy
- StrategyAllocationSummary for global view
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from modules.strategy_brain.strategy_state_engine import get_strategy_state_engine
from modules.strategy_brain.strategy_types import StrategyStateEnum, STATE_MODIFIERS
from modules.strategy_brain.strategy_registry import get_all_strategies

from modules.strategy_brain.allocation.strategy_allocation_types import (
    StrategyAllocationState,
    StrategyAllocationSummary,
    BASE_WEIGHTS,
    STATE_MULTIPLIERS,
    CONFIDENCE_MODIFIER_MIN,
    CONFIDENCE_MODIFIER_MAX,
)
from modules.strategy_brain.allocation.strategy_weight_engine import get_weight_engine
from modules.strategy_brain.allocation.strategy_capital_engine import get_capital_engine


class StrategyAllocationEngine:
    """
    Strategy Allocation Engine - PHASE 19.2
    
    Computes capital allocation for each strategy
    based on strategy state and market conditions.
    """
    
    def __init__(self):
        """Initialize with dependent engines."""
        self.state_engine = get_strategy_state_engine()
        self.weight_engine = get_weight_engine()
        self.capital_engine = get_capital_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════
    
    def compute_allocation(
        self,
        strategy_name: str,
        symbol: str = "BTC",
    ) -> StrategyAllocationState:
        """
        Compute allocation for a single strategy.
        
        Args:
            strategy_name: Name of strategy
            symbol: Reference symbol for market context
        
        Returns:
            StrategyAllocationState with weights and modifiers
        """
        now = datetime.now(timezone.utc)
        
        # Get strategy state
        state = self.state_engine.compute_strategy_state(strategy_name, symbol)
        strategy_state = state.strategy_state.value
        
        # Get all states for normalization
        all_states = self._get_all_strategy_states(symbol)
        
        # Compute weights
        base_weight = self.weight_engine.get_base_weight(strategy_name)
        state_multiplier = STATE_MULTIPLIERS.get(strategy_state, 0.0)
        adjusted_weight = base_weight * state_multiplier
        
        # Compute capital shares for all (needed for normalization)
        adjusted_weights, capital_shares, confidence_modifiers = \
            self.capital_engine.compute_full_allocation(all_states)
        
        # Get this strategy's values
        capital_share = capital_shares.get(strategy_name, 0.0)
        confidence_modifier = confidence_modifiers.get(strategy_name, CONFIDENCE_MODIFIER_MIN)
        
        # Get capital modifier from state
        capital_modifier = STATE_MODIFIERS[state.strategy_state]["capital_modifier"]
        
        # Build reason
        reason = self._build_reason(strategy_name, strategy_state, capital_share)
        
        return StrategyAllocationState(
            strategy_name=strategy_name,
            strategy_state=strategy_state,
            base_weight=base_weight,
            state_multiplier=state_multiplier,
            adjusted_weight=adjusted_weight,
            capital_share=capital_share,
            capital_percent=capital_share * 100,
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            reason=reason,
            timestamp=now,
        )
    
    def compute_all_allocations(
        self,
        symbol: str = "BTC",
    ) -> List[StrategyAllocationState]:
        """
        Compute allocation for all strategies.
        
        Returns list of StrategyAllocationState.
        """
        now = datetime.now(timezone.utc)
        
        # Get all strategy states
        all_states = self._get_all_strategy_states(symbol)
        
        # Compute all weights and shares
        adjusted_weights, capital_shares, confidence_modifiers = \
            self.capital_engine.compute_full_allocation(all_states)
        
        allocations = []
        
        for strategy_name in get_all_strategies():
            strategy_state = all_states.get(strategy_name, "DISABLED")
            
            base_weight = self.weight_engine.get_base_weight(strategy_name)
            state_multiplier = STATE_MULTIPLIERS.get(strategy_state, 0.0)
            adjusted_weight = adjusted_weights.get(strategy_name, 0.0)
            capital_share = capital_shares.get(strategy_name, 0.0)
            confidence_modifier = confidence_modifiers.get(strategy_name, CONFIDENCE_MODIFIER_MIN)
            
            # Get capital modifier from state enum
            state_enum = StrategyStateEnum(strategy_state) if strategy_state in [e.value for e in StrategyStateEnum] else StrategyStateEnum.DISABLED
            capital_modifier = STATE_MODIFIERS[state_enum]["capital_modifier"]
            
            reason = self._build_reason(strategy_name, strategy_state, capital_share)
            
            allocations.append(StrategyAllocationState(
                strategy_name=strategy_name,
                strategy_state=strategy_state,
                base_weight=base_weight,
                state_multiplier=state_multiplier,
                adjusted_weight=adjusted_weight,
                capital_share=capital_share,
                capital_percent=capital_share * 100,
                confidence_modifier=confidence_modifier,
                capital_modifier=capital_modifier,
                reason=reason,
                timestamp=now,
            ))
        
        # Sort by capital share descending
        allocations.sort(key=lambda x: x.capital_share, reverse=True)
        
        return allocations
    
    def compute_summary(self, symbol: str = "BTC") -> StrategyAllocationSummary:
        """
        Compute aggregated allocation summary.
        
        Returns StrategyAllocationSummary with global view.
        """
        now = datetime.now(timezone.utc)
        
        # Get all allocations
        allocations = self.compute_all_allocations(symbol)
        
        # Build allocation dicts
        allocations_dict: Dict[str, float] = {}
        allocations_percent: Dict[str, float] = {}
        
        active_strategies = []
        reduced_strategies = []
        disabled_strategies = []
        
        active_capital = 0.0
        reduced_capital = 0.0
        
        for alloc in allocations:
            allocations_dict[alloc.strategy_name] = alloc.capital_share
            allocations_percent[alloc.strategy_name] = alloc.capital_percent
            
            if alloc.strategy_state == "ACTIVE":
                active_strategies.append(alloc.strategy_name)
                active_capital += alloc.capital_share
            elif alloc.strategy_state == "REDUCED":
                reduced_strategies.append(alloc.strategy_name)
                reduced_capital += alloc.capital_share
            else:
                disabled_strategies.append(alloc.strategy_name)
        
        return StrategyAllocationSummary(
            total_capital=1.0,
            allocations=allocations_dict,
            allocations_percent=allocations_percent,
            active_strategies=active_strategies,
            reduced_strategies=reduced_strategies,
            disabled_strategies=disabled_strategies,
            total_strategies=len(allocations),
            active_count=len(active_strategies),
            reduced_count=len(reduced_strategies),
            disabled_count=len(disabled_strategies),
            active_capital=active_capital,
            reduced_capital=reduced_capital,
            allocation_states=allocations,
            timestamp=now,
        )
    
    # ═══════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════
    
    def _get_all_strategy_states(self, symbol: str) -> Dict[str, str]:
        """Get all strategy states as dict."""
        states = self.state_engine.compute_all_strategies(symbol)
        return {s.strategy_name: s.strategy_state.value for s in states}
    
    def _build_reason(
        self,
        strategy_name: str,
        strategy_state: str,
        capital_share: float,
    ) -> str:
        """Build allocation reason string."""
        if capital_share == 0:
            return f"{strategy_state.lower()}_no_allocation"
        elif capital_share > 0.2:
            return f"{strategy_state.lower()}_high_allocation"
        elif capital_share > 0.1:
            return f"{strategy_state.lower()}_medium_allocation"
        else:
            return f"{strategy_state.lower()}_low_allocation"


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[StrategyAllocationEngine] = None


def get_allocation_engine() -> StrategyAllocationEngine:
    """Get singleton allocation engine instance."""
    global _engine
    if _engine is None:
        _engine = StrategyAllocationEngine()
    return _engine
