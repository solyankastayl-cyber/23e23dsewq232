"""
PHASE 19.3 — Strategy Regime Switch Engine
==========================================
Main engine for strategy regime switching.

Combines:
- Market regime detection (from existing modules)
- Regime-strategy mapping
- Priority calculation

Outputs:
- Primary strategy for current regime
- Secondary strategies
- Inactive strategies
- Modifiers per strategy
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.strategy_brain.strategy_registry import get_all_strategies
from modules.strategy_brain.regime_switch.strategy_regime_types import (
    StrategyPriorityState,
    RegimeSwitchSummary,
    REGIME_CONFIDENCE_WEIGHTS,
    PRIORITY_MODIFIERS,
)
from modules.strategy_brain.regime_switch.strategy_regime_map import (
    get_regime_config,
    get_strategies_for_regime,
    get_regime_map_summary,
    REGIME_STRATEGY_MAP,
)
from modules.strategy_brain.regime_switch.strategy_priority_engine import (
    get_priority_engine,
)


class StrategyRegimeSwitchEngine:
    """
    Strategy Regime Switch Engine - PHASE 19.3
    
    Determines which strategy should be primary
    based on current market regime.
    """
    
    def __init__(self):
        """Initialize with dependent engines."""
        self.priority_engine = get_priority_engine()
        
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
    
    def compute_regime_priority(
        self,
        symbol: str = "BTC",
    ) -> StrategyPriorityState:
        """
        Compute strategy priorities for a symbol based on regime.
        
        Args:
            symbol: Symbol to analyze
        
        Returns:
            StrategyPriorityState with primary/secondary/inactive strategies
        """
        # Get market context
        context = self._get_market_context(symbol)
        
        # Determine regime
        regime_name = context.get("combined_state", "UNDEFINED")
        
        # Compute regime confidence
        regime_confidence, scores = self._compute_regime_confidence(context)
        
        # Compute priorities
        priority_state = self.priority_engine.compute_priorities(
            regime_name=regime_name,
            regime_confidence=regime_confidence,
            scores=scores,
        )
        
        return priority_state
    
    def compute_regime_for_regime_name(
        self,
        regime_name: str,
        regime_confidence: float = 0.7,
    ) -> StrategyPriorityState:
        """
        Compute strategy priorities for a given regime name.
        
        Useful for testing or manual regime specification.
        """
        return self.priority_engine.compute_priorities(
            regime_name=regime_name,
            regime_confidence=regime_confidence,
        )
    
    def get_primary_strategy(self, symbol: str = "BTC") -> str:
        """Get primary strategy for symbol."""
        priority = self.compute_regime_priority(symbol)
        return priority.primary_strategy
    
    def get_strategy_modifier(
        self,
        strategy_name: str,
        symbol: str = "BTC",
    ) -> Dict[str, float]:
        """Get modifiers for a specific strategy."""
        priority = self.compute_regime_priority(symbol)
        return priority.get_modifier_for_strategy(strategy_name)
    
    def compute_summary(
        self,
        symbols: Optional[List[str]] = None,
    ) -> RegimeSwitchSummary:
        """
        Compute summary across multiple symbols.
        
        Args:
            symbols: List of symbols to analyze
        
        Returns:
            RegimeSwitchSummary with aggregated view
        """
        now = datetime.now(timezone.utc)
        symbols = symbols or ["BTC", "ETH", "SOL"]
        
        # Collect priorities per symbol
        priorities = {}
        regime_counts = {}
        primary_strategies = set()
        
        for symbol in symbols:
            try:
                priority = self.compute_regime_priority(symbol)
                priorities[symbol] = priority
                
                # Count regimes
                regime = priority.market_regime
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
                
                # Collect primary strategies
                primary_strategies.add(priority.primary_strategy)
            except Exception:
                pass
        
        # Find dominant regime
        dominant_regime = max(regime_counts, key=regime_counts.get) if regime_counts else "UNDEFINED"
        
        # Compute stability (how consistent regimes are)
        total_symbols = len(priorities)
        dominant_count = regime_counts.get(dominant_regime, 0)
        regime_stability = dominant_count / total_symbols if total_symbols > 0 else 0.0
        
        # Build strategy priority map from first matching priority
        strategy_priority_map = {}
        for symbol, priority in priorities.items():
            if priority.market_regime == dominant_regime:
                strategy_priority_map[priority.primary_strategy] = "primary"
                for s in priority.secondary_strategies:
                    if s not in strategy_priority_map:
                        strategy_priority_map[s] = "secondary"
                for s in priority.inactive_strategies:
                    if s not in strategy_priority_map:
                        strategy_priority_map[s] = "inactive"
                break
        
        return RegimeSwitchSummary(
            dominant_regime=dominant_regime,
            regime_stability=regime_stability,
            primary_strategies=list(primary_strategies),
            strategy_priority_map=strategy_priority_map,
            symbols_analyzed=symbols,
            timestamp=now,
        )
    
    # ═══════════════════════════════════════════════════════════
    # MARKET CONTEXT
    # ═══════════════════════════════════════════════════════════
    
    def _get_market_context(self, symbol: str) -> Dict[str, Any]:
        """Get all market context for regime detection."""
        context = {}
        
        # MarketState
        try:
            if self.market_state_builder:
                state = self.market_state_builder.build(symbol)
                context["trend_state"] = state.trend_state.value
                context["volatility_state"] = state.volatility_state.value
                context["combined_state"] = state.combined_state.value
        except Exception:
            context.setdefault("trend_state", "RANGE")
            context.setdefault("volatility_state", "NORMAL")
            context.setdefault("combined_state", "UNDEFINED")
        
        # Dominance/Breadth
        try:
            if self.market_structure_engine:
                mod = self.market_structure_engine.get_modifier_for_symbol(symbol)
                context["breadth_state"] = mod.get("breadth_state", "MIXED")
        except Exception:
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
        except Exception:
            context.setdefault("interaction_state", "NEUTRAL")
        
        return context
    
    def _compute_regime_confidence(
        self,
        context: Dict[str, Any],
    ) -> tuple:
        """
        Compute regime confidence score.
        
        Formula:
            confidence = 0.40*regime + 0.20*volatility + 0.15*breadth + 0.15*interaction + 0.10*ecology
        
        Returns:
            Tuple of (confidence, scores_dict)
        """
        weights = REGIME_CONFIDENCE_WEIGHTS
        
        # Regime score (based on how clear the regime is)
        combined_state = context.get("combined_state", "UNDEFINED")
        regime_score = self._score_regime_clarity(combined_state)
        
        # Volatility score
        vol_state = context.get("volatility_state", "NORMAL")
        volatility_score = self._score_volatility(vol_state)
        
        # Breadth score
        breadth_state = context.get("breadth_state", "MIXED")
        breadth_score = self._score_breadth(breadth_state)
        
        # Interaction score
        interaction_state = context.get("interaction_state", "NEUTRAL")
        interaction_score = self._score_interaction(interaction_state)
        
        # Ecology score
        ecology_state = context.get("ecology_state", "STABLE")
        ecology_score = self._score_ecology(ecology_state)
        
        # Weighted confidence
        confidence = (
            regime_score * weights["regime"] +
            volatility_score * weights["volatility"] +
            breadth_score * weights["breadth"] +
            interaction_score * weights["interaction"] +
            ecology_score * weights["ecology"]
        )
        
        scores = {
            "regime": regime_score,
            "volatility": volatility_score,
            "breadth": breadth_score,
            "interaction": interaction_score,
            "ecology": ecology_score,
        }
        
        return confidence, scores
    
    def _score_regime_clarity(self, regime: str) -> float:
        """Score how clear/confident the regime detection is."""
        clear_regimes = [
            "TREND_UP", "TREND_DOWN",
            "SQUEEZE_SETUP_LONG", "SQUEEZE_SETUP_SHORT",
            "BREAKOUT_CONFIRMED", "BREAKDOWN_CONFIRMED",
        ]
        
        moderate_regimes = [
            "RANGE", "RANGE_LOW_VOL", "RANGE_HIGH_VOL",
            "VOL_EXPANSION", "VOL_COMPRESSION",
        ]
        
        unclear_regimes = [
            "MIXED", "UNDEFINED", "CONFLICTED",
        ]
        
        if any(r in regime for r in clear_regimes):
            return 0.90
        elif any(r in regime for r in moderate_regimes):
            return 0.70
        elif any(r in regime for r in unclear_regimes):
            return 0.40
        else:
            return 0.60
    
    def _score_volatility(self, vol_state: str) -> float:
        """Score volatility for regime confidence."""
        scores = {
            "LOW": 0.70,
            "NORMAL": 0.85,
            "HIGH": 0.75,
            "EXPANDING": 0.80,
            "CONTRACTING": 0.70,
        }
        return scores.get(vol_state, 0.60)
    
    def _score_breadth(self, breadth_state: str) -> float:
        """Score breadth for regime confidence."""
        scores = {
            "STRONG": 0.90,
            "MIXED": 0.70,
            "WEAK": 0.50,
        }
        return scores.get(breadth_state, 0.60)
    
    def _score_interaction(self, interaction_state: str) -> float:
        """Score interaction for regime confidence."""
        scores = {
            "REINFORCED": 0.90,
            "NEUTRAL": 0.70,
            "CONFLICTED": 0.40,
            "CANCELLED": 0.30,
        }
        return scores.get(interaction_state, 0.50)
    
    def _score_ecology(self, ecology_state: str) -> float:
        """Score ecology for regime confidence."""
        scores = {
            "HEALTHY": 0.90,
            "STABLE": 0.75,
            "STRESSED": 0.50,
            "CRITICAL": 0.30,
        }
        return scores.get(ecology_state, 0.60)


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[StrategyRegimeSwitchEngine] = None


def get_regime_switch_engine() -> StrategyRegimeSwitchEngine:
    """Get singleton regime switch engine instance."""
    global _engine
    if _engine is None:
        _engine = StrategyRegimeSwitchEngine()
    return _engine
