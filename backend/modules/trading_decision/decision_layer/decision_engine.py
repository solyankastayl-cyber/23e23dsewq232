"""
PHASE 14.4 — Trading Decision Engine
======================================
Hierarchical decision engine that combines:
- TA Hypothesis
- Exchange Context
- Market State Matrix

Into a single trading decision.

Architecture:
    TAHypothesis ──────────┐
                            │
    ExchangeContext ────────┼── Decision Engine ── TradingDecision
                            │
    MarketStateMatrix ─────┘

Output: ALLOW / ALLOW_REDUCED / ALLOW_AGGRESSIVE / BLOCK / WAIT / REVERSE_CANDIDATE
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.trading_decision.decision_layer.decision_types import (
    TradingDecision,
    DecisionAction,
    ExecutionMode,
    TradeDirection,
    DecisionRule,
    TADecisionInput,
    ExchangeDecisionInput,
    MarketStateDecisionInput,
)
from modules.trading_decision.decision_layer.decision_rules import (
    SETUP_THRESHOLDS,
    AGREEMENT_THRESHOLDS,
    CONFLICT_THRESHOLDS,
    POSITION_MULTIPLIERS,
    CONFIDENCE_WEIGHTS,
    CONFIDENCE_PENALTIES,
    CONFIDENCE_BONUSES,
    HOSTILE_MARKET_STATES,
    SUPPORTIVE_LONG_STATES,
    SUPPORTIVE_SHORT_STATES,
    EXECUTION_MODE_RULES,
)

# MongoDB
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


class DecisionEngine:
    """
    Trading Decision Engine.
    
    Combines all intelligence sources into a single decision.
    Uses hierarchical rules, not averaging.
    
    PHASE 14.9: Now includes Dominance/Breadth modifiers.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Lazy load builders
        self._ta_builder = None
        self._exchange_aggregator = None
        self._market_state_builder = None
        self._market_structure_engine = None
    
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
    
    def decide(self, symbol: str) -> TradingDecision:
        """
        Make trading decision for symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            TradingDecision with action, direction, confidence, etc.
        """
        now = datetime.now(timezone.utc)
        
        # Get all inputs
        ta_input = self._get_ta_input(symbol)
        exchange_input = self._get_exchange_input(symbol)
        market_state_input = self._get_market_state_input(symbol)
        
        # PHASE 14.9: Get dominance/breadth modifiers
        dom_modifier = self._get_dominance_modifier(symbol)
        
        # Run hierarchical decision rules (now with dominance awareness)
        action, rule, reason = self._apply_decision_rules(
            ta_input, exchange_input, market_state_input, dom_modifier
        )
        
        # Determine direction
        direction = self._determine_direction(ta_input, exchange_input, action, rule)
        
        # Compute confidence (now with dominance modifier)
        confidence = self._compute_confidence(
            ta_input, exchange_input, market_state_input, action, rule, dom_modifier
        )
        
        # Compute position multiplier
        position_multiplier = self._compute_position_multiplier(action, confidence)
        
        # Determine execution mode
        execution_mode = self._determine_execution_mode(action, confidence, market_state_input)
        
        # Build drivers
        drivers = self._build_drivers(
            ta_input, exchange_input, market_state_input, rule
        )
        
        # Build summaries
        ta_summary = {
            "direction": ta_input.direction,
            "setup_quality": round(ta_input.setup_quality, 3),
            "conviction": round(ta_input.conviction, 3),
            "has_valid_setup": ta_input.has_valid_setup,
        }
        
        exchange_summary = {
            "bias": exchange_input.bias,
            "confidence": round(exchange_input.confidence, 3),
            "conflict_ratio": round(exchange_input.conflict_ratio, 3),
            "dominant_signal": exchange_input.dominant_signal,
        }
        
        market_state_summary = {
            "combined_state": market_state_input.combined_state,
            "trend_state": market_state_input.trend_state,
            "risk_state": market_state_input.risk_state,
            "is_hostile": market_state_input.is_hostile,
            "is_supportive": market_state_input.is_supportive,
        }
        
        return TradingDecision(
            symbol=symbol,
            timestamp=now,
            action=action,
            direction=direction,
            confidence=confidence,
            position_multiplier=position_multiplier,
            execution_mode=execution_mode,
            reason=reason,
            decision_rule=rule,
            drivers=drivers,
            ta_summary=ta_summary,
            exchange_summary=exchange_summary,
            market_state_summary=market_state_summary,
        )
    
    def decide_batch(self, symbols: List[str]) -> List[TradingDecision]:
        """Make decisions for multiple symbols."""
        return [self.decide(symbol) for symbol in symbols]
    
    # ═══════════════════════════════════════════════════════════════
    # INPUT GETTERS
    # ═══════════════════════════════════════════════════════════════
    
    def _get_ta_input(self, symbol: str) -> TADecisionInput:
        """Get TA Hypothesis as decision input."""
        try:
            hypothesis = self.ta_builder.build(symbol)
            
            # Determine if valid setup
            has_valid_setup = (
                hypothesis.setup_quality >= SETUP_THRESHOLDS["min_setup_quality"]
                and hypothesis.setup_type.value != "NO_SETUP"
            )
            
            return TADecisionInput(
                direction=hypothesis.direction.value,
                setup_quality=hypothesis.setup_quality,
                trend_strength=hypothesis.trend_strength,
                entry_quality=hypothesis.entry_quality,
                regime_fit=hypothesis.regime_fit,
                conviction=hypothesis.conviction,
                setup_type=hypothesis.setup_type.value,
                has_valid_setup=has_valid_setup,
            )
        except Exception:
            return TADecisionInput(
                direction="NEUTRAL",
                setup_quality=0.0,
                trend_strength=0.0,
                entry_quality=0.5,
                regime_fit=0.5,
                conviction=0.0,
                setup_type="NO_SETUP",
                has_valid_setup=False,
            )
    
    def _get_exchange_input(self, symbol: str) -> ExchangeDecisionInput:
        """Get Exchange Context as decision input."""
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
            
            # Determine dominant signal
            driver_scores = {
                "funding": abs(context.funding_signal.funding_rate * 100) if context.funding_signal else 0,
                "flow": abs(context.flow_pressure),
                "derivatives": abs(context.derivatives_pressure),
                "liquidation": context.cascade_probability,
                "volume": context.volume_signal.anomaly_score if context.volume_signal else 0,
            }
            dominant = max(driver_scores, key=driver_scores.get)
            
            return ExchangeDecisionInput(
                bias=context.exchange_bias.value,
                confidence=context.confidence,
                conflict_ratio=min(conflict, 1.0),
                dominant_signal=dominant,
                crowding_risk=context.crowding_risk,
                squeeze_probability=context.squeeze_probability,
                cascade_probability=context.cascade_probability,
                derivatives_pressure=context.derivatives_pressure,
                flow_pressure=context.flow_pressure,
            )
        except Exception:
            return ExchangeDecisionInput(
                bias="NEUTRAL",
                confidence=0.5,
                conflict_ratio=0.5,
                dominant_signal="none",
                crowding_risk=0.0,
                squeeze_probability=0.0,
                cascade_probability=0.0,
                derivatives_pressure=0.0,
                flow_pressure=0.0,
            )
    
    def _get_market_state_input(self, symbol: str) -> MarketStateDecisionInput:
        """Get Market State as decision input."""
        try:
            state = self.market_state_builder.build(symbol)
            
            combined = state.combined_state.value
            is_hostile = combined in HOSTILE_MARKET_STATES
            is_supportive = combined in SUPPORTIVE_LONG_STATES or combined in SUPPORTIVE_SHORT_STATES
            
            return MarketStateDecisionInput(
                trend_state=state.trend_state.value,
                volatility_state=state.volatility_state.value,
                exchange_state=state.exchange_state.value,
                derivatives_state=state.derivatives_state.value,
                risk_state=state.risk_state.value,
                combined_state=combined,
                confidence=state.confidence,
                is_hostile=is_hostile,
                is_supportive=is_supportive,
            )
        except Exception:
            return MarketStateDecisionInput(
                trend_state="RANGE",
                volatility_state="NORMAL",
                exchange_state="NEUTRAL",
                derivatives_state="BALANCED",
                risk_state="NEUTRAL",
                combined_state="UNDEFINED",
                confidence=0.5,
                is_hostile=False,
                is_supportive=False,
            )
    
    def _get_dominance_modifier(self, symbol: str) -> Dict[str, float]:
        """
        PHASE 14.9: Get dominance/breadth modifiers for symbol.
        
        Returns dict with:
        - confidence_modifier: Multiplier for confidence (0.8 - 1.2)
        - size_modifier: Multiplier for position sizing
        - dominance_regime: BTC_DOM, ETH_DOM, ALT_DOM, BALANCED
        - breadth_state: STRONG, WEAK, MIXED
        - rotation_state: ROTATING_TO_BTC, etc.
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
    
    # ═══════════════════════════════════════════════════════════════
    # HIERARCHICAL DECISION RULES
    # ═══════════════════════════════════════════════════════════════
    
    def _apply_decision_rules(
        self,
        ta: TADecisionInput,
        exchange: ExchangeDecisionInput,
        market_state: MarketStateDecisionInput,
        dom_modifier: Dict[str, float] = None,
    ) -> Tuple[DecisionAction, DecisionRule, str]:
        """
        Apply hierarchical decision rules.
        Returns: (action, rule, reason)
        
        PHASE 14.9: dom_modifier is passed but NOT used to change action.
        Dominance overlay only modifies confidence/sizing, not the base decision.
        """
        
        # ── Rule Group A: No Setup ──
        if not ta.has_valid_setup or ta.conviction < SETUP_THRESHOLDS["min_conviction"]:
            return (
                DecisionAction.WAIT,
                DecisionRule.NO_SETUP,
                "no_valid_ta_setup_detected"
            )
        
        # ── Rule Group F: Bad Market State ──
        if market_state.is_hostile and market_state.confidence < 0.5:
            return (
                DecisionAction.WAIT,
                DecisionRule.BAD_MARKET_STATE,
                f"hostile_market_state_{market_state.combined_state}"
            )
        
        # Determine alignment
        ta_long = ta.direction == "LONG"
        ta_short = ta.direction == "SHORT"
        ex_bullish = exchange.bias == "BULLISH"
        ex_bearish = exchange.bias == "BEARISH"
        ex_neutral = exchange.bias == "NEUTRAL"
        
        aligned = (ta_long and ex_bullish) or (ta_short and ex_bearish)
        conflicted = (ta_long and ex_bearish) or (ta_short and ex_bullish)
        
        # ── Rule Group E: Extreme Conflict / Reverse ──
        if conflicted:
            extreme_conflict = (
                exchange.conflict_ratio >= CONFLICT_THRESHOLDS["extreme_conflict_min"]
                or exchange.squeeze_probability >= CONFLICT_THRESHOLDS["squeeze_extreme"]
                or exchange.cascade_probability >= CONFLICT_THRESHOLDS["cascade_extreme"]
            )
            
            if extreme_conflict and market_state.is_hostile:
                return (
                    DecisionAction.REVERSE_CANDIDATE,
                    DecisionRule.EXTREME_CONFLICT_REVERSE,
                    "extreme_conflict_with_hostile_market_reverse_candidate"
                )
        
        # ── Rule Group B: Strong Agreement ──
        if aligned:
            strong_agreement = (
                ta.conviction >= AGREEMENT_THRESHOLDS["strong_agreement_min_conviction"]
                and exchange.confidence >= AGREEMENT_THRESHOLDS["strong_agreement_min_exchange_conf"]
                and market_state.is_supportive
            )
            
            if strong_agreement:
                return (
                    DecisionAction.ALLOW_AGGRESSIVE,
                    DecisionRule.STRONG_AGREEMENT,
                    "strong_ta_exchange_market_alignment"
                )
        
        # ── Rule Group C: Mild Agreement ──
        if aligned or ex_neutral:
            mild_agreement = (
                ta.conviction >= AGREEMENT_THRESHOLDS["mild_agreement_min_conviction"]
                and not market_state.is_hostile
            )
            
            if mild_agreement:
                return (
                    DecisionAction.ALLOW,
                    DecisionRule.MILD_AGREEMENT,
                    "ta_setup_valid_with_neutral_or_supportive_context"
                )
        
        # ── Rule Group D: Conflict ──
        if conflicted:
            # Strong conflict
            if exchange.conflict_ratio >= CONFLICT_THRESHOLDS["strong_conflict_min"]:
                return (
                    DecisionAction.BLOCK,
                    DecisionRule.STRONG_CONFLICT,
                    "strong_ta_exchange_conflict_blocking_trade"
                )
            
            # Weak conflict
            return (
                DecisionAction.ALLOW_REDUCED,
                DecisionRule.WEAK_CONFLICT,
                "ta_setup_valid_but_exchange_conflicted"
            )
        
        # ── Fallback: Low Conviction ──
        if ta.conviction < AGREEMENT_THRESHOLDS["mild_agreement_min_conviction"]:
            return (
                DecisionAction.WAIT,
                DecisionRule.LOW_CONVICTION,
                "conviction_too_low_waiting"
            )
        
        # Default: Allow with neutral context
        return (
            DecisionAction.ALLOW,
            DecisionRule.MILD_AGREEMENT,
            "default_allow_with_valid_setup"
        )
    
    # ═══════════════════════════════════════════════════════════════
    # DIRECTION, CONFIDENCE, SIZING
    # ═══════════════════════════════════════════════════════════════
    
    def _determine_direction(
        self,
        ta: TADecisionInput,
        exchange: ExchangeDecisionInput,
        action: DecisionAction,
        rule: DecisionRule,
    ) -> TradeDirection:
        """Determine trade direction."""
        
        # Reverse candidate: flip direction
        if action == DecisionAction.REVERSE_CANDIDATE:
            if ta.direction == "LONG":
                return TradeDirection.SHORT
            elif ta.direction == "SHORT":
                return TradeDirection.LONG
            return TradeDirection.NEUTRAL
        
        # Blocked or wait: neutral
        if action in (DecisionAction.BLOCK, DecisionAction.WAIT):
            return TradeDirection.NEUTRAL
        
        # Follow TA direction
        return TradeDirection(ta.direction)
    
    def _compute_confidence(
        self,
        ta: TADecisionInput,
        exchange: ExchangeDecisionInput,
        market_state: MarketStateDecisionInput,
        action: DecisionAction,
        rule: DecisionRule,
        dom_modifier: Dict[str, float] = None,
    ) -> float:
        """
        Compute decision confidence with penalties/bonuses.
        
        PHASE 14.9: Apply dominance modifier to final confidence.
        """
        
        # Base confidence from weighted components
        base_confidence = (
            CONFIDENCE_WEIGHTS["ta_conviction"] * ta.conviction
            + CONFIDENCE_WEIGHTS["exchange_confidence"] * exchange.confidence
            + CONFIDENCE_WEIGHTS["market_state_confidence"] * market_state.confidence
        )
        
        # Apply penalties
        penalties = 0.0
        
        if exchange.conflict_ratio > 0.5:
            penalties += CONFIDENCE_PENALTIES["high_conflict"]
        
        if market_state.is_hostile:
            penalties += CONFIDENCE_PENALTIES["hostile_regime"]
        
        if exchange.squeeze_probability > 0.5:
            penalties += CONFIDENCE_PENALTIES["squeeze_risk"]
        
        # Apply bonuses
        bonuses = 0.0
        
        if rule == DecisionRule.STRONG_AGREEMENT:
            bonuses += CONFIDENCE_BONUSES["strong_alignment"]
        
        if market_state.is_supportive:
            bonuses += CONFIDENCE_BONUSES["supportive_market"]
        
        # Final confidence
        final = base_confidence - penalties + bonuses
        
        # Additional reduction for certain actions
        if action == DecisionAction.BLOCK:
            final *= 0.5
        elif action == DecisionAction.REVERSE_CANDIDATE:
            final *= 0.6
        elif action == DecisionAction.WAIT:
            final *= 0.7
        
        # ── PHASE 14.9: Apply dominance modifier ──
        # Dominance only modifies confidence, not action
        if dom_modifier:
            confidence_mod = dom_modifier.get("confidence_modifier", 1.0)
            final *= confidence_mod
        
        return max(0.0, min(1.0, final))
    
    def _compute_position_multiplier(
        self,
        action: DecisionAction,
        confidence: float,
    ) -> float:
        """Compute position size multiplier."""
        
        action_key = action.value
        config = POSITION_MULTIPLIERS.get(action_key, {"value": 0.0})
        
        if "value" in config:
            return config["value"]
        
        # Scale within range based on confidence
        min_mult = config["min"]
        max_mult = config["max"]
        
        return min_mult + (max_mult - min_mult) * confidence
    
    def _determine_execution_mode(
        self,
        action: DecisionAction,
        confidence: float,
        market_state: MarketStateDecisionInput,
    ) -> ExecutionMode:
        """Determine execution mode."""
        
        # Base mode from action
        base_mode = EXECUTION_MODE_RULES.get(action.value, "NORMAL")
        
        # Adjust for high volatility
        if market_state.volatility_state == "HIGH" and action == DecisionAction.ALLOW:
            return ExecutionMode.PASSIVE
        
        # Adjust for low confidence
        if confidence < 0.5 and base_mode == "NORMAL":
            return ExecutionMode.PASSIVE
        
        return ExecutionMode(base_mode)
    
    def _build_drivers(
        self,
        ta: TADecisionInput,
        exchange: ExchangeDecisionInput,
        market_state: MarketStateDecisionInput,
        rule: DecisionRule,
    ) -> Dict[str, any]:
        """Build explainability drivers."""
        return {
            "ta_direction": ta.direction,
            "ta_conviction": round(ta.conviction, 4),
            "ta_setup_quality": round(ta.setup_quality, 4),
            "exchange_bias": exchange.bias,
            "exchange_confidence": round(exchange.confidence, 4),
            "exchange_conflict_ratio": round(exchange.conflict_ratio, 4),
            "market_state": market_state.combined_state,
            "market_risk_state": market_state.risk_state,
            "dominant_signal": exchange.dominant_signal,
            "decision_rule": rule.value,
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[DecisionEngine] = None


def get_decision_engine() -> DecisionEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = DecisionEngine()
    return _engine
