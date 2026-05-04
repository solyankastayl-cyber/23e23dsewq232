"""
Fractal Market Intelligence Engine

PHASE 32.1 — Fractal Market Intelligence Engine

Determines structural market state across multiple timeframes
to identify fractal alignment and provide context modifiers.

Key features:
- Multi-timeframe state classification (5m, 15m, 1h, 4h, 1d)
- Fractal alignment calculation
- Bias determination (LONG/SHORT/NEUTRAL)
- Confidence scoring
- Integration with Hypothesis Engine via modifier

This is the 5th level of intelligence (Fractal Intelligence).
"""

from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone
from collections import Counter

from .fractal_types import (
    FractalMarketState,
    FractalSummary,
    TimeframeAnalysis,
    FractalModifier,
    TimeframeState,
    FractalBias,
    TIMEFRAMES,
    ALIGNMENT_BIAS_THRESHOLD,
    ALIGNMENT_NEUTRAL_THRESHOLD,
    ALIGNMENT_WEIGHT,
    VOLATILITY_CONSISTENCY_WEIGHT,
    FRACTAL_ALIGNED_MODIFIER,
    FRACTAL_CONFLICT_MODIFIER,
)


# ══════════════════════════════════════════════════════════════
# Fractal Market Intelligence Engine
# ══════════════════════════════════════════════════════════════

