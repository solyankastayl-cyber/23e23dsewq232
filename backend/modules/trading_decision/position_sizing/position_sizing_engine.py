"""
PHASE 14.5 — Position Sizing Engine
====================================
Computes granular position size based on multiple factors.

Architecture:
    TradingDecision ─────┐
                          │
    TAHypothesis ─────────┼── Position Sizing Engine ── PositionSizingDecision
                          │
    ExchangeContext ──────┤
                          │
    MarketStateMatrix ────┤
                          │
    MarketStructure ──────┤  (PHASE 14.9)
                          │
    AlphaEcology ─────────┘  (PHASE 15.7)

Formula (PHASE 15.7):
    final_size_pct = base_risk × risk_multiplier × vol_adj × exchange_adj 
                     × market_adj × dominance_adj × breadth_adj × ecology_adj
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.trading_decision.position_sizing.position_sizing_types import (
    PositionSizingDecision,
    SizeBucket,
    DecisionInputSnapshot,
    TAInputSnapshot,
    ExchangeInputSnapshot,
    MarketStateInputSnapshot,
)
from modules.trading_decision.position_sizing.position_sizing_rules import (
    BASE_RISK_PCT,
    RISK_MULTIPLIER_RANGES,
    VOLATILITY_ADJUSTMENTS,
    EXCHANGE_ADJUSTMENT_RULES,
    HOSTILE_MARKET_STATES,
    SUPPORTIVE_MARKET_STATES,
    MARKET_ADJUSTMENT_RANGES,
    RISK_STATE_ADJUSTMENTS,
    SIZE_BUCKET_THRESHOLDS,
)

# MongoDB
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


class PositionSizingEngine:
    """
    Position Sizing Engine.
    
    Computes final position size based on all trading intelligence inputs.
    
    PHASE 14.9: Now includes dominance/breadth adjustments.
    PHASE 16.6: Now includes interaction aggregator adjustment.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Lazy load other engines
        self._decision_engine = None
        self._ta_builder = None
        self._exchange_aggregator = None
        self._market_state_builder = None
        self._market_structure_engine = None  # PHASE 14.9
        self._ecology_overlay = None  # PHASE 15.7
        self._interaction_aggregator = None  # PHASE 16.6
    
    @property
    def decision_engine(self):
        if self._decision_engine is None:
            from modules.trading_decision.decision_layer.decision_engine import get_decision_engine
            self._decision_engine = get_decision_engine()
        return self._decision_engine
    
    @property
    def ta_builder(self):
        if self._ta_builder is None:
            from modules.ta_engine.hypothesis.ta_hypothesis_builder import get_hypothesis_builder
            self._ta_builder = get_hypothesis_builder()
        return self._ta_builder
    
    @property
    def exchange_aggregator(self):
        if self._exchange_aggregator is None:
            from modules.exchange_intelligence.exchange_context_aggregator import ExchangeContextAggregator
            self._exchange_aggregator = ExchangeContextAggregator()
        return self._exchange_aggregator
    
    @property
    def market_state_builder(self):
        if self._market_state_builder is None:
            from modules.trading_decision.market_state.market_state_builder import get_market_state_builder
            self._market_state_builder = get_market_state_builder()
        return self._market_state_builder
    
    @property
    def market_structure_engine(self):
        """PHASE 14.9: Market structure for dominance/breadth."""
        if self._market_structure_engine is None:
            from modules.market_structure.breadth_dominance.market_structure_engine import get_market_structure_engine
            self._market_structure_engine = get_market_structure_engine()
        return self._market_structure_engine
    
    @property
    def ecology_overlay(self):
        """PHASE 15.7: Ecology overlay for alpha health."""
        if self._ecology_overlay is None:
            from modules.trading.ecology_overlay import get_ecology_overlay
            self._ecology_overlay = get_ecology_overlay()
        return self._ecology_overlay
    
    @property
    def interaction_aggregator(self):
        """PHASE 16.6: Interaction aggregator for combined interaction modifiers."""
        if self._interaction_aggregator is None:
            try:
                from modules.alpha_interactions.interaction_aggregator import get_interaction_aggregator
                self._interaction_aggregator = get_interaction_aggregator()
            except ImportError:
                pass
        return self._interaction_aggregator
    
    def compute(self, symbol: str) -> PositionSizingDecision:
        """
        Compute position sizing for symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            PositionSizingDecision with final size and adjustments
            
        PHASE 15.7: Now includes ecology_adjustment from Alpha Ecology layer.
        PHASE 16.6: Now includes interaction_adjustment from Interaction Aggregator.
        """
        now = datetime.now(timezone.utc)
        
        # Get all inputs
        decision_input = self._get_decision_input(symbol)
        exchange_input = self._get_exchange_input(symbol)
        market_state_input = self._get_market_state_input(symbol)
        
        # PHASE 14.9: Get dominance/breadth modifiers
        dom_modifier = self._get_dominance_modifier(symbol)
        
        # PHASE 15.7: Get ecology modifier
        ecology_modifier = self._get_ecology_modifier(symbol)
        
        # PHASE 16.6: Get interaction aggregate modifier
        interaction_modifier = self._get_interaction_modifier(symbol)
        
        # Compute adjustments
        risk_multiplier = self._compute_risk_multiplier(decision_input)
        volatility_adjustment = self._compute_volatility_adjustment(market_state_input)
        exchange_adjustment = self._compute_exchange_adjustment(exchange_input)
        market_adjustment = self._compute_market_adjustment(market_state_input)
        
        # PHASE 14.9: Compute dominance/breadth adjustments
        dominance_adjustment = self._compute_dominance_adjustment(dom_modifier)
        breadth_adjustment = self._compute_breadth_adjustment(dom_modifier)
        
        # PHASE 15.7: Compute ecology adjustment
        ecology_adjustment = self._compute_ecology_adjustment(ecology_modifier)
        
        # PHASE 16.6: Compute interaction adjustment
        interaction_adjustment = self._compute_interaction_adjustment(interaction_modifier)
        
        # Final size calculation (PHASE 16.6: extended formula)
        final_size_pct = (
            BASE_RISK_PCT
            * risk_multiplier
            * volatility_adjustment
            * exchange_adjustment
            * market_adjustment
            * dominance_adjustment
            * breadth_adjustment
            * ecology_adjustment
            * interaction_adjustment  # PHASE 16.6
        )
        
        # Determine bucket
        size_bucket = self._determine_size_bucket(final_size_pct)
        
        # Build reason
        reason = self._build_reason(
            decision_input, volatility_adjustment, exchange_adjustment, 
            market_adjustment, dominance_adjustment, breadth_adjustment,
            ecology_adjustment, interaction_adjustment  # PHASE 16.6
        )
        
        # Build drivers (PHASE 16.6: extended)
        drivers = {
            "decision_action": decision_input.action,
            "decision_confidence": decision_input.confidence,
            "volatility_state": market_state_input.volatility_state,
            "exchange_conflict_ratio": exchange_input.conflict_ratio,
            "exchange_crowding_risk": exchange_input.crowding_risk,
            "squeeze_probability": exchange_input.squeeze_probability,
            "market_state": market_state_input.combined_state,
            "risk_state": market_state_input.risk_state,
            # PHASE 14.9
            "dominance_regime": dom_modifier.get("dominance_regime", "BALANCED"),
            "breadth_state": dom_modifier.get("breadth_state", "MIXED"),
            "rotation_state": dom_modifier.get("rotation_state", "STABLE"),
            # PHASE 15.7
            "ecology_state": ecology_modifier.get("ecology_state", "STABLE"),
            "ecology_score": ecology_modifier.get("ecology_score", 1.0),
            # PHASE 16.6
            "interaction_state": interaction_modifier.get("interaction_state", "NEUTRAL"),
            "interaction_score": interaction_modifier.get("interaction_score", 0.0),
            "interaction_strongest_force": interaction_modifier.get("strongest_force", "none"),
        }
        
        # Decision summary
        decision_summary = {
            "action": decision_input.action,
            "direction": decision_input.direction,
            "confidence": round(decision_input.confidence, 4),
            "position_multiplier": round(decision_input.position_multiplier, 4),
            "execution_mode": decision_input.execution_mode,
        }
        
        return PositionSizingDecision(
            symbol=symbol,
            timestamp=now,
            base_risk=BASE_RISK_PCT,
            risk_multiplier=risk_multiplier,
            volatility_adjustment=volatility_adjustment,
            exchange_adjustment=exchange_adjustment,
            market_adjustment=market_adjustment,
            dominance_adjustment=dominance_adjustment,
            breadth_adjustment=breadth_adjustment,
            ecology_adjustment=ecology_adjustment,  # PHASE 15.7
            final_size_pct=final_size_pct,
            size_bucket=size_bucket,
            reason=reason,
            drivers=drivers,
            decision_summary=decision_summary,
        )
    
    def compute_batch(self, symbols: List[str]) -> List[PositionSizingDecision]:
        """Compute sizing for multiple symbols."""
        return [self.compute(symbol) for symbol in symbols]
    
    # ═══════════════════════════════════════════════════════════════
    # INPUT GETTERS
    # ═══════════════════════════════════════════════════════════════
    
    def _get_decision_input(self, symbol: str) -> DecisionInputSnapshot:
        """Get Trading Decision as input."""
        try:
            decision = self.decision_engine.decide(symbol)
            return DecisionInputSnapshot(
                action=decision.action.value,
                direction=decision.direction.value,
                confidence=decision.confidence,
                position_multiplier=decision.position_multiplier,
                execution_mode=decision.execution_mode.value,
            )
        except Exception:
            return DecisionInputSnapshot(
                action="WAIT",
                direction="NEUTRAL",
                confidence=0.0,
                position_multiplier=0.0,
                execution_mode="NONE",
            )
    
    def _get_ta_input(self, symbol: str) -> TAInputSnapshot:
        """Get TA Hypothesis as input."""
        try:
            hypothesis = self.ta_builder.build(symbol)
            return TAInputSnapshot(
                setup_quality=hypothesis.setup_quality,
                entry_quality=hypothesis.entry_quality,
                conviction=hypothesis.conviction,
                trend_strength=hypothesis.trend_strength,
            )
        except Exception:
            return TAInputSnapshot(
                setup_quality=0.0,
                entry_quality=0.5,
                conviction=0.0,
                trend_strength=0.0,
            )
    
    def _get_exchange_input(self, symbol: str) -> ExchangeInputSnapshot:
        """Get Exchange Context as input."""
        try:
            context = self.exchange_aggregator.compute(symbol)
            
            # Compute conflict ratio
            signals = []
            if context.funding_signal:
                signals.append(1 if context.funding_signal.funding_rate > 0 else -1)
            signals.append(1 if context.flow_pressure > 0 else -1)
            signals.append(1 if context.derivatives_pressure > 0 else -1)
            
            if signals:
                avg = sum(signals) / len(signals)
                conflict = sum((s - avg) ** 2 for s in signals) / len(signals)
            else:
                conflict = 0
            
            return ExchangeInputSnapshot(
                confidence=context.confidence,
                conflict_ratio=min(conflict, 1.0),
                crowding_risk=context.crowding_risk,
                squeeze_probability=context.squeeze_probability,
                bias=context.exchange_bias.value,
            )
        except Exception:
            return ExchangeInputSnapshot(
                confidence=0.5,
                conflict_ratio=0.5,
                crowding_risk=0.0,
                squeeze_probability=0.0,
                bias="NEUTRAL",
            )
    
    def _get_market_state_input(self, symbol: str) -> MarketStateInputSnapshot:
        """Get Market State as input."""
        try:
            state = self.market_state_builder.build(symbol)
            return MarketStateInputSnapshot(
                volatility_state=state.volatility_state.value,
                derivatives_state=state.derivatives_state.value,
                risk_state=state.risk_state.value,
                combined_state=state.combined_state.value,
                confidence=state.confidence,
            )
        except Exception:
            return MarketStateInputSnapshot(
                volatility_state="NORMAL",
                derivatives_state="BALANCED",
                risk_state="NEUTRAL",
                combined_state="UNDEFINED",
                confidence=0.5,
            )
    
    def _get_dominance_modifier(self, symbol: str) -> Dict[str, float]:
        """
        PHASE 14.9: Get dominance/breadth modifiers for symbol.
        
        Returns dict with confidence and size modifiers.
        """
        try:
            return self.market_structure_engine.get_modifier_for_symbol(symbol)
        except Exception:
            return {
                "confidence_modifier": 1.0,
                "size_modifier": 1.0,
                "dominance_regime": "BALANCED",
                "breadth_state": "MIXED",
                "rotation_state": "STABLE",
            }
    
    def _get_ecology_modifier(self, symbol: str) -> Dict[str, float]:
        """
        PHASE 15.7: Get ecology modifiers for symbol.
        
        Returns dict with ecology state and size modifier.
        """
        try:
            return self.ecology_overlay.ecology_engine.get_modifier_for_symbol(symbol)
        except Exception:
            return {
                "ecology_confidence_modifier": 1.0,
                "ecology_size_modifier": 1.0,
                "ecology_score": 1.0,
                "ecology_state": "STABLE",
                "weakest_component": "none",
            }
    
    def _get_interaction_modifier(self, symbol: str) -> Dict[str, float]:
        """
        PHASE 16.6: Get interaction aggregate modifiers for symbol.
        
        Returns dict with interaction state and size modifier.
        """
        if self.interaction_aggregator is None:
            return {
                "interaction_size_modifier": 1.0,
                "interaction_confidence_modifier": 1.0,
                "interaction_state": "NEUTRAL",
                "interaction_score": 0.0,
                "strongest_force": "none",
                "execution_modifier": "NORMAL",
            }
        
        try:
            return self.interaction_aggregator.get_aggregate_for_symbol(symbol)
        except Exception:
            return {
                "interaction_size_modifier": 1.0,
                "interaction_confidence_modifier": 1.0,
                "interaction_state": "NEUTRAL",
                "interaction_score": 0.0,
                "strongest_force": "none",
                "execution_modifier": "NORMAL",
            }
    
    # ═══════════════════════════════════════════════════════════════
    # ADJUSTMENT CALCULATIONS
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_risk_multiplier(self, decision: DecisionInputSnapshot) -> float:
        """Compute risk multiplier from decision action."""
        action = decision.action
        config = RISK_MULTIPLIER_RANGES.get(action, {"value": 0.0})
        
        if "value" in config:
            return config["value"]
        
        # Scale within range based on confidence
        min_mult = config["min"]
        max_mult = config["max"]
        
        return min_mult + (max_mult - min_mult) * decision.confidence
    
    def _compute_volatility_adjustment(self, market_state: MarketStateInputSnapshot) -> float:
        """Compute volatility adjustment."""
        vol_state = market_state.volatility_state
        return VOLATILITY_ADJUSTMENTS.get(vol_state, 1.0)
    
    def _compute_exchange_adjustment(self, exchange: ExchangeInputSnapshot) -> float:
        """Compute exchange adjustment based on confirmation/conflict."""
        
        # Check for squeeze risk first (highest priority penalty)
        if exchange.squeeze_probability >= EXCHANGE_ADJUSTMENT_RULES["squeeze_risk"]["squeeze_probability_min"]:
            adj_range = EXCHANGE_ADJUSTMENT_RULES["squeeze_risk"]["adjustment_range"]
            # Lower squeeze prob = higher adjustment
            factor = 1.0 - exchange.squeeze_probability
            return adj_range["min"] + (adj_range["max"] - adj_range["min"]) * factor
        
        # Check for crowded/conflicted
        crowded_rule = EXCHANGE_ADJUSTMENT_RULES["crowded_conflicted"]
        if (exchange.crowding_risk >= crowded_rule["crowding_risk_min"] or 
            exchange.conflict_ratio >= crowded_rule["conflict_min"]):
            adj_range = crowded_rule["adjustment_range"]
            # Higher risk = lower adjustment
            risk_avg = (exchange.crowding_risk + exchange.conflict_ratio) / 2
            factor = 1.0 - risk_avg
            return adj_range["min"] + (adj_range["max"] - adj_range["min"]) * factor
        
        # Check for strong confirmation
        strong_rule = EXCHANGE_ADJUSTMENT_RULES["strong_confirmation"]
        if (exchange.confidence >= strong_rule["confidence_min"] and 
            exchange.conflict_ratio <= strong_rule["conflict_max"]):
            adj_range = strong_rule["adjustment_range"]
            return adj_range["min"] + (adj_range["max"] - adj_range["min"]) * exchange.confidence
        
        # Check for moderate confirmation
        mod_rule = EXCHANGE_ADJUSTMENT_RULES["moderate_confirmation"]
        if (exchange.confidence >= mod_rule["confidence_min"] and 
            exchange.conflict_ratio <= mod_rule["conflict_max"]):
            adj_range = mod_rule["adjustment_range"]
            return adj_range["min"] + (adj_range["max"] - adj_range["min"]) * exchange.confidence
        
        # Default: neutral adjustment
        return 1.0
    
    def _compute_market_adjustment(self, market_state: MarketStateInputSnapshot) -> float:
        """Compute market state adjustment."""
        combined = market_state.combined_state
        risk_state = market_state.risk_state
        
        # Determine market category
        if combined in HOSTILE_MARKET_STATES:
            category = "hostile"
        elif combined in SUPPORTIVE_MARKET_STATES:
            category = "supportive"
        elif combined == "UNDEFINED" or "CONFLICTED" in combined:
            category = "mixed"
        else:
            category = "neutral"
        
        # Get base range
        adj_range = MARKET_ADJUSTMENT_RANGES.get(category, MARKET_ADJUSTMENT_RANGES["neutral"])
        
        # Scale by market confidence
        base_adj = adj_range["min"] + (adj_range["max"] - adj_range["min"]) * market_state.confidence
        
        # Apply risk state modifier
        risk_modifier = RISK_STATE_ADJUSTMENTS.get(risk_state, 1.0)
        
        return base_adj * risk_modifier
    
    def _compute_dominance_adjustment(self, dom_modifier: Dict[str, float]) -> float:
        """
        PHASE 14.9: Compute dominance adjustment.
        
        This is the MAIN place where dominance affects sizing.
        """
        # Get confidence modifier (which reflects dominance regime)
        conf_mod = dom_modifier.get("confidence_modifier", 1.0)
        
        # Clamp to reasonable range [0.7, 1.3]
        return max(0.7, min(1.3, conf_mod))
    
    def _compute_breadth_adjustment(self, dom_modifier: Dict[str, float]) -> float:
        """
        PHASE 14.9: Compute breadth adjustment.
        
        Size modifier from market breadth state.
        """
        # Get size modifier from breadth
        size_mod = dom_modifier.get("size_modifier", 1.0)
        
        # Clamp to reasonable range [0.6, 1.15]
        return max(0.6, min(1.15, size_mod))
    
    def _compute_ecology_adjustment(self, ecology_modifier: Dict[str, float]) -> float:
        """
        PHASE 15.7: Compute ecology adjustment.
        
        Size modifier from alpha ecology state.
        
        Ecology States:
            HEALTHY  → 1.05 (boost size)
            STABLE   → 1.00 (neutral)
            STRESSED → 0.85 (reduce size)
            CRITICAL → 0.65 (strong reduce)
        """
        # Get size modifier from ecology
        size_mod = ecology_modifier.get("ecology_size_modifier", 1.0)
        
        # Clamp to reasonable range [0.5, 1.1]
        return max(0.5, min(1.1, size_mod))
    
    def _compute_interaction_adjustment(self, interaction_modifier: Dict[str, float]) -> float:
        """
        PHASE 16.6: Compute interaction adjustment.
        
        Size modifier from interaction aggregator.
        
        Interaction States:
            STRONG_POSITIVE → 1.10 (boost size)
            POSITIVE        → 1.03 (slight boost)
            NEUTRAL         → 1.00 (neutral)
            NEGATIVE        → 0.85 (reduce size)
            CRITICAL        → 0.65 (strong reduce)
        """
        # Get size modifier from interaction aggregator
        size_mod = interaction_modifier.get("interaction_size_modifier", 1.0)
        
        # Clamp to reasonable range [0.5, 1.15]
        return max(0.5, min(1.15, size_mod))
    
    def _determine_size_bucket(self, final_size_pct: float) -> SizeBucket:
        """Determine size bucket from final percentage."""
        if final_size_pct <= SIZE_BUCKET_THRESHOLDS["NONE"]:
            return SizeBucket.NONE
        elif final_size_pct <= SIZE_BUCKET_THRESHOLDS["TINY"]:
            return SizeBucket.TINY
        elif final_size_pct <= SIZE_BUCKET_THRESHOLDS["SMALL"]:
            return SizeBucket.SMALL
        elif final_size_pct <= SIZE_BUCKET_THRESHOLDS["NORMAL"]:
            return SizeBucket.NORMAL
        else:
            return SizeBucket.LARGE
    
    def _build_reason(
        self,
        decision: DecisionInputSnapshot,
        vol_adj: float,
        ex_adj: float,
        market_adj: float,
        dom_adj: float = 1.0,
        breadth_adj: float = 1.0,
        ecology_adj: float = 1.0,
        interaction_adj: float = 1.0,
    ) -> str:
        """Build human-readable reason. PHASE 16.6: includes interaction."""
        reasons = []
        
        # Base action reason
        if decision.action in ("BLOCK", "WAIT"):
            return f"no_position_{decision.action.lower()}"
        elif decision.action == "REVERSE_CANDIDATE":
            return "reverse_candidate_no_position"
        
        reasons.append(f"action_{decision.action.lower()}")
        
        # Volatility impact
        if vol_adj < 0.8:
            reasons.append("high_volatility_reduction")
        elif vol_adj > 1.0:
            reasons.append("low_volatility_boost")
        
        # Exchange impact
        if ex_adj < 0.8:
            reasons.append("exchange_conflict_penalty")
        elif ex_adj > 1.05:
            reasons.append("exchange_confirmation_boost")
        
        # Market impact
        if market_adj < 0.8:
            reasons.append("hostile_market_penalty")
        elif market_adj > 1.0:
            reasons.append("supportive_market_boost")
        
        # PHASE 14.9: Dominance impact
        if dom_adj < 0.9:
            reasons.append("dominance_penalty")
        elif dom_adj > 1.1:
            reasons.append("dominance_boost")
        
        # PHASE 14.9: Breadth impact
        if breadth_adj < 0.85:
            reasons.append("weak_breadth_penalty")
        elif breadth_adj > 1.05:
            reasons.append("strong_breadth_boost")
        
        # PHASE 15.7: Ecology impact
        if ecology_adj < 0.75:
            reasons.append("ecology_critical_penalty")
        elif ecology_adj < 0.9:
            reasons.append("ecology_stressed_penalty")
        elif ecology_adj > 1.02:
            reasons.append("ecology_healthy_boost")
        
        # PHASE 16.6: Interaction impact
        if interaction_adj < 0.70:
            reasons.append("interaction_critical_penalty")
        elif interaction_adj < 0.90:
            reasons.append("interaction_negative_penalty")
        elif interaction_adj > 1.05:
            reasons.append("interaction_positive_boost")
        
        return "_".join(reasons) if reasons else "standard_sizing"


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[PositionSizingEngine] = None


def get_position_sizing_engine() -> PositionSizingEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = PositionSizingEngine()
    return _engine
