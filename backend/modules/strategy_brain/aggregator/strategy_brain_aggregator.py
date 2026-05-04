"""
PHASE 19.4 — Strategy Brain Aggregator
=====================================
Main aggregator for Strategy Brain.

Combines:
- Strategy State Engine (active/reduced/disabled)
- Allocation Engine (capital shares)
- Regime Switch Engine (primary/secondary, regime)

Outputs:
- Unified StrategyBrainState
- Trading Product overlay block
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.strategy_brain.strategy_state_engine import get_strategy_state_engine
from modules.strategy_brain.strategy_types import STATE_MODIFIERS, StrategyStateEnum
from modules.strategy_brain.allocation import get_allocation_engine
from modules.strategy_brain.regime_switch import get_regime_switch_engine, PRIORITY_MODIFIERS

from modules.strategy_brain.aggregator.strategy_brain_types import (
    StrategyBrainState,
    StrategyOverlayEffect,
    RecommendedBias,
    STRATEGY_BIAS_MAP,
    CONFIDENCE_MODIFIER_MIN,
    CONFIDENCE_MODIFIER_MAX,
    CAPITAL_MODIFIER_MIN,
    CAPITAL_MODIFIER_MAX,
)


class StrategyBrainAggregator:
    """
    Strategy Brain Aggregator - PHASE 19.4
    
    Aggregates all Strategy Brain components into
    a unified overlay for Trading Product.
    """
    
    def __init__(self):
        """Initialize with dependent engines."""
        self.state_engine = get_strategy_state_engine()
        self.allocation_engine = get_allocation_engine()
        self.regime_engine = get_regime_switch_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════
    
    def compute_aggregate(self, symbol: str = "BTC") -> StrategyBrainState:
        """
        Compute aggregated Strategy Brain state.
        
        Args:
            symbol: Reference symbol for market context
        
        Returns:
            StrategyBrainState with unified overlay
        """
        now = datetime.now(timezone.utc)
        
        # Get state summary
        state_summary = self.state_engine.compute_summary(symbol)
        
        # Get allocation summary
        alloc_summary = self.allocation_engine.compute_summary(symbol)
        
        # Get regime priority
        regime_priority = self.regime_engine.compute_regime_priority(symbol)
        
        # Extract data
        active_strategies = state_summary.active_strategies
        reduced_strategies = state_summary.reduced_strategies
        disabled_strategies = state_summary.disabled_strategies
        
        primary_strategy = regime_priority.primary_strategy
        secondary_strategies = regime_priority.secondary_strategies
        
        market_regime = regime_priority.market_regime
        regime_confidence = regime_priority.regime_confidence
        
        # Get allocations (only for non-disabled)
        allocations = {
            k: v for k, v in alloc_summary.allocations.items()
            if v > 0
        }
        
        # Compute modifiers
        confidence_modifier, conf_breakdown = self._compute_confidence_modifier(
            primary_strategy=primary_strategy,
            active_strategies=active_strategies,
            regime_confidence=regime_confidence,
            regime_priority=regime_priority,
        )
        
        capital_modifier, cap_breakdown = self._compute_capital_modifier(
            primary_strategy=primary_strategy,
            allocations=allocations,
            active_capital=alloc_summary.active_capital,
            regime_priority=regime_priority,
        )
        
        # Determine overlay effect
        overlay_effect = self._determine_overlay_effect(
            primary_strategy=primary_strategy,
            active_strategies=active_strategies,
            regime_confidence=regime_confidence,
            confidence_modifier=confidence_modifier,
            allocations=allocations,
        )
        
        # Determine recommended bias
        recommended_bias = self._determine_bias(primary_strategy, regime_confidence)
        
        # Build reason
        reason = self._build_reason(
            market_regime=market_regime,
            primary_strategy=primary_strategy,
            overlay_effect=overlay_effect,
            regime_confidence=regime_confidence,
        )
        
        return StrategyBrainState(
            market_regime=market_regime,
            regime_confidence=regime_confidence,
            active_strategies=active_strategies,
            reduced_strategies=reduced_strategies,
            disabled_strategies=disabled_strategies,
            primary_strategy=primary_strategy,
            secondary_strategies=secondary_strategies,
            allocations=allocations,
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            strategy_overlay_effect=overlay_effect,
            recommended_bias=recommended_bias,
            reason=reason,
            active_count=len(active_strategies),
            reduced_count=len(reduced_strategies),
            disabled_count=len(disabled_strategies),
            primary_confidence_score=conf_breakdown.get("primary_score", 0.0),
            active_avg_modifier=conf_breakdown.get("active_avg", 0.0),
            regime_normalized=conf_breakdown.get("regime_norm", 0.0),
            allocation_normalized=cap_breakdown.get("alloc_norm", 0.0),
            timestamp=now,
        )
    
    def get_trading_product_overlay(self, symbol: str = "BTC") -> Dict[str, Any]:
        """
        Get Strategy Brain overlay for Trading Product.
        
        Returns block ready for Trading Product snapshot.
        """
        state = self.compute_aggregate(symbol)
        return state.to_trading_product_block()
    
    def get_summary(self, symbol: str = "BTC") -> Dict[str, Any]:
        """Get compact summary."""
        state = self.compute_aggregate(symbol)
        return state.to_summary()
    
    # ═══════════════════════════════════════════════════════════
    # MODIFIER CALCULATIONS
    # ═══════════════════════════════════════════════════════════
    
    def _compute_confidence_modifier(
        self,
        primary_strategy: str,
        active_strategies: List[str],
        regime_confidence: float,
        regime_priority,
    ) -> tuple:
        """
        Compute confidence modifier.
        
        Formula:
            0.40 * primary_strategy_confidence_modifier
          + 0.30 * avg_active_strategy_modifier
          + 0.30 * regime_confidence_normalized
        
        Returns (modifier, breakdown_dict)
        """
        breakdown = {}
        
        # Primary strategy confidence modifier
        primary_mods = regime_priority.get_modifier_for_strategy(primary_strategy)
        primary_conf_mod = primary_mods.get("confidence_modifier", 1.0)
        breakdown["primary_score"] = primary_conf_mod
        
        # Average active strategy modifier
        if active_strategies:
            active_mods = []
            for s in active_strategies:
                s_mods = regime_priority.get_modifier_for_strategy(s)
                active_mods.append(s_mods.get("confidence_modifier", 1.0))
            active_avg = sum(active_mods) / len(active_mods)
        else:
            active_avg = 0.85  # Default penalty if no active
        breakdown["active_avg"] = active_avg
        
        # Regime confidence normalized (0.5-1.0 → 0.85-1.15)
        regime_norm = 0.85 + (regime_confidence * 0.30)
        breakdown["regime_norm"] = regime_norm
        
        # Weighted calculation
        confidence = (
            0.40 * primary_conf_mod +
            0.30 * active_avg +
            0.30 * regime_norm
        )
        
        # Bound
        confidence = max(CONFIDENCE_MODIFIER_MIN, min(CONFIDENCE_MODIFIER_MAX, confidence))
        
        return confidence, breakdown
    
    def _compute_capital_modifier(
        self,
        primary_strategy: str,
        allocations: Dict[str, float],
        active_capital: float,
        regime_priority,
    ) -> tuple:
        """
        Compute capital modifier.
        
        Formula:
            0.50 * primary_strategy_capital_modifier
          + 0.30 * top_allocation_share_normalized
          + 0.20 * active_capital_distribution
        
        Returns (modifier, breakdown_dict)
        """
        breakdown = {}
        
        # Primary strategy capital modifier
        primary_mods = regime_priority.get_modifier_for_strategy(primary_strategy)
        primary_cap_mod = primary_mods.get("capital_modifier", 1.0)
        breakdown["primary_cap"] = primary_cap_mod
        
        # Top allocation share normalized
        # If top allocation > 0.25, that's strong concentration → boost
        top_alloc = max(allocations.values()) if allocations else 0.0
        alloc_norm = 0.80 + (top_alloc * 1.5)  # 0.25 → 1.175
        alloc_norm = min(1.20, alloc_norm)
        breakdown["alloc_norm"] = alloc_norm
        
        # Active capital distribution (0.0-1.0 → 0.85-1.15)
        active_norm = 0.85 + (active_capital * 0.30)
        breakdown["active_cap"] = active_norm
        
        # Weighted calculation
        capital = (
            0.50 * primary_cap_mod +
            0.30 * alloc_norm +
            0.20 * active_norm
        )
        
        # Bound
        capital = max(CAPITAL_MODIFIER_MIN, min(CAPITAL_MODIFIER_MAX, capital))
        
        return capital, breakdown
    
    # ═══════════════════════════════════════════════════════════
    # OVERLAY EFFECT
    # ═══════════════════════════════════════════════════════════
    
    def _determine_overlay_effect(
        self,
        primary_strategy: str,
        active_strategies: List[str],
        regime_confidence: float,
        confidence_modifier: float,
        allocations: Dict[str, float],
    ) -> StrategyOverlayEffect:
        """
        Determine strategy overlay effect.
        
        SUPPORTIVE: Primary active + high confidence + concentrated allocation
        NEUTRAL: Mixed strategies or moderate confidence
        RESTRICTIVE: Primary disabled/low confidence/fragmented
        """
        # Check if primary is active
        primary_active = primary_strategy in active_strategies
        
        # Check allocation concentration
        top_alloc = max(allocations.values()) if allocations else 0.0
        concentrated = top_alloc > 0.20
        
        # SUPPORTIVE: Primary active, high confidence, concentrated
        if primary_active and regime_confidence >= 0.70 and concentrated:
            return StrategyOverlayEffect.SUPPORTIVE
        
        # RESTRICTIVE: Primary not active, low confidence, fragmented
        if not primary_active or regime_confidence < 0.50 or (top_alloc < 0.15 and len(allocations) > 4):
            return StrategyOverlayEffect.RESTRICTIVE
        
        # Default: NEUTRAL
        return StrategyOverlayEffect.NEUTRAL
    
    # ═══════════════════════════════════════════════════════════
    # RECOMMENDED BIAS
    # ═══════════════════════════════════════════════════════════
    
    def _determine_bias(
        self,
        primary_strategy: str,
        regime_confidence: float,
    ) -> RecommendedBias:
        """
        Determine recommended bias based on primary strategy.
        
        Maps strategy to bias type.
        Returns MIXED if confidence too low.
        """
        if regime_confidence < 0.45:
            return RecommendedBias.MIXED
        
        return STRATEGY_BIAS_MAP.get(primary_strategy, RecommendedBias.MIXED)
    
    # ═══════════════════════════════════════════════════════════
    # REASON BUILDER
    # ═══════════════════════════════════════════════════════════
    
    def _build_reason(
        self,
        market_regime: str,
        primary_strategy: str,
        overlay_effect: StrategyOverlayEffect,
        regime_confidence: float,
    ) -> str:
        """Build human-readable reason string."""
        regime_part = market_regime.lower().replace("_", " ")
        
        strategy_names = {
            "trend_following": "trend following",
            "mean_reversion": "mean-reversion",
            "breakout": "breakout",
            "liquidation_capture": "liquidation capture",
            "flow_following": "flow following",
            "volatility_expansion": "volatility expansion",
            "funding_arb": "funding arbitrage",
            "structure_reversal": "structure reversal",
        }
        
        strategy_part = strategy_names.get(primary_strategy, primary_strategy)
        
        if overlay_effect == StrategyOverlayEffect.SUPPORTIVE:
            return f"{regime_part} with strong {strategy_part} dominance"
        elif overlay_effect == StrategyOverlayEffect.RESTRICTIVE:
            return f"{regime_part} with fragmented strategy signals"
        else:
            return f"{regime_part} with moderate {strategy_part} bias"


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_aggregator: Optional[StrategyBrainAggregator] = None


def get_strategy_brain_aggregator() -> StrategyBrainAggregator:
    """Get singleton aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = StrategyBrainAggregator()
    return _aggregator
