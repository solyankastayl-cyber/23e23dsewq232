"""
Converging Family Detector
==========================

CLOSES 5 PATTERNS AT ONCE:
- symmetrical_triangle
- ascending_triangle
- descending_triangle
- rising_wedge
- falling_wedge

ALL use the same geometric primitive: CONVERGING LINES (narrowing range)
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .swing_engine import SwingEngine, SwingPoint, get_swing_engine
from .geometry_engine import GeometryEngine, GeometryResult, LineRelation, get_geometry_engine


@dataclass
class ConvergingPattern:
    """Detected converging pattern (triangle/wedge)."""
    type: str
    family: str = "converging"
    bias: str = "neutral"
    confidence: float = 0.0
    
    # Lines
    upper_line: Dict = None      # {start, end, slope}
    lower_line: Dict = None
    
    # Key levels
    apex_index: int = None       # Where lines meet
    apex_price: float = None
    breakout_zone: float = None
    
    # Compression
    compression_ratio: float = 0  # 0-1, how much narrowing
    width_start: float = None
    width_end: float = None
    
    # Swings used
    swing_highs: List[Dict] = None
    swing_lows: List[Dict] = None
    
    # Metadata
    start_index: int = None
    end_index: int = None
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "family": self.family,
            "bias": self.bias,
            "confidence": round(self.confidence, 2),
            "upper_line": self.upper_line,
            "lower_line": self.lower_line,
            "apex_index": self.apex_index,
            "apex_price": round(self.apex_price, 2) if self.apex_price else None,
            "breakout_zone": round(self.breakout_zone, 2) if self.breakout_zone else None,
            "compression_ratio": round(self.compression_ratio, 3),
            "width_start": round(self.width_start, 2) if self.width_start else None,
            "width_end": round(self.width_end, 2) if self.width_end else None,
            "swing_highs": self.swing_highs,
            "swing_lows": self.swing_lows,
            "start_index": self.start_index,
            "end_index": self.end_index,
        }


class ConvergingFamilyDetector:
    """
    Detects ALL converging patterns using unified geometry.
    
    Key insight: ALL converging patterns are just variations of:
    - Upper line slope
    - Lower line slope
    - How they converge
    
    Config thresholds:
    - min_compression: minimum 15% narrowing
    - min_swings: at least 2 touches per line
    - horizontal_threshold: slope considered "flat"
    """
    
    def __init__(self, config: Dict = None):
        config = config or {}
        
        self.min_compression = config.get("min_compression", 0.15)       # 15% minimum
        self.min_swings = config.get("min_swings", 2)                     # 2 per side
        self.horizontal_threshold = config.get("horizontal_threshold", 0.001)
        self.slope_threshold = config.get("slope_threshold", 0.002)      # For wedge detection
        
        self.swing_engine = get_swing_engine(config.get("swing_config"))
        self.geometry_engine = get_geometry_engine(config)
    
    def detect(
        self,
        candles: List[Dict],
        swing_highs: List[SwingPoint] = None,
        swing_lows: List[SwingPoint] = None
    ) -> List[ConvergingPattern]:
        """
        Detect all converging family patterns.
        
        Returns list of candidates sorted by confidence.
        """
        if swing_highs is None or swing_lows is None:
            swing_highs, swing_lows = self.swing_engine.find_swings(candles)
        
        if len(swing_highs) < self.min_swings or len(swing_lows) < self.min_swings:
            return []
        
        # Get recent swings
        recent_highs = swing_highs[-5:]
        recent_lows = swing_lows[-5:]
        
        # Analyze geometry
        geometry = self.geometry_engine.analyze_geometry(recent_highs, recent_lows, candles)
        
        if not geometry:
            return []
        
        # Check if there's compression
        if geometry.compression_ratio < self.min_compression:
            return []
        
        candidates = []
        
        # Classify based on slope combination
        upper_slope = geometry.upper_line.slope if geometry.upper_line else 0
        lower_slope = geometry.lower_line.slope if geometry.lower_line else 0
        
        pattern = self._classify_converging_pattern(
            upper_slope, 
            lower_slope, 
            geometry,
            recent_highs,
            recent_lows,
            candles
        )
        
        if pattern:
            candidates.append(pattern)
        
        return candidates
    
    def _classify_converging_pattern(
        self,
        upper_slope: float,
        lower_slope: float,
        geometry: GeometryResult,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        candles: List[Dict]
    ) -> Optional[ConvergingPattern]:
        """
        Classify the converging pattern based on slopes.
        
        Rules:
        - Symmetrical: both slopes converging toward each other
        - Ascending: flat top, rising bottom
        - Descending: rising top (less), flat bottom
        - Rising Wedge: both rising, but converging
        - Falling Wedge: both falling, but converging
        """
        upper_is_flat = self._is_flat(upper_slope)
        lower_is_flat = self._is_flat(lower_slope)
        upper_is_rising = upper_slope > self.slope_threshold
        upper_is_falling = upper_slope < -self.slope_threshold
        lower_is_rising = lower_slope > self.slope_threshold
        lower_is_falling = lower_slope < -self.slope_threshold
        
        # Determine pattern type
        if upper_is_flat and lower_is_rising:
            pattern_type = "ascending_triangle"
            bias = "bullish"
            confidence_bonus = 0.1
        
        elif lower_is_flat and upper_is_falling:
            pattern_type = "descending_triangle"
            bias = "bearish"
            confidence_bonus = 0.1
        
        elif upper_is_rising and lower_is_rising:
            # Both rising but upper less steep = rising wedge
            if upper_slope < lower_slope:
                pattern_type = "rising_wedge"
                bias = "bearish"
                confidence_bonus = 0.05
            else:
                return None  # Diverging, not converging
        
        elif upper_is_falling and lower_is_falling:
            # Both falling but lower less steep = falling wedge
            if upper_slope < lower_slope:
                pattern_type = "falling_wedge"
                bias = "bullish"
                confidence_bonus = 0.05
            else:
                return None
        
        elif upper_is_falling and lower_is_rising:
            pattern_type = "symmetrical_triangle"
            bias = "neutral"
            confidence_bonus = 0.15  # Most reliable
        
        else:
            # Generic triangle
            pattern_type = "symmetrical_triangle"
            bias = "neutral"
            confidence_bonus = 0
        
        # Calculate confidence
        compression_score = min(geometry.compression_ratio / 0.3, 1.0)  # 30% compression = max
        symmetry_score = geometry.symmetry_score
        touches = min(len(swing_highs), len(swing_lows))
        touch_score = min(touches / 4, 1.0)  # 4 touches per side = max
        
        confidence = (
            compression_score * 0.35 +
            symmetry_score * 0.25 +
            touch_score * 0.25 +
            confidence_bonus +
            0.15  # Base
        )
        
        # CRITICAL: NEVER 100% confidence - max 0.92
        confidence = min(confidence, 0.92)
        
        # Calculate apex
        apex_price = None
        if geometry.apex_index and geometry.upper_line and geometry.lower_line:
            apex_price = geometry.upper_line.price_at(geometry.apex_index)
        
        # Current price position
        current_price = candles[-1].get("close", 0)
        breakout_zone = geometry.upper_line.price_at(len(candles) - 1) if geometry.upper_line else current_price
        
        return ConvergingPattern(
            type=pattern_type,
            bias=bias,
            confidence=confidence,
            upper_line={
                "start": swing_highs[0].to_dict(),
                "end": swing_highs[-1].to_dict(),
                "slope": round(upper_slope, 6),
            } if geometry.upper_line else None,
            lower_line={
                "start": swing_lows[0].to_dict(),
                "end": swing_lows[-1].to_dict(),
                "slope": round(lower_slope, 6),
            } if geometry.lower_line else None,
            apex_index=geometry.apex_index,
            apex_price=apex_price,
            breakout_zone=breakout_zone,
            compression_ratio=geometry.compression_ratio,
            width_start=geometry.width_start,
            width_end=geometry.width_end,
            swing_highs=[h.to_dict() for h in swing_highs],
            swing_lows=[l.to_dict() for l in swing_lows],
            start_index=min(swing_highs[0].index, swing_lows[0].index),
            end_index=max(swing_highs[-1].index, swing_lows[-1].index),
        )
    
    def _is_flat(self, slope: float) -> bool:
        """Check if slope is approximately flat."""
        return abs(slope) <= self.horizontal_threshold


# Singleton
_converging_detector = None

def get_converging_family_detector(config: Dict = None) -> ConvergingFamilyDetector:
    global _converging_detector
    if _converging_detector is None or config:
        _converging_detector = ConvergingFamilyDetector(config)
    return _converging_detector
