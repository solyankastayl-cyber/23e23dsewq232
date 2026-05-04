"""
Parallel Family Detector
========================

CLOSES 6 PATTERNS AT ONCE:
- ascending_channel
- descending_channel  
- horizontal_channel
- bull_flag
- bear_flag
- pennant

ALL use the same geometric primitive: PARALLEL LINES
(or nearly parallel for flags/pennants)

DIFFERENCE FROM CONVERGING:
- Converging: lines meet at apex
- Parallel: lines stay same distance apart (or nearly so)

KEY GEOMETRY:
- Two trendlines with SIMILAR slopes
- Price bouncing between them
- Minimum 2 touches on each line
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import statistics

from .swing_engine import SwingPoint, get_swing_engine
from .geometry_engine import get_geometry_engine
from .pattern_family_matrix import PatternFamily, PatternBias
from ..pole_builder import build_pole_from_candles, validate_flag_against_pole, get_flag_target


@dataclass
class ParallelPattern:
    """Detected parallel pattern (channel/flag/pennant)."""
    type: str
    family: str = "parallel"
    bias: str = "neutral"
    confidence: float = 0.0
    
    # Trendlines
    upper_line: Dict = None   # {slope, intercept, touches, start, end}
    lower_line: Dict = None   # {slope, intercept, touches, start, end}
    
    # Key levels
    channel_top: float = None
    channel_bottom: float = None
    channel_width: float = None
    
    # For targets
    target: float = None
    breakout_level: float = None
    breakdown_level: float = None
    
    # Window info (for validator)
    start_index: int = None
    end_index: int = None
    window: Dict = None
    
    # Touch points for rendering
    upper_touches: List[Dict] = None
    lower_touches: List[Dict] = None
    
    # Prior trend (for flags)
    prior_trend: str = None  # "up" or "down"
    pole_height: float = None
    pole: Dict = None  # Full pole data for rendering
    
    def __post_init__(self):
        if self.window is None and self.start_index is not None and self.end_index is not None:
            self.window = {
                "start_index": self.start_index,
                "end_index": self.end_index,
                "length": self.end_index - self.start_index
            }
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "family": self.family,
            "bias": self.bias,
            "confidence": round(self.confidence, 3),
            "upper_line": self.upper_line,
            "lower_line": self.lower_line,
            "channel_top": round(self.channel_top, 2) if self.channel_top else None,
            "channel_bottom": round(self.channel_bottom, 2) if self.channel_bottom else None,
            "channel_width": round(self.channel_width, 4) if self.channel_width else None,
            "target": round(self.target, 2) if self.target else None,
            "breakout_level": round(self.breakout_level, 2) if self.breakout_level else None,
            "breakdown_level": round(self.breakdown_level, 2) if self.breakdown_level else None,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "window": self.window,
            "upper_touches": self.upper_touches,
            "lower_touches": self.lower_touches,
            "prior_trend": self.prior_trend,
            "pole_height": round(self.pole_height, 2) if self.pole_height else None,
            "pole": self.pole,  # Full pole data for rendering
        }


class ParallelFamilyDetector:
    """
    Detects ALL parallel patterns using trendline geometry.
    
    ALGORITHM:
    1. Find swing highs/lows
    2. Fit trendlines to highs and lows separately
    3. Check if slopes are similar (parallel)
    4. Classify based on slope direction and context
    
    Config:
    - slope_tolerance: max difference in slopes for "parallel" (default 0.15)
    - min_touches: minimum touches per line (default 2)
    - min_bars: minimum pattern width in bars (default 8)
    - max_bars: maximum pattern width (default 60)
    """
    
    def __init__(self, config: Dict = None):
        config = config or {}
        
        self.slope_tolerance = config.get("slope_tolerance", 0.15)  # 15% difference
        self.min_touches = config.get("min_touches", 2)
        self.min_bars = config.get("min_bars", 8)
        self.max_bars = config.get("max_bars", 60)
        self.min_width_pct = config.get("min_width_pct", 0.02)  # 2% channel width
        self.max_width_pct = config.get("max_width_pct", 0.15)  # 15% max width
        
        self.swing_engine = get_swing_engine(config.get("swing_config"))
        self.geometry_engine = get_geometry_engine()
    
    def detect(
        self,
        candles: List[Dict],
        swing_highs: List[SwingPoint] = None,
        swing_lows: List[SwingPoint] = None
    ) -> List[ParallelPattern]:
        """
        Detect all parallel family patterns.
        
        Returns list of candidates sorted by confidence.
        """
        if swing_highs is None or swing_lows is None:
            swing_highs, swing_lows = self.swing_engine.find_swings(candles)
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return []
        
        candidates = []
        
        # Try to detect channels
        channel = self._detect_channel(candles, swing_highs, swing_lows)
        if channel:
            candidates.append(channel)
        
        # Try to detect flags (need prior trend)
        flag = self._detect_flag(candles, swing_highs, swing_lows)
        if flag:
            candidates.append(flag)
        
        # Try to detect pennant
        pennant = self._detect_pennant(candles, swing_highs, swing_lows)
        if pennant:
            candidates.append(pennant)
        
        # Sort by confidence
        candidates.sort(key=lambda p: p.confidence, reverse=True)
        
        return candidates
    
    # =========================================================================
    # CHANNEL DETECTION
    # =========================================================================
    
    def _detect_channel(
        self,
        candles: List[Dict],
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint]
    ) -> Optional[ParallelPattern]:
        """
        Detect ascending/descending/horizontal channel.
        
        RULES:
        - Two parallel trendlines
        - At least 2 touches on each
        - Slope determines type (up/down/horizontal)
        """
        # Use recent swings (last N)
        lookback = min(len(candles), 50)
        recent_highs = [h for h in swing_highs if h.index >= len(candles) - lookback]
        recent_lows = [low for low in swing_lows if low.index >= len(candles) - lookback]
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        # Fit trendlines
        upper_line = self._fit_trendline(recent_highs, candles)
        lower_line = self._fit_trendline(recent_lows, candles)
        
        if not upper_line or not lower_line:
            return None
        
        # Check if parallel
        slope_diff = abs(upper_line["slope"] - lower_line["slope"])
        avg_slope = (abs(upper_line["slope"]) + abs(lower_line["slope"])) / 2
        
        # Normalize slope difference
        if avg_slope > 0.0001:
            parallelism = slope_diff / avg_slope
        else:
            parallelism = slope_diff  # Both nearly horizontal
        
        if parallelism > self.slope_tolerance:
            return None  # Not parallel enough
        
        # Check minimum touches
        if upper_line["touches"] < self.min_touches or lower_line["touches"] < self.min_touches:
            return None
        
        # Calculate channel properties
        current_price = candles[-1].get("close", 0)
        current_idx = len(candles) - 1
        
        # Get current channel boundaries
        channel_top = upper_line["slope"] * current_idx + upper_line["intercept"]
        channel_bottom = lower_line["slope"] * current_idx + lower_line["intercept"]
        channel_width = (channel_top - channel_bottom) / current_price if current_price > 0 else 0
        
        # Validate width
        if channel_width < self.min_width_pct or channel_width > self.max_width_pct:
            return None
        
        # Determine channel type based on average slope
        avg_slope_val = (upper_line["slope"] + lower_line["slope"]) / 2
        slope_normalized = avg_slope_val / current_price if current_price > 0 else avg_slope_val
        
        if slope_normalized > 0.0005:  # Ascending
            channel_type = "ascending_channel"
            bias = "bullish"
            target = channel_top + (channel_top - channel_bottom)  # Breakout target
        elif slope_normalized < -0.0005:  # Descending
            channel_type = "descending_channel"
            bias = "bearish"
            target = channel_bottom - (channel_top - channel_bottom)  # Breakdown target
        else:  # Horizontal
            channel_type = "horizontal_channel"
            bias = "neutral"
            target = None
        
        # Calculate confidence
        touch_score = min((upper_line["touches"] + lower_line["touches"]) / 6, 1.0)
        parallel_score = 1 - (parallelism / self.slope_tolerance) if self.slope_tolerance > 0 else 1.0
        width_score = min(channel_width / 0.05, 1.0)  # 5% width = max score
        
        confidence = min(touch_score * 0.4 + parallel_score * 0.4 + width_score * 0.2, 0.92)
        
        # Get touch points for rendering
        upper_touches = [{"index": h.index, "time": h.timestamp, "price": h.price} for h in recent_highs[-4:]]
        lower_touches = [{"index": low.index, "time": low.timestamp, "price": low.price} for low in recent_lows[-4:]]
        
        # Window
        start_idx = min(recent_highs[0].index, recent_lows[0].index)
        end_idx = max(recent_highs[-1].index, recent_lows[-1].index)
        
        return ParallelPattern(
            type=channel_type,
            bias=bias,
            confidence=confidence,
            upper_line={
                "slope": upper_line["slope"],
                "intercept": upper_line["intercept"],
                "touches": upper_line["touches"],
                "start_time": upper_touches[0]["time"] if upper_touches else None,
                "end_time": upper_touches[-1]["time"] if upper_touches else None,
            },
            lower_line={
                "slope": lower_line["slope"],
                "intercept": lower_line["intercept"],
                "touches": lower_line["touches"],
                "start_time": lower_touches[0]["time"] if lower_touches else None,
                "end_time": lower_touches[-1]["time"] if lower_touches else None,
            },
            channel_top=channel_top,
            channel_bottom=channel_bottom,
            channel_width=channel_width,
            target=target,
            breakout_level=channel_top,
            breakdown_level=channel_bottom,
            start_index=start_idx,
            end_index=end_idx,
            upper_touches=upper_touches,
            lower_touches=lower_touches,
        )
    
    # =========================================================================
    # FLAG DETECTION
    # =========================================================================
    
    def _detect_flag(
        self,
        candles: List[Dict],
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint]
    ) -> Optional[ParallelPattern]:
        """
        Detect bull/bear flag.
        
        FLAG RULES:
        - Strong prior move (the "pole")
        - Consolidation channel against the trend
        - Parallel boundaries
        - Typically 5-25 bars
        
        BULL FLAG: up pole + down-sloping or horizontal channel
        BEAR FLAG: down pole + up-sloping or horizontal channel
        """
        if len(candles) < 30:
            return None
        
        # Look for recent consolidation (last 20 bars)
        consolidation_window = 20
        pole_window = 15
        
        recent_highs = [h for h in swing_highs if h.index >= len(candles) - consolidation_window]
        recent_lows = [low for low in swing_lows if low.index >= len(candles) - consolidation_window]
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        # Fit trendlines for consolidation
        upper_line = self._fit_trendline(recent_highs, candles)
        lower_line = self._fit_trendline(recent_lows, candles)
        
        if not upper_line or not lower_line:
            return None
        
        # Check parallelism
        slope_diff = abs(upper_line["slope"] - lower_line["slope"])
        avg_slope = (abs(upper_line["slope"]) + abs(lower_line["slope"])) / 2
        
        if avg_slope > 0.0001:
            parallelism = slope_diff / avg_slope
        else:
            parallelism = slope_diff
        
        if parallelism > self.slope_tolerance * 1.5:  # Slightly more lenient for flags
            return None
        
        # Check for prior pole (strong move before consolidation)
        pole_start = len(candles) - consolidation_window - pole_window
        if pole_start < 0:
            pole_start = 0
        
        pole_end = len(candles) - consolidation_window
        
        pole_candles = candles[pole_start:pole_end]
        if len(pole_candles) < 5:
            return None
        
        pole_start_price = pole_candles[0].get("close", 0)
        pole_end_price = pole_candles[-1].get("close", 0)
        
        if pole_start_price <= 0:
            return None
        
        pole_move = (pole_end_price - pole_start_price) / pole_start_price
        
        # Need at least 5% move for a valid pole
        if abs(pole_move) < 0.05:
            return None
        
        # Use pole_builder for better pole detection
        consolidation_start = len(candles) - consolidation_window
        pole = build_pole_from_candles(candles, consolidation_start, lookback=20, min_move_pct=0.03)
        
        # Determine flag type
        avg_slope_val = (upper_line["slope"] + lower_line["slope"]) / 2
        current_price = candles[-1].get("close", 0)
        slope_normalized = avg_slope_val / current_price if current_price > 0 else 0
        
        # Validate flag against pole using pole_builder
        if pole and not validate_flag_against_pole(pole, slope_normalized):
            return None
        
        if pole_move > 0:  # Up pole
            # Bull flag: consolidation should be down-sloping or flat
            if slope_normalized > 0.0003:  # Consolidation sloping up too much
                return None
            
            flag_type = "bull_flag"
            bias = "bullish"
            prior_trend = "up"
            
            # Target = breakout + pole height
            channel_top = upper_line["slope"] * (len(candles) - 1) + upper_line["intercept"]
            target = get_flag_target(pole, channel_top) if pole else channel_top + abs(pole_move * pole_start_price)
            
        else:  # Down pole
            # Bear flag: consolidation should be up-sloping or flat
            if slope_normalized < -0.0003:  # Consolidation sloping down too much
                return None
            
            flag_type = "bear_flag"
            bias = "bearish"
            prior_trend = "down"
            
            # Target = breakdown - pole height
            channel_bottom = lower_line["slope"] * (len(candles) - 1) + lower_line["intercept"]
            target = get_flag_target(pole, channel_bottom) if pole else channel_bottom - abs(pole_move * pole_start_price)
        
        # Calculate confidence
        pole_strength = min(abs(pole_move) / 0.10, 1.0)  # 10% move = max
        parallel_score = 1 - (parallelism / (self.slope_tolerance * 1.5))
        touch_score = min((upper_line["touches"] + lower_line["touches"]) / 5, 1.0)
        
        confidence = min(pole_strength * 0.4 + parallel_score * 0.3 + touch_score * 0.3, 0.92)
        
        # Get touch points
        upper_touches = [{"index": h.index, "time": h.timestamp, "price": h.price} for h in recent_highs[-3:]]
        lower_touches = [{"index": low.index, "time": low.timestamp, "price": low.price} for low in recent_lows[-3:]]
        
        # Window
        start_idx = min(h.index for h in recent_highs) if recent_highs else len(candles) - consolidation_window
        end_idx = len(candles) - 1
        
        channel_top = upper_line["slope"] * (len(candles) - 1) + upper_line["intercept"]
        channel_bottom = lower_line["slope"] * (len(candles) - 1) + lower_line["intercept"]
        
        return ParallelPattern(
            type=flag_type,
            bias=bias,
            confidence=confidence,
            upper_line={
                "slope": upper_line["slope"],
                "intercept": upper_line["intercept"],
                "touches": upper_line["touches"],
            },
            lower_line={
                "slope": lower_line["slope"],
                "intercept": lower_line["intercept"],
                "touches": lower_line["touches"],
            },
            channel_top=channel_top,
            channel_bottom=channel_bottom,
            channel_width=(channel_top - channel_bottom) / current_price if current_price > 0 else 0,
            target=target,
            breakout_level=channel_top if bias == "bullish" else None,
            breakdown_level=channel_bottom if bias == "bearish" else None,
            start_index=start_idx,
            end_index=end_idx,
            upper_touches=upper_touches,
            lower_touches=lower_touches,
            prior_trend=prior_trend,
            pole_height=pole.get("height") if pole else abs(pole_move * pole_start_price),
            pole=pole,  # Include full pole data for SVG rendering
        )
    
    # =========================================================================
    # PENNANT DETECTION
    # =========================================================================
    
    def _detect_pennant(
        self,
        candles: List[Dict],
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint]
    ) -> Optional[ParallelPattern]:
        """
        Detect pennant (small symmetrical triangle after strong move).
        
        PENNANT = POLE + SYMMETRICAL TRIANGLE
        
        Difference from flag:
        - Flag: parallel lines
        - Pennant: converging lines (like mini triangle)
        
        But still part of parallel family because it follows same pole logic.
        """
        if len(candles) < 25:
            return None
        
        # Look for recent tight consolidation
        consolidation_window = 15
        pole_window = 10
        
        recent_highs = [h for h in swing_highs if h.index >= len(candles) - consolidation_window]
        recent_lows = [low for low in swing_lows if low.index >= len(candles) - consolidation_window]
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return None
        
        # Fit trendlines
        upper_line = self._fit_trendline(recent_highs, candles)
        lower_line = self._fit_trendline(recent_lows, candles)
        
        if not upper_line or not lower_line:
            return None
        
        # For pennant, lines should be CONVERGING (opposite slopes)
        if upper_line["slope"] * lower_line["slope"] > 0:  # Same direction = not converging
            return None
        
        # Upper should be down, lower should be up (or close to it)
        if upper_line["slope"] > 0.0001 or lower_line["slope"] < -0.0001:
            return None  # Not converging properly
        
        # Check for prior pole
        pole_start = len(candles) - consolidation_window - pole_window
        if pole_start < 0:
            pole_start = 0
        
        pole_end = len(candles) - consolidation_window
        pole_candles = candles[pole_start:pole_end]
        
        if len(pole_candles) < 3:
            return None
        
        pole_start_price = pole_candles[0].get("close", 0)
        pole_end_price = pole_candles[-1].get("close", 0)
        
        if pole_start_price <= 0:
            return None
        
        pole_move = (pole_end_price - pole_start_price) / pole_start_price
        
        # Need at least 5% move
        if abs(pole_move) < 0.05:
            return None
        
        # Determine direction
        if pole_move > 0:
            bias = "bullish"
            prior_trend = "up"
        else:
            bias = "bearish"
            prior_trend = "down"
        
        # Calculate confidence
        pole_strength = min(abs(pole_move) / 0.08, 1.0)
        convergence = abs(upper_line["slope"]) + abs(lower_line["slope"])
        convergence_score = min(convergence / 0.001, 1.0)
        
        confidence = min(pole_strength * 0.5 + convergence_score * 0.3 + 0.2, 0.85)
        
        # Get current levels
        current_idx = len(candles) - 1
        channel_top = upper_line["slope"] * current_idx + upper_line["intercept"]
        channel_bottom = lower_line["slope"] * current_idx + lower_line["intercept"]
        current_price = candles[-1].get("close", 0)
        
        # Target
        target = current_price + (pole_move * pole_start_price) if bias == "bullish" else current_price - abs(pole_move * pole_start_price)
        
        upper_touches = [{"index": h.index, "time": h.timestamp, "price": h.price} for h in recent_highs[-3:]]
        lower_touches = [{"index": low.index, "time": low.timestamp, "price": low.price} for low in recent_lows[-3:]]
        
        return ParallelPattern(
            type="pennant",
            bias=bias,
            confidence=confidence,
            upper_line={
                "slope": upper_line["slope"],
                "intercept": upper_line["intercept"],
                "touches": upper_line["touches"],
            },
            lower_line={
                "slope": lower_line["slope"],
                "intercept": lower_line["intercept"],
                "touches": lower_line["touches"],
            },
            channel_top=channel_top,
            channel_bottom=channel_bottom,
            channel_width=(channel_top - channel_bottom) / current_price if current_price > 0 else 0,
            target=target,
            breakout_level=channel_top if bias == "bullish" else None,
            breakdown_level=channel_bottom if bias == "bearish" else None,
            start_index=len(candles) - consolidation_window,
            end_index=len(candles) - 1,
            upper_touches=upper_touches,
            lower_touches=lower_touches,
            prior_trend=prior_trend,
            pole_height=abs(pole_move * pole_start_price),
        )
    
    # =========================================================================
    # HELPER: Fit Trendline
    # =========================================================================
    
    def _fit_trendline(
        self,
        points: List[SwingPoint],
        candles: List[Dict]
    ) -> Optional[Dict]:
        """
        Fit a linear trendline to swing points.
        
        Returns: {slope, intercept, touches, r_squared}
        """
        if len(points) < 2:
            return None
        
        # Use linear regression
        x = [p.index for p in points]
        y = [p.price for p in points]
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(xi ** 2 for xi in x)
        
        denom = n * sum_x2 - sum_x ** 2
        if abs(denom) < 0.0001:
            return None
        
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        
        # Count touches (points within 1% of line)
        touches = 0
        for p in points:
            line_price = slope * p.index + intercept
            if p.price > 0:
                deviation = abs(p.price - line_price) / p.price
                if deviation < 0.01:  # Within 1%
                    touches += 1
        
        return {
            "slope": slope,
            "intercept": intercept,
            "touches": touches,
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_parallel_detector = None

def get_parallel_family_detector(config: Dict = None) -> ParallelFamilyDetector:
    """Get parallel family detector instance."""
    global _parallel_detector
    if _parallel_detector is None or config:
        _parallel_detector = ParallelFamilyDetector(config)
    return _parallel_detector
