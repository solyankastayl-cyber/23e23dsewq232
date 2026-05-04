"""
Pattern Geometry Builder
=========================

Строит ПОЛНЫЙ geometry contract из anchors.
НЕ рисует напрямую из detector output!

Pipeline:
detector found pattern → build geometry contract → validate shape → render gate → ui
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import math


@dataclass
class GeometryContract:
    """Complete geometry contract for rendering."""
    pattern_type: str
    
    # Window
    window_start: int = 0  # timestamp
    window_end: int = 0
    window_bars: int = 0
    
    # Anchors
    upper_anchors: List[Dict] = field(default_factory=list)
    lower_anchors: List[Dict] = field(default_factory=list)
    
    # Boundaries (computed from anchors)
    upper_boundary: Dict = field(default_factory=dict)  # {x1, y1, x2, y2}
    lower_boundary: Dict = field(default_factory=dict)
    
    # Apex (for wedge/triangle)
    apex: Optional[Dict] = None  # {time, price}
    
    # Shape metrics
    upper_slope: float = 0.0
    lower_slope: float = 0.0
    compression_ratio: float = 0.0
    convergence: bool = False
    cleanliness: float = 0.0
    
    # Validation
    is_valid: bool = False
    rejection_reason: Optional[str] = None
    
    # Render mode
    render_mode: str = "polygon"  # polygon, lines, area
    
    def to_dict(self) -> Dict:
        return {
            "pattern_type": self.pattern_type,
            "window": {
                "start": self.window_start,
                "end": self.window_end,
                "bars": self.window_bars,
            },
            "anchors": {
                "upper": self.upper_anchors,
                "lower": self.lower_anchors,
            },
            "boundaries": {
                "upper": self.upper_boundary,
                "lower": self.lower_boundary,
            },
            "apex": self.apex,
            "shape_metrics": {
                "upper_slope": round(self.upper_slope, 6),
                "lower_slope": round(self.lower_slope, 6),
                "compression_ratio": round(self.compression_ratio, 3),
                "convergence": self.convergence,
                "cleanliness": round(self.cleanliness, 2),
            },
            "is_valid": self.is_valid,
            "rejection_reason": self.rejection_reason,
            "render_mode": self.render_mode,
        }


class PatternGeometryBuilder:
    """
    Builds geometry contract from pattern candidate.
    
    NOT just 2 lines - full contract with:
    - Window trimmed to anchors
    - All anchor points
    - Validated boundaries
    - Shape metrics
    """
    
    def build(
        self,
        pattern_type: str,
        boundaries: List[Dict],
        candles: List[Dict],
        debug_info: Dict = None,
    ) -> GeometryContract:
        """
        Build geometry contract from V2 pipeline boundaries.
        
        Args:
            pattern_type: e.g., "falling_wedge"
            boundaries: List of boundary objects with y1, y2, x1, x2
            candles: Price candles
            debug_info: Debug info from detector
        """
        contract = GeometryContract(pattern_type=pattern_type)
        
        if not boundaries or not candles:
            contract.rejection_reason = "No boundaries or candles"
            return contract
        
        # Extract upper and lower boundaries
        upper_b = None
        lower_b = None
        
        for b in boundaries:
            if isinstance(b, dict):
                b_id = b.get("id", "")
                if "upper" in b_id:
                    upper_b = b
                elif "lower" in b_id:
                    lower_b = b
        
        if not upper_b or not lower_b:
            contract.rejection_reason = "Missing upper or lower boundary"
            return contract
        
        # Extract anchor points from boundaries
        upper_anchors = self._extract_anchors(upper_b, candles, is_upper=True)
        lower_anchors = self._extract_anchors(lower_b, candles, is_upper=False)
        
        contract.upper_anchors = upper_anchors
        contract.lower_anchors = lower_anchors
        
        # Determine window from anchors
        all_times = [a["time"] for a in upper_anchors + lower_anchors if a.get("time")]
        if all_times:
            contract.window_start = min(all_times)
            contract.window_end = max(all_times)
        
        # Get window bars from debug or calculate
        if debug_info:
            contract.window_bars = debug_info.get("window_bars", 0)
        
        if not contract.window_bars and candles:
            # Estimate from timestamps
            start_idx = self._find_candle_index(candles, contract.window_start)
            end_idx = self._find_candle_index(candles, contract.window_end)
            contract.window_bars = max(1, end_idx - start_idx)
        
        # Build boundary lines
        contract.upper_boundary = {
            "x1": upper_b.get("x1", 0),
            "y1": upper_b.get("y1", 0),
            "x2": upper_b.get("x2", 0),
            "y2": upper_b.get("y2", 0),
        }
        contract.lower_boundary = {
            "x1": lower_b.get("x1", 0),
            "y1": lower_b.get("y1", 0),
            "x2": lower_b.get("x2", 0),
            "y2": lower_b.get("y2", 0),
        }
        
        # Calculate slopes
        contract.upper_slope = self._calc_slope(contract.upper_boundary)
        contract.lower_slope = self._calc_slope(contract.lower_boundary)
        
        # Calculate compression
        start_width = abs(contract.upper_boundary["y1"] - contract.lower_boundary["y1"])
        end_width = abs(contract.upper_boundary["y2"] - contract.lower_boundary["y2"])
        
        if start_width > 0:
            contract.compression_ratio = end_width / start_width
        
        contract.convergence = contract.compression_ratio < 0.85
        
        # Calculate apex for wedge/triangle
        contract.apex = self._calc_apex(contract.upper_boundary, contract.lower_boundary)
        
        # Calculate cleanliness (how well price respects boundaries)
        contract.cleanliness = self._calc_cleanliness(
            candles, contract.upper_boundary, contract.lower_boundary,
            contract.window_start, contract.window_end
        )
        
        contract.is_valid = True
        return contract
    
    def _extract_anchors(self, boundary: Dict, candles: List[Dict], is_upper: bool) -> List[Dict]:
        """Extract anchor points from boundary."""
        anchors = []
        
        x1, y1 = boundary.get("x1", 0), boundary.get("y1", 0)
        x2, y2 = boundary.get("x2", 0), boundary.get("y2", 0)
        
        if x1 and y1:
            anchors.append({"time": x1, "price": y1, "type": "start"})
        if x2 and y2:
            anchors.append({"time": x2, "price": y2, "type": "end"})
        
        return anchors
    
    def _find_candle_index(self, candles: List[Dict], timestamp: int) -> int:
        """Find candle index for timestamp."""
        for i, c in enumerate(candles):
            t = c.get("time", c.get("timestamp", 0))
            if t > 1e12:
                t //= 1000
            if t >= timestamp:
                return i
        return len(candles) - 1
    
    def _calc_slope(self, boundary: Dict) -> float:
        """Calculate slope of boundary line."""
        x1, y1 = boundary.get("x1", 0), boundary.get("y1", 0)
        x2, y2 = boundary.get("x2", 0), boundary.get("y2", 0)
        
        if x2 == x1:
            return 0
        
        return (y2 - y1) / (x2 - x1)
    
    def _calc_apex(self, upper: Dict, lower: Dict) -> Optional[Dict]:
        """Calculate apex (intersection point) of two lines."""
        # Line 1: y = m1*x + b1
        # Line 2: y = m2*x + b2
        
        m1 = self._calc_slope(upper)
        m2 = self._calc_slope(lower)
        
        if abs(m1 - m2) < 1e-10:
            return None  # Parallel lines
        
        b1 = upper["y1"] - m1 * upper["x1"]
        b2 = lower["y1"] - m2 * lower["x1"]
        
        # Intersection: m1*x + b1 = m2*x + b2
        # x = (b2 - b1) / (m1 - m2)
        apex_x = (b2 - b1) / (m1 - m2)
        apex_y = m1 * apex_x + b1
        
        return {"time": int(apex_x), "price": round(apex_y, 2)}
    
    def _calc_cleanliness(
        self,
        candles: List[Dict],
        upper: Dict,
        lower: Dict,
        start_time: int,
        end_time: int,
    ) -> float:
        """Calculate how cleanly price respects boundaries."""
        if not candles:
            return 0.0
        
        violations = 0
        total = 0
        
        for c in candles:
            t = c.get("time", c.get("timestamp", 0))
            if t > 1e12:
                t //= 1000
            
            if t < start_time or t > end_time:
                continue
            
            total += 1
            
            # Calculate expected upper/lower at this time
            upper_val = self._line_value_at(upper, t)
            lower_val = self._line_value_at(lower, t)
            
            high = c.get("high", 0)
            low = c.get("low", 0)
            
            # Check violations (body piercing through line)
            if high > upper_val * 1.01:  # 1% tolerance
                violations += 1
            if low < lower_val * 0.99:
                violations += 1
        
        if total == 0:
            return 0.0
        
        return 1.0 - (violations / (total * 2))
    
    def _line_value_at(self, boundary: Dict, x: int) -> float:
        """Get y value of line at x."""
        slope = self._calc_slope(boundary)
        b = boundary["y1"] - slope * boundary["x1"]
        return slope * x + b


def get_pattern_geometry_builder() -> PatternGeometryBuilder:
    return PatternGeometryBuilder()
