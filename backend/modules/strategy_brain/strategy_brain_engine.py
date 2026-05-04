"""
Strategy Brain Engine

PHASE 29.5 — Strategy Brain Integration with Hypothesis Engine

Connects:
    Hypothesis Engine
    ↓
    Strategy Selection

Instead of selecting strategy directly from Regime, uses market hypothesis.
This makes the architecture much stronger.
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone

from .strategy_types import (
    StrategyDecision,
    StrategySummary,
    StrategyCandidate,
    HYPOTHESIS_STRATEGY_MAP,
    MICROSTRUCTURE_EXECUTION_QUALITY,
    WEIGHT_CONFIDENCE,
    WEIGHT_RELIABILITY,
    WEIGHT_REGIME,
    WEIGHT_MICROSTRUCTURE,
    AVAILABLE_STRATEGIES,
)


# ══════════════════════════════════════════════════════════════
# Strategy Brain Engine
# ══════════════════════════════════════════════════════════════

class StrategyBrainEngine:
    """
    Strategy Brain Engine — PHASE 29.5
    
    Integrates:
    - Hypothesis Engine
    - Regime Intelligence
    - Microstructure Intelligence
    
    To select optimal trading strategy.
    
    Flow:
    RegimeContext + Hypothesis + MicrostructureContext → Strategy Brain
    """
    
    def __init__(self):
        self._decisions: Dict[str, List[StrategyDecision]] = {}
        self._current: Dict[str, StrategyDecision] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Get Candidate Strategies
    # ═══════════════════════════════════════════════════════════
    
    def get_candidate_strategies(
        self,
        hypothesis_type: str,
    ) -> List[str]:
        """
        Get candidate strategies for hypothesis type.
        
        Returns list of suitable strategies or empty list for NO_EDGE.
        """
        return HYPOTHESIS_STRATEGY_MAP.get(hypothesis_type, [])
    
    # ═══════════════════════════════════════════════════════════
    # 2. Calculate Microstructure Quality
    # ═══════════════════════════════════════════════════════════
    
    def get_microstructure_quality(
        self,
        microstructure_state: str,
    ) -> float:
        """
        Map microstructure state to execution quality.
        
        SUPPORTIVE → 1.0
        NEUTRAL → 0.7
        FRAGILE → 0.45
        STRESSED → 0.25
        """
        return MICROSTRUCTURE_EXECUTION_QUALITY.get(microstructure_state, 0.5)
    
    # ═══════════════════════════════════════════════════════════
    # 3. Calculate Suitability Score
    # ═══════════════════════════════════════════════════════════
    
    def calculate_suitability_score(
        self,
        confidence: float,
        reliability: float,
        regime_support: float,
        microstructure_state: str,
    ) -> float:
        """
        Calculate strategy suitability score.
        
        Formula:
        suitability_score =
            0.45 * hypothesis_confidence
            + 0.25 * hypothesis_reliability
            + 0.20 * regime_support
            + 0.10 * microstructure_execution_quality
        """
        micro_quality = self.get_microstructure_quality(microstructure_state)
        
        score = (
            WEIGHT_CONFIDENCE * confidence
            + WEIGHT_RELIABILITY * reliability
            + WEIGHT_REGIME * regime_support
            + WEIGHT_MICROSTRUCTURE * micro_quality
        )
        
        return round(min(max(score, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 4. Check Execution Filter
    # ═══════════════════════════════════════════════════════════
    
    def should_block_strategy(
        self,
        execution_state: str,
    ) -> bool:
        """
        Check if strategy should be blocked due to unfavorable execution.
        
        If execution_state = UNFAVORABLE → strategy blocked
        """
        return execution_state == "UNFAVORABLE"
    
    # ═══════════════════════════════════════════════════════════
    # 5. Generate Strategy Reason
    # ═══════════════════════════════════════════════════════════
    
    def generate_reason(
        self,
        hypothesis_type: str,
        selected_strategy: str,
        directional_bias: str,
        regime_type: str,
        microstructure_state: str,
        execution_state: str,
    ) -> str:
        """
        Generate explanation for strategy selection.
        """
        if selected_strategy == "none":
            if execution_state == "UNFAVORABLE":
                return "strategy blocked due to unfavorable execution conditions"
            return "no suitable strategy for current market hypothesis"
        
        parts = []
        
        # Hypothesis alignment
        type_descriptions = {
            "BULLISH_CONTINUATION": "bullish continuation hypothesis",
            "BEARISH_CONTINUATION": "bearish continuation hypothesis",
            "BREAKOUT_FORMING": "breakout formation hypothesis",
            "RANGE_MEAN_REVERSION": "range mean reversion hypothesis",
            "SHORT_SQUEEZE_SETUP": "short squeeze setup",
            "LONG_SQUEEZE_SETUP": "long squeeze setup",
            "VOLATILE_UNWIND": "volatile unwind pattern",
        }
        
        parts.append(f"{type_descriptions.get(hypothesis_type, hypothesis_type.lower())}")
        
        # Regime context
        if regime_type == "TRENDING":
            parts.append("aligns with trending regime")
        elif regime_type == "RANGING":
            parts.append("suits range-bound market")
        elif regime_type == "VOLATILE":
            parts.append("appropriate for volatile conditions")
        
        # Microstructure context
        if microstructure_state == "SUPPORTIVE":
            parts.append("and supportive orderbook structure")
        elif microstructure_state == "NEUTRAL":
            parts.append("with neutral microstructure")
        elif microstructure_state in ("FRAGILE", "STRESSED"):
            parts.append(f"despite {microstructure_state.lower()} microstructure")
        
        # Directional note
        if directional_bias != "NEUTRAL":
            parts.append(f"({directional_bias.lower()} bias)")
        
        return " ".join(parts)
    
    # ═══════════════════════════════════════════════════════════
    # 6. Select Best Strategy
    # ═══════════════════════════════════════════════════════════
    
    def select_strategy(
        self,
        symbol: str,
        hypothesis_type: str,
        directional_bias: str,
        confidence: float,
        reliability: float,
        regime_support: float,
        regime_type: str,
        microstructure_state: str,
        execution_state: str,
    ) -> StrategyDecision:
        """
        Select optimal strategy based on hypothesis and market context.
        
        Steps:
        1. Get candidate strategies for hypothesis type
        2. Check execution filter
        3. Calculate suitability score
        4. Select best strategy
        5. Generate reason
        """
        # 1. Get candidates
        candidates = self.get_candidate_strategies(hypothesis_type)
        
        # 2. Check execution filter
        if self.should_block_strategy(execution_state):
            decision = StrategyDecision(
                symbol=symbol,
                hypothesis_type=hypothesis_type,
                directional_bias=directional_bias,
                selected_strategy="none",
                alternative_strategies=[],
                suitability_score=0.0,
                execution_state=execution_state,
                confidence=confidence,
                reliability=reliability,
                reason="strategy blocked due to unfavorable execution conditions",
            )
            self._store_decision(symbol, decision)
            return decision
        
        # 3. Check if no candidates
        if not candidates:
            decision = StrategyDecision(
                symbol=symbol,
                hypothesis_type=hypothesis_type,
                directional_bias=directional_bias,
                selected_strategy="none",
                alternative_strategies=[],
                suitability_score=0.0,
                execution_state=execution_state,
                confidence=confidence,
                reliability=reliability,
                reason="no suitable strategy for current market hypothesis",
            )
            self._store_decision(symbol, decision)
            return decision
        
        # 4. Calculate suitability score
        suitability = self.calculate_suitability_score(
            confidence=confidence,
            reliability=reliability,
            regime_support=regime_support,
            microstructure_state=microstructure_state,
        )
        
        # 5. Select first candidate (highest priority)
        selected = candidates[0]
        alternatives = candidates[1:] if len(candidates) > 1 else []
        
        # 6. Generate reason
        reason = self.generate_reason(
            hypothesis_type=hypothesis_type,
            selected_strategy=selected,
            directional_bias=directional_bias,
            regime_type=regime_type,
            microstructure_state=microstructure_state,
            execution_state=execution_state,
        )
        
        decision = StrategyDecision(
            symbol=symbol,
            hypothesis_type=hypothesis_type,
            directional_bias=directional_bias,
            selected_strategy=selected,
            alternative_strategies=alternatives,
            suitability_score=suitability,
            execution_state=execution_state,
            confidence=confidence,
            reliability=reliability,
            reason=reason,
        )
        
        self._store_decision(symbol, decision)
        return decision
    
    # ═══════════════════════════════════════════════════════════
    # 7. Select Strategy from Hypothesis
    # ═══════════════════════════════════════════════════════════
    
    def select_strategy_from_hypothesis(
        self,
        symbol: str,
    ) -> StrategyDecision:
        """
        Select strategy using live hypothesis from Hypothesis Engine.
        
        Fetches current hypothesis and makes strategy decision.
        """
        # Get hypothesis from Hypothesis Engine
        try:
            from modules.hypothesis_engine import get_hypothesis_engine
            hypothesis_engine = get_hypothesis_engine()
            hypothesis = hypothesis_engine.generate_hypothesis_simulated(symbol)
        except Exception as e:
            # Fallback to NO_EDGE if engine unavailable
            return StrategyDecision(
                symbol=symbol,
                hypothesis_type="NO_EDGE",
                directional_bias="NEUTRAL",
                selected_strategy="none",
                alternative_strategies=[],
                suitability_score=0.0,
                execution_state="UNFAVORABLE",
                confidence=0.0,
                reliability=0.0,
                reason=f"hypothesis engine unavailable: {str(e)}",
            )
        
        # Get regime type
        regime_type = "TRENDING"  # Default
        try:
            from modules.regime_intelligence_v2 import get_regime_context_engine
            regime_engine = get_regime_context_engine()
            regime_ctx = regime_engine.get_context(symbol)
            if regime_ctx:
                regime_type = regime_ctx.regime_type
        except Exception:
            pass
        
        # Get microstructure state
        microstructure_state = "NEUTRAL"  # Default
        try:
            from modules.microstructure_intelligence_v2 import get_microstructure_context_engine
            micro_engine = get_microstructure_context_engine()
            micro_ctx = micro_engine.get_context(symbol)
            if micro_ctx:
                microstructure_state = micro_ctx.microstructure_state
        except Exception:
            pass
        
        return self.select_strategy(
            symbol=symbol,
            hypothesis_type=hypothesis.hypothesis_type,
            directional_bias=hypothesis.directional_bias,
            confidence=hypothesis.confidence,
            reliability=hypothesis.reliability,
            regime_support=hypothesis.regime_support,
            regime_type=regime_type,
            microstructure_state=microstructure_state,
            execution_state=hypothesis.execution_state,
        )
    
    # ═══════════════════════════════════════════════════════════
    # 8. Storage
    # ═══════════════════════════════════════════════════════════
    
    def _store_decision(self, symbol: str, decision: StrategyDecision) -> None:
        """Store decision in history."""
        if symbol not in self._decisions:
            self._decisions[symbol] = []
        self._decisions[symbol].append(decision)
        self._current[symbol] = decision
    
    def get_decision(self, symbol: str) -> Optional[StrategyDecision]:
        """Get current decision for symbol."""
        return self._current.get(symbol)
    
    def get_history(self, symbol: str, limit: int = 100) -> List[StrategyDecision]:
        """Get decision history for symbol."""
        history = self._decisions.get(symbol, [])
        return sorted(history, key=lambda d: d.created_at, reverse=True)[:limit]
    
    # ═══════════════════════════════════════════════════════════
    # 9. Summary
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, symbol: str) -> StrategySummary:
        """Get summary statistics for symbol."""
        history = self.get_history(symbol, limit=500)
        
        if not history:
            return StrategySummary(
                symbol=symbol,
                total_decisions=0,
            )
        
        # Strategy counts
        strategy_counts = {
            "trend_following": 0,
            "breakout_trading": 0,
            "mean_reversion": 0,
            "volatility_expansion": 0,
            "liquidation_capture": 0,
            "range_trading": 0,
            "basis_trade": 0,
            "funding_arb": 0,
            "none": 0,
        }
        
        for d in history:
            if d.selected_strategy in strategy_counts:
                strategy_counts[d.selected_strategy] += 1
        
        # Averages
        avg_suitability = sum(d.suitability_score for d in history) / len(history)
        avg_confidence = sum(d.confidence for d in history) / len(history)
        avg_reliability = sum(d.reliability for d in history) / len(history)
        
        current = history[0] if history else None
        
        return StrategySummary(
            symbol=symbol,
            total_decisions=len(history),
            trend_following_count=strategy_counts["trend_following"],
            breakout_trading_count=strategy_counts["breakout_trading"],
            mean_reversion_count=strategy_counts["mean_reversion"],
            volatility_expansion_count=strategy_counts["volatility_expansion"],
            liquidation_capture_count=strategy_counts["liquidation_capture"],
            range_trading_count=strategy_counts["range_trading"],
            basis_trade_count=strategy_counts["basis_trade"],
            funding_arb_count=strategy_counts["funding_arb"],
            none_count=strategy_counts["none"],
            avg_suitability_score=round(avg_suitability, 4),
            avg_confidence=round(avg_confidence, 4),
            avg_reliability=round(avg_reliability, 4),
            current_strategy=current.selected_strategy if current else "none",
            current_hypothesis=current.hypothesis_type if current else "NO_EDGE",
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_strategy_brain: Optional[StrategyBrainEngine] = None


def get_strategy_brain() -> StrategyBrainEngine:
    """Get singleton instance of StrategyBrainEngine."""
    global _strategy_brain
    if _strategy_brain is None:
        _strategy_brain = StrategyBrainEngine()
    return _strategy_brain
