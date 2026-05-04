"""
Pattern Render Builder — Unified Render Contract
=================================================

CRITICAL: This is what was MISSING.

Backend is smart (patterns, ranking, triggers, regime).
Frontend is blind (doesn't know HOW to draw).

This layer translates:
    pattern → geometry → render_contract

One unified format for ALL patterns:
{
    "type": "double_top",
    "render_mode": "polyline",
    "window": {"start": time, "end": time},
    "polyline": [...points],
    "levels": [...horizontal lines],
    "lines": [...trendlines],
    "points": [...markers]
}

Frontend just does: switch(render.type) → draw()
"""

from typing import Any, Dict, List, Optional


def _norm_time(t):
    """Normalize timestamp to seconds (int)."""
    if t is None:
        return None
    
    # Already a number
    if isinstance(t, (int, float)):
        # Handle milliseconds vs seconds
        if t > 9999999999:
            return int(t / 1000)
        return int(t)
    
    # ISO string
    if isinstance(t, str):
        from datetime import datetime
        try:
            # Try parsing ISO format
            if 'T' in t:
                dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
                return int(dt.timestamp())
            # Try direct int conversion
            return int(t)
        except (ValueError, TypeError):
            return None
    
    return None


def _point(time, price, label=None):
    """Create a point object."""
    p = {
        "time": _norm_time(time),
        "price": float(price) if price is not None else None,
    }
    if label:
        p["label"] = label
    return p


def _extract_point(data: Dict, key: str) -> Optional[Dict]:
    """Extract point from various formats."""
    if not data:
        return None
    
    # Direct point
    if key in data:
        pt = data[key]
        if isinstance(pt, dict):
            time = pt.get("time") or pt.get("timestamp") or pt.get("index")
            price = pt.get("price") or pt.get("value")
            if time is not None and price is not None:
                return {"time": time, "price": price}
    
    return None


def build_render_contract(
    dominant: Optional[Dict[str, Any]], 
    active_range: Optional[Dict[str, Any]] = None,
    candles: List[Dict] = None
) -> Optional[Dict[str, Any]]:
    """
    Main entry point — builds render contract from dominant pattern.
    
    Returns unified format that frontend can draw.
    """
    # Priority: active range first (it's the clearest visual)
    if active_range and active_range.get("top") and active_range.get("bottom"):
        return build_range_render(active_range, candles)
    
    if not dominant:
        return None
    
    ptype = dominant.get("type", "").lower()
    
    # Route to specific builder
    if ptype in ("double_top", "double_bottom"):
        return build_double_pattern_render(dominant, ptype, candles)
    
    if ptype in ("triple_top", "triple_bottom"):
        return build_triple_pattern_render(dominant, ptype, candles)
    
    if "triangle" in ptype:
        return build_triangle_render(dominant, ptype, candles)
    
    if "wedge" in ptype:
        return build_wedge_render(dominant, ptype, candles)
    
    if ptype in ("inverse_head_shoulders", "head_shoulders"):
        return build_hs_render(dominant, ptype, candles)
    
    if "range" in ptype or "rectangle" in ptype:
        return build_pattern_range_render(dominant, candles)
    
    if "channel" in ptype:
        return build_channel_render(dominant, ptype, candles)
    
    return None


# =============================================================================
# RANGE / RECTANGLE
# =============================================================================

def build_range_render(r: Dict[str, Any], candles: List[Dict] = None) -> Dict[str, Any]:
    """Build render for range/rectangle pattern."""
    top = r.get("top") or r.get("resistance")
    bottom = r.get("bottom") or r.get("support")
    
    if top is None or bottom is None:
        return None
    
    # Get time window
    left_time = r.get("left_time") or r.get("start_time") or r.get("start_index")
    right_time = r.get("right_time") or r.get("end_time") or r.get("end_index")
    
    # Fallback to candles
    if candles and (left_time is None or right_time is None):
        if left_time is None:
            left_time = candles[0].get("time", candles[0].get("timestamp", 0))
        if right_time is None:
            right_time = candles[-1].get("time", candles[-1].get("timestamp", 0))
    
    return {
        "type": "range",
        "render_mode": "box",
        "window": {
            "start": _norm_time(left_time),
            "end": _norm_time(right_time),
        },
        "box": {
            "top": float(top),
            "bottom": float(bottom),
        },
        "labels": [
            {"kind": "resistance", "price": float(top), "text": f"R {float(top):,.0f}"},
            {"kind": "support", "price": float(bottom), "text": f"S {float(bottom):,.0f}"},
        ],
    }


