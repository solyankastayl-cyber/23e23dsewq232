"""
Regime Transition Detector — Engine

Core logic for detecting regime transitions before they happen.

Features:
- Transition probability calculation
- Next regime candidate prediction
- Trigger factor identification
- Transition state classification (STABLE, EARLY_SHIFT, ACTIVE_TRANSITION, UNSTABLE)
"""

from typing import Optional, List, Dict, Tuple
from datetime import datetime

from .regime_transition_types import (
    RegimeTransitionState,
    TransitionSummary,
    RegimeMetricSnapshot,
    RegimeType,
    NextRegimeCandidate,
    TransitionState,
    STABLE_THRESHOLD,
    EARLY_SHIFT_THRESHOLD,
    ACTIVE_TRANSITION_THRESHOLD,
    WEIGHT_TREND_SHIFT,
    WEIGHT_VOLATILITY_SHIFT,
    WEIGHT_LIQUIDITY_SHIFT,
    WEIGHT_CONFIDENCE_DECAY,
    PROB_WEIGHT_SCORE,
    PROB_WEIGHT_CONFIDENCE,
    TRANSITION_MODIFIERS,
    TREND_SHIFT_THRESHOLD,
    VOLATILITY_SHIFT_THRESHOLD,
    LIQUIDITY_SHIFT_THRESHOLD,
    CONFIDENCE_DECAY_THRESHOLD,
)
from .regime_types import MarketRegime
from .regime_detection_engine import RegimeDetectionEngine, get_regime_detection_engine
from .regime_registry import RegimeRegistry, get_regime_registry


