"""
Pattern Geometry Contract
=========================

Universal schema for pattern visualization.
Backend converts ANY pattern to this format.
Frontend renders ONLY primitives (segments, levels, zones, markers).

GEOMETRY CONTRACT:
{
    "type": "ascending_triangle",
    "label": "Ascending Triangle",
    "direction": "bullish",
    "confidence": 0.85,
    "status": "active",
    "geometry": {
        "segments": [
            {"kind": "resistance", "style": "solid", "points": [{"time": t, "price": p}, ...]},
            {"kind": "support_rising", "style": "solid", "points": [...]}
        ],
        "levels": [
            {"kind": "breakout", "price": 73968.0, "label": "Breakout"},
            {"kind": "invalidation", "price": 70236.0, "label": "Invalidation"}
        ],
        "zones": [
            {"kind": "pattern_area", "time_start": t, "time_end": t, "price_top": p, "price_bottom": p}
        ],
        "markers": [
            {"kind": "anchor", "time": t, "price": p, "label": "H1"}
        ]
    }
}

SUPPORTED SEGMENT KINDS:
- resistance, support, support_rising, support_falling
- neckline, upper_channel, lower_channel
- trendline_upper, trendline_lower
- left_shoulder, head, right_shoulder (for H&S)

SUPPORTED LEVEL KINDS:
- breakout, invalidation, neckline, target

SUPPORTED ZONE KINDS:
- pattern_area, consolidation, apex_zone

SUPPORTED MARKER KINDS:
- anchor, peak, trough, shoulder, head
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class GeometrySegment:
    """Line segment for pattern boundary."""
    kind: str  # resistance, support, neckline, etc.
    points: List[Dict[str, float]]  # [{"time": t, "price": p}, ...]
    style: str = "solid"  # solid, dashed, dotted
    color: Optional[str] = None


@dataclass
class GeometryLevel:
    """Horizontal price level."""
    kind: str  # breakout, invalidation, neckline, target
    price: float
    label: Optional[str] = None
    style: str = "dashed"
    color: Optional[str] = None


@dataclass
class GeometryZone:
    """Rectangular area (e.g., consolidation zone)."""
    kind: str  # pattern_area, apex_zone
    time_start: int
    time_end: int
    price_top: float
    price_bottom: float
    color: Optional[str] = None
    opacity: float = 0.1


@dataclass
class GeometryMarker:
    """Point marker with optional label."""
    kind: str  # anchor, peak, trough, shoulder, head
    time: int
    price: float
    label: Optional[str] = None


@dataclass
class PatternGeometry:
    """Universal geometry container."""
    segments: List[GeometrySegment] = field(default_factory=list)
    levels: List[GeometryLevel] = field(default_factory=list)
    zones: List[GeometryZone] = field(default_factory=list)
    markers: List[GeometryMarker] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "segments": [
                {"kind": s.kind, "style": s.style, "points": s.points, "color": s.color}
                for s in self.segments
            ],
            "levels": [
                {"kind": lvl.kind, "price": lvl.price, "label": lvl.label, "style": lvl.style, "color": lvl.color}
                for lvl in self.levels
            ],
            "zones": [
                {"kind": z.kind, "time_start": z.time_start, "time_end": z.time_end, 
                 "price_top": z.price_top, "price_bottom": z.price_bottom, "color": z.color, "opacity": z.opacity}
                for z in self.zones
            ],
            "markers": [
                {"kind": m.kind, "time": m.time, "price": m.price, "label": m.label}
                for m in self.markers
            ],
        }


# =====================================================
# HELPER FUNCTIONS for format normalization
# =====================================================

def _get_time(p: Dict) -> int:
    """Extract time from point dict, handling various field names."""
    if not p:
        return 0
    t = p.get("time", p.get("timestamp", 0))
    return int(t) if t else 0


def _get_price(p: Dict) -> float:
    """Extract price from point dict, handling various field names."""
    if not p:
        return 0.0
    return float(p.get("price", p.get("value", 0)))


def _to_point(p: Dict) -> Dict:
    """Convert any point format to standard {time, price}."""
    return {"time": _get_time(p), "price": _get_price(p)}


def _normalize_points_format(raw_points: Any, pattern_type: str) -> Dict:
    """
    Convert LIST-based points (from DetectedPattern) to DICT format.
    
    Input formats:
    1. Already dict: {upper: [...], lower: [...]} → return as-is
    2. List of points: [{type: "top1", ...}, ...] → convert to dict
    3. Wrapped list: {points: [...]} → unwrap and convert
    """
    if not raw_points:
        return {}
    
    # Already correct dict format
    if isinstance(raw_points, dict) and "upper" in raw_points:
        return raw_points
    if isinstance(raw_points, dict) and "markers" in raw_points:
        return raw_points
    
    # Unwrap {points: [...]} format
    points_list = raw_points
    if isinstance(raw_points, dict) and "points" in raw_points:
        points_list = raw_points["points"]
    
    # If not a list, return as dict
    if not isinstance(points_list, list):
        return raw_points if isinstance(raw_points, dict) else {}
    
    # Convert list to dict based on pattern type and point types
    result = {}
    
    # Group by point type
    type_groups = {}
    for p in points_list:
        if isinstance(p, dict):
            p_type = p.get("type", "unknown")
            if p_type not in type_groups:
                type_groups[p_type] = []
            type_groups[p_type].append(p)
    
    # Pattern-specific conversion
    if "double" in pattern_type:
        # Double top/bottom: top1, top2, neckline OR bottom1, bottom2, neckline
        if "top1" in type_groups:
            result["peaks"] = [type_groups["top1"][0], type_groups.get("top2", [{}])[0]]
        elif "bottom1" in type_groups:
            result["peaks"] = [type_groups["bottom1"][0], type_groups.get("bottom2", [{}])[0]]
        if "neckline" in type_groups:
            result["neckline"] = type_groups["neckline"][0]
            
    elif "channel" in pattern_type:
        # Channel: high_start, high_end, low_start, low_end
        upper = []
        lower = []
        for p in points_list:
            p_type = p.get("type", "")
            if "high" in p_type:
                upper.append(p)
            elif "low" in p_type:
                lower.append(p)
        if upper:
            result["upper"] = upper
        if lower:
            result["lower"] = lower
            
    elif "flag" in pattern_type or "pennant" in pattern_type:
        # Flag: pole_start, pole_end, flag_end
        pole = []
        flag = []
        for p in points_list:
            p_type = p.get("type", "")
            if "pole" in p_type:
                pole.append(p)
            elif "flag" in p_type:
                flag.append(p)
        if pole:
            result["pole"] = pole
        if flag:
            result["flag_end"] = flag
            
    elif "compression" in pattern_type:
        # Compression: start, end
        if "start" in type_groups:
            result["start"] = type_groups["start"][0]
        if "end" in type_groups:
            result["end"] = type_groups["end"][0]
    
    else:
        # Generic: keep original structure
        result = raw_points if isinstance(raw_points, dict) else {"points": points_list}
    
    return result


def normalize_pattern_geometry(pattern: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert any pattern format to universal geometry contract.
    
    This is the SINGLE place where pattern-specific logic lives.
    Frontend NEVER needs to know pattern internals.
    
    HANDLES MULTIPLE INPUT FORMATS:
    1. PatternCandidate with dict points: {upper: [...], lower: [...]}
    2. DetectedPattern with list points: [{type: "top1", ...}, ...]
    3. H&S detector with nested markers: {markers: {left_shoulder: {...}}}
    """
    if not pattern:
        return None
    
    pattern_type = pattern.get("type", "").lower()
    raw_points = pattern.get("points", {})
    anchor_points = pattern.get("anchor_points", {})
    breakout = pattern.get("breakout_level")
    invalidation = pattern.get("invalidation")
    
    geometry = PatternGeometry()
    
    # =====================================================
    # HELPER: Convert list-based points to dict format
    # =====================================================
    points = _normalize_points_format(raw_points, pattern_type)
    
    # ===========================================
    # TRIANGLES
    # ===========================================
    if "triangle" in pattern_type:
        # Upper line (resistance or descending trendline)
        if "upper" in points and len(points["upper"]) >= 2:
            upper_pts = points["upper"]
            kind = "resistance" if "ascending" in pattern_type else "resistance_falling"
            geometry.segments.append(GeometrySegment(
                kind=kind,
                points=[_to_point(p) for p in upper_pts],
                style="solid",
                color="#ef4444" if "descending" in pattern_type else "#64748b"
            ))
        
        # Lower line (support or ascending trendline)
        if "lower" in points and len(points["lower"]) >= 2:
            lower_pts = points["lower"]
            kind = "support_rising" if "ascending" in pattern_type else "support"
            geometry.segments.append(GeometrySegment(
                kind=kind,
                points=[_to_point(p) for p in lower_pts],
                style="solid",
                color="#16a34a" if "ascending" in pattern_type else "#64748b"
            ))
        
        # Anchor markers
        for side, anchors in anchor_points.items():
            if isinstance(anchors, list):
                for i, a in enumerate(anchors):
                    geometry.markers.append(GeometryMarker(
                        kind="anchor",
                        time=_get_time(a),
                        price=_get_price(a),
                        label=f"{side[0].upper()}{i+1}"
                    ))
    
    # ===========================================
    # CHANNELS (ascending, descending, horizontal)
    # ===========================================
    elif "channel" in pattern_type:
        if "upper" in points and len(points["upper"]) >= 2:
            geometry.segments.append(GeometrySegment(
                kind="upper_channel",
                points=[_to_point(p) for p in points["upper"]],
                style="solid",
                color="#ef4444"
            ))
        if "lower" in points and len(points["lower"]) >= 2:
            geometry.segments.append(GeometrySegment(
                kind="lower_channel",
                points=[_to_point(p) for p in points["lower"]],
                style="solid",
                color="#16a34a"
            ))
    
    # ===========================================
    # HEAD & SHOULDERS (handles nested markers)
    # ===========================================
    elif "head" in pattern_type and "shoulder" in pattern_type:
        is_inverse = "inverse" in pattern_type
        
        # Build neckline from upper/lower points
        neckline_key = "upper" if is_inverse else "lower"
        if neckline_key in points and len(points[neckline_key]) >= 2:
            geometry.segments.append(GeometrySegment(
                kind="neckline",
                points=[_to_point(p) for p in points[neckline_key]],
                style="dashed",
                color="#f59e0b"
            ))
        
        # Handle nested markers format: points.markers.left_shoulder
        markers_data = points.get("markers", {})
        if isinstance(markers_data, dict):
            for key in ["left_shoulder", "head", "right_shoulder"]:
                if key in markers_data:
                    p = markers_data[key]
                    geometry.markers.append(GeometryMarker(
                        kind=key,
                        time=_get_time(p),
                        price=_get_price(p),
                        label=key.replace("_", " ").title()
                    ))
        
        # Also check flat format: points.left_shoulder
        for key in ["left_shoulder", "head", "right_shoulder"]:
            if key in points and key not in (markers_data or {}):
                p = points[key]
                geometry.markers.append(GeometryMarker(
                    kind=key,
                    time=_get_time(p),
                    price=_get_price(p),
                    label=key.replace("_", " ").title()
                ))
    
    # ===========================================
    # DOUBLE TOP / BOTTOM
    # ===========================================
    elif "double" in pattern_type:
        is_top = "top" in pattern_type
        marker_kind = "peak" if is_top else "trough"
        label_prefix = "T" if is_top else "B"
        
        # Handle various peak formats
        peaks = []
        if "peaks" in points:
            peaks = points["peaks"]
        elif "top1" in points or "bottom1" in points:
            key1 = "top1" if is_top else "bottom1"
            key2 = "top2" if is_top else "bottom2"
            peaks = [points.get(key1), points.get(key2)]
        elif "peak1" in points:
            peaks = [points.get("peak1"), points.get("peak2")]
        
        for i, p in enumerate(peaks):
            if p:
                geometry.markers.append(GeometryMarker(
                    kind=marker_kind,
                    time=_get_time(p),
                    price=_get_price(p),
                    label=f"{label_prefix}{i+1}"
                ))
        
        # Neckline
        if "neckline" in points:
            neckline_data = points["neckline"]
            if isinstance(neckline_data, list) and len(neckline_data) >= 2:
                geometry.segments.append(GeometrySegment(
                    kind="neckline",
                    points=[_to_point(p) for p in neckline_data],
                    style="dashed",
                    color="#f59e0b"
                ))
            elif isinstance(neckline_data, dict):
                # Single neckline point - create horizontal line
                neckline_price = _get_price(neckline_data)
                neckline_time = _get_time(neckline_data)
                if neckline_price and peaks:
                    first_time = _get_time(peaks[0]) if peaks[0] else neckline_time
                    last_time = _get_time(peaks[-1]) if peaks[-1] else neckline_time
                    geometry.segments.append(GeometrySegment(
                        kind="neckline",
                        points=[
                            {"time": first_time, "price": neckline_price},
                            {"time": last_time, "price": neckline_price}
                        ],
                        style="dashed",
                        color="#f59e0b"
                    ))
    
    # ===========================================
    # WEDGE (rising, falling)
    # ===========================================
    elif "wedge" in pattern_type:
        if "upper" in points and isinstance(points["upper"], list) and len(points["upper"]) >= 2:
            geometry.segments.append(GeometrySegment(
                kind="trendline_upper",
                points=[_to_point(p) for p in points["upper"]],
                style="solid",
                color="#ef4444"
            ))
        if "lower" in points and isinstance(points["lower"], list) and len(points["lower"]) >= 2:
            geometry.segments.append(GeometrySegment(
                kind="trendline_lower",
                points=[_to_point(p) for p in points["lower"]],
                style="solid",
                color="#16a34a"
            ))
    
    # ===========================================
    # FLAG / PENNANT
    # ===========================================
    elif "flag" in pattern_type or "pennant" in pattern_type:
        # Pole
        if "pole" in points and isinstance(points["pole"], list) and len(points["pole"]) >= 2:
            geometry.segments.append(GeometrySegment(
                kind="pole",
                points=[_to_point(p) for p in points["pole"]],
                style="solid",
                color="#3b82f6"
            ))
        
        # Flag boundaries (if available)
        if "flag_upper" in points and isinstance(points["flag_upper"], list):
            geometry.segments.append(GeometrySegment(
                kind="flag_upper",
                points=[_to_point(p) for p in points["flag_upper"]],
                style="solid",
                color="#64748b"
            ))
        if "flag_lower" in points and isinstance(points["flag_lower"], list):
            geometry.segments.append(GeometrySegment(
                kind="flag_lower",
                points=[_to_point(p) for p in points["flag_lower"]],
                style="solid",
                color="#64748b"
            ))
        
        # If pole points from list format
        if "pole" not in points and len(points.get("points", [])) >= 2:
            pole_points = [p for p in points.get("points", []) if "pole" in p.get("type", "")]
            if len(pole_points) >= 2:
                geometry.segments.append(GeometrySegment(
                    kind="pole",
                    points=[_to_point(p) for p in pole_points],
                    style="solid",
                    color="#3b82f6"
                ))
    
    # ===========================================
    # COMPRESSION / SQUEEZE
    # ===========================================
    elif "compression" in pattern_type or "squeeze" in pattern_type:
        # Add zone for compression area
        start_pt = points.get("start")
        end_pt = points.get("end")
        if start_pt and end_pt:
            # Get price range from breakout/invalidation or estimate
            price_top = breakout or _get_price(end_pt) * 1.02
            price_bottom = invalidation or _get_price(end_pt) * 0.98
            geometry.zones.append(GeometryZone(
                kind="consolidation",
                time_start=_get_time(start_pt),
                time_end=_get_time(end_pt),
                price_top=price_top,
                price_bottom=price_bottom,
                opacity=0.1,
                color="#64748b"
            ))
    
    # ===========================================
    # RANGE / RECTANGLE  
    # ===========================================
    elif "range" in pattern_type or "rectangle" in pattern_type:
        # Upper boundary
        if "upper" in points and isinstance(points["upper"], list) and len(points["upper"]) >= 2:
            geometry.segments.append(GeometrySegment(
                kind="resistance",
                points=[_to_point(p) for p in points["upper"]],
                style="solid",
                color="#ef4444"
            ))
        elif "resistance" in points and isinstance(points["resistance"], list):
            geometry.segments.append(GeometrySegment(
                kind="resistance",
                points=[_to_point(p) for p in points["resistance"]],
                style="solid",
                color="#ef4444"
            ))
        
        # Lower boundary
        if "lower" in points and isinstance(points["lower"], list) and len(points["lower"]) >= 2:
            geometry.segments.append(GeometrySegment(
                kind="support",
                points=[_to_point(p) for p in points["lower"]],
                style="solid",
                color="#16a34a"
            ))
        elif "support" in points and isinstance(points["support"], list):
            geometry.segments.append(GeometrySegment(
                kind="support",
                points=[_to_point(p) for p in points["support"]],
                style="solid",
                color="#16a34a"
            ))
        
        # Add zone if we have both levels
        if breakout and invalidation:
            all_times = []
            for key, pts in points.items():
                if isinstance(pts, list):
                    for p in pts:
                        t = _get_time(p)
                        if t:
                            all_times.append(t)
            if all_times:
                geometry.zones.append(GeometryZone(
                    kind="pattern_area",
                    time_start=min(all_times),
                    time_end=max(all_times),
                    price_top=max(breakout, invalidation),
                    price_bottom=min(breakout, invalidation),
                    opacity=0.08
                ))
    
    # ===========================================
    # BREAKOUT / BREAKDOWN
    # ===========================================
    elif "breakout" in pattern_type or "breakdown" in pattern_type:
        # Simple marker at breakout point
        level_price = points.get("level") or breakout
        if level_price:
            geometry.markers.append(GeometryMarker(
                kind="breakout_point",
                time=_get_time(points) if isinstance(points, dict) else 0,
                price=level_price if isinstance(level_price, (int, float)) else _get_price({"price": level_price}),
                label="Breakout" if "up" in pattern_type else "Breakdown"
            ))
    
    # ===========================================
    # COMMON: LEVELS (breakout, invalidation)
    # ===========================================
    if breakout:
        geometry.levels.append(GeometryLevel(
            kind="breakout",
            price=breakout,
            label="Breakout",
            style="dashed",
            color="#16a34a"
        ))
    
    if invalidation:
        geometry.levels.append(GeometryLevel(
            kind="invalidation",
            price=invalidation,
            label="Invalidation",
            style="dotted",
            color="#ef4444"
        ))
    
    # ===========================================
    # BUILD FINAL CONTRACT
    # ===========================================
    label_map = {
        "ascending_triangle": "Ascending Triangle",
        "descending_triangle": "Descending Triangle",
        "symmetrical_triangle": "Symmetrical Triangle",
        "ascending_channel": "Ascending Channel",
        "descending_channel": "Descending Channel",
        "horizontal_channel": "Horizontal Channel",
        "head_shoulders": "Head & Shoulders",
        "head_and_shoulders": "Head & Shoulders",
        "inverse_head_shoulders": "Inverse Head & Shoulders",
        "inverse_head_and_shoulders": "Inverse Head & Shoulders",
        "double_top": "Double Top",
        "double_bottom": "Double Bottom",
        "triple_top": "Triple Top",
        "triple_bottom": "Triple Bottom",
        "rising_wedge": "Rising Wedge",
        "falling_wedge": "Falling Wedge",
        "bull_flag": "Bull Flag",
        "bear_flag": "Bear Flag",
        "pennant": "Pennant",
        "range": "Trading Range",
        "rectangle": "Rectangle",
        "compression": "Compression",
        "squeeze": "Squeeze",
        "breakout_up": "Breakout Up",
        "breakdown": "Breakdown",
    }
    
    return {
        "type": pattern_type,
        "label": label_map.get(pattern_type, pattern_type.replace("_", " ").title()),
        "direction": pattern.get("direction", "neutral"),
        "confidence": round(pattern.get("confidence", 0), 2),
        "status": "active",
        "geometry": geometry.to_dict(),
    }


# Singleton for easy import
def get_geometry_normalizer():
    return normalize_pattern_geometry
