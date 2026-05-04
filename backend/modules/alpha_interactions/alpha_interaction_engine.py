"""
PHASE 16.1 — Alpha Interaction Engine (Foundation)
===================================================
Analyzes signal interactions: reinforcement vs conflict.

Purpose:
    Understand how signals from different sources interact.
    TA + Exchange + Market State + Ecology → Interaction assessment.

Formula:
    reinforcement_score = 
        0.40 * ta_exchange_alignment
        + 0.30 * trend_alignment
        + 0.30 * ecology_support
    
    conflict_score =
        0.50 * ta_exchange_conflict
        + 0.30 * exchange_conflict_ratio
        + 0.20 * hostile_market_mismatch
    
    net_interaction_score = reinforcement_score - conflict_score

States:
    > 0.20 → REINFORCED (signals strengthen each other)
    -0.20 to 0.20 → NEUTRAL (signals are independent)
    < -0.20 → CONFLICTED (signals contradict)

Confidence Modifiers:
    REINFORCED: 1.05 - 1.15
    NEUTRAL: 1.00
    CONFLICTED: 0.75 - 0.90

Key Principle:
    Interaction NEVER blocks a signal.
    It only modifies confidence.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_interactions.alpha_interaction_types import (
    InteractionState,
    AlphaInteractionState,
    TAInputForInteraction,
    ExchangeInputForInteraction,
    MarketStateInputForInteraction,
    EcologyInputForInteraction,
    INTERACTION_THRESHOLDS,
    INTERACTION_MODIFIERS,
    REINFORCEMENT_WEIGHTS,
    CONFLICT_WEIGHTS,
)

# MongoDB
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# DIRECTION MAPPING
# ══════════════════════════════════════════════════════════════

DIRECTION_TO_NUMERIC = {
    "LONG": 1.0,
    "BULLISH": 1.0,
    "SHORT": -1.0,
    "BEARISH": -1.0,
    "NEUTRAL": 0.0,
}

TREND_STATE_TO_DIRECTION = {
    "TREND_UP": "LONG",
    "TREND_DOWN": "SHORT",
    "RANGE": "NEUTRAL",
    "MIXED": "NEUTRAL",
}

EXCHANGE_STATE_TO_DIRECTION = {
    "BULLISH": "LONG",
    "BEARISH": "SHORT",
    "NEUTRAL": "NEUTRAL",
    "CONFLICTED": "NEUTRAL",
}


# ══════════════════════════════════════════════════════════════
# ALPHA INTERACTION ENGINE
# ══════════════════════════════════════════════════════════════

class AlphaInteractionEngine:
    """
    Alpha Interaction Engine - PHASE 16.1
    
    Analyzes how signals reinforce or conflict with each other.
    
    Input Sources:
        - TAHypothesis: direction, conviction, trend_strength
        - ExchangeContext: bias, confidence, conflict_ratio
        - MarketStateMatrix: trend_state, exchange_state
        - AlphaEcology: ecology_score, ecology_state
    
    Output:
        AlphaInteractionState with reinforcement/conflict analysis.
    
    Key Principle:
        Interaction NEVER blocks a signal.
        It only modifies confidence.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Lazy load upstream engines
        self._ta_hypothesis_builder = None
        self._exchange_aggregator = None
        self._market_state_builder = None
        self._ecology_engine = None
        self._reinforcement_patterns_engine = None
        self._conflict_patterns_engine = None
        self._synergy_engine = None
        self._cancellation_engine = None
    
    # ═══════════════════════════════════════════════════════════
    # LAZY LOADERS
    # ═══════════════════════════════════════════════════════════
    
    @property
    def ta_hypothesis_builder(self):
        if self._ta_hypothesis_builder is None:
            try:
                from modules.ta_engine.hypothesis.ta_hypothesis_builder import get_ta_hypothesis_builder
                self._ta_hypothesis_builder = get_ta_hypothesis_builder()
            except ImportError:
                pass
        return self._ta_hypothesis_builder
    
    @property
    def exchange_aggregator(self):
        if self._exchange_aggregator is None:
            try:
                from modules.exchange_intelligence.exchange_context_aggregator import get_exchange_aggregator
                self._exchange_aggregator = get_exchange_aggregator()
            except ImportError:
                pass
        return self._exchange_aggregator
    
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
    def ecology_engine(self):
        if self._ecology_engine is None:
            try:
                from modules.alpha_ecology.alpha_ecology_engine import get_alpha_ecology_engine
                self._ecology_engine = get_alpha_ecology_engine()
            except ImportError:
                pass
        return self._ecology_engine
    
    @property
    def reinforcement_patterns_engine(self):
        if self._reinforcement_patterns_engine is None:
            try:
                from modules.alpha_interactions.reinforcement_patterns_engine import get_reinforcement_patterns_engine
                self._reinforcement_patterns_engine = get_reinforcement_patterns_engine()
            except ImportError:
                pass
        return self._reinforcement_patterns_engine
    
    @property
    def conflict_patterns_engine(self):
        if self._conflict_patterns_engine is None:
            try:
                from modules.alpha_interactions.conflict_patterns_engine import get_conflict_patterns_engine
                self._conflict_patterns_engine = get_conflict_patterns_engine()
            except ImportError:
                pass
        return self._conflict_patterns_engine
    
    @property
    def synergy_engine(self):
        if self._synergy_engine is None:
            try:
                from modules.alpha_interactions.synergy_engine import get_synergy_engine
                self._synergy_engine = get_synergy_engine()
            except ImportError:
                pass
        return self._synergy_engine
    
    @property
    def cancellation_engine(self):
        if self._cancellation_engine is None:
            try:
                from modules.alpha_interactions.cancellation_engine import get_cancellation_engine
                self._cancellation_engine = get_cancellation_engine()
            except ImportError:
                pass
        return self._cancellation_engine
    
    # ═══════════════════════════════════════════════════════════
    # MAIN ANALYSIS
    # ═══════════════════════════════════════════════════════════
    
    def analyze(self, symbol: str) -> AlphaInteractionState:
        """
        Analyze signal interactions for a symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            AlphaInteractionState with interaction assessment
        """
        now = datetime.now(timezone.utc)
        
        # Gather inputs from upstream engines
        ta_input = self._get_ta_input(symbol)
        exchange_input = self._get_exchange_input(symbol)
        market_state_input = self._get_market_state_input(symbol)
        ecology_input = self._get_ecology_input(symbol)
        
        # Calculate base reinforcement score
        base_reinforcement = self._calculate_reinforcement(
            ta_input, exchange_input, market_state_input, ecology_input
        )
        
        # PHASE 16.2: Add pattern-based reinforcement
        pattern_data = self._get_pattern_reinforcement(symbol)
        pattern_strength = pattern_data.get("pattern_reinforcement_strength", 0.0)
        patterns_detected = pattern_data.get("patterns_detected", [])
        
        # PHASE 16.4: Add synergy-based reinforcement
        synergy_data = self._get_synergy_patterns(symbol)
        synergy_strength = synergy_data.get("synergy_strength", 0.0)
        synergy_patterns = synergy_data.get("synergy_patterns", [])
        
        # PHASE 16.5: Get cancellation data
        cancellation_data = self._get_cancellation_patterns(symbol)
        cancellation_strength = cancellation_data.get("cancellation_strength", 0.0)
        cancellation_patterns = cancellation_data.get("cancellation_patterns", [])
        trade_cancelled = cancellation_data.get("trade_cancelled", False)
        
        # Integrate pattern + synergy - cancellation:
        # reinforcement_score += pattern * 0.3 + synergy * 0.25 - cancellation * 0.4
        reinforcement_score = base_reinforcement + (pattern_strength * 0.3) + (synergy_strength * 0.25) - (cancellation_strength * 0.4)
        reinforcement_score = max(0.0, min(1.0, reinforcement_score))  # Clamp 0-1
        
        # Calculate base conflict score
        base_conflict = self._calculate_conflict(
            ta_input, exchange_input, market_state_input
        )
        
        # PHASE 16.3: Add pattern-based conflict
        conflict_data = self._get_conflict_patterns(symbol)
        conflict_pattern_strength = conflict_data.get("pattern_conflict_strength", 0.0)
        conflict_patterns = conflict_data.get("conflict_patterns", [])
        
        # Integrate conflict pattern: conflict_score += conflict_pattern_strength * 0.35
        conflict_score = base_conflict + (conflict_pattern_strength * 0.35)
        conflict_score = min(1.0, conflict_score)  # Cap at 1.0
        
        # Calculate net interaction score
        net_interaction_score = reinforcement_score - conflict_score
        
        # Determine interaction state
        interaction_state = self._determine_state(net_interaction_score)
        
        # PHASE 16.5: Override state if trade cancelled
        if trade_cancelled:
            interaction_state = InteractionState.CONFLICTED
        
        # Calculate confidence modifier
        confidence_modifier = self._calculate_modifier(
            interaction_state, net_interaction_score
        )
        
        # PHASE 16.5: Apply cancellation modifier
        if cancellation_strength > 0:
            cancellation_modifier = cancellation_data.get("cancellation_modifier", 1.0)
            confidence_modifier = confidence_modifier * cancellation_modifier
            confidence_modifier = max(0.5, confidence_modifier)  # Floor at 0.5
        
        # Build drivers with pattern info
        drivers = self._build_drivers(
            ta_input, exchange_input, market_state_input, ecology_input,
            reinforcement_score, conflict_score
        )
        
        # Add reinforcement pattern data to drivers
        drivers["patterns_detected"] = patterns_detected
        drivers["pattern_strength"] = round(pattern_strength, 4)
        drivers["pattern_count"] = len(patterns_detected)
        drivers["dominant_pattern"] = pattern_data.get("dominant_pattern")
        
        # PHASE 16.3: Add conflict pattern data to drivers
        drivers["conflict_patterns"] = conflict_patterns
        drivers["conflict_pattern_strength"] = round(conflict_pattern_strength, 4)
        drivers["conflict_count"] = len(conflict_patterns)
        drivers["conflict_severity"] = conflict_data.get("conflict_severity", "LOW_CONFLICT")
        drivers["dominant_conflict"] = conflict_data.get("dominant_conflict")
        
        # PHASE 16.4: Add synergy pattern data to drivers
        drivers["synergy_patterns"] = synergy_patterns
        drivers["synergy_strength"] = round(synergy_strength, 4)
        drivers["synergy_count"] = len(synergy_patterns)
        drivers["synergy_potential"] = synergy_data.get("synergy_potential", "LOW")
        drivers["dominant_synergy"] = synergy_data.get("dominant_synergy")
        
        # PHASE 16.5: Add cancellation pattern data to drivers
        drivers["cancellation_patterns"] = cancellation_patterns
        drivers["cancellation_strength"] = round(cancellation_strength, 4)
        drivers["cancellation_count"] = len(cancellation_patterns)
        drivers["trade_cancelled"] = trade_cancelled
        drivers["dominant_cancellation"] = cancellation_data.get("dominant_cancellation")
        
        return AlphaInteractionState(
            symbol=symbol,
            timestamp=now,
            reinforcement_score=reinforcement_score,
            conflict_score=conflict_score,
            net_interaction_score=net_interaction_score,
            interaction_state=interaction_state,
            confidence_modifier=confidence_modifier,
            drivers=drivers,
            ta_input=ta_input,
            exchange_input=exchange_input,
            market_state_input=market_state_input,
            ecology_input=ecology_input,
        )
    
    def analyze_from_inputs(
        self,
        symbol: str,
        ta_input: TAInputForInteraction,
        exchange_input: ExchangeInputForInteraction,
        market_state_input: MarketStateInputForInteraction,
        ecology_input: EcologyInputForInteraction,
    ) -> AlphaInteractionState:
        """
        Analyze with provided inputs (for testing).
        """
        now = datetime.now(timezone.utc)
        
        reinforcement_score = self._calculate_reinforcement(
            ta_input, exchange_input, market_state_input, ecology_input
        )
        
        conflict_score = self._calculate_conflict(
            ta_input, exchange_input, market_state_input
        )
        
        net_interaction_score = reinforcement_score - conflict_score
        
        interaction_state = self._determine_state(net_interaction_score)
        
        confidence_modifier = self._calculate_modifier(
            interaction_state, net_interaction_score
        )
        
        drivers = self._build_drivers(
            ta_input, exchange_input, market_state_input, ecology_input,
            reinforcement_score, conflict_score
        )
        
        return AlphaInteractionState(
            symbol=symbol,
            timestamp=now,
            reinforcement_score=reinforcement_score,
            conflict_score=conflict_score,
            net_interaction_score=net_interaction_score,
            interaction_state=interaction_state,
            confidence_modifier=confidence_modifier,
            drivers=drivers,
            ta_input=ta_input,
            exchange_input=exchange_input,
            market_state_input=market_state_input,
            ecology_input=ecology_input,
        )
    
    # ═══════════════════════════════════════════════════════════
    # INPUT GATHERING
    # ═══════════════════════════════════════════════════════════
    
    def _get_ta_input(self, symbol: str) -> TAInputForInteraction:
        """Get TA Hypothesis input."""
        if self.ta_hypothesis_builder is None:
            return TAInputForInteraction(
                direction="NEUTRAL",
                conviction=0.5,
                trend_strength=0.5,
                setup_quality=0.5,
                regime="RANGE",
            )
        
        try:
            ta_result = self.ta_hypothesis_builder.build_hypothesis(symbol)
            return TAInputForInteraction(
                direction=ta_result.direction.value,
                conviction=ta_result.conviction,
                trend_strength=ta_result.trend_strength,
                setup_quality=ta_result.setup_quality,
                regime=ta_result.regime.value,
            )
        except Exception:
            return TAInputForInteraction(
                direction="NEUTRAL",
                conviction=0.5,
                trend_strength=0.5,
                setup_quality=0.5,
                regime="RANGE",
            )
    
    def _get_exchange_input(self, symbol: str) -> ExchangeInputForInteraction:
        """Get Exchange Context input."""
        if self.exchange_aggregator is None:
            return ExchangeInputForInteraction(
                bias="NEUTRAL",
                confidence=0.5,
                dominant_signal="none",
                conflict_ratio=0.5,
            )
        
        try:
            exchange_result = self.exchange_aggregator.aggregate(symbol)
            
            # Calculate conflict ratio from internal signals
            conflict_ratio = self._estimate_exchange_conflict(exchange_result)
            
            # Determine dominant signal
            dominant = self._get_dominant_signal(exchange_result)
            
            return ExchangeInputForInteraction(
                bias=exchange_result.exchange_bias.value,
                confidence=exchange_result.confidence,
                dominant_signal=dominant,
                conflict_ratio=conflict_ratio,
            )
        except Exception:
            return ExchangeInputForInteraction(
                bias="NEUTRAL",
                confidence=0.5,
                dominant_signal="none",
                conflict_ratio=0.5,
            )
    
    def _get_market_state_input(self, symbol: str) -> MarketStateInputForInteraction:
        """Get Market State Matrix input."""
        if self.market_state_builder is None:
            return MarketStateInputForInteraction(
                trend_state="MIXED",
                exchange_state="NEUTRAL",
                combined_state="UNDEFINED",
            )
        
        try:
            market_state = self.market_state_builder.build_state(symbol)
            return MarketStateInputForInteraction(
                trend_state=market_state.trend_state.value,
                exchange_state=market_state.exchange_state.value,
                combined_state=market_state.combined_state.value,
            )
        except Exception:
            return MarketStateInputForInteraction(
                trend_state="MIXED",
                exchange_state="NEUTRAL",
                combined_state="UNDEFINED",
            )
    
    def _get_ecology_input(self, symbol: str) -> EcologyInputForInteraction:
        """Get Alpha Ecology input."""
        if self.ecology_engine is None:
            return EcologyInputForInteraction(
                ecology_score=0.9,
                ecology_state="STABLE",
            )
        
        try:
            ecology_result = self.ecology_engine.analyze(symbol)
            return EcologyInputForInteraction(
                ecology_score=ecology_result.ecology_score,
                ecology_state=ecology_result.ecology_state.value,
            )
        except Exception:
            return EcologyInputForInteraction(
                ecology_score=0.9,
                ecology_state="STABLE",
            )
    
    # ═══════════════════════════════════════════════════════════
    # REINFORCEMENT CALCULATION
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_reinforcement(
        self,
        ta_input: TAInputForInteraction,
        exchange_input: ExchangeInputForInteraction,
        market_state_input: MarketStateInputForInteraction,
        ecology_input: EcologyInputForInteraction,
    ) -> float:
        """
        Calculate reinforcement score.
        
        Reinforcement occurs when signals align:
        - TA LONG + Exchange LONG → reinforcement
        - TA direction matches trend state → reinforcement
        - Ecology is supportive → reinforcement boost
        """
        # 1. TA-Exchange alignment
        ta_direction = DIRECTION_TO_NUMERIC.get(ta_input.direction, 0.0)
        exchange_direction = DIRECTION_TO_NUMERIC.get(exchange_input.bias, 0.0)
        
        if ta_direction != 0 and exchange_direction != 0:
            # Same direction = reinforcement
            if ta_direction == exchange_direction:
                ta_exchange_alignment = 1.0 * min(ta_input.conviction, exchange_input.confidence)
            else:
                ta_exchange_alignment = 0.0
        else:
            # Neutral signals don't contribute
            ta_exchange_alignment = 0.3 * max(ta_input.conviction, exchange_input.confidence)
        
        # 2. Trend alignment
        trend_direction = TREND_STATE_TO_DIRECTION.get(market_state_input.trend_state, "NEUTRAL")
        trend_numeric = DIRECTION_TO_NUMERIC.get(trend_direction, 0.0)
        
        if ta_direction != 0 and trend_numeric != 0:
            if ta_direction == trend_numeric:
                trend_alignment = 1.0 * ta_input.trend_strength
            else:
                trend_alignment = 0.0
        else:
            trend_alignment = 0.3 * ta_input.trend_strength
        
        # 3. Ecology support
        ecology_support = 0.0
        if ecology_input.ecology_state in ["HEALTHY", "STABLE"]:
            ecology_support = ecology_input.ecology_score
        elif ecology_input.ecology_state == "STRESSED":
            ecology_support = ecology_input.ecology_score * 0.5
        else:  # CRITICAL
            ecology_support = 0.0
        
        # Weighted sum
        reinforcement_score = (
            REINFORCEMENT_WEIGHTS["ta_exchange_alignment"] * ta_exchange_alignment
            + REINFORCEMENT_WEIGHTS["trend_alignment"] * trend_alignment
            + REINFORCEMENT_WEIGHTS["ecology_support"] * ecology_support
        )
        
        return max(0.0, min(1.0, reinforcement_score))
    
    # ═══════════════════════════════════════════════════════════
    # CONFLICT CALCULATION
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_conflict(
        self,
        ta_input: TAInputForInteraction,
        exchange_input: ExchangeInputForInteraction,
        market_state_input: MarketStateInputForInteraction,
    ) -> float:
        """
        Calculate conflict score.
        
        Conflict occurs when signals disagree:
        - TA LONG + Exchange SHORT → conflict
        - TA direction != trend state → conflict
        - Exchange has high conflict_ratio → conflict
        """
        # 1. TA-Exchange conflict
        ta_direction = DIRECTION_TO_NUMERIC.get(ta_input.direction, 0.0)
        exchange_direction = DIRECTION_TO_NUMERIC.get(exchange_input.bias, 0.0)
        
        if ta_direction != 0 and exchange_direction != 0:
            # Opposite direction = conflict
            if ta_direction == -exchange_direction:
                ta_exchange_conflict = 1.0 * max(ta_input.conviction, exchange_input.confidence)
            else:
                ta_exchange_conflict = 0.0
        else:
            ta_exchange_conflict = 0.0
        
        # 2. Exchange internal conflict
        exchange_conflict_component = exchange_input.conflict_ratio
        
        # 3. Hostile market mismatch
        # TA is bullish but market state is bearish (or vice versa)
        trend_direction = TREND_STATE_TO_DIRECTION.get(market_state_input.trend_state, "NEUTRAL")
        trend_numeric = DIRECTION_TO_NUMERIC.get(trend_direction, 0.0)
        
        if ta_direction != 0 and trend_numeric != 0:
            if ta_direction == -trend_numeric:
                hostile_mismatch = 1.0 * (1.0 - ta_input.setup_quality)
            else:
                hostile_mismatch = 0.0
        else:
            hostile_mismatch = 0.0
        
        # Weighted sum
        conflict_score = (
            CONFLICT_WEIGHTS["ta_exchange_conflict"] * ta_exchange_conflict
            + CONFLICT_WEIGHTS["exchange_conflict_ratio"] * exchange_conflict_component
            + CONFLICT_WEIGHTS["hostile_market_mismatch"] * hostile_mismatch
        )
        
        return max(0.0, min(1.0, conflict_score))
    
    # ═══════════════════════════════════════════════════════════
    # STATE DETERMINATION
    # ═══════════════════════════════════════════════════════════
    
    def _determine_state(self, net_score: float) -> InteractionState:
        """
        Determine interaction state from net score.
        
        > 0.20 → REINFORCED
        -0.20 to 0.20 → NEUTRAL
        < -0.20 → CONFLICTED
        """
        if net_score > INTERACTION_THRESHOLDS["reinforced_min"]:
            return InteractionState.REINFORCED
        elif net_score < INTERACTION_THRESHOLDS["conflicted_max"]:
            return InteractionState.CONFLICTED
        else:
            return InteractionState.NEUTRAL
    
    # ═══════════════════════════════════════════════════════════
    # MODIFIER CALCULATION
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_modifier(
        self, 
        state: InteractionState, 
        net_score: float
    ) -> float:
        """
        Calculate confidence modifier based on state and net score.
        
        REINFORCED: 1.05 - 1.15 (stronger reinforcement = higher)
        NEUTRAL: 1.00
        CONFLICTED: 0.75 - 0.90 (stronger conflict = lower)
        """
        modifiers = INTERACTION_MODIFIERS[state]
        mod_min = modifiers["confidence_modifier_min"]
        mod_max = modifiers["confidence_modifier_max"]
        
        if state == InteractionState.REINFORCED:
            # Scale from 1.05 to 1.15 based on how strong the reinforcement is
            # net_score ranges from 0.20 to ~1.0 for REINFORCED
            strength = (net_score - 0.20) / 0.80  # Normalize to 0-1
            strength = max(0.0, min(1.0, strength))
            modifier = mod_min + (mod_max - mod_min) * strength
            
        elif state == InteractionState.CONFLICTED:
            # Scale from 0.90 to 0.75 based on how strong the conflict is
            # net_score ranges from -0.20 to ~-1.0 for CONFLICTED
            strength = (-0.20 - net_score) / 0.80  # Normalize to 0-1
            strength = max(0.0, min(1.0, strength))
            modifier = mod_max - (mod_max - mod_min) * strength
            
        else:  # NEUTRAL
            modifier = 1.0
        
        # Ensure bounds (0.5 minimum as per ecology principle)
        return max(0.5, min(1.15, modifier))
    
    # ═══════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _estimate_exchange_conflict(self, exchange_result) -> float:
        """Estimate exchange internal conflict ratio."""
        try:
            # If funding says bullish but flow says bearish, conflict is high
            funding_bias = 1 if exchange_result.funding_state.value in ["LONG_CROWDED", "EXTREME_LONG"] else (
                -1 if exchange_result.funding_state.value in ["SHORT_CROWDED", "EXTREME_SHORT"] else 0
            )
            
            flow_bias = exchange_result.flow_pressure  # -1 to 1
            
            # If signs differ, conflict
            if funding_bias * flow_bias < 0:
                return abs(funding_bias - flow_bias) / 2
            
            return 0.0
        except Exception:
            return 0.5
    
    def _get_dominant_signal(self, exchange_result) -> str:
        """Get dominant exchange signal."""
        try:
            signals = {
                "funding": abs(exchange_result.crowding_risk),
                "flow": abs(exchange_result.flow_pressure),
                "derivatives": abs(exchange_result.derivatives_pressure),
                "liquidation": exchange_result.liquidation_risk,
            }
            return max(signals, key=signals.get)
        except Exception:
            return "unknown"
    
    def _build_drivers(
        self,
        ta_input: TAInputForInteraction,
        exchange_input: ExchangeInputForInteraction,
        market_state_input: MarketStateInputForInteraction,
        ecology_input: EcologyInputForInteraction,
        reinforcement_score: float,
        conflict_score: float,
    ) -> Dict[str, Any]:
        """Build explainability drivers."""
        return {
            "ta_direction": ta_input.direction,
            "exchange_bias": exchange_input.bias,
            "trend_state": market_state_input.trend_state,
            "ecology_state": ecology_input.ecology_state,
            "alignment": "ALIGNED" if ta_input.direction == exchange_input.bias else (
                "CONFLICTED" if (
                    (ta_input.direction == "LONG" and exchange_input.bias == "BEARISH") or
                    (ta_input.direction == "SHORT" and exchange_input.bias == "BULLISH")
                ) else "NEUTRAL"
            ),
            "dominant_signal": exchange_input.dominant_signal,
            "reinforcement_components": {
                "ta_exchange": round(reinforcement_score * 0.4, 4),
                "trend": round(reinforcement_score * 0.3, 4),
                "ecology": round(reinforcement_score * 0.3, 4),
            },
            "conflict_components": {
                "ta_exchange": round(conflict_score * 0.5, 4),
                "exchange_internal": round(conflict_score * 0.3, 4),
                "market_mismatch": round(conflict_score * 0.2, 4),
            },
        }
    
    def _get_pattern_reinforcement(self, symbol: str) -> Dict[str, Any]:
        """
        Get pattern-based reinforcement from Reinforcement Patterns Engine.
        PHASE 16.2 integration.
        """
        if self.reinforcement_patterns_engine is None:
            return {
                "pattern_reinforcement_strength": 0.0,
                "pattern_modifier": 1.0,
                "patterns_detected": [],
                "pattern_count": 0,
                "dominant_pattern": None,
            }
        
        try:
            return self.reinforcement_patterns_engine.get_pattern_strength_for_interaction(symbol)
        except Exception:
            return {
                "pattern_reinforcement_strength": 0.0,
                "pattern_modifier": 1.0,
                "patterns_detected": [],
                "pattern_count": 0,
                "dominant_pattern": None,
            }
    
    def _get_conflict_patterns(self, symbol: str) -> Dict[str, Any]:
        """
        Get pattern-based conflict from Conflict Patterns Engine.
        PHASE 16.3 integration.
        """
        if self.conflict_patterns_engine is None:
            return {
                "pattern_conflict_strength": 0.0,
                "conflict_modifier": 1.0,
                "conflict_patterns": [],
                "conflict_count": 0,
                "conflict_severity": "LOW_CONFLICT",
                "dominant_conflict": None,
            }
        
        try:
            return self.conflict_patterns_engine.get_conflict_strength_for_interaction(symbol)
        except Exception:
            return {
                "pattern_conflict_strength": 0.0,
                "conflict_modifier": 1.0,
                "conflict_patterns": [],
                "conflict_count": 0,
                "conflict_severity": "LOW_CONFLICT",
                "dominant_conflict": None,
            }
    
    def _get_synergy_patterns(self, symbol: str) -> Dict[str, Any]:
        """
        Get synergy patterns from Synergy Engine.
        PHASE 16.4 integration.
        """
        if self.synergy_engine is None:
            return {
                "synergy_strength": 0.0,
                "synergy_modifier": 1.0,
                "synergy_patterns": [],
                "synergy_count": 0,
                "synergy_potential": "LOW",
                "dominant_synergy": None,
            }
        
        try:
            return self.synergy_engine.get_synergy_strength_for_interaction(symbol)
        except Exception:
            return {
                "synergy_strength": 0.0,
                "synergy_modifier": 1.0,
                "synergy_patterns": [],
                "synergy_count": 0,
                "synergy_potential": "LOW",
                "dominant_synergy": None,
            }
    
    def _get_cancellation_patterns(self, symbol: str) -> Dict[str, Any]:
        """
        Get cancellation patterns from Cancellation Engine.
        PHASE 16.5 integration.
        """
        if self.cancellation_engine is None:
            return {
                "cancellation_strength": 0.0,
                "cancellation_modifier": 1.0,
                "cancellation_patterns": [],
                "cancellation_count": 0,
                "trade_cancelled": False,
                "dominant_cancellation": None,
            }
        
        try:
            return self.cancellation_engine.get_cancellation_for_interaction(symbol)
        except Exception:
            return {
                "cancellation_strength": 0.0,
                "cancellation_modifier": 1.0,
                "cancellation_patterns": [],
                "cancellation_count": 0,
                "trade_cancelled": False,
                "dominant_cancellation": None,
            }
    
    # ═══════════════════════════════════════════════════════════
    # PUBLIC API FOR TRADING PIPELINE
    # ═══════════════════════════════════════════════════════════
    
    def get_modifier_for_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Get interaction modifiers for Trading Product integration.
        """
        result = self.analyze(symbol)
        
        return {
            "interaction_confidence_modifier": result.confidence_modifier,
            "interaction_state": result.interaction_state.value,
            "reinforcement_score": result.reinforcement_score,
            "conflict_score": result.conflict_score,
            "net_interaction_score": result.net_interaction_score,
            "drivers": result.drivers,
        }
    
    def compute_interaction(
        self,
        ta_signal: Dict[str, Any],
        exchange_signal: Dict[str, Any],
        fractal_signal: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compute interaction from provided signals.
        
        This is the simplified API for testing and external integration.
        
        Args:
            ta_signal: {"direction": "LONG"|"SHORT"|"NEUTRAL", "confidence": 0-1, "symbol": str}
            exchange_signal: {"direction": "LONG"|"SHORT"|"NEUTRAL", "confidence": 0-1, "symbol": str}
            fractal_signal: Optional {"direction": "LONG"|"SHORT"|"HOLD", "confidence": 0-1, ...}
        
        Returns:
            {"direction": str, "confidence": float, "interaction_state": str, ...}
        
        Key Principle:
            Direction is determined by TA + Exchange, NOT by fractal.
            Fractal only modifies confidence.
        """
        # Extract directions
        ta_direction = ta_signal.get("direction", "NEUTRAL")
        ta_confidence = ta_signal.get("confidence", 0.5)
        exchange_direction = exchange_signal.get("direction", "NEUTRAL")
        exchange_confidence = exchange_signal.get("confidence", 0.5)
        
        # Map exchange bias for compatibility
        exchange_bias_map = {"LONG": "BULLISH", "SHORT": "BEARISH", "NEUTRAL": "NEUTRAL"}
        exchange_bias = exchange_bias_map.get(exchange_direction, exchange_direction)
        
        # Determine final direction (TA + Exchange vote, NOT fractal)
        ta_numeric = DIRECTION_TO_NUMERIC.get(ta_direction, 0.0)
        exchange_numeric = DIRECTION_TO_NUMERIC.get(exchange_bias, 0.0)
        
        # Weighted vote
        weighted_vote = ta_numeric * ta_confidence + exchange_numeric * exchange_confidence
        
        if weighted_vote > 0.2:
            final_direction = "LONG"
        elif weighted_vote < -0.2:
            final_direction = "SHORT"
        else:
            final_direction = "NEUTRAL"
        
        # Base confidence
        base_confidence = (ta_confidence + exchange_confidence) / 2
        
        # Calculate interaction state (alignment)
        if ta_direction == exchange_direction and ta_direction != "NEUTRAL":
            interaction_state = "REINFORCED"
            confidence_modifier = 1.10
        elif ta_direction != exchange_direction and ta_direction != "NEUTRAL" and exchange_direction != "NEUTRAL":
            interaction_state = "CONFLICTED"
            confidence_modifier = 0.85
        else:
            interaction_state = "NEUTRAL"
            confidence_modifier = 1.0
        
        # Apply fractal modifier (but NOT direction change)
        fractal_modifier = 1.0
        fractal_applied = False
        
        if fractal_signal is not None:
            fractal_direction = fractal_signal.get("direction", "HOLD")
            fractal_confidence = fractal_signal.get("confidence", 0.0)
            fractal_reliability = fractal_signal.get("reliability", 0.0)
            fractal_strength = fractal_confidence * fractal_reliability
            
            if fractal_direction != "HOLD" and fractal_strength > 0.3:
                fractal_applied = True
                
                # Fractal aligns with final direction
                if fractal_direction == final_direction:
                    # Supportive fractal -> small boost (bounded)
                    fractal_modifier = min(1.0 + fractal_strength * 0.10, 1.10)
                elif fractal_direction in ["LONG", "SHORT"] and fractal_direction != final_direction:
                    # Conflicting fractal -> reduce confidence (bounded)
                    fractal_modifier = max(1.0 - fractal_strength * 0.15, 0.85)
                # IMPORTANT: Direction does NOT change
        
        # Final confidence
        final_confidence = base_confidence * confidence_modifier * fractal_modifier
        final_confidence = max(0.3, min(1.0, final_confidence))  # Bounds
        
        return {
            "direction": final_direction,
            "confidence": round(final_confidence, 4),
            "base_confidence": round(base_confidence, 4),
            "interaction_state": interaction_state,
            "confidence_modifier": round(confidence_modifier, 4),
            "fractal_modifier": round(fractal_modifier, 4),
            "fractal_applied": fractal_applied,
            "ta_direction": ta_direction,
            "exchange_direction": exchange_direction,
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[AlphaInteractionEngine] = None


def get_alpha_interaction_engine() -> AlphaInteractionEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = AlphaInteractionEngine()
    return _engine