def build_pattern_range_render(p: Dict[str, Any], candles: List[Dict] = None) -> Optional[Dict[str, Any]]:
    """Build render for pattern-based range."""
    top = p.get("resistance") or p.get("bounds", {}).get("top")
    bottom = p.get("support") or p.get("bounds", {}).get("bottom")
    
    if top is None or bottom is None:
        return None
    
    # Get window from pattern
    start_idx = p.get("start_index", 0)
    end_idx = p.get("end_index", -1)
    
    left_time = None
    right_time = None
    
    if candles:
        if start_idx < len(candles):
            left_time = candles[start_idx].get("time", candles[start_idx].get("timestamp"))
        if end_idx == -1 or end_idx >= len(candles):
            right_time = candles[-1].get("time", candles[-1].get("timestamp"))
        elif end_idx < len(candles):
            right_time = candles[end_idx].get("time", candles[end_idx].get("timestamp"))
    
    return {
        "type": p.get("type", "range"),
        "render_mode": "box",
        "window": {
            "start": _norm_time(left_time),
            "end": _norm_time(right_time),
        },
        "box": {
            "top": float(top),
            "bottom": float(bottom),
        },
        "labels": [
            {"kind": "resistance", "price": float(top), "text": f"R {float(top):,.0f}"},
            {"kind": "support", "price": float(bottom), "text": f"S {float(bottom):,.0f}"},
        ],
    }


# =============================================================================
# DOUBLE TOP / DOUBLE BOTTOM
# =============================================================================

def build_double_pattern_render(p: Dict[str, Any], ptype: str, candles: List[Dict] = None) -> Optional[Dict[str, Any]]:
    """Build render for double top/bottom."""
    # Extract points from various formats
    peaks = p.get("peaks", [])
    troughs = p.get("troughs", [])
    neckline = p.get("neckline")
    
    p1 = None
    p2 = None
    valley = None
    
    if ptype == "double_top":
        # Two peaks, one valley between
        if len(peaks) >= 2:
            p1 = peaks[0]
            p2 = peaks[1]
        if len(troughs) >= 1:
            valley = troughs[0]
    else:  # double_bottom
        # Two troughs, one peak between
        if len(troughs) >= 2:
            p1 = troughs[0]
            p2 = troughs[1]
        if len(peaks) >= 1:
            valley = peaks[0]
    
    if not p1 or not p2 or not valley:
        return None
    
    # Get timestamps from candles if using indices
    def get_point_with_time(pt, candles):
        if not pt:
            return None
        
        time = pt.get("time") or pt.get("timestamp")
        price = pt.get("price")
        idx = pt.get("index")
        
        if time is None and idx is not None and candles and idx < len(candles):
            time = candles[idx].get("time", candles[idx].get("timestamp"))
        
        if time is None or price is None:
            return None
        
        return {"time": time, "price": price}
    
    p1_pt = get_point_with_time(p1, candles)
    p2_pt = get_point_with_time(p2, candles)
    valley_pt = get_point_with_time(valley, candles)
    
    if not p1_pt or not p2_pt or not valley_pt:
        return None
    
    times = [p1_pt["time"], valley_pt["time"], p2_pt["time"]]
    left_time = min(times)
    right_time = max(times)
    
    return {
        "type": ptype,
        "render_mode": "polyline",
        "window": {
            "start": _norm_time(left_time),
            "end": _norm_time(right_time),
        },
        "polyline": [
            _point(p1_pt["time"], p1_pt["price"], "P1"),
            _point(valley_pt["time"], valley_pt["price"], "V"),
            _point(p2_pt["time"], p2_pt["price"], "P2"),
        ],
        "levels": [
            {"kind": "neckline", "price": float(neckline)} if neckline else None,
            {"kind": "target", "price": float(p.get("target"))} if p.get("target") else None,
        ],
    }


# =============================================================================
# TRIPLE TOP / TRIPLE BOTTOM
# =============================================================================

