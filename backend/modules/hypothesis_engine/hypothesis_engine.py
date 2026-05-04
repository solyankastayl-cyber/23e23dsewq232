"""
Hypothesis Engine — Core Engine

PHASE 29.1 — Hypothesis Contract + Core Engine
PHASE 29.2 — Hypothesis Scoring Engine Integration
PHASE 29.3 — Hypothesis Conflict Resolver Integration

Features:
- Generates hypothesis candidates from intelligence layer signals
- Scores candidates using weighted formula
- Selects best hypothesis
- Computes confidence and reliability
- Maps execution state from microstructure

PHASE 29.2 additions:
- structural_score: idea quality
- execution_score: execution safety
- conflict_score: layer disagreement

PHASE 29.3 additions:
- conflict_state: LOW/MODERATE/HIGH classification
- Automatic confidence/reliability reduction on conflict
- Execution state downgrade on conflict
"""

import math
from typing import Optional, Dict, List
from datetime import datetime

from .hypothesis_types import (
    MarketHypothesis,
    HypothesisCandidate,
    HypothesisInputLayers,
    HypothesisSummary,
    WEIGHT_ALPHA,
    WEIGHT_REGIME,
    WEIGHT_MICROSTRUCTURE,
    WEIGHT_MACRO,
)
from .hypothesis_scoring_engine import (
    HypothesisScoringEngine,
    get_hypothesis_scoring_engine,
)
from .hypothesis_conflict_resolver import (
    HypothesisConflictResolver,
    get_hypothesis_conflict_resolver,
    ConflictState,
)


