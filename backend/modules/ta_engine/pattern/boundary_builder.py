"""
Boundary Builder v1
===================

Builds pattern boundaries from anchor points.
NOT regression, but EXPLICIT line through 2 anchor points.

Key principle:
- Line goes through exactly 2 anchor points
- Other points are validated as touches, not used for construction
- Line is constrained to pattern window
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class BoundaryLine:
    """Represents a pattern boundary line."""
    slope: float
    intercept: float
    start_index: int
    end_index: int
    start_time: int
    end_time: int
    start_price: float
    end_price: float
    
    def project(self, index: int) -> float:
        """Project line to get price at given index."""
        return self.slope * index + self.intercept
    
    def project_time(self, time: int, start_time: int, end_time: int) -> float:
        """Project line to get price at given time."""
        if end_time == start_time:
            return self.start_price
        t_ratio = (time - start_time) / (end_time - start_time)
        idx = self.start_index + t_ratio * (self.end_index - self.start_index)
        return self.project(idx)
    
    def to_dict(self) -> Dict:
        return {
            "slope": self.slope,
            "intercept": self.intercept,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "start_price": self.start_price,
            "end_price": self.end_price,
        }


class BoundaryBuilder:
    """
    Builds pattern boundaries from anchor points.
    
    NOT regression fitting.
    Uses explicit anchor-to-anchor line construction.
    """
    
    def build_line_from_anchors(self, anchors: List[Dict]) -> Optional[BoundaryLine]:
        """
        Build a line through anchor points.
        
        Uses first and last anchor to define the line.
        Middle anchors (if any) are not used for construction,
        but should be validated as touches.
        """
        if len(anchors) < 2:
            return None
        
        # Use first and last anchors
        p1 = anchors[0]
        p2 = anchors[-1]
        
        idx1 = p1.get("index", 0)
        idx2 = p2.get("index", 0)
        price1 = p1.get("price", 0)
        price2 = p2.get("price", 0)
        time1 = p1.get("time", 0)
        time2 = p2.get("time", 0)
        
        if idx1 == idx2:
            # Vertical line (shouldn't happen)
            return None
        
        # Calculate slope and intercept
        slope = (price2 - price1) / (idx2 - idx1)
        intercept = price1 - slope * idx1
        
        return BoundaryLine(
            slope=slope,
            intercept=intercept,
            start_index=idx1,
            end_index=idx2,
            start_time=time1,
            end_time=time2,
            start_price=price1,
            end_price=price2,
        )
    
    def build_horizontal_line(self, anchors: List[Dict]) -> Optional[BoundaryLine]:
        """
        Build a horizontal line at the average price of anchors.
        Used for flat resistance/support levels in triangles.
        """
        if not anchors:
            return None
        
        avg_price = sum(a.get("price", 0) for a in anchors) / len(anchors)
        
        # Use first and last for time bounds
        p1 = anchors[0]
        p2 = anchors[-1]
        
        return BoundaryLine(
            slope=0,
            intercept=avg_price,
            start_index=p1.get("index", 0),
            end_index=p2.get("index", 0),
            start_time=p1.get("time", 0),
            end_time=p2.get("time", 0),
            start_price=avg_price,
            end_price=avg_price,
        )
    
    def extend_line_to_window(
        self, 
        line: BoundaryLine, 
        window_start_idx: int, 
        window_end_idx: int,
        candles: List[Dict]
    ) -> BoundaryLine:
        """
        Extend line to fill the pattern window.
        Projects prices at window boundaries.
        """
        start_price = line.project(window_start_idx)
        end_price = line.project(window_end_idx)
        
        # Get times from candles
        start_time = candles[window_start_idx].get("time", 0) if window_start_idx < len(candles) else line.start_time
        end_time = candles[window_end_idx].get("time", 0) if window_end_idx < len(candles) else line.end_time
        
        return BoundaryLine(
            slope=line.slope,
            intercept=line.intercept,
            start_index=window_start_idx,
            end_index=window_end_idx,
            start_time=start_time,
            end_time=end_time,
            start_price=start_price,
            end_price=end_price,
        )
    
    def build_render_boundary(
        self,
        boundary_id: str,
        line: BoundaryLine,
        style: str = "primary"
    ) -> Dict:
        """
        Build render-ready boundary object for frontend.
        """
        return {
            "id": boundary_id,
            "kind": "trendline",
            "style": style,
            "x1": line.start_time,
            "y1": line.start_price,
            "x2": line.end_time,
            "y2": line.end_price,
        }


# Singleton
_boundary_builder = None

def get_boundary_builder() -> BoundaryBuilder:
    """Get boundary builder singleton."""
    global _boundary_builder
    if _boundary_builder is None:
        _boundary_builder = BoundaryBuilder()
    return _boundary_builder