def build_triple_pattern_render(p: Dict[str, Any], ptype: str, candles: List[Dict] = None) -> Optional[Dict[str, Any]]:
    """Build render for triple top/bottom."""
    peaks = p.get("peaks", [])
    troughs = p.get("troughs", [])
    neckline = p.get("neckline")
    
    def get_point_with_time(pt, candles):
        if not pt:
            return None
        time = pt.get("time") or pt.get("timestamp")
        price = pt.get("price")
        idx = pt.get("index")
        if time is None and idx is not None and candles and idx < len(candles):
            time = candles[idx].get("time", candles[idx].get("timestamp"))
        if time is None or price is None:
            return None
        return {"time": time, "price": price}
    
    polyline = []
    
    if ptype == "triple_top":
        # P1 - V1 - P2 - V2 - P3
        if len(peaks) >= 3 and len(troughs) >= 2:
            polyline = [
                get_point_with_time(peaks[0], candles),
                get_point_with_time(troughs[0], candles),
                get_point_with_time(peaks[1], candles),
                get_point_with_time(troughs[1], candles),
                get_point_with_time(peaks[2], candles),
            ]
    else:  # triple_bottom
        if len(troughs) >= 3 and len(peaks) >= 2:
            polyline = [
                get_point_with_time(troughs[0], candles),
                get_point_with_time(peaks[0], candles),
                get_point_with_time(troughs[1], candles),
                get_point_with_time(peaks[1], candles),
                get_point_with_time(troughs[2], candles),
            ]
    
    # Filter None points
    polyline = [pt for pt in polyline if pt]
    
    if len(polyline) < 3:
        return None
    
    times = [pt["time"] for pt in polyline]
    
    return {
        "type": ptype,
        "render_mode": "polyline",
        "window": {
            "start": _norm_time(min(times)),
            "end": _norm_time(max(times)),
        },
        "polyline": [
            _point(pt["time"], pt["price"], f"P{i+1}" if i % 2 == 0 else f"V{i//2+1}")
            for i, pt in enumerate(polyline)
        ],
        "levels": [
            {"kind": "neckline", "price": float(neckline)} if neckline else None,
        ],
    }


# =============================================================================
# TRIANGLES
# =============================================================================

def build_triangle_render(p: Dict[str, Any], ptype: str, candles: List[Dict] = None) -> Optional[Dict[str, Any]]:
    """Build render for triangle patterns."""
    # Get swing points
    swing_highs = p.get("swing_highs", [])
    swing_lows = p.get("swing_lows", [])
    
    # Also check direct highs/lows
    if not swing_highs:
        swing_highs = p.get("highs", [])
    if not swing_lows:
        swing_lows = p.get("lows", [])
    
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        # Try to build from upper_line/lower_line
        upper = p.get("upper_line", {})
        lower = p.get("lower_line", {})
        
        if upper.get("start") and upper.get("end") and lower.get("start") and lower.get("end"):
            upper_from = upper["start"]
            upper_to = upper["end"]
            lower_from = lower["start"]
            lower_to = lower["end"]
            
            def get_time(pt, candles):
                t = pt.get("time") or pt.get("timestamp")
                if t is None and pt.get("index") is not None and candles:
                    idx = pt["index"]
                    if idx < len(candles):
                        t = candles[idx].get("time", candles[idx].get("timestamp"))
                return t
            
            times = [
                get_time(upper_from, candles),
                get_time(upper_to, candles),
                get_time(lower_from, candles),
                get_time(lower_to, candles),
            ]
            times = [t for t in times if t is not None]
            
            if len(times) < 4:
                return None
            
            return {
                "type": ptype,
                "render_mode": "two_lines",
                "window": {
                    "start": _norm_time(min(times)),
                    "end": _norm_time(max(times)),
                },
                "lines": [
                    {
                        "kind": "upper",
                        "from": _point(get_time(upper_from, candles), upper_from.get("price")),
                        "to": _point(get_time(upper_to, candles), upper_to.get("price")),
                    },
                    {
                        "kind": "lower",
                        "from": _point(get_time(lower_from, candles), lower_from.get("price")),
                        "to": _point(get_time(lower_to, candles), lower_to.get("price")),
                    },
                ],
                "points": [],
            }
        return None
    
    def get_point_with_time(pt, candles):
        if not pt:
            return None
        time = pt.get("time") or pt.get("timestamp")
        price = pt.get("price")
        idx = pt.get("index")
        if time is None and idx is not None and candles and idx < len(candles):
            time = candles[idx].get("time", candles[idx].get("timestamp"))
        if time is None or price is None:
            return None
        return {"time": time, "price": price}
    
    # Get boundary points
    upper_from = get_point_with_time(swing_highs[0], candles)
    upper_to = get_point_with_time(swing_highs[-1], candles)
    lower_from = get_point_with_time(swing_lows[0], candles)
    lower_to = get_point_with_time(swing_lows[-1], candles)
    
    if not upper_from or not upper_to or not lower_from or not lower_to:
        return None
    
    times = [upper_from["time"], upper_to["time"], lower_from["time"], lower_to["time"]]
    
    # All points for markers
    all_points = []
    for h in swing_highs:
        pt = get_point_with_time(h, candles)
        if pt:
            all_points.append(pt)
    for l in swing_lows:
        pt = get_point_with_time(l, candles)
        if pt:
            all_points.append(pt)
    
    return {
        "type": ptype,
        "render_mode": "two_lines",
        "window": {
            "start": _norm_time(min(times)),
            "end": _norm_time(max(times)),
        },
        "lines": [
            {
                "kind": "upper",
                "from": _point(upper_from["time"], upper_from["price"]),
                "to": _point(upper_to["time"], upper_to["price"]),
            },
            {
                "kind": "lower",
                "from": _point(lower_from["time"], lower_from["price"]),
                "to": _point(lower_to["time"], lower_to["price"]),
            },
        ],
        "points": [_point(pt["time"], pt["price"]) for pt in all_points],
    }


