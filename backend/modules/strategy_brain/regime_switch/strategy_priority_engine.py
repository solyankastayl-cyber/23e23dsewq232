"""
PHASE 19.3 — Strategy Priority Engine
=====================================
Computes strategy priorities based on regime and modifiers.

Process:
1. Get regime configuration
2. Determine primary/secondary/inactive
3. Apply modifiers
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from modules.strategy_brain.strategy_registry import get_all_strategies
from modules.strategy_brain.regime_switch.strategy_regime_types import (
    PRIORITY_MODIFIERS,
    StrategyPriorityState,
)
from modules.strategy_brain.regime_switch.strategy_regime_map import (
    get_regime_config,
    RegimeStrategyConfig,
)


class StrategyPriorityEngine:
    """
    Strategy Priority Engine.
    
    Determines strategy priorities based on market regime.
    """
    
    def __init__(self):
        """Initialize priority engine."""
        self.all_strategies = get_all_strategies()
    
    def compute_priorities(
        self,
        regime_name: str,
        regime_confidence: float,
        scores: Optional[Dict[str, float]] = None,
    ) -> StrategyPriorityState:
        """
        Compute strategy priorities for a regime.
        
        Args:
            regime_name: Current market regime
            regime_confidence: Confidence in regime detection
            scores: Optional breakdown scores
        
        Returns:
            StrategyPriorityState with priorities and modifiers
        """
        now = datetime.now(timezone.utc)
        scores = scores or {}
        
        # Get regime config
        config = get_regime_config(regime_name)
        
        # Determine priorities
        primary, secondary, inactive = self._categorize_strategies(config)
        
        # Select primary strategy (first in list)
        primary_strategy = primary[0] if primary else "funding_arb"
        
        # Compute modifiers
        strategy_modifiers = self._compute_modifiers(primary, secondary, inactive)
        
        # Build reason
        reason = self._build_reason(regime_name, primary_strategy, regime_confidence)
        
        return StrategyPriorityState(
            market_regime=regime_name,
            regime_confidence=regime_confidence,
            primary_strategy=primary_strategy,
            secondary_strategies=secondary,
            inactive_strategies=inactive,
            strategy_modifiers=strategy_modifiers,
            regime_score=scores.get("regime", 0.0),
            volatility_score=scores.get("volatility", 0.0),
            breadth_score=scores.get("breadth", 0.0),
            interaction_score=scores.get("interaction", 0.0),
            ecology_score=scores.get("ecology", 0.0),
            timestamp=now,
            reason=reason,
        )
    
    def _categorize_strategies(
        self,
        config: Optional[RegimeStrategyConfig],
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Categorize strategies into primary/secondary/inactive.
        
        Returns tuple of (primary, secondary, inactive) lists.
        """
        if config is None:
            # Default: funding_arb primary, rest inactive
            return ["funding_arb"], [], [
                s for s in self.all_strategies if s != "funding_arb"
            ]
        
        primary = config.primary_strategies.copy()
        secondary = config.secondary_strategies.copy()
        
        # Anti strategies go to inactive
        inactive = config.anti_strategies.copy()
        
        # Remaining strategies go to inactive too
        categorized = set(primary + secondary + inactive)
        for strategy in self.all_strategies:
            if strategy not in categorized:
                inactive.append(strategy)
        
        return primary, secondary, inactive
    
    def _compute_modifiers(
        self,
        primary: List[str],
        secondary: List[str],
        inactive: List[str],
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute modifiers for each strategy based on priority.
        """
        modifiers = {}
        
        for strategy in primary:
            modifiers[strategy] = PRIORITY_MODIFIERS["primary"].copy()
        
        for strategy in secondary:
            modifiers[strategy] = PRIORITY_MODIFIERS["secondary"].copy()
        
        for strategy in inactive:
            modifiers[strategy] = PRIORITY_MODIFIERS["inactive"].copy()
        
        return modifiers
    
    def _build_reason(
        self,
        regime_name: str,
        primary_strategy: str,
        regime_confidence: float,
    ) -> str:
        """Build reason string."""
        confidence_level = "high" if regime_confidence >= 0.7 else "medium" if regime_confidence >= 0.5 else "low"
        return f"{regime_name.lower()}_{confidence_level}_confidence_{primary_strategy}_primary"
    
    def get_priority_level(
        self,
        strategy_name: str,
        priority_state: StrategyPriorityState,
    ) -> str:
        """Get priority level for a strategy."""
        if strategy_name == priority_state.primary_strategy:
            return "primary"
        elif strategy_name in priority_state.secondary_strategies:
            return "secondary"
        else:
            return "inactive"


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[StrategyPriorityEngine] = None


def get_priority_engine() -> StrategyPriorityEngine:
    """Get singleton priority engine instance."""
    global _engine
    if _engine is None:
        _engine = StrategyPriorityEngine()
    return _engine
