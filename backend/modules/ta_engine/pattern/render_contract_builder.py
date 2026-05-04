"""
Pattern Render Contract Builder v4
==================================

Converts detected patterns into render-ready geometry.

Key principles:
1. Patterns live inside bounded time windows
2. Boundaries are clean trendlines, not pivot connections
3. Frontend draws primitives directly, no reconstruction
4. Support primary + alternative patterns

Render Contract Structure:
{
    "type": "ascending_triangle",
    "label": "Ascending Triangle",
    "direction": "bullish",
    "status": "active",
    "confidence": 0.74,
    "geometry_score": 0.81,
    "render_quality": 0.79,
    "window": {"start": timestamp, "end": timestamp},
    "render": {
        "boundaries": [...],
        "levels": [...],
        "touch_points": [...],
        "markers": [...],
        "zones": []
    }
}
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import numpy as np


class PatternRenderContractBuilder:
    """
    Builds render-ready pattern contracts for frontend visualization.
    
    Key difference from old approach:
    - OLD: return pivot points, frontend reconstructs
    - NEW: return complete render primitives, frontend just draws
    """
    
    # Pattern type mappings
    PATTERN_LABELS = {
        "ascending_triangle": "Ascending Triangle",
        "descending_triangle": "Descending Triangle",
        "symmetrical_triangle": "Symmetrical Triangle",
        "rising_wedge": "Rising Wedge",
        "falling_wedge": "Falling Wedge",
        "ascending_channel": "Ascending Channel",
        "descending_channel": "Descending Channel",
        "horizontal_channel": "Horizontal Channel",
        "double_top": "Double Top",
        "double_bottom": "Double Bottom",
        "head_and_shoulders": "Head & Shoulders",
        "inverse_head_and_shoulders": "Inverse H&S",
        "bull_flag": "Bull Flag",
        "bear_flag": "Bear Flag",
        "cup_and_handle": "Cup & Handle",
    }
    
    PATTERN_DIRECTIONS = {
        "ascending_triangle": "bullish",
        "descending_triangle": "bearish",
        "symmetrical_triangle": "neutral",
        "rising_wedge": "bearish",
        "falling_wedge": "bullish",
        "ascending_channel": "bullish",
        "descending_channel": "bearish",
        "horizontal_channel": "neutral",
        "double_top": "bearish",
        "double_bottom": "bullish",
        "head_and_shoulders": "bearish",
        "inverse_head_and_shoulders": "bullish",
        "bull_flag": "bullish",
        "bear_flag": "bearish",
        "cup_and_handle": "bullish",
    }
    
    def build(self, pattern: Dict, candles: List[Dict]) -> Optional[Dict]:
        """
        Build render contract from detected pattern.
        
        Args:
            pattern: Detected pattern dict with geometry
            candles: OHLC candles for context
            
        Returns:
            Render-ready pattern contract or None
        """
        if not pattern:
            return None
            
        pattern_type = pattern.get("type", "unknown")
        
        # Route to specific builder
        if "triangle" in pattern_type:
            return self._build_triangle(pattern, candles)
        elif "wedge" in pattern_type:
            return self._build_wedge(pattern, candles)
        elif "channel" in pattern_type:
            return self._build_channel(pattern, candles)
        elif pattern_type in ["double_top", "double_bottom"]:
            return self._build_double(pattern, candles)
        elif "head" in pattern_type or "shoulders" in pattern_type:
            return self._build_head_shoulders(pattern, candles)
        elif "flag" in pattern_type:
            return self._build_flag(pattern, candles)
        else:
            return self._build_generic(pattern, candles)
    
    def _build_triangle(self, pattern: Dict, candles: List[Dict]) -> Dict:
        """
        Build triangle render contract.
        
        Triangle structure:
        - upper_boundary: resistance trendline
        - lower_boundary: support trendline
        - breakout_level: horizontal at resistance (ascending) or support (descending)
        - touch_points: where price touched boundaries
        """
        pattern_type = pattern.get("type", "ascending_triangle")
        
        # Get window bounds
        window = self._get_pattern_window(pattern, candles)
        
        # Get boundary lines - try upper_line/lower_line first, then anchor_points
        upper_line = pattern.get("upper_line", {})
        lower_line = pattern.get("lower_line", {})
        
        # If no upper_line/lower_line, build from anchor_points
        anchor_points = pattern.get("anchor_points", {})
        if not upper_line and anchor_points.get("upper"):
            upper_pts = anchor_points["upper"]
            if len(upper_pts) >= 2:
                upper_line = {
                    "start_time": upper_pts[0].get("time"),
                    "start_price": upper_pts[0].get("value"),
                    "end_time": upper_pts[-1].get("time"),
                    "end_price": upper_pts[-1].get("value"),
                }
        
        if not lower_line and anchor_points.get("lower"):
            lower_pts = anchor_points["lower"]
            if len(lower_pts) >= 2:
                lower_line = {
                    "start_time": lower_pts[0].get("time"),
                    "start_price": lower_pts[0].get("value"),
                    "end_time": lower_pts[-1].get("time"),
                    "end_price": lower_pts[-1].get("value"),
                }
        
        # Build clean boundaries
        upper_boundary = self._build_boundary(
            "upper_boundary", 
            upper_line, 
            window, 
            candles,
            style="primary"
        )
        lower_boundary = self._build_boundary(
            "lower_boundary", 
            lower_line, 
            window, 
            candles,
            style="primary"
        )
        
        # Determine breakout level
        if pattern_type == "ascending_triangle":
            breakout_price = upper_boundary.get("y1", 0) if upper_boundary else None
            breakout_kind = "resistance_breakout"
        elif pattern_type == "descending_triangle":
            breakout_price = lower_boundary.get("y1", 0) if lower_boundary else None
            breakout_kind = "support_breakdown"
        else:
            # Symmetrical - use apex point
            breakout_price = self._calculate_apex_price(upper_boundary, lower_boundary)
            breakout_kind = "apex"
        
        # Build touch points
        touch_points = self._extract_touch_points(pattern, candles)
        
        # Calculate render quality
        render_quality = self._calculate_render_quality(
            [upper_boundary, lower_boundary],
            touch_points,
            window
        )
        
        return {
            "type": pattern_type,
            "label": self.PATTERN_LABELS.get(pattern_type, pattern_type.replace("_", " ").title()),
            "direction": pattern.get("direction", self.PATTERN_DIRECTIONS.get(pattern_type, "neutral")),
            "status": "active" if pattern.get("is_active", True) else "completed",
            "confidence": pattern.get("final_score", pattern.get("confidence", 0.5)),
            "geometry_score": pattern.get("geometry_score", 0.5),
            "render_quality": render_quality,
            "window": window,
            "render": {
                "boundaries": [b for b in [upper_boundary, lower_boundary] if b],
                "levels": [
                    {
                        "id": "breakout_level",
                        "kind": breakout_kind,
                        "price": breakout_price,
                        "label": "Breakout" if "breakout" in breakout_kind else "Target",
                        "start": window["start"],
                        "end": window["end"],
                    }
                ] if breakout_price else [],
                "touch_points": touch_points,
                "markers": self._build_markers(pattern, candles),
                "zones": [],
            }
        }
    
    def _build_wedge(self, pattern: Dict, candles: List[Dict]) -> Dict:
        """
        Build wedge render contract.
        
        Wedge structure:
        - Converging boundaries (both angled)
        - Breakout typically opposite to wedge direction
        """
        pattern_type = pattern.get("type", "falling_wedge")
        window = self._get_pattern_window(pattern, candles)
        
        upper_line = pattern.get("upper_line", {})
        lower_line = pattern.get("lower_line", {})
        
        # Build from anchor_points if no lines
        anchor_points = pattern.get("anchor_points", {})
        if not upper_line and anchor_points.get("upper"):
            upper_pts = anchor_points["upper"]
            if len(upper_pts) >= 2:
                upper_line = {
                    "start_time": upper_pts[0].get("time"),
                    "start_price": upper_pts[0].get("value"),
                    "end_time": upper_pts[-1].get("time"),
                    "end_price": upper_pts[-1].get("value"),
                }
        
        if not lower_line and anchor_points.get("lower"):
            lower_pts = anchor_points["lower"]
            if len(lower_pts) >= 2:
                lower_line = {
                    "start_time": lower_pts[0].get("time"),
                    "start_price": lower_pts[0].get("value"),
                    "end_time": lower_pts[-1].get("time"),
                    "end_price": lower_pts[-1].get("value"),
                }
        
        upper_boundary = self._build_boundary("upper_boundary", upper_line, window, candles, "primary")
        lower_boundary = self._build_boundary("lower_boundary", lower_line, window, candles, "primary")
        
        # Wedge breakout is at the boundary opposite to direction
        if pattern_type == "falling_wedge":
            breakout_price = upper_boundary.get("y2") if upper_boundary else None
            breakout_kind = "bullish_breakout"
        else:  # rising_wedge
            breakout_price = lower_boundary.get("y2") if lower_boundary else None
            breakout_kind = "bearish_breakdown"
        
        touch_points = self._extract_touch_points(pattern, candles)
        render_quality = self._calculate_render_quality([upper_boundary, lower_boundary], touch_points, window)
        
        return {
            "type": pattern_type,
            "label": self.PATTERN_LABELS.get(pattern_type, pattern_type.replace("_", " ").title()),
            "direction": pattern.get("direction", self.PATTERN_DIRECTIONS.get(pattern_type, "neutral")),
            "status": "active" if pattern.get("is_active", True) else "completed",
            "confidence": pattern.get("final_score", pattern.get("confidence", 0.5)),
            "geometry_score": pattern.get("geometry_score", 0.5),
            "render_quality": render_quality,
            "window": window,
            "render": {
                "boundaries": [b for b in [upper_boundary, lower_boundary] if b],
                "levels": [
                    {
                        "id": "breakout_level",
                        "kind": breakout_kind,
                        "price": breakout_price,
                        "label": "Breakout",
                        "start": window["start"],
                        "end": window["end"],
                    }
                ] if breakout_price else [],
                "touch_points": touch_points,
                "markers": self._build_markers(pattern, candles),
                "zones": [],
            }
        }
    
    def _build_channel(self, pattern: Dict, candles: List[Dict]) -> Dict:
        """
        Build channel render contract.
        
        Channel structure:
        - Two parallel boundaries
        - Zone between boundaries
        """
        pattern_type = pattern.get("type", "horizontal_channel")
        window = self._get_pattern_window(pattern, candles)
        
        upper_line = pattern.get("upper_line", {})
        lower_line = pattern.get("lower_line", {})
        
        upper_boundary = self._build_boundary("upper_boundary", upper_line, window, candles, "primary")
        lower_boundary = self._build_boundary("lower_boundary", lower_line, window, candles, "primary")
        
        # Build channel zone
        zone = None
        if upper_boundary and lower_boundary:
            zone = {
                "id": "channel_zone",
                "kind": "channel",
                "left": window["start"],
                "right": window["end"],
                "top": max(upper_boundary.get("y1", 0), upper_boundary.get("y2", 0)),
                "bottom": min(lower_boundary.get("y1", 0), lower_boundary.get("y2", 0)),
            }
        
        touch_points = self._extract_touch_points(pattern, candles)
        render_quality = self._calculate_render_quality([upper_boundary, lower_boundary], touch_points, window)
        
        return {
            "type": pattern_type,
            "label": self.PATTERN_LABELS.get(pattern_type, pattern_type.replace("_", " ").title()),
            "direction": pattern.get("direction", self.PATTERN_DIRECTIONS.get(pattern_type, "neutral")),
            "status": "active" if pattern.get("is_active", True) else "completed",
            "confidence": pattern.get("final_score", pattern.get("confidence", 0.5)),
            "geometry_score": pattern.get("geometry_score", 0.5),
            "render_quality": render_quality,
            "window": window,
            "render": {
                "boundaries": [b for b in [upper_boundary, lower_boundary] if b],
                "levels": [],
                "touch_points": touch_points,
                "markers": self._build_markers(pattern, candles),
                "zones": [zone] if zone else [],
            }
        }
    
    def _build_double(self, pattern: Dict, candles: List[Dict]) -> Dict:
        """
        Build double top/bottom render contract.
        
        Structure:
        - Two peaks/troughs
        - Neckline
        - Markers for peaks
        """
        pattern_type = pattern.get("type", "double_top")
        window = self._get_pattern_window(pattern, candles)
        
        # Get peaks/troughs
        pivots = pattern.get("pivots", [])
        peaks = [p for p in pivots if p.get("type") == "high"]
        troughs = [p for p in pivots if p.get("type") == "low"]
        
        # Determine key points
        if pattern_type == "double_top":
            key_points = peaks[:2] if len(peaks) >= 2 else peaks
            neckline_points = troughs
        else:  # double_bottom
            key_points = troughs[:2] if len(troughs) >= 2 else troughs
            neckline_points = peaks
        
        # Build neckline
        neckline = None
        if neckline_points:
            neckline_price = neckline_points[0].get("price", 0)
            neckline = {
                "id": "neckline",
                "kind": "neckline",
                "price": neckline_price,
                "label": "Neckline",
                "start": window["start"],
                "end": window["end"],
            }
        
        # Build markers for peaks/troughs
        markers = []
        for i, kp in enumerate(key_points):
            markers.append({
                "time": kp.get("time", kp.get("timestamp", 0)),
                "price": kp.get("price", 0),
                "label": f"{'Top' if pattern_type == 'double_top' else 'Bottom'} {i+1}",
                "type": "peak" if pattern_type == "double_top" else "trough",
            })
        
        touch_points = self._extract_touch_points(pattern, candles)
        render_quality = self._calculate_render_quality([], touch_points, window, len(key_points))
        
        return {
            "type": pattern_type,
            "label": self.PATTERN_LABELS.get(pattern_type, pattern_type.replace("_", " ").title()),
            "direction": pattern.get("direction", self.PATTERN_DIRECTIONS.get(pattern_type, "neutral")),
            "status": "active" if pattern.get("is_active", True) else "completed",
            "confidence": pattern.get("final_score", pattern.get("confidence", 0.5)),
            "geometry_score": pattern.get("geometry_score", 0.5),
            "render_quality": render_quality,
            "window": window,
            "render": {
                "boundaries": [],
                "levels": [neckline] if neckline else [],
                "touch_points": touch_points,
                "markers": markers,
                "zones": [],
            }
        }
    
    def _build_head_shoulders(self, pattern: Dict, candles: List[Dict]) -> Dict:
        """
        Build head & shoulders render contract.
        
        Structure:
        - Left shoulder, head, right shoulder markers
        - Neckline connecting troughs
        """
        pattern_type = pattern.get("type", "head_and_shoulders")
        is_inverse = "inverse" in pattern_type
        window = self._get_pattern_window(pattern, candles)
        
        # Get pivots
        pivots = pattern.get("pivots", [])
        
        # Sort pivots by time
        sorted_pivots = sorted(pivots, key=lambda p: p.get("time", p.get("timestamp", 0)))
        
        # Identify LS, H, RS
        markers = []
        if len(sorted_pivots) >= 3:
            if is_inverse:
                # For inverse: troughs are LS, H, RS
                troughs = [p for p in sorted_pivots if p.get("type") == "low"]
                if len(troughs) >= 3:
                    markers = [
                        {"time": troughs[0].get("time", 0), "price": troughs[0].get("price", 0), "label": "LS", "type": "shoulder"},
                        {"time": troughs[1].get("time", 0), "price": troughs[1].get("price", 0), "label": "H", "type": "head"},
                        {"time": troughs[2].get("time", 0), "price": troughs[2].get("price", 0), "label": "RS", "type": "shoulder"},
                    ]
            else:
                # For regular: peaks are LS, H, RS
                peaks = [p for p in sorted_pivots if p.get("type") == "high"]
                if len(peaks) >= 3:
                    markers = [
                        {"time": peaks[0].get("time", 0), "price": peaks[0].get("price", 0), "label": "LS", "type": "shoulder"},
                        {"time": peaks[1].get("time", 0), "price": peaks[1].get("price", 0), "label": "H", "type": "head"},
                        {"time": peaks[2].get("time", 0), "price": peaks[2].get("price", 0), "label": "RS", "type": "shoulder"},
                    ]
        
        # Build neckline
        neckline = None
        neckline_data = pattern.get("neckline", {})
        if neckline_data:
            neckline = {
                "id": "neckline",
                "kind": "neckline",
                "price": neckline_data.get("price", neckline_data.get("y1", 0)),
                "label": "Neckline",
                "start": window["start"],
                "end": window["end"],
            }
        
        touch_points = self._extract_touch_points(pattern, candles)
        render_quality = self._calculate_render_quality([], touch_points, window, len(markers))
        
        return {
            "type": pattern_type,
            "label": self.PATTERN_LABELS.get(pattern_type, pattern_type.replace("_", " ").title()),
            "direction": pattern.get("direction", self.PATTERN_DIRECTIONS.get(pattern_type, "neutral")),
            "status": "active" if pattern.get("is_active", True) else "completed",
            "confidence": pattern.get("final_score", pattern.get("confidence", 0.5)),
            "geometry_score": pattern.get("geometry_score", 0.5),
            "render_quality": render_quality,
            "window": window,
            "render": {
                "boundaries": [],
                "levels": [neckline] if neckline else [],
                "touch_points": touch_points,
                "markers": markers,
                "zones": [],
            }
        }
    
    def _build_flag(self, pattern: Dict, candles: List[Dict]) -> Dict:
        """Build flag pattern render contract."""
        pattern_type = pattern.get("type", "bull_flag")
        window = self._get_pattern_window(pattern, candles)
        
        upper_line = pattern.get("upper_line", {})
        lower_line = pattern.get("lower_line", {})
        
        upper_boundary = self._build_boundary("upper_boundary", upper_line, window, candles, "primary")
        lower_boundary = self._build_boundary("lower_boundary", lower_line, window, candles, "primary")
        
        touch_points = self._extract_touch_points(pattern, candles)
        render_quality = self._calculate_render_quality([upper_boundary, lower_boundary], touch_points, window)
        
        return {
            "type": pattern_type,
            "label": self.PATTERN_LABELS.get(pattern_type, pattern_type.replace("_", " ").title()),
            "direction": pattern.get("direction", self.PATTERN_DIRECTIONS.get(pattern_type, "neutral")),
            "status": "active" if pattern.get("is_active", True) else "completed",
            "confidence": pattern.get("final_score", pattern.get("confidence", 0.5)),
            "geometry_score": pattern.get("geometry_score", 0.5),
            "render_quality": render_quality,
            "window": window,
            "render": {
                "boundaries": [b for b in [upper_boundary, lower_boundary] if b],
                "levels": [],
                "touch_points": touch_points,
                "markers": self._build_markers(pattern, candles),
                "zones": [],
            }
        }
    
    def _build_generic(self, pattern: Dict, candles: List[Dict]) -> Dict:
        """Build generic pattern render contract."""
        pattern_type = pattern.get("type", "unknown")
        window = self._get_pattern_window(pattern, candles)
        
        upper_line = pattern.get("upper_line", {})
        lower_line = pattern.get("lower_line", {})
        
        upper_boundary = self._build_boundary("upper_boundary", upper_line, window, candles, "primary")
        lower_boundary = self._build_boundary("lower_boundary", lower_line, window, candles, "primary")
        
        touch_points = self._extract_touch_points(pattern, candles)
        render_quality = self._calculate_render_quality([upper_boundary, lower_boundary], touch_points, window)
        
        return {
            "type": pattern_type,
            "label": pattern_type.replace("_", " ").title(),
            "direction": pattern.get("direction", "neutral"),
            "status": "active" if pattern.get("is_active", True) else "completed",
            "confidence": pattern.get("final_score", pattern.get("confidence", 0.5)),
            "geometry_score": pattern.get("geometry_score", 0.5),
            "render_quality": render_quality,
            "window": window,
            "render": {
                "boundaries": [b for b in [upper_boundary, lower_boundary] if b],
                "levels": [],
                "touch_points": touch_points,
                "markers": self._build_markers(pattern, candles),
                "zones": [],
            }
        }
    
    # ═══════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════
    
    def _get_pattern_window(self, pattern: Dict, candles: List[Dict]) -> Dict:
        """
        Extract pattern time window.
        
        CRITICAL: Pattern must live inside bounded window, not span entire chart.
        Use anchor_points to determine actual pattern boundaries.
        """
        # Try to get from anchor_points first (most accurate)
        anchor_points = pattern.get("anchor_points", {})
        upper_pts = anchor_points.get("upper", [])
        lower_pts = anchor_points.get("lower", [])
        
        all_times = []
        for pt in upper_pts + lower_pts:
            t = pt.get("time")
            if t:
                all_times.append(t)
        
        if all_times:
            # Use actual anchor point times
            start_time = min(all_times)
            end_time = max(all_times)
            
            # Find indices
            start_idx = 0
            end_idx = len(candles) - 1
            for i, c in enumerate(candles):
                c_time = c.get("time", c.get("timestamp", 0))
                if c_time <= start_time:
                    start_idx = i
                if c_time <= end_time:
                    end_idx = i
            
            return {
                "start": start_time,
                "end": end_time,
                "start_index": start_idx,
                "end_index": end_idx,
            }
        
        # Fallback to pattern indices
        start_idx = pattern.get("start_index", 0)
        end_idx = pattern.get("end_index", len(candles) - 1)
        
        # Fallback to line endpoints
        upper_line = pattern.get("upper_line", {})
        lower_line = pattern.get("lower_line", {})
        
        if upper_line.get("start_index") is not None:
            start_idx = min(start_idx, upper_line.get("start_index", start_idx))
        if lower_line.get("start_index") is not None:
            start_idx = min(start_idx, lower_line.get("start_index", start_idx))
            
        if upper_line.get("end_index") is not None:
            end_idx = max(end_idx, upper_line.get("end_index", end_idx))
        if lower_line.get("end_index") is not None:
            end_idx = max(end_idx, lower_line.get("end_index", end_idx))
        
        # Convert to timestamps
        start_time = self._get_candle_time(candles, start_idx)
        end_time = self._get_candle_time(candles, end_idx)
        
        return {
            "start": start_time,
            "end": end_time,
            "start_index": start_idx,
            "end_index": end_idx,
        }
    
    def _get_candle_time(self, candles: List[Dict], idx: int) -> int:
        """Get timestamp from candle by index."""
        if not candles:
            return 0
        idx = max(0, min(idx, len(candles) - 1))
        candle = candles[idx]
        time_val = candle.get("time", candle.get("timestamp", 0))
        if isinstance(time_val, str):
            try:
                dt = datetime.fromisoformat(time_val.replace("Z", "+00:00"))
                return int(dt.timestamp())
            except:
                return 0
        return int(time_val)
    
    def _build_boundary(
        self, 
        boundary_id: str, 
        line_data: Dict, 
        window: Dict, 
        candles: List[Dict],
        style: str = "primary"
    ) -> Optional[Dict]:
        """
        Build clean boundary line from pattern line data.
        
        CRITICAL: 
        - Lines are strictly bounded by window
        - No extrapolation beyond pattern
        """
        if not line_data:
            return None
        
        # Get coordinates
        x1 = line_data.get("start_time", line_data.get("x1"))
        y1 = line_data.get("start_price", line_data.get("y1"))
        x2 = line_data.get("end_time", line_data.get("x2"))
        y2 = line_data.get("end_price", line_data.get("y2"))
        
        # Fallback to indices
        if x1 is None and line_data.get("start_index") is not None:
            x1 = self._get_candle_time(candles, line_data["start_index"])
        if x2 is None and line_data.get("end_index") is not None:
            x2 = self._get_candle_time(candles, line_data["end_index"])
        
        # Validate
        if x1 is None or y1 is None or x2 is None or y2 is None:
            return None
        
        # Clamp to window
        x1 = max(x1, window.get("start", x1))
        x2 = min(x2, window.get("end", x2))
        
        return {
            "id": boundary_id,
            "kind": "trendline",
            "style": style,
            "x1": x1,
            "y1": float(y1),
            "x2": x2,
            "y2": float(y2),
        }
    
    def _extract_touch_points(self, pattern: Dict, candles: List[Dict]) -> List[Dict]:
        """Extract boundary touch points from pattern."""
        touch_points = []
        
        # Try to get from pattern
        pivots = pattern.get("pivots", [])
        upper_touches = pattern.get("upper_touches", [])
        lower_touches = pattern.get("lower_touches", [])
        
        # Add pivots as touch points
        for pivot in pivots:
            tp = {
                "time": pivot.get("time", pivot.get("timestamp", 0)),
                "price": pivot.get("price", 0),
                "side": "upper" if pivot.get("type") == "high" else "lower",
            }
            if tp["time"] and tp["price"]:
                touch_points.append(tp)
        
        # Add explicit touches
        for touch in upper_touches:
            tp = {
                "time": touch.get("time", touch.get("timestamp", 0)),
                "price": touch.get("price", 0),
                "side": "upper",
            }
            if tp["time"] and tp["price"]:
                touch_points.append(tp)
                
        for touch in lower_touches:
            tp = {
                "time": touch.get("time", touch.get("timestamp", 0)),
                "price": touch.get("price", 0),
                "side": "lower",
            }
            if tp["time"] and tp["price"]:
                touch_points.append(tp)
        
        return touch_points
    
    def _build_markers(self, pattern: Dict, candles: List[Dict]) -> List[Dict]:
        """Build simple markers for key points."""
        markers = []
        
        # Apex for triangles
        apex = pattern.get("apex")
        if apex:
            markers.append({
                "time": apex.get("time", 0),
                "price": apex.get("price", 0),
                "label": "Apex",
                "type": "apex",
            })
        
        return markers
    
    def _calculate_apex_price(self, upper: Optional[Dict], lower: Optional[Dict]) -> Optional[float]:
        """Calculate apex price for symmetrical triangles."""
        if not upper or not lower:
            return None
        
        # Simple average of end prices
        upper_end = upper.get("y2", 0)
        lower_end = lower.get("y2", 0)
        
        if upper_end and lower_end:
            return (upper_end + lower_end) / 2
        return None
    
    def _calculate_render_quality(
        self, 
        boundaries: List[Optional[Dict]], 
        touch_points: List[Dict],
        window: Dict,
        key_points_count: int = 0
    ) -> float:
        """
        Calculate visual render quality score.
        
        Factors:
        - Boundary completeness
        - Touch point count
        - Window size (not too small, not too large)
        """
        score = 0.5
        
        # Boundary completeness
        valid_boundaries = [b for b in boundaries if b is not None]
        if len(valid_boundaries) >= 2:
            score += 0.2
        elif len(valid_boundaries) >= 1:
            score += 0.1
        
        # Touch points
        if len(touch_points) >= 4:
            score += 0.15
        elif len(touch_points) >= 2:
            score += 0.1
        
        # Key points (for H&S, double patterns)
        if key_points_count >= 3:
            score += 0.15
        elif key_points_count >= 2:
            score += 0.1
        
        return min(1.0, score)


# Singleton
_render_contract_builder = None

def get_render_contract_builder() -> PatternRenderContractBuilder:
    """Get render contract builder singleton."""
    global _render_contract_builder
    if _render_contract_builder is None:
        _render_contract_builder = PatternRenderContractBuilder()
    return _render_contract_builder