# =============================================================================
# WEDGES
# =============================================================================

def build_wedge_render(p: Dict[str, Any], ptype: str, candles: List[Dict] = None) -> Optional[Dict[str, Any]]:
    """Build render for wedge patterns — same as triangles."""
    return build_triangle_render(p, ptype, candles)


# =============================================================================
# HEAD & SHOULDERS
# =============================================================================

def build_hs_render(p: Dict[str, Any], ptype: str, candles: List[Dict] = None) -> Optional[Dict[str, Any]]:
    """Build render for H&S patterns."""
    # Try to get from pattern data
    left_shoulder = p.get("left_shoulder")
    head = p.get("head")
    right_shoulder = p.get("right_shoulder")
    neckline = p.get("neckline")
    
    # Also check nested points
    pts = p.get("points", {})
    if not left_shoulder:
        left_shoulder = pts.get("left_shoulder")
    if not head:
        head = pts.get("head")
    if not right_shoulder:
        right_shoulder = pts.get("right_shoulder")
    
    def get_point_with_time(pt, candles):
        if not pt:
            return None
        time = pt.get("time") or pt.get("timestamp")
        price = pt.get("price")
        idx = pt.get("index")
        if time is None and idx is not None and candles and idx < len(candles):
            time = candles[idx].get("time", candles[idx].get("timestamp"))
        if time is None or price is None:
            return None
        return {"time": time, "price": price}
    
    ls_pt = get_point_with_time(left_shoulder, candles)
    h_pt = get_point_with_time(head, candles)
    rs_pt = get_point_with_time(right_shoulder, candles)
    
    if not ls_pt or not h_pt or not rs_pt:
        return None
    
    times = [ls_pt["time"], h_pt["time"], rs_pt["time"]]
    
    # Neckline points (if available)
    nl_left = p.get("neckline_left") or pts.get("neckline_left")
    nl_right = p.get("neckline_right") or pts.get("neckline_right")
    
    nl_left_pt = get_point_with_time(nl_left, candles)
    nl_right_pt = get_point_with_time(nl_right, candles)
    
    lines = []
    if nl_left_pt and nl_right_pt:
        lines.append({
            "kind": "neckline",
            "from": _point(nl_left_pt["time"], nl_left_pt["price"]),
            "to": _point(nl_right_pt["time"], nl_right_pt["price"]),
        })
    elif neckline is not None:
        # Draw horizontal neckline
        lines.append({
            "kind": "neckline",
            "from": _point(min(times), neckline),
            "to": _point(max(times), neckline),
        })
    
    return {
        "type": ptype,
        "render_mode": "hs",
        "window": {
            "start": _norm_time(min(times)),
            "end": _norm_time(max(times)),
        },
        "polyline": [
            _point(ls_pt["time"], ls_pt["price"], "LS"),
            _point(h_pt["time"], h_pt["price"], "H"),
            _point(rs_pt["time"], rs_pt["price"], "RS"),
        ],
        "lines": lines,
    }


# =============================================================================
# CHANNELS
# =============================================================================

def build_channel_render(p: Dict[str, Any], ptype: str, candles: List[Dict] = None) -> Optional[Dict[str, Any]]:
    """Build render for channel patterns."""
    # Same as triangles/wedges - two parallel lines
    return build_triangle_render(p, ptype, candles)