class RegimeTransitionEngine:
    """
    Regime Transition Detection Engine.
    
    Analyzes regime metric changes over time to predict transitions.
    
    Transition Score formula:
    score = 0.35 * trend_shift + 0.35 * volatility_shift + 0.20 * liquidity_shift + 0.10 * confidence_decay
    
    Transition Probability formula:
    prob = 0.70 * transition_score + 0.30 * (1 - regime_confidence)
    """
    
    def __init__(
        self,
        regime_engine: Optional[RegimeDetectionEngine] = None,
        registry: Optional[RegimeRegistry] = None,
    ):
        self._regime_engine = regime_engine or get_regime_detection_engine()
        self._registry = registry or get_regime_registry()
        self._snapshots: List[RegimeMetricSnapshot] = []
        self._current_transition: Optional[RegimeTransitionState] = None
    
    # ═══════════════════════════════════════════════════════════
    # Metric Shifts
    # ═══════════════════════════════════════════════════════════
    
    def calculate_trend_shift(
        self,
        current: float,
        previous: float,
    ) -> float:
        """Calculate trend strength shift."""
        shift = abs(current - previous)
        # Normalize to 0-1 (cap at 0.5 difference)
        return min(shift / 0.5, 1.0)
    
    def calculate_volatility_shift(
        self,
        current: float,
        previous: float,
    ) -> float:
        """Calculate volatility level shift."""
        shift = abs(current - previous)
        return min(shift / 0.5, 1.0)
    
    def calculate_liquidity_shift(
        self,
        current: float,
        previous: float,
    ) -> float:
        """Calculate liquidity level shift."""
        shift = abs(current - previous)
        return min(shift / 0.5, 1.0)
    
    def calculate_confidence_decay(
        self,
        current: float,
        previous: float,
    ) -> float:
        """Calculate confidence decay (only if decreasing)."""
        decay = max(previous - current, 0.0)
        return min(decay / 0.5, 1.0)
    
    # ═══════════════════════════════════════════════════════════
    # Transition Score
    # ═══════════════════════════════════════════════════════════
    
    def calculate_transition_score(
        self,
        current: RegimeMetricSnapshot,
        previous: RegimeMetricSnapshot,
    ) -> float:
        """
        Calculate transition score.
        
        Formula:
        score = 0.35 * trend_shift + 0.35 * volatility_shift + 0.20 * liquidity_shift + 0.10 * confidence_decay
        """
        trend_shift = self.calculate_trend_shift(
            current.trend_strength,
            previous.trend_strength,
        )
        
        volatility_shift = self.calculate_volatility_shift(
            current.volatility_level,
            previous.volatility_level,
        )
        
        liquidity_shift = self.calculate_liquidity_shift(
            current.liquidity_level,
            previous.liquidity_level,
        )
        
        confidence_decay = self.calculate_confidence_decay(
            current.regime_confidence,
            previous.regime_confidence,
        )
        
        score = (
            WEIGHT_TREND_SHIFT * trend_shift +
            WEIGHT_VOLATILITY_SHIFT * volatility_shift +
            WEIGHT_LIQUIDITY_SHIFT * liquidity_shift +
            WEIGHT_CONFIDENCE_DECAY * confidence_decay
        )
        
        return round(min(max(score, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Transition Probability
    # ═══════════════════════════════════════════════════════════
    
    def calculate_transition_probability(
        self,
        transition_score: float,
        regime_confidence: float,
    ) -> float:
        """
        Calculate transition probability.
        
        Formula:
        prob = 0.70 * transition_score + 0.30 * (1 - regime_confidence)
        """
        probability = (
            PROB_WEIGHT_SCORE * transition_score +
            PROB_WEIGHT_CONFIDENCE * (1.0 - regime_confidence)
        )
        
        return round(min(max(probability, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Next Regime Candidate
    # ═══════════════════════════════════════════════════════════
    
    def detect_next_regime_candidate(
        self,
        current: RegimeMetricSnapshot,
        previous: RegimeMetricSnapshot,
    ) -> NextRegimeCandidate:
        """
        Detect next regime candidate based on metric changes.
        
        Transition patterns:
        - TRENDING → RANGING: trend falls, vol low
        - TRENDING → VOLATILE: vol rises sharply
        - RANGING → TRENDING: trend rises
        - RANGING → ILLIQUID: liquidity falls
        - VOLATILE → TRENDING: vol falls, trend rises
        - VOLATILE → ILLIQUID: liquidity falls
        - ILLIQUID → RANGING: liquidity recovers, trend low
        - ILLIQUID → TRENDING: liquidity recovers, trend rises
        """
        current_regime = current.regime_type
        
        trend_delta = current.trend_strength - previous.trend_strength
        vol_delta = current.volatility_level - previous.volatility_level
        liq_delta = current.liquidity_level - previous.liquidity_level
        
        # TRENDING transitions
        if current_regime == "TRENDING":
            if trend_delta < -0.10 and current.volatility_level < 0.35:
                return "RANGING"
            if vol_delta > 0.15:
                return "VOLATILE"
            if liq_delta < -0.20:
                return "ILLIQUID"
        
        # RANGING transitions
        elif current_regime == "RANGING":
            if trend_delta > 0.10:
                return "TRENDING"
            if vol_delta > 0.15:
                return "VOLATILE"
            if liq_delta < -0.20:
                return "ILLIQUID"
        
        # VOLATILE transitions
        elif current_regime == "VOLATILE":
            if vol_delta < -0.15 and trend_delta > 0.05:
                return "TRENDING"
            if vol_delta < -0.10 and current.trend_strength < 0.20:
                return "RANGING"
            if liq_delta < -0.20:
                return "ILLIQUID"
        
        # ILLIQUID transitions
        elif current_regime == "ILLIQUID":
            if liq_delta > 0.15 and current.trend_strength < 0.20:
                return "RANGING"
            if liq_delta > 0.15 and trend_delta > 0.05:
                return "TRENDING"
            if vol_delta > 0.15:
                return "VOLATILE"
        
        return "NONE"
    
    # ═══════════════════════════════════════════════════════════
    # Transition State Classification
    # ═══════════════════════════════════════════════════════════
    
    def classify_transition_state(
        self,
        transition_probability: float,
    ) -> TransitionState:
        """
        Classify transition state based on probability.
        
        Thresholds:
        - STABLE: prob < 0.25
        - EARLY_SHIFT: 0.25 ≤ prob < 0.45
        - ACTIVE_TRANSITION: 0.45 ≤ prob < 0.70
        - UNSTABLE: prob ≥ 0.70
        """
        if transition_probability < STABLE_THRESHOLD:
            return "STABLE"
        elif transition_probability < EARLY_SHIFT_THRESHOLD:
            return "EARLY_SHIFT"
        elif transition_probability < ACTIVE_TRANSITION_THRESHOLD:
            return "ACTIVE_TRANSITION"
        else:
            return "UNSTABLE"
    
    # ═══════════════════════════════════════════════════════════
    # Modifiers
    # ═══════════════════════════════════════════════════════════
    
    def get_modifiers(
        self,
        transition_state: TransitionState,
    ) -> Dict[str, float]:
        """Get confidence and capital modifiers for transition state."""
        return TRANSITION_MODIFIERS.get(transition_state, TRANSITION_MODIFIERS["STABLE"])
    
    # ═══════════════════════════════════════════════════════════
    # Trigger Factors
    # ═══════════════════════════════════════════════════════════
    
    def extract_trigger_factors(
        self,
        current: RegimeMetricSnapshot,
        previous: RegimeMetricSnapshot,
    ) -> List[str]:
        """
        Extract trigger factors causing the transition.
        
        Returns list of active triggers.
        """
        triggers = []
        
        # Trend changes
        trend_delta = current.trend_strength - previous.trend_strength
        if abs(trend_delta) >= TREND_SHIFT_THRESHOLD:
            if trend_delta > 0:
                triggers.append("trend_strength_expansion")
            else:
                triggers.append("trend_strength_decay")
        
        # Volatility changes
        vol_delta = current.volatility_level - previous.volatility_level
        if abs(vol_delta) >= VOLATILITY_SHIFT_THRESHOLD:
            if vol_delta > 0:
                triggers.append("volatility_expansion")
            else:
                triggers.append("volatility_contraction")
        
        # Liquidity changes
        liq_delta = current.liquidity_level - previous.liquidity_level
        if abs(liq_delta) >= LIQUIDITY_SHIFT_THRESHOLD:
            if liq_delta > 0:
                triggers.append("liquidity_recovery")
            else:
                triggers.append("liquidity_drain")
        
        # Confidence decay
        conf_decay = previous.regime_confidence - current.regime_confidence
        if conf_decay >= CONFIDENCE_DECAY_THRESHOLD:
            triggers.append("regime_confidence_drop")
        
        return triggers
    
    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_reason(
        self,
        current_regime: str,
        next_candidate: str,
        transition_state: str,
        triggers: List[str],
    ) -> str:
        """Generate human-readable reason for transition state."""
        regime_lower = current_regime.lower()
        
        if transition_state == "STABLE":
            return f"{regime_lower} regime is stable with no significant transition signals"
        
        trigger_str = " and ".join(t.replace("_", " ") for t in triggers[:2]) if triggers else "metric shifts"
        
        if next_candidate == "NONE":
            return f"{regime_lower} regime showing instability due to {trigger_str}"
        
        next_lower = next_candidate.lower()
        
        if transition_state == "EARLY_SHIFT":
            return f"{regime_lower} regime showing early signs of shift toward {next_lower} as {trigger_str}"
        elif transition_state == "ACTIVE_TRANSITION":
            return f"{regime_lower} regime is destabilizing as {trigger_str}, likely transitioning to {next_lower}"
        else:  # UNSTABLE
            return f"{regime_lower} regime highly unstable with {trigger_str}, imminent shift to {next_lower}"
    
    # ═══════════════════════════════════════════════════════════
    # Main Detection
    # ═══════════════════════════════════════════════════════════
    
    def detect_transition(
        self,
        current: RegimeMetricSnapshot,
        previous: RegimeMetricSnapshot,
        symbol: str = "BTCUSDT",
        timeframe: str = "1H",
    ) -> RegimeTransitionState:
        """
        Detect current transition state.
        
        Requires current and previous regime snapshots.
        """
        # Calculate transition score
        transition_score = self.calculate_transition_score(current, previous)
        
        # Calculate probability
        transition_probability = self.calculate_transition_probability(
            transition_score,
            current.regime_confidence,
        )
        
        # Detect next regime candidate
        next_candidate = self.detect_next_regime_candidate(current, previous)
        
        # Classify state
        transition_state = self.classify_transition_state(transition_probability)
        
        # Get modifiers
        modifiers = self.get_modifiers(transition_state)
        
        # Extract triggers
        triggers = self.extract_trigger_factors(current, previous)
        
        # Generate reason
        reason = self.generate_reason(
            current.regime_type,
            next_candidate,
            transition_state,
            triggers,
        )
        
        result = RegimeTransitionState(
            current_regime=current.regime_type,
            next_regime_candidate=next_candidate,
            transition_probability=transition_probability,
            transition_score=transition_score,
            transition_state=transition_state,
            trigger_factors=triggers,
            confidence_modifier=modifiers["confidence_modifier"],
            capital_modifier=modifiers["capital_modifier"],
            reason=reason,
            symbol=symbol,
            timeframe=timeframe,
        )
        
        self._current_transition = result
        return result
    
    # ═══════════════════════════════════════════════════════════
    # Simulated Detection
    # ═══════════════════════════════════════════════════════════
    
    async def detect_transition_from_history(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "1H",
    ) -> RegimeTransitionState:
        """
        Detect transition using regime history.
        
        Gets last 2 snapshots from history for comparison.
        """
        # Get current regime
        current_regime = self._regime_engine.detect_regime_simulated(symbol, timeframe)
        
        # Create current snapshot
        current_snapshot = RegimeMetricSnapshot(
            regime_type=current_regime.regime_type,
            trend_strength=current_regime.trend_strength,
            volatility_level=current_regime.volatility_level,
            liquidity_level=current_regime.liquidity_level,
            regime_confidence=current_regime.regime_confidence,
            dominant_driver=current_regime.dominant_driver,
        )
        
        # Get previous from history or create simulated
        history = await self._registry.get_history(symbol, timeframe, limit=2)
        
        if history and len(history) >= 1:
            prev = history[0]
            previous_snapshot = RegimeMetricSnapshot(
                regime_type=prev.regime_type,
                trend_strength=prev.trend_strength,
                volatility_level=prev.volatility,
                liquidity_level=prev.liquidity,
                regime_confidence=prev.confidence,
                dominant_driver=prev.dominant_driver,
            )
        else:
            # Create simulated previous (slightly different)
            previous_snapshot = RegimeMetricSnapshot(
                regime_type=current_regime.regime_type,
                trend_strength=current_regime.trend_strength * 0.95,
                volatility_level=current_regime.volatility_level * 0.90,
                liquidity_level=current_regime.liquidity_level * 1.05,
                regime_confidence=current_regime.regime_confidence * 1.05,
                dominant_driver=current_regime.dominant_driver,
            )
        
        # Store snapshot
        self._snapshots.append(current_snapshot)
        if len(self._snapshots) > 10:
            self._snapshots = self._snapshots[-10:]
        
        return self.detect_transition(
            current_snapshot,
            previous_snapshot,
            symbol,
            timeframe,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    @property
    def current_transition(self) -> Optional[RegimeTransitionState]:
        """Get current transition state."""
        return self._current_transition
    
    def get_snapshots(self) -> List[RegimeMetricSnapshot]:
        """Get stored snapshots."""
        return self._snapshots.copy()


# Singleton
_engine: Optional[RegimeTransitionEngine] = None


def get_regime_transition_engine() -> RegimeTransitionEngine:
    """Get singleton instance of RegimeTransitionEngine."""
    global _engine
    if _engine is None:
        _engine = RegimeTransitionEngine()
    return _engine