class FractalEngine:
    """
    Fractal Market Intelligence Engine — PHASE 32.1
    
    Analyzes market structure across multiple timeframes to determine
    fractal alignment and provide context for hypothesis scoring.
    
    Pipeline:
    1. Classify each timeframe state (TREND_UP/DOWN, RANGE, VOLATILE)
    2. Calculate alignment across timeframes
    3. Determine fractal bias
    4. Calculate confidence
    5. Provide modifier for hypothesis scoring
    """
    
    def __init__(self):
        self._states: Dict[str, List[FractalMarketState]] = {}
        self._current: Dict[str, FractalMarketState] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Timeframe State Classification
    # ═══════════════════════════════════════════════════════════
    
    def classify_timeframe_state(
        self,
        ema_slope: float,
        atr_expansion: float,
        structure_break: bool,
    ) -> Tuple[TimeframeState, float]:
        """
        Classify timeframe state based on indicators.
        
        - TREND_UP: Positive EMA slope, low-moderate ATR
        - TREND_DOWN: Negative EMA slope, low-moderate ATR
        - VOLATILE: High ATR expansion (>1.5)
        - RANGE: Low ATR, flat EMA slope
        
        Returns: (state, confidence)
        """
        # Volatile check first
        if atr_expansion > 1.5:
            return "VOLATILE", min(0.5 + atr_expansion * 0.2, 0.9)
        
        # Trend detection
        if abs(ema_slope) > 0.02:  # Significant slope
            if ema_slope > 0:
                confidence = min(0.5 + abs(ema_slope) * 10, 0.95)
                return "TREND_UP", confidence
            else:
                confidence = min(0.5 + abs(ema_slope) * 10, 0.95)
                return "TREND_DOWN", confidence
        
        # Range if no trend and low volatility
        if atr_expansion < 0.8 and abs(ema_slope) < 0.01:
            return "RANGE", 0.6 + (1 - atr_expansion) * 0.3
        
        # Default to range with lower confidence
        return "RANGE", 0.5
    
    def analyze_timeframe(
        self,
        timeframe: str,
        ema_slope: float = 0.0,
        atr_expansion: float = 1.0,
        structure_break: bool = False,
    ) -> TimeframeAnalysis:
        """
        Analyze a single timeframe.
        """
        state, confidence = self.classify_timeframe_state(
            ema_slope, atr_expansion, structure_break
        )
        
        # Boost confidence if structure break confirms trend
        if structure_break and state in ["TREND_UP", "TREND_DOWN"]:
            confidence = min(confidence + 0.1, 1.0)
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            state=state,
            ema_slope=ema_slope,
            atr_expansion=atr_expansion,
            structure_break=structure_break,
            confidence=round(confidence, 4),
        )
    
    # ═══════════════════════════════════════════════════════════
    # 2. Fractal Alignment Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_alignment(
        self,
        tf_states: Dict[str, TimeframeState],
    ) -> Tuple[float, str]:
        """
        Calculate fractal alignment across timeframes.
        
        Formula: alignment = matching_trend_frames / total_frames
        
        Returns: (alignment, dominant_direction)
        """
        if not tf_states:
            return 0.0, "NEUTRAL"
        
        # Count directional states
        up_count = sum(1 for s in tf_states.values() if s == "TREND_UP")
        down_count = sum(1 for s in tf_states.values() if s == "TREND_DOWN")
        total = len(tf_states)
        
        # Calculate alignment with dominant direction
        if up_count >= down_count:
            dominant_count = up_count
            dominant = "TREND_UP"
        else:
            dominant_count = down_count
            dominant = "TREND_DOWN"
        
        # Include RANGE as partial alignment if no trend dominates
        if dominant_count < total * 0.4:
            # No clear trend dominance
            return 0.2, "NEUTRAL"
        
        alignment = dominant_count / total
        return round(alignment, 4), dominant
    
    # ═══════════════════════════════════════════════════════════
    # 3. Fractal Bias Determination
    # ═══════════════════════════════════════════════════════════
    
    def determine_bias(
        self,
        alignment: float,
        dominant_direction: str,
    ) -> FractalBias:
        """
        Determine fractal bias based on alignment.
        
        alignment >= 0.6 → bias = dominant trend
        alignment < 0.4 → bias = NEUTRAL
        """
        if alignment >= ALIGNMENT_BIAS_THRESHOLD:
            if dominant_direction == "TREND_UP":
                return "LONG"
            elif dominant_direction == "TREND_DOWN":
                return "SHORT"
        
        if alignment < ALIGNMENT_NEUTRAL_THRESHOLD:
            return "NEUTRAL"
        
        # Between 0.4 and 0.6 - return weak directional bias
        if dominant_direction == "TREND_UP":
            return "LONG"
        elif dominant_direction == "TREND_DOWN":
            return "SHORT"
        
        return "NEUTRAL"
    
    # ═══════════════════════════════════════════════════════════
    # 4. Volatility Consistency
    # ═══════════════════════════════════════════════════════════
    
    def calculate_volatility_consistency(
        self,
        tf_states: Dict[str, TimeframeState],
    ) -> float:
        """
        Calculate volatility consistency across timeframes.
        
        High consistency = similar volatility regimes
        Low consistency = mixed volatility regimes
        """
        if not tf_states:
            return 0.5
        
        volatile_count = sum(1 for s in tf_states.values() if s == "VOLATILE")
        total = len(tf_states)
        
        # Consistency is highest when all frames agree (either all volatile or none)
        volatile_ratio = volatile_count / total
        
        # Consistency peaks at 0 or 1, lowest at 0.5
        consistency = 1.0 - 2 * abs(volatile_ratio - 0.5) if volatile_ratio <= 0.5 else 1.0 - 2 * abs(volatile_ratio - 0.5)
        consistency = abs(1.0 - 2 * min(volatile_ratio, 1 - volatile_ratio))
        
        return round(max(0.3, consistency), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 5. Fractal Confidence Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_confidence(
        self,
        alignment: float,
        volatility_consistency: float,
    ) -> float:
        """
        Calculate fractal confidence.
        
        Formula:
        confidence = 0.60 × alignment + 0.40 × volatility_consistency
        
        Bounded: 0 ≤ confidence ≤ 1
        """
        confidence = (
            ALIGNMENT_WEIGHT * alignment
            + VOLATILITY_CONSISTENCY_WEIGHT * volatility_consistency
        )
        
        return round(max(0.0, min(1.0, confidence)), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 6. Generate Fractal State
    # ═══════════════════════════════════════════════════════════
    
    def generate_fractal_state(
        self,
        symbol: str,
        tf_data: Optional[Dict[str, Dict]] = None,
    ) -> FractalMarketState:
        """
        Generate fractal market state for symbol.
        
        If tf_data not provided, generates mock data for testing.
        """
        symbol = symbol.upper()
        
        if tf_data is None:
            tf_data = self._generate_mock_tf_data(symbol)
        
        # Analyze each timeframe
        tf_analyses = {}
        tf_states = {}
        
        for tf in TIMEFRAMES:
            data = tf_data.get(tf, {})
            analysis = self.analyze_timeframe(
                tf,
                ema_slope=data.get("ema_slope", 0.0),
                atr_expansion=data.get("atr_expansion", 1.0),
                structure_break=data.get("structure_break", False),
            )
            tf_analyses[tf] = analysis
            tf_states[tf] = analysis.state
        
        # Calculate alignment
        alignment, dominant = self.calculate_alignment(tf_states)
        
        # Determine bias
        bias = self.determine_bias(alignment, dominant)
        
        # Calculate volatility consistency
        vol_consistency = self.calculate_volatility_consistency(tf_states)
        
        # Calculate confidence
        confidence = self.calculate_confidence(alignment, vol_consistency)
        
        # Build state
        state = FractalMarketState(
            symbol=symbol,
            tf_5m_state=tf_states.get("5m", "RANGE"),
            tf_15m_state=tf_states.get("15m", "RANGE"),
            tf_1h_state=tf_states.get("1h", "RANGE"),
            tf_4h_state=tf_states.get("4h", "RANGE"),
            tf_1d_state=tf_states.get("1d", "RANGE"),
            fractal_alignment=alignment,
            fractal_bias=bias,
            fractal_confidence=confidence,
            volatility_consistency=vol_consistency,
            tf_states=tf_states,
        )
        
        # Store
        self._store_state(symbol, state)
        
        return state
    
    def _generate_mock_tf_data(self, symbol: str) -> Dict[str, Dict]:
        """Generate mock timeframe data for testing."""
        import hashlib
        
        # Generate pseudo-random but deterministic data based on symbol
        seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
        
        mock_data = {}
        slopes = [0.03, 0.025, 0.02, 0.01, 0.005]  # Generally bullish
        
        for i, tf in enumerate(TIMEFRAMES):
            # Create realistic-looking data
            slope_base = slopes[i] * (1 if (seed + i) % 3 != 0 else -1)
            
            mock_data[tf] = {
                "ema_slope": slope_base * (1 + (seed % 10) / 20),
                "atr_expansion": 0.8 + (((seed + i) % 10) / 10),
                "structure_break": ((seed + i) % 4) == 0,
            }
        
        return mock_data
    
    # ═══════════════════════════════════════════════════════════
    # 7. Fractal Modifier for Hypothesis
    # ═══════════════════════════════════════════════════════════
    
    def get_fractal_modifier(
        self,
        symbol: str,
        hypothesis_bias: str,
    ) -> FractalModifier:
        """
        Get fractal modifier for hypothesis scoring.
        
        If fractal_bias matches hypothesis: modifier = 1.08
        If conflict: modifier = 0.92
        """
        symbol = symbol.upper()
        
        state = self._current.get(symbol)
        if state is None:
            state = self.generate_fractal_state(symbol)
        
        # Determine alignment
        h_bias_normalized = hypothesis_bias.upper()
        if h_bias_normalized in ["LONG", "BULLISH", "TREND_UP", "UP"]:
            h_bias_normalized = "LONG"
        elif h_bias_normalized in ["SHORT", "BEARISH", "TREND_DOWN", "DOWN"]:
            h_bias_normalized = "SHORT"
        else:
            h_bias_normalized = "NEUTRAL"
        
        is_aligned = (
            (state.fractal_bias == "LONG" and h_bias_normalized == "LONG")
            or (state.fractal_bias == "SHORT" and h_bias_normalized == "SHORT")
            or state.fractal_bias == "NEUTRAL"
        )
        
        if is_aligned:
            modifier = FRACTAL_ALIGNED_MODIFIER if state.fractal_bias != "NEUTRAL" else 1.0
            reason = f"Fractal aligned: {state.fractal_bias}"
        else:
            modifier = FRACTAL_CONFLICT_MODIFIER
            reason = f"Fractal conflict: hypothesis={h_bias_normalized}, fractal={state.fractal_bias}"
        
        return FractalModifier(
            hypothesis_bias=hypothesis_bias,
            fractal_bias=state.fractal_bias,
            alignment=state.fractal_alignment,
            is_aligned=is_aligned,
            modifier=modifier,
            reason=reason,
        )
    
    # ═══════════════════════════════════════════════════════════
    # 8. Storage
    # ═══════════════════════════════════════════════════════════
    
    def _store_state(self, symbol: str, state: FractalMarketState) -> None:
        """Store state in memory."""
        if symbol not in self._states:
            self._states[symbol] = []
        self._states[symbol].append(state)
        self._current[symbol] = state
    
    def get_current_state(self, symbol: str) -> Optional[FractalMarketState]:
        """Get current fractal state."""
        return self._current.get(symbol.upper())
    
    def get_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[FractalMarketState]:
        """Get state history."""
        history = self._states.get(symbol.upper(), [])
        return sorted(history, key=lambda s: s.created_at, reverse=True)[:limit]
    
    # ═══════════════════════════════════════════════════════════
    # 9. Summary
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, symbol: str) -> FractalSummary:
        """Get fractal summary for symbol."""
        symbol = symbol.upper()
        history = self._states.get(symbol, [])
        current = self._current.get(symbol)
        
        if not history or not current:
            return FractalSummary(symbol=symbol)
        
        # Current state distribution
        current_states = current.get_all_states()
        state_counts = Counter(current_states.values())
        
        # Historical averages
        avg_alignment = sum(s.fractal_alignment for s in history) / len(history)
        avg_confidence = sum(s.fractal_confidence for s in history) / len(history)
        
        # Find highest alignment
        highest = max(history, key=lambda s: s.fractal_alignment)
        
        # Calculate alignment streak
        streak = 0
        for s in sorted(history, key=lambda x: x.created_at, reverse=True):
            if s.fractal_alignment >= ALIGNMENT_BIAS_THRESHOLD:
                streak += 1
            else:
                break
        
        return FractalSummary(
            symbol=symbol,
            current_alignment=current.fractal_alignment,
            current_bias=current.fractal_bias,
            current_confidence=current.fractal_confidence,
            trend_up_count=state_counts.get("TREND_UP", 0),
            trend_down_count=state_counts.get("TREND_DOWN", 0),
            range_count=state_counts.get("RANGE", 0),
            volatile_count=state_counts.get("VOLATILE", 0),
            avg_alignment=round(avg_alignment, 4),
            avg_confidence=round(avg_confidence, 4),
            alignment_streak=streak,
            highest_alignment=highest.fractal_alignment,
            total_snapshots=len(history),
            last_updated=current.created_at,
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_fractal_engine: Optional[FractalEngine] = None


def get_fractal_engine() -> FractalEngine:
    """Get singleton instance of FractalEngine."""
    global _fractal_engine
    if _fractal_engine is None:
        _fractal_engine = FractalEngine()
    return _fractal_engine