class HypothesisEngine:
    """
    Hypothesis Engine.

    Collects signals from intelligence layers, generates candidates,
    scores them, and selects the best market hypothesis.
    """

    def __init__(self):
        self._current_hypotheses: Dict[str, MarketHypothesis] = {}
        self._history: Dict[str, list] = {}

    # ═══════════════════════════════════════════════════════════
    # Candidate Generation
    # ═══════════════════════════════════════════════════════════

    def _generate_bullish_continuation(
        self, layers: HypothesisInputLayers,
    ) -> Optional[HypothesisCandidate]:
        """
        BULLISH_CONTINUATION

        Conditions:
        - alpha direction = BULLISH
        - regime = TRENDING
        - microstructure != STRESSED
        """
        if layers.alpha_direction != "BULLISH":
            return None
        if layers.regime_type != "TRENDING":
            return None
        if layers.microstructure_state == "STRESSED":
            return None

        return HypothesisCandidate(
            hypothesis_type="BULLISH_CONTINUATION",
            alpha_support=layers.alpha_strength,
            regime_support=layers.regime_confidence,
            microstructure_support=layers.microstructure_confidence,
            macro_support=layers.macro_confidence,
            directional_bias="LONG",
        )

    def _generate_bearish_continuation(
        self, layers: HypothesisInputLayers,
    ) -> Optional[HypothesisCandidate]:
        """
        BEARISH_CONTINUATION

        Conditions:
        - alpha direction = BEARISH
        - regime = TRENDING
        - microstructure != SUPPORTIVE
        """
        if layers.alpha_direction != "BEARISH":
            return None
        if layers.regime_type != "TRENDING":
            return None
        if layers.microstructure_state == "SUPPORTIVE":
            return None

        return HypothesisCandidate(
            hypothesis_type="BEARISH_CONTINUATION",
            alpha_support=layers.alpha_strength,
            regime_support=layers.regime_confidence,
            microstructure_support=layers.microstructure_confidence,
            macro_support=layers.macro_confidence,
            directional_bias="SHORT",
        )

    def _generate_breakout_forming(
        self, layers: HypothesisInputLayers,
    ) -> Optional[HypothesisCandidate]:
        """
        BREAKOUT_FORMING

        Conditions:
        - alpha breakout factors strong (>= 0.5)
        - regime = TRENDING or in transition
        - vacuum_direction aligned
        - pressure directional
        """
        if layers.alpha_breakout_strength < 0.5:
            return None
        if layers.regime_type not in ("TRENDING",) and not layers.regime_in_transition:
            return None
        if not layers.pressure_directional:
            return None

        # Determine bias from pressure/vacuum direction
        if layers.pressure_direction == "UP" or layers.vacuum_direction == "UP":
            bias = "LONG"
        elif layers.pressure_direction == "DOWN" or layers.vacuum_direction == "DOWN":
            bias = "SHORT"
        else:
            bias = "LONG"  # default if directional but no clear direction

        return HypothesisCandidate(
            hypothesis_type="BREAKOUT_FORMING",
            alpha_support=layers.alpha_breakout_strength,
            regime_support=layers.regime_confidence,
            microstructure_support=layers.microstructure_confidence,
            macro_support=layers.macro_confidence,
            directional_bias=bias,
        )

    def _generate_range_mean_reversion(
        self, layers: HypothesisInputLayers,
    ) -> Optional[HypothesisCandidate]:
        """
        RANGE_MEAN_REVERSION

        Conditions:
        - regime = RANGING
        - alpha mean_reversion factors active (>= 0.4)
        - microstructure balanced (NEUTRAL or SUPPORTIVE)
        """
        if layers.regime_type != "RANGING":
            return None
        if layers.alpha_mean_reversion_strength < 0.4:
            return None
        if layers.microstructure_state not in ("NEUTRAL", "SUPPORTIVE"):
            return None

        # Bias depends on alpha direction
        if layers.alpha_direction == "BULLISH":
            bias = "LONG"
        elif layers.alpha_direction == "BEARISH":
            bias = "SHORT"
        else:
            bias = "NEUTRAL"

        return HypothesisCandidate(
            hypothesis_type="RANGE_MEAN_REVERSION",
            alpha_support=layers.alpha_mean_reversion_strength,
            regime_support=layers.regime_confidence,
            microstructure_support=layers.microstructure_confidence,
            macro_support=layers.macro_confidence,
            directional_bias=bias,
        )

    def _generate_no_edge(
        self, layers: HypothesisInputLayers,
    ) -> HypothesisCandidate:
        """
        NO_EDGE — Fallback.

        Always generated. Represents the absence of a clear edge.
        Low support values when alpha weak / regime uncertain / micro stressed.
        """
        # NO_EDGE gets reduced support scores
        alpha_support = max(0.0, 1.0 - layers.alpha_strength) * 0.3
        regime_support = max(0.0, 1.0 - layers.regime_confidence) * 0.3
        micro_support = max(0.0, 1.0 - layers.microstructure_confidence) * 0.3
        macro_support = max(0.0, 1.0 - layers.macro_confidence) * 0.3

        return HypothesisCandidate(
            hypothesis_type="NO_EDGE",
            alpha_support=round(alpha_support, 4),
            regime_support=round(regime_support, 4),
            microstructure_support=round(micro_support, 4),
            macro_support=round(macro_support, 4),
            directional_bias="NEUTRAL",
        )

    # ═══════════════════════════════════════════════════════════
    # Scoring
    # ═══════════════════════════════════════════════════════════

    def calculate_raw_score(self, candidate: HypothesisCandidate) -> float:
        """
        Calculate raw score for a candidate.

        Formula:
        raw_score = 0.40 * alpha + 0.30 * regime + 0.20 * micro + 0.10 * macro
        """
        score = (
            WEIGHT_ALPHA * candidate.alpha_support
            + WEIGHT_REGIME * candidate.regime_support
            + WEIGHT_MICROSTRUCTURE * candidate.microstructure_support
            + WEIGHT_MACRO * candidate.macro_support
        )
        return round(score, 4)

    def calculate_confidence(self, raw_score: float) -> float:
        """
        Confidence = raw_score, clipped to [0, 1].
        """
        return round(min(max(raw_score, 0.0), 1.0), 4)

    def calculate_reliability(self, candidate: HypothesisCandidate) -> float:
        """
        Reliability depends on layer agreement.

        reliability = 1 - std(alpha_support, regime_support, microstructure_support)
        Clipped to [0, 1].
        """
        values = [
            candidate.alpha_support,
            candidate.regime_support,
            candidate.microstructure_support,
        ]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance)

        reliability = 1.0 - std
        return round(min(max(reliability, 0.0), 1.0), 4)

    # ═══════════════════════════════════════════════════════════
    # Execution State
    # ═══════════════════════════════════════════════════════════

    def map_execution_state(self, microstructure_state: str) -> str:
        """
        Map microstructure state to execution state.

        SUPPORTIVE → FAVORABLE
        NEUTRAL → CAUTIOUS
        FRAGILE / STRESSED → UNFAVORABLE
        """
        if microstructure_state == "SUPPORTIVE":
            return "FAVORABLE"
        elif microstructure_state == "NEUTRAL":
            return "CAUTIOUS"
        else:
            return "UNFAVORABLE"

    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════

    def generate_reason(
        self,
        hypothesis_type: str,
        layers: HypothesisInputLayers,
    ) -> str:
        """Generate human-readable reason for the hypothesis."""

        if hypothesis_type == "BULLISH_CONTINUATION":
            return "alpha momentum factors align with trending regime and stable microstructure"

        elif hypothesis_type == "BEARISH_CONTINUATION":
            return "bearish alpha factors align with trending regime and deteriorating microstructure"

        elif hypothesis_type == "BREAKOUT_FORMING":
            return "breakout factors align with directional pressure and vacuum formation"

        elif hypothesis_type == "RANGE_MEAN_REVERSION":
            return "ranging regime with mean reversion alpha factors and balanced orderbook"

        elif hypothesis_type == "NO_EDGE":
            parts = []
            if layers.alpha_strength < 0.4:
                parts.append("weak alpha signal")
            if layers.regime_confidence < 0.4:
                parts.append("uncertain regime")
            if layers.microstructure_state in ("FRAGILE", "STRESSED"):
                parts.append("stressed microstructure")
            if not parts:
                parts.append("no clear directional edge detected")
            return "no actionable edge: " + ", ".join(parts)

        return f"{hypothesis_type.lower().replace('_', ' ')} detected from intelligence layers"

    # ═══════════════════════════════════════════════════════════
    # Main Generation
    # ═══════════════════════════════════════════════════════════

    def generate_candidates(
        self, layers: HypothesisInputLayers,
    ) -> List[HypothesisCandidate]:
        """
        Generate all applicable hypothesis candidates from input layers.

        Always includes NO_EDGE as fallback.
        """
        candidates = []

        # Try each hypothesis generator
        bullish = self._generate_bullish_continuation(layers)
        if bullish:
            candidates.append(bullish)

        bearish = self._generate_bearish_continuation(layers)
        if bearish:
            candidates.append(bearish)

        breakout = self._generate_breakout_forming(layers)
        if breakout:
            candidates.append(breakout)

        mean_rev = self._generate_range_mean_reversion(layers)
        if mean_rev:
            candidates.append(mean_rev)

        # Always add NO_EDGE as fallback
        no_edge = self._generate_no_edge(layers)
        candidates.append(no_edge)

        return candidates

    def select_best_candidate(
        self, candidates: List[HypothesisCandidate],
    ) -> HypothesisCandidate:
        """
        Select the candidate with the highest raw_score.
        """
        best = None
        best_score = -1.0

        for candidate in candidates:
            score = self.calculate_raw_score(candidate)
            if score > best_score:
                best_score = score
                best = candidate

        return best

    def generate_hypothesis(
        self,
        symbol: str,
        layers: HypothesisInputLayers,
        execution_confidence_modifier: float = 1.0,
        transition_state: str = "STABLE",
    ) -> MarketHypothesis:
        """
        Generate the best market hypothesis for a symbol.

        Steps:
        1. Generate candidates
        2. Score each candidate
        3. Select best
        4. Compute confidence / reliability using scoring engine
        5. Apply conflict resolver (PHASE 29.3)
        6. Map execution state
        7. Build MarketHypothesis
        
        PHASE 29.2: Uses HypothesisScoringEngine for:
        - structural_score
        - execution_score
        - conflict_score
        - confidence (derived)
        - reliability (derived)
        - execution_state (derived from execution_score)
        
        PHASE 29.3: Uses HypothesisConflictResolver for:
        - conflict_state classification
        - confidence adjustment on conflict
        - reliability adjustment on conflict
        - execution_state downgrade on conflict
        """
        # Generate candidates
        candidates = self.generate_candidates(layers)

        # Select best
        best = self.select_best_candidate(candidates)

        # PHASE 29.2: Use scoring engine
        # PHASE 34: Now includes regime_memory_score
        scoring_engine = get_hypothesis_scoring_engine()
        scores = scoring_engine.score_hypothesis(
            candidate=best,
            layers=layers,
            execution_confidence_modifier=execution_confidence_modifier,
            transition_state=transition_state,
            symbol=symbol,
        )

        # Generate base reason
        base_reason = scoring_engine.generate_enhanced_reason(
            hypothesis_type=best.hypothesis_type,
            scores=scores,
            layers=layers,
        )

        # PHASE 29.3: Apply conflict resolver
        conflict_resolver = get_hypothesis_conflict_resolver()
        resolution = conflict_resolver.resolve(
            conflict_score=scores["conflict_score"],
            confidence=scores["confidence"],
            reliability=scores["reliability"],
            execution_state=scores["execution_state"],
            alpha_support=best.alpha_support,
            regime_support=best.regime_support,
            microstructure_support=best.microstructure_support,
            hypothesis_type=best.hypothesis_type,
        )

        # Combine reason with conflict suffix
        if resolution.reason_suffix:
            final_reason = f"{base_reason} — {resolution.reason_suffix}"
        else:
            final_reason = base_reason

        hypothesis = MarketHypothesis(
            symbol=symbol,
            hypothesis_type=best.hypothesis_type,
            directional_bias=best.directional_bias,
            # PHASE 29.2 scoring
            structural_score=scores["structural_score"],
            execution_score=scores["execution_score"],
            conflict_score=scores["conflict_score"],
            # PHASE 29.3 conflict state
            conflict_state=resolution.conflict_state.value,
            # Adjusted by conflict resolver
            confidence=resolution.adjusted_confidence,
            reliability=resolution.adjusted_reliability,
            # Layer support
            alpha_support=best.alpha_support,
            regime_support=best.regime_support,
            microstructure_support=best.microstructure_support,
            macro_fractal_support=best.macro_support,
            # Execution state adjusted by conflict resolver
            execution_state=resolution.adjusted_execution_state,
            reason=final_reason,
        )

        # Cache
        self._current_hypotheses[symbol] = hypothesis
        if symbol not in self._history:
            self._history[symbol] = []
        self._history[symbol].append(hypothesis)

        return hypothesis

    # ═══════════════════════════════════════════════════════════
    # Simulated Build
    # ═══════════════════════════════════════════════════════════

    def generate_hypothesis_simulated(
        self,
        symbol: str = "BTC",
    ) -> MarketHypothesis:
        """
        Generate hypothesis using simulated data from intelligence layers.

        Pulls from existing engines where available, otherwise uses
        sensible defaults that represent a typical market state.
        
        PHASE 29.2: Also fetches execution context modifier and
        regime transition state for scoring.
        """
        # Try to get data from MicrostructureContext
        micro_state = "NEUTRAL"
        micro_confidence = 0.5
        execution_confidence_modifier = 1.0

        try:
            from modules.microstructure_intelligence_v2 import (
                get_microstructure_context_engine,
            )
            ctx_engine = get_microstructure_context_engine()
            ctx = ctx_engine.get_context(symbol)
            if not ctx:
                ctx = ctx_engine.build_context_simulated(symbol)
            micro_state = ctx.microstructure_state
            # Normalize confidence_modifier to [0,1] range
            micro_confidence = round(
                min(max((ctx.confidence_modifier - 0.82) / (1.12 - 0.82), 0.0), 1.0), 4
            )
            # PHASE 29.2: Get raw confidence modifier for scoring engine
            execution_confidence_modifier = ctx.confidence_modifier
            vacuum_dir = ctx.vacuum_direction
            pressure_dir = "NONE"
            pressure_directional = ctx.pressure_bias != "BALANCED"
            if ctx.pressure_bias == "BID_DOMINANT":
                pressure_dir = "UP"
            elif ctx.pressure_bias == "ASK_DOMINANT":
                pressure_dir = "DOWN"
        except Exception:
            vacuum_dir = "NONE"
            pressure_dir = "NONE"
            pressure_directional = False

        # Try to get data from RegimeContext
        regime_type = "TRENDING"
        regime_confidence = 0.6
        regime_in_transition = False
        transition_state = "STABLE"

        try:
            from modules.regime_intelligence_v2 import (
                get_regime_context_engine,
            )
            regime_engine = get_regime_context_engine()
            regime_ctx = regime_engine.get_context(symbol)
            if regime_ctx:
                regime_type = regime_ctx.regime_type
                regime_confidence = regime_ctx.confidence
                regime_in_transition = regime_ctx.in_transition
        except Exception:
            pass

        # PHASE 29.2: Try to get regime transition state
        try:
            from modules.regime_intelligence_v2 import (
                get_regime_transition_engine,
            )
            transition_engine = get_regime_transition_engine()
            transition = transition_engine.get_transition_state(symbol)
            if transition:
                transition_state = transition.transition_state
        except Exception:
            pass

        # Simulated alpha data
        alpha_direction = "BULLISH"
        alpha_strength = 0.65
        alpha_breakout = 0.45
        alpha_mean_rev = 0.30

        # Simulated macro data
        macro_confidence = 0.55

        layers = HypothesisInputLayers(
            alpha_direction=alpha_direction,
            alpha_strength=alpha_strength,
            alpha_breakout_strength=alpha_breakout,
            alpha_mean_reversion_strength=alpha_mean_rev,
            regime_type=regime_type,
            regime_confidence=regime_confidence,
            regime_in_transition=regime_in_transition,
            microstructure_state=micro_state,
            microstructure_confidence=micro_confidence,
            vacuum_direction=vacuum_dir,
            pressure_directional=pressure_directional,
            pressure_direction=pressure_dir,
            macro_confidence=macro_confidence,
        )

        return self.generate_hypothesis(
            symbol,
            layers,
            execution_confidence_modifier=execution_confidence_modifier,
            transition_state=transition_state,
        )

    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════

    def get_summary(self, symbol: str) -> HypothesisSummary:
        """Get summary of hypothesis history for symbol."""
        history = self._history.get(symbol, [])

        if not history:
            return HypothesisSummary(
                symbol=symbol,
                total_records=0,
            )

        # Type counts
        type_map = {
            "BULLISH_CONTINUATION": 0,
            "BEARISH_CONTINUATION": 0,
            "BREAKOUT_FORMING": 0,
            "RANGE_MEAN_REVERSION": 0,
            "NO_EDGE": 0,
        }
        other_count = 0
        for h in history:
            if h.hypothesis_type in type_map:
                type_map[h.hypothesis_type] += 1
            else:
                other_count += 1

        # Bias counts
        long_c = len([h for h in history if h.directional_bias == "LONG"])
        short_c = len([h for h in history if h.directional_bias == "SHORT"])
        neutral_c = len([h for h in history if h.directional_bias == "NEUTRAL"])

        # Execution state counts
        favorable_c = len([h for h in history if h.execution_state == "FAVORABLE"])
        cautious_c = len([h for h in history if h.execution_state == "CAUTIOUS"])
        unfavorable_c = len([h for h in history if h.execution_state == "UNFAVORABLE"])

        # Averages
        avg_conf = sum(h.confidence for h in history) / len(history)
        avg_rel = sum(h.reliability for h in history) / len(history)

        latest = history[-1]

        return HypothesisSummary(
            symbol=symbol,
            total_records=len(history),
            bullish_continuation_count=type_map["BULLISH_CONTINUATION"],
            bearish_continuation_count=type_map["BEARISH_CONTINUATION"],
            breakout_forming_count=type_map["BREAKOUT_FORMING"],
            range_mean_reversion_count=type_map["RANGE_MEAN_REVERSION"],
            no_edge_count=type_map["NO_EDGE"],
            other_count=other_count,
            long_count=long_c,
            short_count=short_c,
            neutral_count=neutral_c,
            favorable_count=favorable_c,
            cautious_count=cautious_c,
            unfavorable_count=unfavorable_c,
            average_confidence=round(avg_conf, 4),
            average_reliability=round(avg_rel, 4),
            current_hypothesis=latest.hypothesis_type,
            current_bias=latest.directional_bias,
        )

    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════

    def get_hypothesis(self, symbol: str) -> Optional[MarketHypothesis]:
        """Get cached hypothesis for symbol."""
        return self._current_hypotheses.get(symbol)

    def get_all_hypotheses(self) -> Dict[str, MarketHypothesis]:
        """Get all cached hypotheses."""
        return self._current_hypotheses.copy()


# Singleton
_engine: Optional[HypothesisEngine] = None


def get_hypothesis_engine() -> HypothesisEngine:
    """Get singleton instance of HypothesisEngine."""
    global _engine
    if _engine is None:
        _engine = HypothesisEngine()
    return _engine
