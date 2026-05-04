"""
Geometry Engine — Unified Geometric Rules
==========================================

ONE engine for ALL geometric relationships:
- equal_highs / equal_lows
- parallel lines
- converging lines
- slope calculation
- compression detection
- symmetry check

Used by ALL pattern families.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math

from .swing_engine import SwingPoint


class LineRelation(Enum):
    HORIZONTAL = "horizontal"      # flat
    PARALLEL_UP = "parallel_up"    # both ascending
    PARALLEL_DOWN = "parallel_down"  # both descending
    CONVERGING = "converging"      # narrowing
    DIVERGING = "diverging"        # widening


@dataclass
class TrendLine:
    """A trend line through swing points."""
    start_point: SwingPoint
    end_point: SwingPoint
    slope: float           # price change per bar
    slope_angle: float     # degrees
    touches: int
    strength: float        # 0-1
    
    def price_at(self, index: int) -> float:
        """Get price on line at given index."""
        bars_from_start = index - self.start_point.index
        return self.start_point.price + (self.slope * bars_from_start)
    
    def to_dict(self) -> Dict:
        return {
            "start": self.start_point.to_dict(),
            "end": self.end_point.to_dict(),
            "slope": round(self.slope, 6),
            "slope_angle": round(self.slope_angle, 2),
            "touches": self.touches,
            "strength": round(self.strength, 3),
        }


@dataclass
class GeometryResult:
    """Result of geometry analysis."""
    relation: LineRelation
    upper_line: Optional[TrendLine]
    lower_line: Optional[TrendLine]
    compression_ratio: float    # 0-1, how much narrowing
    symmetry_score: float       # 0-1, how symmetric
    width_start: float          # range width at start
    width_end: float            # range width at end
    apex_index: Optional[int]   # where lines meet (for triangles)
    
    def to_dict(self) -> Dict:
        return {
            "relation": self.relation.value,
            "upper_line": self.upper_line.to_dict() if self.upper_line else None,
            "lower_line": self.lower_line.to_dict() if self.lower_line else None,
            "compression_ratio": round(self.compression_ratio, 3),
            "symmetry_score": round(self.symmetry_score, 3),
            "width_start": round(self.width_start, 2),
            "width_end": round(self.width_end, 2),
            "apex_index": self.apex_index,
        }


class GeometryEngine:
    """
    Unified geometric analysis engine.
    
    Thresholds (all configurable):
    - equal_threshold: % difference for "equal" prices
    - parallel_threshold: slope difference for "parallel"
    - horizontal_threshold: slope for "flat"
    - min_compression: compression to qualify as converging
    """
    
    def __init__(self, config: Dict = None):
        config = config or {}
        
        # Core thresholds
        self.equal_threshold = config.get("equal_threshold", 0.02)       # 2%
        self.parallel_threshold = config.get("parallel_threshold", 0.3)  # slope diff
        self.horizontal_threshold = config.get("horizontal_threshold", 0.001)  # near zero slope
        self.min_compression = config.get("min_compression", 0.15)       # 15% narrowing
        self.min_touches = config.get("min_touches", 2)
    
    # =========================================================================
    # CORE GEOMETRIC CHECKS
    # =========================================================================
    
    def are_equal(self, price1: float, price2: float) -> bool:
        """Check if two prices are approximately equal."""
        if price1 == 0:
            return False
        diff = abs(price1 - price2) / price1
        return diff <= self.equal_threshold
    
    def are_equal_prices(self, prices: List[float], threshold: float = None) -> Tuple[bool, float]:
        """
        Check if list of prices are approximately equal.
        Returns (is_equal, variance_score 0-1)
        """
        threshold = threshold or self.equal_threshold
        
        if len(prices) < 2:
            return True, 1.0
        
        avg = sum(prices) / len(prices)
        if avg == 0:
            return False, 0.0
        
        max_diff = max(abs(p - avg) / avg for p in prices)
        variance = 1 - min(max_diff / threshold, 1.0) if threshold > 0 else 0
        
        return max_diff <= threshold, variance
    
    def calculate_slope(self, p1: SwingPoint, p2: SwingPoint) -> float:
        """Calculate slope between two points (price change per bar)."""
        bars = p2.index - p1.index
        if bars == 0:
            return 0
        return (p2.price - p1.price) / bars
    
    def calculate_slope_angle(self, slope: float, price_scale: float = 1000) -> float:
        """Calculate angle in degrees (normalized for price scale)."""
        normalized_slope = slope / price_scale if price_scale > 0 else slope
        return math.degrees(math.atan(normalized_slope))
    
    def is_horizontal(self, slope: float) -> bool:
        """Check if slope is approximately horizontal."""
        return abs(slope) <= self.horizontal_threshold
    
    def are_parallel(self, slope1: float, slope2: float) -> bool:
        """Check if two slopes are parallel."""
        if slope1 == 0 and slope2 == 0:
            return True
        avg = (abs(slope1) + abs(slope2)) / 2
        if avg == 0:
            return True
        diff = abs(slope1 - slope2) / avg
        return diff <= self.parallel_threshold
    
    def are_converging(self, upper_slope: float, lower_slope: float) -> bool:
        """Check if lines are converging (upper descending, lower ascending, or both)."""
        # Lines converge when upper slope < lower slope
        # e.g., upper = -0.5, lower = 0.3 → converging
        # e.g., upper = -0.2, lower = -0.5 → upper less negative, still converging
        return upper_slope < lower_slope
    
    # =========================================================================
    # TRENDLINE BUILDING
    # =========================================================================
    
    def build_trendline(
        self, 
        swings: List[SwingPoint],
        all_candles: List[Dict] = None
    ) -> Optional[TrendLine]:
        """Build best-fit trendline through swing points."""
        if len(swings) < 2:
            return None
        
        # Use first and last for slope
        start = swings[0]
        end = swings[-1]
        
        slope = self.calculate_slope(start, end)
        
        # Count touches (swings that are close to the line)
        touches = 0
        tolerance = abs(end.price - start.price) * 0.02  # 2% of range
        
        for swing in swings:
            expected = start.price + slope * (swing.index - start.index)
            if abs(swing.price - expected) <= tolerance:
                touches += 1
        
        # Strength based on touches and consistency
        strength = min(touches / len(swings), 1.0)
        
        return TrendLine(
            start_point=start,
            end_point=end,
            slope=slope,
            slope_angle=self.calculate_slope_angle(slope, start.price),
            touches=touches,
            strength=strength,
        )
    
    # =========================================================================
    # FULL GEOMETRY ANALYSIS
    # =========================================================================
    
    def analyze_geometry(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        candles: List[Dict] = None
    ) -> Optional[GeometryResult]:
        """
        Analyze geometric relationship between swing highs and lows.
        
        Returns GeometryResult with:
        - relation type (horizontal, parallel, converging, diverging)
        - upper/lower trendlines
        - compression ratio
        - symmetry score
        """
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        
        # Build trendlines
        upper_line = self.build_trendline(swing_highs, candles)
        lower_line = self.build_trendline(swing_lows, candles)
        
        if not upper_line or not lower_line:
            return None
        
        # Calculate widths
        # Use first and last points to measure compression
        first_high = swing_highs[0].price
        first_low = swing_lows[0].price
        last_high = swing_highs[-1].price
        last_low = swing_lows[-1].price
        
        width_start = first_high - first_low
        width_end = last_high - last_low
        
        # Compression ratio (0 = no compression, 1 = fully compressed)
        if width_start > 0:
            compression = 1 - (width_end / width_start)
            compression = max(0, min(compression, 1))  # Clamp 0-1
        else:
            compression = 0
        
        # Determine relation
        upper_slope = upper_line.slope
        lower_slope = lower_line.slope
        
        if self.is_horizontal(upper_slope) and self.is_horizontal(lower_slope):
            relation = LineRelation.HORIZONTAL
        elif self.are_parallel(upper_slope, lower_slope):
            relation = LineRelation.PARALLEL_UP if upper_slope > 0 else LineRelation.PARALLEL_DOWN
        elif self.are_converging(upper_slope, lower_slope):
            relation = LineRelation.CONVERGING
        else:
            relation = LineRelation.DIVERGING
        
        # Calculate apex (where lines meet) for converging patterns
        apex_index = None
        if relation == LineRelation.CONVERGING:
            # Solve for intersection: upper_start + upper_slope * x = lower_start + lower_slope * x
            slope_diff = lower_slope - upper_slope
            if abs(slope_diff) > 0.0001:
                price_diff = first_high - first_low
                bars_to_apex = price_diff / slope_diff
                apex_index = int(swing_highs[0].index + bars_to_apex)
        
        # Symmetry score (how balanced are upper and lower)
        symmetry = self._calculate_symmetry(swing_highs, swing_lows)
        
        return GeometryResult(
            relation=relation,
            upper_line=upper_line,
            lower_line=lower_line,
            compression_ratio=compression,
            symmetry_score=symmetry,
            width_start=width_start,
            width_end=width_end,
            apex_index=apex_index,
        )
    
    def _calculate_symmetry(
        self, 
        swing_highs: List[SwingPoint], 
        swing_lows: List[SwingPoint]
    ) -> float:
        """Calculate how symmetric the pattern is (0-1)."""
        # Compare number of touches
        count_diff = abs(len(swing_highs) - len(swing_lows))
        max_count = max(len(swing_highs), len(swing_lows))
        count_symmetry = 1 - (count_diff / max_count) if max_count > 0 else 0
        
        # Compare spacing consistency
        high_spacing = self._average_spacing(swing_highs)
        low_spacing = self._average_spacing(swing_lows)
        
        if high_spacing > 0 and low_spacing > 0:
            spacing_ratio = min(high_spacing, low_spacing) / max(high_spacing, low_spacing)
        else:
            spacing_ratio = 0.5
        
        return (count_symmetry * 0.5 + spacing_ratio * 0.5)
    
    def _average_spacing(self, swings: List[SwingPoint]) -> float:
        """Calculate average bar spacing between swings."""
        if len(swings) < 2:
            return 0
        
        spacings = []
        for i in range(1, len(swings)):
            spacings.append(swings[i].index - swings[i-1].index)
        
        return sum(spacings) / len(spacings) if spacings else 0
    
    # =========================================================================
    # SPECIFIC GEOMETRY CHECKS
    # =========================================================================
    
    def check_double_formation(
        self, 
        peaks: List[SwingPoint],
        valley_between: Optional[SwingPoint] = None,
        formation_type: str = "top"  # "top" or "bottom"
    ) -> Dict:
        """
        Check if peaks form a valid double top/bottom.
        
        Returns:
        - valid: bool
        - price_equality: 0-1 (how equal the peaks are)
        - depth: % pullback between peaks
        - spacing: bars between peaks
        """
        if len(peaks) < 2:
            return {"valid": False, "reason": "need_2_peaks"}
        
        p1, p2 = peaks[-2], peaks[-1]
        
        # Price equality
        prices_equal, equality_score = self.are_equal_prices([p1.price, p2.price])
        
        # For double top: second peak should not be significantly higher
        # For double bottom: second peak should not be significantly lower
        if formation_type == "top" and p2.price > p1.price * (1 + self.equal_threshold):
            return {"valid": False, "reason": "second_peak_higher"}
        if formation_type == "bottom" and p2.price < p1.price * (1 - self.equal_threshold):
            return {"valid": False, "reason": "second_peak_lower"}
        
        # Depth (pullback between peaks)
        depth = 0
        if valley_between:
            if formation_type == "top":
                depth = (p1.price - valley_between.price) / p1.price
            else:
                depth = (valley_between.price - p1.price) / p1.price
        
        # Spacing
        spacing = p2.index - p1.index
        
        # Minimum requirements
        min_depth = 0.02  # 2% minimum pullback
        min_spacing = 5   # minimum 5 bars apart
        
        valid = (
            prices_equal and 
            depth >= min_depth and 
            spacing >= min_spacing
        )
        
        return {
            "valid": valid,
            "price_equality": equality_score,
            "depth": depth,
            "spacing": spacing,
            "p1": p1.to_dict(),
            "p2": p2.to_dict(),
            "neckline": valley_between.price if valley_between else None,
        }
    
    def check_compression(
        self,
        swing_highs: List[SwingPoint],
        swing_lows: List[SwingPoint],
        min_ratio: float = None
    ) -> Dict:
        """
        Check if there's significant compression (narrowing range).
        
        Used for: triangles, wedges, squeezes
        """
        min_ratio = min_ratio or self.min_compression
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {"compressed": False, "reason": "not_enough_swings"}
        
        # First and last range
        width_start = swing_highs[0].price - swing_lows[0].price
        width_end = swing_highs[-1].price - swing_lows[-1].price
        
        if width_start <= 0:
            return {"compressed": False, "reason": "invalid_range"}
        
        compression = 1 - (width_end / width_start)
        
        return {
            "compressed": compression >= min_ratio,
            "compression_ratio": compression,
            "width_start": width_start,
            "width_end": width_end,
        }


# Singleton instance
_geometry_engine = None

def get_geometry_engine(config: Dict = None) -> GeometryEngine:
    global _geometry_engine
    if _geometry_engine is None or config:
        _geometry_engine = GeometryEngine(config)
    return _geometry_engine
