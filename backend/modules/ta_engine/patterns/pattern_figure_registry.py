"""
Pattern Figure Registry v2
==========================

ONLY REAL CHART PATTERNS - NOT market state, NOT tools.

This registry contains 50+ validated pattern figures organized by category:
- REVERSAL: double top, H&S, rounding, etc.
- CONTINUATION: flags, pennants, triangles, etc.
- HARMONIC: bat, butterfly, gartley, cypher, etc.
- CANDLESTICK: engulfing, pin bar, doji families, etc.

IMPORTANT: Channel, trend, EMA, VWAP, Fibonacci, S/R, liquidity — 
           these are NOT patterns. They are market_state, tools, or context.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class PatternCategory(str, Enum):
    REVERSAL = "reversal"
    CONTINUATION = "continuation"
    HARMONIC = "harmonic"
    CANDLESTICK = "candlestick"
    COMPLEX = "complex"


class PatternState(str, Enum):
    FORMING = "forming"
    ACTIVE = "active"
    BROKEN = "broken"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"


class PatternBias(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class PatternDefinition:
    """Definition of a pattern type."""
    id: str
    name: str
    category: PatternCategory
    default_bias: PatternBias
    min_touches: int
    min_candles: int
    max_candles: int
    symmetry_tolerance: float  # 0-1, how symmetric pattern must be
    description: str
    breakout_required: bool = True
    has_neckline: bool = False
    has_apex: bool = False
    fib_ratios: Optional[List[float]] = None  # For harmonic patterns
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "default_bias": self.default_bias.value,
            "min_touches": self.min_touches,
            "min_candles": self.min_candles,
            "max_candles": self.max_candles,
            "symmetry_tolerance": self.symmetry_tolerance,
            "description": self.description,
            "breakout_required": self.breakout_required,
            "has_neckline": self.has_neckline,
            "has_apex": self.has_apex,
            "fib_ratios": self.fib_ratios,
        }


class PatternFigureRegistry:
    """
    Registry of 50+ real chart pattern figures.
    
    NOT included here (they belong to other layers):
    - trend (market_state)
    - channel (market_state)
    - support/resistance (tools)
    - EMA/MA (indicators)
    - Fibonacci (tools)
    - liquidity zones (smart money layer)
    """
    
    def __init__(self):
        self._patterns: Dict[str, PatternDefinition] = {}
        self._register_all()
    
    def _register_all(self):
        """Register all 50+ pattern figures."""
        
        # ═══════════════════════════════════════════════════════════════
        # REVERSAL PATTERNS (13+)
        # ═══════════════════════════════════════════════════════════════
        
        self._register(PatternDefinition(
            id="double_top", name="Double Top",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.BEARISH,
            min_touches=2, min_candles=20, max_candles=100,
            symmetry_tolerance=0.15, has_neckline=True,
            description="Two peaks at similar level followed by breakdown"
        ))
        
        self._register(PatternDefinition(
            id="double_bottom", name="Double Bottom",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.BULLISH,
            min_touches=2, min_candles=20, max_candles=100,
            symmetry_tolerance=0.15, has_neckline=True,
            description="Two troughs at similar level followed by breakout"
        ))
        
        self._register(PatternDefinition(
            id="triple_top", name="Triple Top",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.BEARISH,
            min_touches=3, min_candles=30, max_candles=150,
            symmetry_tolerance=0.15, has_neckline=True,
            description="Three peaks at similar level"
        ))
        
        self._register(PatternDefinition(
            id="triple_bottom", name="Triple Bottom",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.BULLISH,
            min_touches=3, min_candles=30, max_candles=150,
            symmetry_tolerance=0.15, has_neckline=True,
            description="Three troughs at similar level"
        ))
        
        self._register(PatternDefinition(
            id="head_shoulders", name="Head and Shoulders",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.BEARISH,
            min_touches=5, min_candles=30, max_candles=200,
            symmetry_tolerance=0.20, has_neckline=True,
            description="Left shoulder, head, right shoulder - bearish reversal"
        ))
        
        self._register(PatternDefinition(
            id="inverse_head_shoulders", name="Inverse Head and Shoulders",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.BULLISH,
            min_touches=5, min_candles=30, max_candles=200,
            symmetry_tolerance=0.20, has_neckline=True,
            description="Inverted H&S - bullish reversal"
        ))
        
        self._register(PatternDefinition(
            id="rounding_top", name="Rounding Top",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.BEARISH,
            min_touches=10, min_candles=50, max_candles=300,
            symmetry_tolerance=0.25,
            description="Gradual curved top - distribution"
        ))
        
        self._register(PatternDefinition(
            id="rounding_bottom", name="Rounding Bottom",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.BULLISH,
            min_touches=10, min_candles=50, max_candles=300,
            symmetry_tolerance=0.25,
            description="Gradual curved bottom - accumulation (saucer)"
        ))
        
        self._register(PatternDefinition(
            id="cup_handle", name="Cup and Handle",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.BULLISH,
            min_touches=8, min_candles=40, max_candles=250,
            symmetry_tolerance=0.20,
            description="U-shaped cup followed by small consolidation handle"
        ))
        
        self._register(PatternDefinition(
            id="bump_run", name="Bump and Run Reversal",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.BEARISH,
            min_touches=5, min_candles=30, max_candles=150,
            symmetry_tolerance=0.25,
            description="Lead-in, bump, run phases"
        ))
        
        self._register(PatternDefinition(
            id="island_reversal", name="Island Reversal",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.NEUTRAL,
            min_touches=2, min_candles=5, max_candles=20,
            symmetry_tolerance=0.30,
            description="Isolated price action with gaps on both sides"
        ))
        
        self._register(PatternDefinition(
            id="v_top", name="V-Top",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.BEARISH,
            min_touches=2, min_candles=10, max_candles=50,
            symmetry_tolerance=0.35,
            description="Sharp reversal at top"
        ))
        
        self._register(PatternDefinition(
            id="v_bottom", name="V-Bottom",
            category=PatternCategory.REVERSAL, default_bias=PatternBias.BULLISH,
            min_touches=2, min_candles=10, max_candles=50,
            symmetry_tolerance=0.35,
            description="Sharp reversal at bottom"
        ))
        
        # ═══════════════════════════════════════════════════════════════
        # CONTINUATION PATTERNS (14+)
        # ═══════════════════════════════════════════════════════════════
        
        self._register(PatternDefinition(
            id="bull_flag", name="Bull Flag",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.BULLISH,
            min_touches=4, min_candles=10, max_candles=50,
            symmetry_tolerance=0.20,
            description="Upward pole followed by downward sloping consolidation"
        ))
        
        self._register(PatternDefinition(
            id="bear_flag", name="Bear Flag",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.BEARISH,
            min_touches=4, min_candles=10, max_candles=50,
            symmetry_tolerance=0.20,
            description="Downward pole followed by upward sloping consolidation"
        ))
        
        self._register(PatternDefinition(
            id="pennant", name="Pennant",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.NEUTRAL,
            min_touches=4, min_candles=10, max_candles=40,
            symmetry_tolerance=0.15, has_apex=True,
            description="Symmetrical triangle following a pole"
        ))
        
        self._register(PatternDefinition(
            id="ascending_triangle", name="Ascending Triangle",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.BULLISH,
            min_touches=4, min_candles=15, max_candles=80,
            symmetry_tolerance=0.20, has_apex=True,
            description="Flat top, rising bottom - typically bullish"
        ))
        
        self._register(PatternDefinition(
            id="descending_triangle", name="Descending Triangle",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.BEARISH,
            min_touches=4, min_candles=15, max_candles=80,
            symmetry_tolerance=0.20, has_apex=True,
            description="Flat bottom, falling top - typically bearish"
        ))
        
        self._register(PatternDefinition(
            id="symmetrical_triangle", name="Symmetrical Triangle",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.NEUTRAL,
            min_touches=4, min_candles=15, max_candles=80,
            symmetry_tolerance=0.15, has_apex=True,
            description="Converging trendlines - breaks in direction of prior trend"
        ))
        
        self._register(PatternDefinition(
            id="expanding_triangle", name="Expanding Triangle",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.NEUTRAL,
            min_touches=4, min_candles=15, max_candles=80,
            symmetry_tolerance=0.20, has_apex=True,
            description="Diverging trendlines - increased volatility"
        ))
        
        self._register(PatternDefinition(
            id="rising_wedge", name="Rising Wedge",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.BEARISH,
            min_touches=4, min_candles=15, max_candles=80,
            symmetry_tolerance=0.20, has_apex=True,
            description="Both trendlines rising, converging - bearish"
        ))
        
        self._register(PatternDefinition(
            id="falling_wedge", name="Falling Wedge",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.BULLISH,
            min_touches=4, min_candles=15, max_candles=80,
            symmetry_tolerance=0.20, has_apex=True,
            description="Both trendlines falling, converging - bullish"
        ))
        
        self._register(PatternDefinition(
            id="rectangle_bull", name="Bullish Rectangle",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.BULLISH,
            min_touches=4, min_candles=15, max_candles=80,
            symmetry_tolerance=0.10,
            description="Horizontal consolidation in uptrend"
        ))
        
        self._register(PatternDefinition(
            id="rectangle_bear", name="Bearish Rectangle",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.BEARISH,
            min_touches=4, min_candles=15, max_candles=80,
            symmetry_tolerance=0.10,
            description="Horizontal consolidation in downtrend"
        ))
        
        self._register(PatternDefinition(
            id="broadening_formation", name="Broadening Formation",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=20, max_candles=100,
            symmetry_tolerance=0.25,
            description="Megaphone pattern - expanding price range"
        ))
        
        self._register(PatternDefinition(
            id="measured_move", name="Measured Move",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.NEUTRAL,
            min_touches=3, min_candles=20, max_candles=150,
            symmetry_tolerance=0.25,
            description="AB=CD move projection"
        ))
        
        self._register(PatternDefinition(
            id="high_tight_flag", name="High Tight Flag",
            category=PatternCategory.CONTINUATION, default_bias=PatternBias.BULLISH,
            min_touches=4, min_candles=5, max_candles=25,
            symmetry_tolerance=0.20,
            description="Strong flag after 100%+ gain"
        ))
        
        # ═══════════════════════════════════════════════════════════════
        # HARMONIC PATTERNS (12+)
        # ═══════════════════════════════════════════════════════════════
        
        self._register(PatternDefinition(
            id="gartley", name="Gartley",
            category=PatternCategory.HARMONIC, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=20, max_candles=150,
            symmetry_tolerance=0.10,
            fib_ratios=[0.618, 0.382, 0.786],
            description="XABCD with specific Fibonacci ratios"
        ))
        
        self._register(PatternDefinition(
            id="bat", name="Bat",
            category=PatternCategory.HARMONIC, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=20, max_candles=150,
            symmetry_tolerance=0.10,
            fib_ratios=[0.382, 0.886, 0.886],
            description="Bat harmonic with 0.886 retracement"
        ))
        
        self._register(PatternDefinition(
            id="butterfly", name="Butterfly",
            category=PatternCategory.HARMONIC, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=20, max_candles=150,
            symmetry_tolerance=0.10,
            fib_ratios=[0.786, 1.27, 1.618],
            description="Butterfly with extended D point"
        ))
        
        self._register(PatternDefinition(
            id="crab", name="Crab",
            category=PatternCategory.HARMONIC, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=20, max_candles=150,
            symmetry_tolerance=0.10,
            fib_ratios=[0.382, 0.886, 1.618],
            description="Crab with 1.618 extension"
        ))
        
        self._register(PatternDefinition(
            id="deep_crab", name="Deep Crab",
            category=PatternCategory.HARMONIC, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=20, max_candles=150,
            symmetry_tolerance=0.10,
            fib_ratios=[0.886, 0.886, 1.618],
            description="Deep crab with 0.886 B point"
        ))
        
        self._register(PatternDefinition(
            id="shark", name="Shark",
            category=PatternCategory.HARMONIC, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=20, max_candles=150,
            symmetry_tolerance=0.10,
            fib_ratios=[0.446, 1.13, 1.618],
            description="Shark pattern (0XABC)"
        ))
        
        self._register(PatternDefinition(
            id="cypher", name="Cypher",
            category=PatternCategory.HARMONIC, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=20, max_candles=150,
            symmetry_tolerance=0.10,
            fib_ratios=[0.382, 1.272, 0.786],
            description="Cypher pattern"
        ))
        
        self._register(PatternDefinition(
            id="three_drives", name="Three Drives",
            category=PatternCategory.HARMONIC, default_bias=PatternBias.NEUTRAL,
            min_touches=6, min_candles=30, max_candles=200,
            symmetry_tolerance=0.15,
            fib_ratios=[1.272, 1.618],
            description="Three impulsive drives with Fib extensions"
        ))
        
        self._register(PatternDefinition(
            id="abcd", name="ABCD",
            category=PatternCategory.HARMONIC, default_bias=PatternBias.NEUTRAL,
            min_touches=4, min_candles=15, max_candles=100,
            symmetry_tolerance=0.15,
            fib_ratios=[0.618, 1.272],
            description="Basic AB=CD harmonic"
        ))
        
        self._register(PatternDefinition(
            id="wolfe_wave", name="Wolfe Wave",
            category=PatternCategory.HARMONIC, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=20, max_candles=150,
            symmetry_tolerance=0.20,
            description="5-wave structure with converging lines"
        ))
        
        self._register(PatternDefinition(
            id="dragon", name="Dragon",
            category=PatternCategory.HARMONIC, default_bias=PatternBias.BULLISH,
            min_touches=5, min_candles=25, max_candles=150,
            symmetry_tolerance=0.20,
            description="Dragon bottom reversal pattern"
        ))
        
        self._register(PatternDefinition(
            id="inverse_dragon", name="Inverse Dragon",
            category=PatternCategory.HARMONIC, default_bias=PatternBias.BEARISH,
            min_touches=5, min_candles=25, max_candles=150,
            symmetry_tolerance=0.20,
            description="Dragon top reversal pattern"
        ))
        
        # ═══════════════════════════════════════════════════════════════
        # COMPLEX / ELLIOTT / ADVANCED (8+)
        # ═══════════════════════════════════════════════════════════════
        
        self._register(PatternDefinition(
            id="diamond_top", name="Diamond Top",
            category=PatternCategory.COMPLEX, default_bias=PatternBias.BEARISH,
            min_touches=6, min_candles=30, max_candles=150,
            symmetry_tolerance=0.20,
            description="Expanding then contracting formation at top"
        ))
        
        self._register(PatternDefinition(
            id="diamond_bottom", name="Diamond Bottom",
            category=PatternCategory.COMPLEX, default_bias=PatternBias.BULLISH,
            min_touches=6, min_candles=30, max_candles=150,
            symmetry_tolerance=0.20,
            description="Expanding then contracting formation at bottom"
        ))
        
        self._register(PatternDefinition(
            id="broadening_wedge", name="Broadening Wedge",
            category=PatternCategory.COMPLEX, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=20, max_candles=100,
            symmetry_tolerance=0.25,
            description="Expanding wedge formation"
        ))
        
        self._register(PatternDefinition(
            id="diagonal", name="Diagonal",
            category=PatternCategory.COMPLEX, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=20, max_candles=100,
            symmetry_tolerance=0.20,
            description="Elliott wave diagonal (leading/ending)"
        ))
        
        self._register(PatternDefinition(
            id="ending_diagonal", name="Ending Diagonal",
            category=PatternCategory.COMPLEX, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=15, max_candles=80,
            symmetry_tolerance=0.20,
            description="5-wave ending diagonal - reversal signal"
        ))
        
        self._register(PatternDefinition(
            id="elliott_impulse", name="Elliott Impulse",
            category=PatternCategory.COMPLEX, default_bias=PatternBias.NEUTRAL,
            min_touches=5, min_candles=30, max_candles=300,
            symmetry_tolerance=0.30,
            description="5-wave impulse pattern"
        ))
        
        self._register(PatternDefinition(
            id="elliott_correction", name="Elliott Correction",
            category=PatternCategory.COMPLEX, default_bias=PatternBias.NEUTRAL,
            min_touches=3, min_candles=15, max_candles=150,
            symmetry_tolerance=0.30,
            description="ABC corrective wave"
        ))
        
        self._register(PatternDefinition(
            id="flat_correction", name="Flat Correction",
            category=PatternCategory.COMPLEX, default_bias=PatternBias.NEUTRAL,
            min_touches=3, min_candles=15, max_candles=100,
            symmetry_tolerance=0.20,
            description="3-3-5 flat corrective pattern"
        ))
        
        # ═══════════════════════════════════════════════════════════════
        # CANDLESTICK PATTERNS (15+)
        # ═══════════════════════════════════════════════════════════════
        
        self._register(PatternDefinition(
            id="bullish_engulfing", name="Bullish Engulfing",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BULLISH,
            min_touches=2, min_candles=2, max_candles=3,
            symmetry_tolerance=0.50, breakout_required=False,
            description="Large bull candle engulfs prior bear candle"
        ))
        
        self._register(PatternDefinition(
            id="bearish_engulfing", name="Bearish Engulfing",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BEARISH,
            min_touches=2, min_candles=2, max_candles=3,
            symmetry_tolerance=0.50, breakout_required=False,
            description="Large bear candle engulfs prior bull candle"
        ))
        
        self._register(PatternDefinition(
            id="hammer", name="Hammer",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BULLISH,
            min_touches=1, min_candles=1, max_candles=2,
            symmetry_tolerance=0.50, breakout_required=False,
            description="Long lower wick, small body at top"
        ))
        
        self._register(PatternDefinition(
            id="inverted_hammer", name="Inverted Hammer",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BULLISH,
            min_touches=1, min_candles=1, max_candles=2,
            symmetry_tolerance=0.50, breakout_required=False,
            description="Long upper wick, small body at bottom"
        ))
        
        self._register(PatternDefinition(
            id="shooting_star", name="Shooting Star",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BEARISH,
            min_touches=1, min_candles=1, max_candles=2,
            symmetry_tolerance=0.50, breakout_required=False,
            description="Long upper wick, small body at bottom - at top"
        ))
        
        self._register(PatternDefinition(
            id="hanging_man", name="Hanging Man",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BEARISH,
            min_touches=1, min_candles=1, max_candles=2,
            symmetry_tolerance=0.50, breakout_required=False,
            description="Hammer shape at top of uptrend"
        ))
        
        self._register(PatternDefinition(
            id="doji", name="Doji",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.NEUTRAL,
            min_touches=1, min_candles=1, max_candles=2,
            symmetry_tolerance=0.50, breakout_required=False,
            description="Open equals close - indecision"
        ))
        
        self._register(PatternDefinition(
            id="dragonfly_doji", name="Dragonfly Doji",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BULLISH,
            min_touches=1, min_candles=1, max_candles=2,
            symmetry_tolerance=0.50, breakout_required=False,
            description="Doji with long lower wick"
        ))
        
        self._register(PatternDefinition(
            id="gravestone_doji", name="Gravestone Doji",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BEARISH,
            min_touches=1, min_candles=1, max_candles=2,
            symmetry_tolerance=0.50, breakout_required=False,
            description="Doji with long upper wick"
        ))
        
        self._register(PatternDefinition(
            id="morning_star", name="Morning Star",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BULLISH,
            min_touches=3, min_candles=3, max_candles=5,
            symmetry_tolerance=0.40, breakout_required=False,
            description="3-candle bullish reversal"
        ))
        
        self._register(PatternDefinition(
            id="evening_star", name="Evening Star",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BEARISH,
            min_touches=3, min_candles=3, max_candles=5,
            symmetry_tolerance=0.40, breakout_required=False,
            description="3-candle bearish reversal"
        ))
        
        self._register(PatternDefinition(
            id="three_white_soldiers", name="Three White Soldiers",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BULLISH,
            min_touches=3, min_candles=3, max_candles=4,
            symmetry_tolerance=0.30, breakout_required=False,
            description="Three consecutive bull candles"
        ))
        
        self._register(PatternDefinition(
            id="three_black_crows", name="Three Black Crows",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BEARISH,
            min_touches=3, min_candles=3, max_candles=4,
            symmetry_tolerance=0.30, breakout_required=False,
            description="Three consecutive bear candles"
        ))
        
        self._register(PatternDefinition(
            id="inside_bar", name="Inside Bar",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.NEUTRAL,
            min_touches=2, min_candles=2, max_candles=3,
            symmetry_tolerance=0.50, breakout_required=False,
            description="Current candle inside prior candle range"
        ))
        
        self._register(PatternDefinition(
            id="outside_bar", name="Outside Bar",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.NEUTRAL,
            min_touches=2, min_candles=2, max_candles=3,
            symmetry_tolerance=0.50, breakout_required=False,
            description="Current candle engulfs prior candle range"
        ))
        
        self._register(PatternDefinition(
            id="pin_bar", name="Pin Bar",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.NEUTRAL,
            min_touches=1, min_candles=1, max_candles=2,
            symmetry_tolerance=0.50, breakout_required=False,
            description="Long wick, small body - rejection"
        ))
        
        self._register(PatternDefinition(
            id="tweezer_top", name="Tweezer Top",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BEARISH,
            min_touches=2, min_candles=2, max_candles=3,
            symmetry_tolerance=0.40, breakout_required=False,
            description="Two candles with matching highs"
        ))
        
        self._register(PatternDefinition(
            id="tweezer_bottom", name="Tweezer Bottom",
            category=PatternCategory.CANDLESTICK, default_bias=PatternBias.BULLISH,
            min_touches=2, min_candles=2, max_candles=3,
            symmetry_tolerance=0.40, breakout_required=False,
            description="Two candles with matching lows"
        ))
    
    def _register(self, pattern: PatternDefinition):
        """Register a pattern definition."""
        self._patterns[pattern.id] = pattern
    
    def get(self, pattern_id: str) -> Optional[PatternDefinition]:
        """Get pattern by ID."""
        return self._patterns.get(pattern_id)
    
    def get_all(self) -> List[PatternDefinition]:
        """Get all patterns."""
        return list(self._patterns.values())
    
    def get_by_category(self, category: PatternCategory) -> List[PatternDefinition]:
        """Get patterns by category."""
        return [p for p in self._patterns.values() if p.category == category]
    
    def count(self) -> int:
        """Total registered patterns."""
        return len(self._patterns)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export registry as dict."""
        return {
            "total": self.count(),
            "reversal": [p.to_dict() for p in self.get_by_category(PatternCategory.REVERSAL)],
            "continuation": [p.to_dict() for p in self.get_by_category(PatternCategory.CONTINUATION)],
            "harmonic": [p.to_dict() for p in self.get_by_category(PatternCategory.HARMONIC)],
            "candlestick": [p.to_dict() for p in self.get_by_category(PatternCategory.CANDLESTICK)],
            "complex": [p.to_dict() for p in self.get_by_category(PatternCategory.COMPLEX)],
        }


# Singleton
_registry: Optional[PatternFigureRegistry] = None


def get_pattern_figure_registry() -> PatternFigureRegistry:
    global _registry
    if _registry is None:
        _registry = PatternFigureRegistry()
    return _registry
