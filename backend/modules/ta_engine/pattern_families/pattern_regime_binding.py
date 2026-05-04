"""
Pattern Regime Binding
======================

CRITICAL LAYER: Pattern changes meaning based on market regime.

- triangle in trend continuation ≠ triangle in dead chop
- double bottom after capitulation ≠ double bottom inside noisy range
- inverse H&S at macro support ≠ inverse H&S in the middle of nowhere

This layer:
1. Detects current regime
2. Binds pattern to regime context
3. Adjusts score with bonus/penalty
4. Sets actionability level
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class MarketRegime(Enum):
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE_ACTIVE = "range_active"
    COMPRESSION = "compression"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


class Actionability(Enum):
    HIGH = "high"      # Can trade now
    MEDIUM = "medium"  # Trade with caution / reduced size
    LOW = "low"        # Wait for confirmation
    NONE = "none"      # Do not trade


@dataclass
class RegimeContext:
    """Current market regime context."""
    regime: MarketRegime
    trend: str           # up / down / neutral
    impulse_dir: str     # bullish / bearish / neutral
    volatility: str      # high / normal / low
    structure_bias: str  # bullish / bearish / neutral
    
    def to_dict(self) -> Dict:
        return {
            "regime": self.regime.value,
            "trend": self.trend,
            "impulse_dir": self.impulse_dir,
            "volatility": self.volatility,
            "structure_bias": self.structure_bias,
        }


@dataclass
class BoundPattern:
    """Pattern with regime binding applied."""
    pattern: Dict
    bonus: int
    penalty: int
    bound_score: float
    actionability: Actionability
    interpretation: List[str]
    regime_context: RegimeContext
    
    def to_dict(self) -> Dict:
        return {
            **self.pattern,
            "regime_binding": {
                "bonus": self.bonus,
                "penalty": self.penalty,
                "bound_score": round(self.bound_score, 2),
                "actionability": self.actionability.value,
                "interpretation": self.interpretation,
                "regime": self.regime_context.regime.value,
                "trend": self.regime_context.trend,
            }
        }


class PatternRegimeBinder:
    """
    Binds patterns to market regime context.
    
    RULES:
    - Same pattern has different meaning in different regimes
    - Bonus for aligned patterns
    - Penalty for counter-trend patterns
    - Actionability based on fit
    """
    
    def __init__(self, config: Dict = None):
        config = config or {}
        self.alignment_bonus = config.get("alignment_bonus", 8)
        self.misalignment_penalty = config.get("misalignment_penalty", 6)
    
    def detect_regime(
        self,
        structure: Dict = None,
        impulse: Dict = None,
        candles: List[Dict] = None
    ) -> RegimeContext:
        """
        Detect current market regime from available data.
        """
        structure = structure or {}
        impulse = impulse or {}
        
        # Get trend from structure
        trend = structure.get("trend", "neutral")
        if trend not in ["up", "down", "neutral"]:
            trend = "neutral"
        
        # Get impulse direction
        impulse_dir = impulse.get("direction", "neutral")
        if impulse_dir not in ["bullish", "bearish", "neutral"]:
            impulse_dir = "neutral"
        
        # Volatility from candles
        volatility = "normal"
        if candles and len(candles) >= 20:
            volatility = self._detect_volatility(candles)
        
        # Structure bias
        structure_bias = structure.get("bias", "neutral")
        
        # Determine regime
        regime = self._classify_regime(trend, impulse_dir, volatility, structure)
        
        return RegimeContext(
            regime=regime,
            trend=trend,
            impulse_dir=impulse_dir,
            volatility=volatility,
            structure_bias=structure_bias,
        )
    
    def _detect_volatility(self, candles: List[Dict]) -> str:
        """Detect volatility state from candles."""
        if len(candles) < 20:
            return "normal"
        
        # Calculate ATR ratio (recent vs older)
        recent = candles[-10:]
        older = candles[-20:-10]
        
        def avg_range(c_list):
            return sum(c.get("high", 0) - c.get("low", 0) for c in c_list) / len(c_list)
        
        recent_atr = avg_range(recent)
        older_atr = avg_range(older)
        
        if older_atr == 0:
            return "normal"
        
        ratio = recent_atr / older_atr
        
        if ratio < 0.6:
            return "low"  # Compression
        elif ratio > 1.5:
            return "high"  # Expansion
        return "normal"
    
    def _classify_regime(
        self,
        trend: str,
        impulse_dir: str,
        volatility: str,
        structure: Dict
    ) -> MarketRegime:
        """Classify into one of 5 regimes."""
        
        # Clear trend
        if trend == "up" and impulse_dir in ["bullish", "neutral"]:
            return MarketRegime.TREND_UP
        
        if trend == "down" and impulse_dir in ["bearish", "neutral"]:
            return MarketRegime.TREND_DOWN
        
        # Compression / Squeeze
        if volatility == "low":
            return MarketRegime.COMPRESSION
        
        # Range / Sideways
        if trend == "neutral" and volatility == "normal":
            return MarketRegime.RANGE_ACTIVE
        
        # Transition (conflicting signals)
        if (trend == "up" and impulse_dir == "bearish") or \
           (trend == "down" and impulse_dir == "bullish"):
            return MarketRegime.TRANSITION
        
        return MarketRegime.UNKNOWN
    
    def bind(
        self,
        pattern: Dict,
        regime_context: RegimeContext
    ) -> BoundPattern:
        """
        Bind a pattern to regime context.
        
        Adjusts score and sets actionability based on regime fit.
        """
        if not pattern:
            return None
        
        ptype = pattern.get("type", "").lower()
        bias = pattern.get("bias", "neutral")
        original_score = pattern.get("confidence", 0.5) * 100  # Convert to 0-100 scale
        
        bonus = 0
        penalty = 0
        interpretation = []
        actionability = Actionability.LOW
        
        regime = regime_context.regime
        trend = regime_context.trend
        impulse_dir = regime_context.impulse_dir
        
        # =====================================================
        # PATTERN-SPECIFIC REGIME BINDING RULES
        # =====================================================
        
        # 1. SYMMETRICAL TRIANGLE
        if ptype == "symmetrical_triangle":
            interpretation.append("Compression structure, NOT directional by itself")
            
            if regime in [MarketRegime.COMPRESSION, MarketRegime.RANGE_ACTIVE]:
                bonus += 2
                interpretation.append("Fits compression/range regime")
            else:
                penalty += 2
                interpretation.append("Triangle in trend = weaker signal")
            
            if trend in ["up", "down"]:
                interpretation.append(f"Breakout likely in {trend} direction based on structure")
                actionability = Actionability.MEDIUM
            else:
                interpretation.append("Wait for breakout direction")
                actionability = Actionability.LOW
        
        # 2. ASCENDING TRIANGLE
        elif ptype == "ascending_triangle":
            if trend == "up":
                bonus += self.alignment_bonus
                interpretation.append("Bullish continuation aligned with uptrend")
                actionability = Actionability.HIGH
            elif trend == "down":
                penalty += self.misalignment_penalty
                interpretation.append("Bullish pattern fights bearish structure")
                actionability = Actionability.LOW
            else:
                bonus += 2
                interpretation.append("Bullish pattern in neutral structure")
                actionability = Actionability.MEDIUM
        
        # 3. DESCENDING TRIANGLE
        elif ptype == "descending_triangle":
            if trend == "down":
                bonus += self.alignment_bonus
                interpretation.append("Bearish continuation aligned with downtrend")
                actionability = Actionability.HIGH
            elif trend == "up":
                penalty += self.misalignment_penalty
                interpretation.append("Bearish pattern fights bullish structure")
                actionability = Actionability.LOW
            else:
                bonus += 2
                interpretation.append("Bearish pattern in neutral structure")
                actionability = Actionability.MEDIUM
        
        # 4. DOUBLE TOP
        elif ptype == "double_top":
            if trend == "up":
                bonus += 7
                interpretation.append("Reversal pattern after bullish advance - high probability")
                actionability = Actionability.HIGH
            elif regime in [MarketRegime.RANGE_ACTIVE]:
                penalty += 3
                interpretation.append("Inside range, double top is range-bound behavior")
                actionability = Actionability.MEDIUM
            else:
                interpretation.append("Double top needs uptrend context for best results")
                actionability = Actionability.MEDIUM
        
        # 5. DOUBLE BOTTOM
        elif ptype == "double_bottom":
            if trend == "down":
                bonus += 7
                interpretation.append("Reversal pattern after bearish decline - high probability")
                actionability = Actionability.HIGH
            elif regime in [MarketRegime.RANGE_ACTIVE]:
                penalty += 3
                interpretation.append("Inside range, double bottom is range-bound behavior")
                actionability = Actionability.MEDIUM
            else:
                interpretation.append("Double bottom needs downtrend context for best results")
                actionability = Actionability.MEDIUM
        
        # 6. TRIPLE TOP
        elif ptype == "triple_top":
            if trend == "up":
                bonus += 8
                interpretation.append("Strong reversal after extended advance")
                actionability = Actionability.HIGH
            else:
                penalty += 2
                interpretation.append("Triple top most effective after uptrend")
                actionability = Actionability.MEDIUM
        
        # 7. TRIPLE BOTTOM
        elif ptype == "triple_bottom":
            if trend == "down":
                bonus += 8
                interpretation.append("Strong reversal after extended decline")
                actionability = Actionability.HIGH
            else:
                penalty += 2
                interpretation.append("Triple bottom most effective after downtrend")
                actionability = Actionability.MEDIUM
        
        # 8. INVERSE HEAD & SHOULDERS
        elif ptype == "inverse_head_shoulders":
            if trend == "down":
                bonus += self.alignment_bonus
                interpretation.append("Bullish reversal after downtrend - classic setup")
                actionability = Actionability.HIGH
            elif regime in [MarketRegime.RANGE_ACTIVE]:
                penalty += 2
                interpretation.append("Inside active range, needs breakout confirmation")
                actionability = Actionability.MEDIUM
            else:
                interpretation.append("iH&S works best at end of downtrend")
                actionability = Actionability.MEDIUM
        
        # 9. HEAD & SHOULDERS
        elif ptype == "head_shoulders":
            if trend == "up":
                bonus += self.alignment_bonus
                interpretation.append("Bearish reversal after uptrend - classic setup")
                actionability = Actionability.HIGH
            elif regime in [MarketRegime.RANGE_ACTIVE]:
                penalty += 2
                interpretation.append("Inside active range, needs breakdown confirmation")
                actionability = Actionability.MEDIUM
            else:
                interpretation.append("H&S works best at end of uptrend")
                actionability = Actionability.MEDIUM
        
        # 10. RANGE / RECTANGLE
        elif ptype in ["range", "rectangle", "loose_range", "active_range"]:
            if regime in [MarketRegime.RANGE_ACTIVE, MarketRegime.COMPRESSION]:
                bonus += self.alignment_bonus
                interpretation.append("Range structure consistent with current regime")
                actionability = Actionability.MEDIUM
            else:
                penalty += 4
                interpretation.append("Range pattern conflicts with trending regime")
                actionability = Actionability.LOW
        
        # 11. FALLING WEDGE
        elif ptype == "falling_wedge":
            if trend == "down":
                bonus += 5
                interpretation.append("Bullish reversal pattern in bearish context - watch for breakout")
                actionability = Actionability.MEDIUM
            elif trend == "up":
                bonus += 3
                interpretation.append("Bullish continuation in uptrend")
                actionability = Actionability.MEDIUM
            else:
                interpretation.append("Falling wedge - wait for breakout")
                actionability = Actionability.LOW
        
        # 12. RISING WEDGE
        elif ptype == "rising_wedge":
            if trend == "up":
                bonus += 5
                interpretation.append("Bearish reversal pattern in bullish context - watch for breakdown")
                actionability = Actionability.MEDIUM
            elif trend == "down":
                bonus += 3
                interpretation.append("Bearish continuation in downtrend")
                actionability = Actionability.MEDIUM
            else:
                interpretation.append("Rising wedge - wait for breakdown")
                actionability = Actionability.LOW
        
        # DEFAULT
        else:
            interpretation.append("No specific regime binding rule")
            actionability = Actionability.LOW
        
        # Calculate bound score
        bound_score = original_score + bonus - penalty
        bound_score = max(0, min(bound_score, 100))  # Clamp 0-100
        
        return BoundPattern(
            pattern=pattern,
            bonus=bonus,
            penalty=penalty,
            bound_score=bound_score,
            actionability=actionability,
            interpretation=interpretation,
            regime_context=regime_context,
        )
    
    def bind_all(
        self,
        patterns: List[Dict],
        regime_context: RegimeContext
    ) -> List[BoundPattern]:
        """Bind all patterns to regime context."""
        bound = []
        for p in patterns:
            bp = self.bind(p, regime_context)
            if bp:
                bound.append(bp)
        
        # Sort by bound_score
        bound.sort(key=lambda x: x.bound_score, reverse=True)
        return bound


# Singleton
_regime_binder = None

def get_pattern_regime_binder(config: Dict = None) -> PatternRegimeBinder:
    global _regime_binder
    if _regime_binder is None or config:
        _regime_binder = PatternRegimeBinder(config)
    return _regime_binder
