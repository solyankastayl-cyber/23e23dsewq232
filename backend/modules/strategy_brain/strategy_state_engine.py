"""
PHASE 19.1 — Strategy State Engine
==================================
Computes strategy suitability and state based on market conditions.

Input sources:
- MarketState (trend, volatility, exchange, derivatives, risk)
- Dominance/Breadth (dominance_regime, breadth_state)
- Alpha Ecology (ecology_state)
- Alpha Interaction (interaction_state)

Output:
- StrategyState for each strategy
- StrategySummary with aggregated view
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.strategy_brain.strategy_types import (
    StrategyType,
    StrategyConfig,
    StrategyState,
    StrategyStateEnum,
    StrategySummary,
    STATE_THRESHOLDS,
    STATE_MODIFIERS,
)
from modules.strategy_brain.strategy_registry import (
    STRATEGY_REGISTRY,
    get_strategy_config,
    get_all_strategies,
)


class StrategyStateEngine:
    """
    Strategy State Engine - PHASE 19.1
    
    Computes suitability and state for each strategy family
    based on current market conditions.
    """
    
    def __init__(self):
        # Lazy load dependent engines
        self._market_state_builder = None
        self._market_structure_engine = None
        self._ecology_overlay = None
        self._interaction_aggregator = None
    
    # ═══════════════════════════════════════════════════════════
    # LAZY LOADERS
    # ═══════════════════════════════════════════════════════════
    
    @property
    def market_state_builder(self):
        if self._market_state_builder is None:
            try:
                from modules.trading_decision.market_state.market_state_builder import get_market_state_builder
                self._market_state_builder = get_market_state_builder()
            except ImportError:
                pass
        return self._market_state_builder
    
    @property
    def market_structure_engine(self):
        if self._market_structure_engine is None:
            try:
                from modules.market_structure.breadth_dominance.market_structure_engine import get_market_structure_engine
                self._market_structure_engine = get_market_structure_engine()
            except ImportError:
                pass
        return self._market_structure_engine
    
    @property
    def ecology_overlay(self):
        if self._ecology_overlay is None:
            try:
                from modules.trading.ecology_overlay import get_ecology_overlay
                self._ecology_overlay = get_ecology_overlay()
            except ImportError:
                pass
        return self._ecology_overlay
    
    @property
    def interaction_aggregator(self):
        if self._interaction_aggregator is None:
            try:
                from modules.alpha_interactions.interaction_aggregator import get_interaction_aggregator
                self._interaction_aggregator = get_interaction_aggregator()
            except ImportError:
                pass
        return self._interaction_aggregator
    
    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════
    
    def compute_strategy_state(
        self,
        strategy_name: str,
        symbol: str = "BTC",
    ) -> StrategyState:
        """
        Compute state for a single strategy.
        
        Args:
            strategy_name: Name of strategy to evaluate
            symbol: Reference symbol for market context
        
        Returns:
            StrategyState with suitability and modifiers
        """
        now = datetime.now(timezone.utc)
        
        config = get_strategy_config(strategy_name)
        if config is None:
            return StrategyState(
                strategy_name=strategy_name,
                strategy_type=StrategyType.TREND_FOLLOWING,  # Default
                strategy_state=StrategyStateEnum.DISABLED,
                suitability_score=0.0,
                confidence_modifier=0.70,
                capital_modifier=0.0,
                reason="strategy_not_found",
                timestamp=now,
            )
        
        # Get market context
        context = self._get_market_context(symbol)
        
        # Compute suitability scores
        regime_score = self._compute_regime_score(config, context)
        volatility_score = self._compute_volatility_score(config, context)
        breadth_score = self._compute_breadth_score(config, context)
        interaction_score = self._compute_interaction_score(config, context)
        ecology_score = self._compute_ecology_score(config, context)
        
        # Weighted suitability
        suitability = (
            regime_score * config.regime_weight +
            volatility_score * config.volatility_weight +
            breadth_score * config.breadth_weight +
            interaction_score * config.interaction_weight +
            ecology_score * config.ecology_weight
        )
        
        # Determine state
        state = self._determine_state(suitability)
        
        # Get modifiers
        modifiers = STATE_MODIFIERS[state]
        
        # Build reason
        reason = self._build_reason(config, context, state, suitability)
        
        return StrategyState(
            strategy_name=strategy_name,
            strategy_type=config.strategy_type,
            strategy_state=state,
            suitability_score=suitability,
            confidence_modifier=modifiers["confidence_modifier"],
            capital_modifier=modifiers["capital_modifier"],
            reason=reason,
            timestamp=now,
            regime_score=regime_score,
            volatility_score=volatility_score,
            breadth_score=breadth_score,
            interaction_score=interaction_score,
            ecology_score=ecology_score,
            market_context=context,
        )
    
    def compute_all_strategies(self, symbol: str = "BTC") -> List[StrategyState]:
        """Compute state for all strategies."""
        return [
            self.compute_strategy_state(name, symbol)
            for name in get_all_strategies()
        ]
    
    def compute_summary(self, symbol: str = "BTC") -> StrategySummary:
        """
        Compute aggregated summary of all strategy states.
        
        Returns:
            StrategySummary with active/reduced/disabled lists
        """
        now = datetime.now(timezone.utc)
        
        # Get market context
        context = self._get_market_context(symbol)
        
        # Compute all states
        states = self.compute_all_strategies(symbol)
        
        # Categorize
        active = []
        reduced = []
        disabled = []
        
        for s in states:
            if s.strategy_state == StrategyStateEnum.ACTIVE:
                active.append(s.strategy_name)
            elif s.strategy_state == StrategyStateEnum.REDUCED:
                reduced.append(s.strategy_name)
            else:
                disabled.append(s.strategy_name)
        
        return StrategySummary(
            market_regime=context.get("combined_state", "UNDEFINED"),
            volatility_state=context.get("volatility_state", "NORMAL"),
            breadth_state=context.get("breadth_state", "MIXED"),
            interaction_state=context.get("interaction_state", "NEUTRAL"),
            ecology_state=context.get("ecology_state", "STABLE"),
            active_strategies=active,
            reduced_strategies=reduced,
            disabled_strategies=disabled,
            strategy_count=len(states),
            active_count=len(active),
            reduced_count=len(reduced),
            disabled_count=len(disabled),
            timestamp=now,
            strategy_states=states,
        )
    
    # ═══════════════════════════════════════════════════════════
    # MARKET CONTEXT
    # ═══════════════════════════════════════════════════════════
    
    def _get_market_context(self, symbol: str) -> Dict[str, Any]:
        """Get all market context for suitability calculation."""
        context = {}
        
        # MarketState
        try:
            if self.market_state_builder:
                state = self.market_state_builder.build(symbol)
                context["trend_state"] = state.trend_state.value
                context["volatility_state"] = state.volatility_state.value
                context["exchange_state"] = state.exchange_state.value
                context["derivatives_state"] = state.derivatives_state.value
                context["risk_state"] = state.risk_state.value
                context["combined_state"] = state.combined_state.value
        except Exception:
            context.setdefault("trend_state", "RANGE")
            context.setdefault("volatility_state", "NORMAL")
            context.setdefault("combined_state", "UNDEFINED")
        
        # Dominance/Breadth
        try:
            if self.market_structure_engine:
                mod = self.market_structure_engine.get_modifier_for_symbol(symbol)
                context["dominance_regime"] = mod.get("dominance_regime", "BALANCED")
                context["breadth_state"] = mod.get("breadth_state", "MIXED")
                context["rotation_state"] = mod.get("rotation_state", "STABLE")
        except Exception:
            context.setdefault("dominance_regime", "BALANCED")
            context.setdefault("breadth_state", "MIXED")
        
        # Alpha Ecology
        try:
            if self.ecology_overlay:
                eco = self.ecology_overlay.get_trading_product_ecology(symbol)
                context["ecology_state"] = eco.get("state", "STABLE")
                context["ecology_score"] = eco.get("score", 1.0)
        except Exception:
            context.setdefault("ecology_state", "STABLE")
            context.setdefault("ecology_score", 1.0)
        
        # Alpha Interaction
        try:
            if self.interaction_aggregator:
                inter = self.interaction_aggregator.get_aggregate_for_symbol(symbol)
                context["interaction_state"] = inter.get("interaction_state", "NEUTRAL")
                context["interaction_score"] = inter.get("interaction_score", 0.0)
        except Exception:
            context.setdefault("interaction_state", "NEUTRAL")
            context.setdefault("interaction_score", 0.0)
        
        return context
    
    # ═══════════════════════════════════════════════════════════
    # SUITABILITY CALCULATIONS
    # ═══════════════════════════════════════════════════════════
    
    def _compute_regime_score(
        self,
        config: StrategyConfig,
        context: Dict[str, Any],
    ) -> float:
        """
        Compute regime suitability score.
        
        Score range: 0.0 - 1.0
        """
        combined_state = context.get("combined_state", "UNDEFINED")
        trend_state = context.get("trend_state", "RANGE")
        
        # Check anti-regimes (hard penalty)
        for anti in config.anti_regimes:
            if anti in combined_state or anti == combined_state:
                return 0.1
            if anti == trend_state:
                return 0.2
        
        # Check preferred regimes (boost)
        for pref in config.preferred_regimes:
            if pref in combined_state or pref == combined_state:
                return 0.95
            if pref == trend_state:
                return 0.85
        
        # Neutral
        return 0.5
    
    def _compute_volatility_score(
        self,
        config: StrategyConfig,
        context: Dict[str, Any],
    ) -> float:
        """
        Compute volatility suitability score.
        
        Score range: 0.0 - 1.0
        """
        vol_state = context.get("volatility_state", "NORMAL")
        
        # Check anti-volatility (hard penalty)
        if vol_state in config.anti_volatility:
            return 0.15
        
        # Check preferred volatility (boost)
        if vol_state in config.preferred_volatility:
            return 0.90
        
        # Neutral
        return 0.50
    
    def _compute_breadth_score(
        self,
        config: StrategyConfig,
        context: Dict[str, Any],
    ) -> float:
        """
        Compute breadth suitability score.
        
        Score range: 0.0 - 1.0
        """
        breadth_state = context.get("breadth_state", "MIXED")
        min_breadth = config.min_breadth
        
        breadth_rank = {"STRONG": 3, "MIXED": 2, "WEAK": 1}
        
        current_rank = breadth_rank.get(breadth_state, 2)
        min_rank = breadth_rank.get(min_breadth, 2)
        
        if current_rank < min_rank:
            # Below minimum = penalty
            return 0.25
        elif current_rank > min_rank:
            # Above minimum = boost
            return 0.90
        else:
            # At minimum
            return 0.60
    
    def _compute_interaction_score(
        self,
        config: StrategyConfig,
        context: Dict[str, Any],
    ) -> float:
        """
        Compute interaction suitability score.
        
        Score range: 0.0 - 1.0
        """
        interaction_state = context.get("interaction_state", "NEUTRAL")
        
        # Check anti-interaction (hard penalty)
        if interaction_state in config.anti_interaction:
            return 0.20
        
        # Check preferred interaction (boost)
        if interaction_state in config.preferred_interaction:
            return 0.90
        
        # Neutral
        return 0.55
    
    def _compute_ecology_score(
        self,
        config: StrategyConfig,
        context: Dict[str, Any],
    ) -> float:
        """
        Compute ecology suitability score.
        
        Score range: 0.0 - 1.0
        
        Ecology states affect all strategies:
        - HEALTHY: boost
        - STABLE: neutral
        - STRESSED: penalty
        - CRITICAL: hard penalty
        """
        ecology_state = context.get("ecology_state", "STABLE")
        
        ecology_scores = {
            "HEALTHY": 0.90,
            "STABLE": 0.70,
            "STRESSED": 0.45,
            "CRITICAL": 0.20,
        }
        
        return ecology_scores.get(ecology_state, 0.60)
    
    # ═══════════════════════════════════════════════════════════
    # STATE DETERMINATION
    # ═══════════════════════════════════════════════════════════
    
    def _determine_state(self, suitability: float) -> StrategyStateEnum:
        """
        Determine strategy state from suitability score.
        
        Thresholds:
        - >= 0.70: ACTIVE
        - >= 0.45: REDUCED
        - <  0.45: DISABLED
        """
        if suitability >= STATE_THRESHOLDS["ACTIVE"]:
            return StrategyStateEnum.ACTIVE
        elif suitability >= STATE_THRESHOLDS["REDUCED"]:
            return StrategyStateEnum.REDUCED
        else:
            return StrategyStateEnum.DISABLED
    
    def _build_reason(
        self,
        config: StrategyConfig,
        context: Dict[str, Any],
        state: StrategyStateEnum,
        suitability: float,
    ) -> str:
        """Build human-readable reason string."""
        parts = []
        
        # State reason
        if state == StrategyStateEnum.ACTIVE:
            parts.append("suitable_conditions")
        elif state == StrategyStateEnum.REDUCED:
            parts.append("partial_suitability")
        else:
            parts.append("unsuitable_conditions")
        
        # Key factors
        combined = context.get("combined_state", "UNDEFINED")
        vol = context.get("volatility_state", "NORMAL")
        breadth = context.get("breadth_state", "MIXED")
        
        # Anti-regime hit
        if combined in config.anti_regimes or any(a in combined for a in config.anti_regimes):
            parts.append(f"anti_regime_{combined.lower()}")
        
        # Anti-volatility hit
        if vol in config.anti_volatility:
            parts.append(f"anti_volatility_{vol.lower()}")
        
        # Breadth below minimum
        breadth_rank = {"STRONG": 3, "MIXED": 2, "WEAK": 1}
        if breadth_rank.get(breadth, 2) < breadth_rank.get(config.min_breadth, 2):
            parts.append("weak_breadth")
        
        return "_".join(parts) if parts else f"score_{round(suitability, 2)}"


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[StrategyStateEngine] = None


def get_strategy_state_engine() -> StrategyStateEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = StrategyStateEngine()
    return _engine


# ══════════════════════════════════════════════════════════════
# Additional convenience methods added to StrategyStateEngine
# ══════════════════════════════════════════════════════════════

# Monkey-patch get_active_strategies for backward compatibility
def _get_active_strategies(self, symbol: str = "BTC") -> Dict[str, Any]:
    """
    Get active strategies for a symbol.
    
    Returns:
        Dict with active_strategies list and metadata
    """
    try:
        summary = self.compute_summary(symbol)
        
        active_list = []
        for state in summary.strategy_states:
            if state.strategy_state.value == "ACTIVE":
                active_list.append({
                    "id": state.strategy_name,
                    "type": state.strategy_type.value,
                    "suitability": round(state.suitability_score, 4),
                    "confidence_modifier": round(state.confidence_modifier, 4),
                    "capital_modifier": round(state.capital_modifier, 4),
                })
        
        return {
            "symbol": symbol,
            "active_strategies": active_list,
            "active_count": len(active_list),
            "total_strategies": summary.strategy_count,
            "market_regime": summary.market_regime,
            "timestamp": summary.timestamp.isoformat(),
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "active_strategies": [],
            "active_count": 0,
            "error": str(e),
        }

StrategyStateEngine.get_active_strategies = _get_active_strategies
