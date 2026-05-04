"""
Market State Engine — Regime Detection

Determines current market state:
- TRENDING
- RANGING
- BREAKOUT
- VOLATILE
- COMPRESSION

This enables adaptive strategy selection and indicator weighting.
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum
import numpy as np


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

class MarketState(str, Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    BREAKOUT_UP = "breakout_up"
    BREAKOUT_DOWN = "breakout_down"
    VOLATILE = "volatile"
    COMPRESSION = "compression"
    UNKNOWN = "unknown"


class MarketStateResult(BaseModel):
    """Result of market state detection."""
    state: MarketState
    confidence: float = Field(ge=0.0, le=1.0)
    sub_states: List[str] = Field(default_factory=list)  # Secondary characteristics
    
    # State metrics
    trend_strength: float = 0.0
    volatility_level: float = 0.0  # normalized
    range_width: float = 0.0
    breakout_strength: float = 0.0
    
    # Regime Stability - NEW
    regime_confidence: float = 0.0  # How stable is current regime
    regime_stability: str = "stable"  # stable, weakening, transitioning, forming
    regime_outlook: str = ""  # trend_strong, trend_weakening, range_forming, breakout_imminent
    
    # Recommended actions
    recommended_indicators: List[str] = Field(default_factory=list)
    recommended_strategy: str = "neutral"
    
    # Probabilities for each state
    state_probabilities: Dict[str, float] = Field(default_factory=dict)
    
    reasoning: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ═══════════════════════════════════════════════════════════════
# Indicator Recommendations by State
# ═══════════════════════════════════════════════════════════════

STATE_INDICATOR_MAP = {
    MarketState.TRENDING_UP: {
        "indicators": ["ema", "ichimoku", "supertrend", "psar", "macd"],
        "strategy": "trend_following_long",
        "description": "Strong uptrend - use trend indicators, follow momentum"
    },
    MarketState.TRENDING_DOWN: {
        "indicators": ["ema", "ichimoku", "supertrend", "psar", "macd"],
        "strategy": "trend_following_short",
        "description": "Strong downtrend - use trend indicators, follow momentum"
    },
    MarketState.RANGING: {
        "indicators": ["bollinger", "rsi", "cci", "stochastic", "keltner"],
        "strategy": "mean_reversion",
        "description": "Range-bound - use oscillators, fade extremes"
    },
    MarketState.BREAKOUT_UP: {
        "indicators": ["donchian", "keltner", "atr", "volume", "momentum"],
        "strategy": "breakout_long",
        "description": "Bullish breakout - confirm with volume, ride momentum"
    },
    MarketState.BREAKOUT_DOWN: {
        "indicators": ["donchian", "keltner", "atr", "volume", "momentum"],
        "strategy": "breakout_short",
        "description": "Bearish breakdown - confirm with volume, ride momentum"
    },
    MarketState.VOLATILE: {
        "indicators": ["atr", "bollinger", "keltner", "vwap"],
        "strategy": "reduced_size",
        "description": "High volatility - reduce position size, wider stops"
    },
    MarketState.COMPRESSION: {
        "indicators": ["bollinger", "keltner", "atr", "donchian"],
        "strategy": "prepare_breakout",
        "description": "Compression detected - prepare for breakout"
    },
}


# ═══════════════════════════════════════════════════════════════
# Market State Engine
# ═══════════════════════════════════════════════════════════════

class MarketStateEngine:
    """
    Detects current market state from price action and indicators.
    
    Uses multiple detection methods:
    1. ADX for trend strength
    2. Bollinger bandwidth for volatility
    3. Price position for range detection
    4. Breakout detection via Donchian
    5. Compression detection via squeeze
    """
    
    def __init__(self):
        self.lookback_period = 50
    
    def detect_state(
        self,
        candles: List[Dict[str, Any]],
        feature_vector: Optional[Dict[str, Any]] = None
    ) -> MarketStateResult:
        """
        Detect current market state.
        
        Args:
            candles: OHLCV data
            feature_vector: Optional pre-calculated feature vector
        
        Returns:
            MarketStateResult with state and recommendations
        """
        
        if len(candles) < 30:
            return MarketStateResult(
                state=MarketState.UNKNOWN,
                confidence=0.0,
                reasoning="Insufficient data for state detection"
            )
        
        # Calculate all metrics
        trend_strength = self._calculate_trend_strength(candles)
        volatility_level = self._calculate_volatility_level(candles)
        range_metrics = self._calculate_range_metrics(candles)
        breakout_metrics = self._calculate_breakout_metrics(candles)
        compression = self._detect_compression(candles)
        
        # Use feature vector if provided
        if feature_vector:
            trend_score = feature_vector.get("trend_score", 0)
            momentum_score = feature_vector.get("momentum_score", 0)
            breakout_score = feature_vector.get("breakout_score", 0)
        else:
            trend_score = trend_strength["direction_score"]
            momentum_score = 0
            breakout_score = breakout_metrics["strength"]
        
        # Calculate state probabilities
        probs = self._calculate_state_probabilities(
            trend_strength, volatility_level, range_metrics, 
            breakout_metrics, compression, trend_score, breakout_score
        )
        
        # Determine primary state
        state, confidence = self._determine_state(probs)
        
        # Get recommendations
        state_info = STATE_INDICATOR_MAP.get(state, STATE_INDICATOR_MAP[MarketState.RANGING])
        
        # Build sub-states
        sub_states = []
        if volatility_level > 0.7:
            sub_states.append("high_volatility")
        elif volatility_level < 0.3:
            sub_states.append("low_volatility")
        
        if compression["is_compressed"]:
            sub_states.append("squeeze_active")
        
        if range_metrics["in_range"]:
            sub_states.append("range_bound")
        
        # Calculate regime stability and outlook
        regime_confidence, regime_stability, regime_outlook = self._calculate_regime_stability(
            trend_strength, volatility_level, breakout_metrics, compression, trend_score
        )
        
        # Build reasoning
        reasoning = self._build_reasoning(
            state, trend_strength, volatility_level, 
            range_metrics, breakout_metrics, compression
        )
        
        return MarketStateResult(
            state=state,
            confidence=confidence,
            sub_states=sub_states,
            trend_strength=round(trend_strength["adx"], 2),
            volatility_level=round(volatility_level, 2),
            range_width=round(range_metrics["width_pct"], 4),
            breakout_strength=round(breakout_metrics["strength"], 2),
            regime_confidence=round(regime_confidence, 3),
            regime_stability=regime_stability,
            regime_outlook=regime_outlook,
            recommended_indicators=state_info["indicators"],
            recommended_strategy=state_info["strategy"],
            state_probabilities=probs,
            reasoning=reasoning,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Metric Calculations
    # ═══════════════════════════════════════════════════════════════
    
    def _calculate_trend_strength(self, candles: List[Dict]) -> Dict[str, Any]:
        """
        Calculate trend strength using ADX and directional movement.
        
        ADX > 25 = trending
        ADX > 40 = strong trend
        ADX < 20 = ranging
        """
        period = 14
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        
        # Calculate +DM and -DM
        plus_dm = []
        minus_dm = []
        tr_list = []
        
        for i in range(1, len(candles)):
            high_diff = highs[i] - highs[i-1]
            low_diff = lows[i-1] - lows[i]
            
            plus = high_diff if high_diff > low_diff and high_diff > 0 else 0
            minus = low_diff if low_diff > high_diff and low_diff > 0 else 0
            
            plus_dm.append(plus)
            minus_dm.append(minus)
            
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
        
        if len(tr_list) < period:
            return {"adx": 0, "plus_di": 0, "minus_di": 0, "direction_score": 0}
        
        # Smoothed averages
        atr = self._smooth_average(tr_list, period)
        smooth_plus_dm = self._smooth_average(plus_dm, period)
        smooth_minus_dm = self._smooth_average(minus_dm, period)
        
        # DI calculations
        plus_di = (smooth_plus_dm / atr) * 100 if atr > 0 else 0
        minus_di = (smooth_minus_dm / atr) * 100 if atr > 0 else 0
        
        # DX and ADX
        di_sum = plus_di + minus_di
        dx = abs(plus_di - minus_di) / di_sum * 100 if di_sum > 0 else 0
        
        # Simple ADX approximation
        adx = dx  # In production, would use smoothed DX
        
        # Direction score (-1 to +1)
        direction_score = (plus_di - minus_di) / max(plus_di + minus_di, 1)
        
        return {
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
            "direction_score": direction_score,
            "is_trending": adx > 25,
            "is_strong_trend": adx > 40,
        }
    
    def _calculate_volatility_level(self, candles: List[Dict]) -> float:
        """
        Calculate normalized volatility level (0-1).
        
        Uses Bollinger Bandwidth percentile.
        """
        closes = [c["close"] for c in candles]
        period = 20
        
        # Calculate current bandwidth
        current_std = np.std(closes[-period:])
        current_sma = np.mean(closes[-period:])
        current_bw = (2 * current_std) / current_sma if current_sma > 0 else 0
        
        # Calculate historical bandwidths
        bandwidths = []
        for i in range(period, len(closes)):
            std = np.std(closes[i-period:i])
            sma = np.mean(closes[i-period:i])
            bw = (2 * std) / sma if sma > 0 else 0
            bandwidths.append(bw)
        
        if not bandwidths:
            return 0.5
        
        # Percentile rank
        percentile = sum(1 for bw in bandwidths if bw < current_bw) / len(bandwidths)
        
        return percentile
    
    def _calculate_range_metrics(self, candles: List[Dict]) -> Dict[str, Any]:
        """
        Calculate range-bound metrics.
        """
        period = 20
        
        highs = [c["high"] for c in candles[-period:]]
        lows = [c["low"] for c in candles[-period:]]
        closes = [c["close"] for c in candles[-period:]]
        
        range_high = max(highs)
        range_low = min(lows)
        range_mid = (range_high + range_low) / 2
        range_width = range_high - range_low
        
        current_price = closes[-1]
        width_pct = range_width / range_mid if range_mid > 0 else 0
        
        # Check if price is bouncing within range
        touches_high = sum(1 for h in highs if h >= range_high * 0.99)
        touches_low = sum(1 for l in lows if l <= range_low * 1.01)
        
        # Range-bound if multiple touches and not breaking out
        in_range = (
            touches_high >= 2 and touches_low >= 2 and
            range_low <= current_price <= range_high and
            width_pct < 0.15  # Not too wide
        )
        
        return {
            "range_high": range_high,
            "range_low": range_low,
            "range_mid": range_mid,
            "width": range_width,
            "width_pct": width_pct,
            "touches_high": touches_high,
            "touches_low": touches_low,
            "in_range": in_range,
            "position_in_range": (current_price - range_low) / range_width if range_width > 0 else 0.5,
        }
    
    def _calculate_breakout_metrics(self, candles: List[Dict]) -> Dict[str, Any]:
        """
        Calculate breakout detection metrics.
        """
        period = 20
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]
        
        # Donchian levels
        donchian_high = max(highs[-period:])
        donchian_low = min(lows[-period:])
        
        current = closes[-1]
        prev_close = closes[-2] if len(closes) > 1 else current
        
        # Breakout detection
        breakout_up = current > donchian_high * 0.998
        breakout_down = current < donchian_low * 1.002
        
        # Volume confirmation
        avg_volume = np.mean(volumes[-period:]) if volumes else 0
        current_volume = volumes[-1] if volumes else 0
        volume_surge = current_volume > avg_volume * 1.5 if avg_volume > 0 else False
        
        # Breakout strength
        if breakout_up:
            strength = min(1.0, (current - donchian_high) / (donchian_high * 0.02))
            direction = "up"
        elif breakout_down:
            strength = min(1.0, (donchian_low - current) / (donchian_low * 0.02))
            direction = "down"
        else:
            strength = 0.0
            direction = "none"
        
        # Adjust strength by volume
        if volume_surge and strength > 0:
            strength = min(1.0, strength * 1.3)
        
        return {
            "donchian_high": donchian_high,
            "donchian_low": donchian_low,
            "is_breakout_up": breakout_up,
            "is_breakout_down": breakout_down,
            "volume_surge": volume_surge,
            "strength": strength,
            "direction": direction,
        }
    
    def _detect_compression(self, candles: List[Dict]) -> Dict[str, Any]:
        """
        Detect volatility compression (squeeze).
        
        Compression occurs when:
        - Bollinger bands inside Keltner channels
        - ATR declining
        - Range narrowing
        """
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        
        period = 20
        
        # Bollinger
        bb_sma = np.mean(closes[-period:])
        bb_std = np.std(closes[-period:])
        bb_upper = bb_sma + 2 * bb_std
        bb_lower = bb_sma - 2 * bb_std
        
        # Keltner
        ema = self._ema(closes, period)[-1]
        atr = self._calculate_atr(candles, 10)
        kc_upper = ema + 1.5 * atr
        kc_lower = ema - 1.5 * atr
        
        # Squeeze detection
        is_compressed = bb_lower > kc_lower and bb_upper < kc_upper
        
        # ATR trend
        atr_values = []
        for i in range(20, len(candles)):
            atr_val = self._calculate_atr(candles[:i], 10)
            atr_values.append(atr_val)
        
        atr_declining = False
        if len(atr_values) >= 10:
            recent_atr = np.mean(atr_values[-5:])
            older_atr = np.mean(atr_values[-10:-5])
            atr_declining = recent_atr < older_atr * 0.9
        
        # Compression score
        if is_compressed and atr_declining:
            compression_score = 0.9
        elif is_compressed:
            compression_score = 0.7
        elif atr_declining:
            compression_score = 0.5
        else:
            compression_score = 0.0
        
        return {
            "is_compressed": is_compressed,
            "atr_declining": atr_declining,
            "compression_score": compression_score,
            "bb_width": bb_upper - bb_lower,
            "kc_width": kc_upper - kc_lower,
        }
    
    # ═══════════════════════════════════════════════════════════════
    # State Determination
    # ═══════════════════════════════════════════════════════════════
    
    def _calculate_state_probabilities(
        self,
        trend: Dict,
        volatility: float,
        range_metrics: Dict,
        breakout: Dict,
        compression: Dict,
        trend_score: float,
        breakout_score: float
    ) -> Dict[str, float]:
        """Calculate probability for each market state."""
        
        probs = {
            "trending_up": 0.0,
            "trending_down": 0.0,
            "ranging": 0.0,
            "breakout_up": 0.0,
            "breakout_down": 0.0,
            "volatile": 0.0,
            "compression": 0.0,
        }
        
        # Trending probabilities
        if trend["adx"] > 25:
            if trend_score > 0.2:
                probs["trending_up"] = min(0.8, 0.4 + trend["adx"] / 100)
            elif trend_score < -0.2:
                probs["trending_down"] = min(0.8, 0.4 + trend["adx"] / 100)
        
        # Ranging probability
        if range_metrics["in_range"] and trend["adx"] < 25:
            probs["ranging"] = 0.6
        elif trend["adx"] < 20:
            probs["ranging"] = 0.4
        
        # Breakout probabilities
        if breakout["is_breakout_up"]:
            probs["breakout_up"] = 0.6 + breakout["strength"] * 0.3
        if breakout["is_breakout_down"]:
            probs["breakout_down"] = 0.6 + breakout["strength"] * 0.3
        
        # Volatile probability
        if volatility > 0.7:
            probs["volatile"] = 0.5 + (volatility - 0.7) * 1.5
        
        # Compression probability
        if compression["is_compressed"]:
            probs["compression"] = compression["compression_score"]
        
        # Normalize
        total = sum(probs.values())
        if total > 0:
            probs = {k: round(v / total, 3) for k, v in probs.items()}
        
        return probs
    
    def _determine_state(self, probs: Dict[str, float]) -> tuple:
        """Determine primary state from probabilities."""
        
        if not probs or max(probs.values()) == 0:
            return MarketState.UNKNOWN, 0.0
        
        # Find highest probability
        max_state = max(probs, key=probs.get)
        max_prob = probs[max_state]
        
        state_map = {
            "trending_up": MarketState.TRENDING_UP,
            "trending_down": MarketState.TRENDING_DOWN,
            "ranging": MarketState.RANGING,
            "breakout_up": MarketState.BREAKOUT_UP,
            "breakout_down": MarketState.BREAKOUT_DOWN,
            "volatile": MarketState.VOLATILE,
            "compression": MarketState.COMPRESSION,
        }
        
        state = state_map.get(max_state, MarketState.UNKNOWN)
        
        return state, max_prob
    
    def _build_reasoning(
        self,
        state: MarketState,
        trend: Dict,
        volatility: float,
        range_metrics: Dict,
        breakout: Dict,
        compression: Dict
    ) -> str:
        """Build human-readable reasoning."""
        
        parts = [f"State: {state.value}"]
        
        if trend["adx"] > 25:
            parts.append(f"ADX={trend['adx']:.1f} (trending)")
        else:
            parts.append(f"ADX={trend['adx']:.1f} (weak trend)")
        
        if volatility > 0.7:
            parts.append(f"High volatility ({volatility:.0%})")
        elif volatility < 0.3:
            parts.append(f"Low volatility ({volatility:.0%})")
        
        if range_metrics["in_range"]:
            parts.append(f"Range-bound ({range_metrics['width_pct']:.1%} width)")
        
        if breakout["is_breakout_up"] or breakout["is_breakout_down"]:
            parts.append(f"Breakout {breakout['direction']} (strength={breakout['strength']:.2f})")
        
        if compression["is_compressed"]:
            parts.append("Squeeze detected")
        
        return " | ".join(parts)
    
    def _calculate_regime_stability(
        self,
        trend: Dict[str, Any],
        volatility: float,
        breakout: Dict[str, Any],
        compression: Dict[str, Any],
        trend_score: float
    ) -> tuple:
        """
        Calculate regime stability metrics.
        
        Returns:
            (regime_confidence, regime_stability, regime_outlook)
            
        regime_confidence: How stable/confident is the current regime (0-1)
        regime_stability: "stable", "weakening", "transitioning", "forming"
        regime_outlook: "trend_strong", "trend_weakening", "range_forming", "breakout_imminent"
        """
        
        # Calculate base regime confidence
        # Formula: 0.5 * |trend_score| + 0.3 * (1 - volatility) + 0.2 * breakout_alignment
        
        trend_component = 0.5 * min(1.0, abs(trend_score))
        volatility_component = 0.3 * (1 - volatility)  # Lower volatility = more stable
        
        # Breakout alignment
        if breakout["is_breakout_up"] and trend_score > 0:
            breakout_alignment = breakout["strength"]
        elif breakout["is_breakout_down"] and trend_score < 0:
            breakout_alignment = breakout["strength"]
        else:
            breakout_alignment = 0.0
        
        breakout_component = 0.2 * breakout_alignment
        
        regime_confidence = trend_component + volatility_component + breakout_component
        regime_confidence = max(0.0, min(1.0, regime_confidence))
        
        # Determine stability
        adx = trend.get("adx", 0)
        
        if regime_confidence > 0.7 and adx > 30:
            regime_stability = "stable"
        elif regime_confidence > 0.5 and adx > 20:
            regime_stability = "stable"
        elif compression["is_compressed"]:
            regime_stability = "transitioning"
        elif volatility > 0.7:
            regime_stability = "forming"
        elif regime_confidence < 0.3:
            regime_stability = "weakening"
        else:
            regime_stability = "stable"
        
        # Determine outlook
        if adx > 40 and abs(trend_score) > 0.5:
            regime_outlook = "trend_strong"
        elif adx > 25 and adx < 40 and abs(trend_score) < 0.3:
            regime_outlook = "trend_weakening"
        elif compression["is_compressed"] and compression["compression_score"] > 0.7:
            regime_outlook = "breakout_imminent"
        elif volatility < 0.3 and not breakout["is_breakout_up"] and not breakout["is_breakout_down"]:
            regime_outlook = "range_forming"
        elif adx < 20:
            regime_outlook = "range_forming"
        else:
            regime_outlook = "trend_continuing"
        
        return regime_confidence, regime_stability, regime_outlook
    
    # ═══════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════
    
    def _smooth_average(self, data: List[float], period: int) -> float:
        """Calculate smoothed average."""
        if not data or len(data) < period:
            return np.mean(data) if data else 0
        return np.mean(data[-period:])
    
    def _ema(self, data: List[float], period: int) -> List[float]:
        """Calculate EMA."""
        if not data:
            return []
        k = 2 / (period + 1)
        ema = [data[0]]
        for i in range(1, len(data)):
            ema.append(data[i] * k + ema[-1] * (1 - k))
        return ema
    
    def _calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate ATR."""
        if len(candles) < 2:
            return candles[0]["high"] - candles[0]["low"] if candles else 0
        
        tr_values = []
        for i in range(1, min(len(candles), period + 1)):
            tr = max(
                candles[i]["high"] - candles[i]["low"],
                abs(candles[i]["high"] - candles[i-1]["close"]),
                abs(candles[i]["low"] - candles[i-1]["close"])
            )
            tr_values.append(tr)
        
        return np.mean(tr_values) if tr_values else 0


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_state_engine: Optional[MarketStateEngine] = None

def get_market_state_engine() -> MarketStateEngine:
    """Get singleton instance."""
    global _state_engine
    if _state_engine is None:
        _state_engine = MarketStateEngine()
    return _state_engine
