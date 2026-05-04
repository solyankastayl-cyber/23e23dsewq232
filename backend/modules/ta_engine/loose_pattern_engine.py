"""
LOOSE PATTERN ENGINE — Human-like Interpretation Layer
========================================================

When STRICT engine says "no pattern", this layer provides
intelligent interpretation like a real trader would.

STRICT = truth (textbook patterns)
LOOSE = interpretation (developing formations)

LOOSE patterns are rendered differently:
- Lower opacity
- Dashed lines
- "Developing" label
"""

from typing import List, Dict, Optional


# ═══════════════════════════════════════════════════════════════
# PATTERN PRIORITY (stops chaos - higher = more important)
# ═══════════════════════════════════════════════════════════════

PATTERN_PRIORITY = {
    "head_shoulders": 10,
    "inverse_head_shoulders": 10,
    "double_top": 9,
    "double_bottom": 9,
    "triple_top": 9,
    "triple_bottom": 9,
    "ascending_triangle": 8,
    "descending_triangle": 8,
    "symmetrical_triangle": 8,
    "falling_wedge": 7,
    "rising_wedge": 7,
    "bull_flag": 7,
    "bear_flag": 7,
    "channel": 5,
    "range": 4,
    "loose_wedge": 3,
    "loose_triangle": 3,
    "loose_range": 2,
    "structure": 1,
}


# ═══════════════════════════════════════════════════════════════
# RENDER PROFILES (how to draw each mode)
# ═══════════════════════════════════════════════════════════════

RENDER_PROFILE = {
    "strict": {
        "opacity": 0.22,
        "lineWidth": 2.5,
        "dash": False,
        "fill": True,
    },
    "loose": {
        "opacity": 0.10,
        "lineWidth": 1.5,
        "dash": True,
        "fill": True,
    },
}


# ═══════════════════════════════════════════════════════════════
# PATTERN MODEL (unified structure)
# ═══════════════════════════════════════════════════════════════

def make_pattern(
    p_type: str,
    anchors: List[Dict],
    confidence: float,
    quality: float,
    priority: int = None,
    mode: str = "strict",
    bias: str = "neutral",
    meta: Dict = None,
) -> Dict:
    """Create unified pattern object"""
    if priority is None:
        priority = PATTERN_PRIORITY.get(p_type, 1)
    
    return {
        "type": p_type,
        "anchors": anchors,
        "confidence": confidence,
        "quality": quality,
        "priority": priority,
        "mode": mode,  # strict | loose
        "bias": bias,
        "meta": meta or {},
        "render_profile": RENDER_PROFILE.get(mode, RENDER_PROFILE["loose"]),
    }


# ═══════════════════════════════════════════════════════════════
# ANCHOR BUILDER (shared utility)
# ═══════════════════════════════════════════════════════════════

def order_polygon_anchors(anchors: List[Dict]) -> List[Dict]:
    """
    Order anchors for correct polygon rendering.
    
    ECharts draws polygon as: point1 → point2 → point3 → point4
    If order is wrong → crosses / garbage / broken figures
    
    Correct order:
    - top-left → top-right → bottom-right → bottom-left
    """
    if len(anchors) < 4:
        return anchors
    
    # Separate top (higher prices) and bottom (lower prices)
    sorted_by_price = sorted(anchors, key=lambda x: x.get("price", 0), reverse=True)
    top_two = sorted_by_price[:2]
    bottom_two = sorted_by_price[2:]
    
    # Sort top by time (left to right)
    top = sorted(top_two, key=lambda x: x.get("time", 0))
    # Sort bottom by time reversed (right to left for polygon closure)
    bottom = sorted(bottom_two, key=lambda x: x.get("time", 0), reverse=True)
    
    return top + bottom


def build_anchors(highs: List[Dict], lows: List[Dict]) -> List[Dict]:
    """Build polygon anchors from highs/lows - CORRECTLY ORDERED"""
    if not highs or not lows:
        return []
    
    # Sort by time
    highs_sorted = sorted(highs, key=lambda x: x.get("time", 0))
    lows_sorted = sorted(lows, key=lambda x: x.get("time", 0))
    
    anchors = [
        {"time": highs_sorted[0]["time"], "price": highs_sorted[0]["price"]},   # Top-left
        {"time": highs_sorted[-1]["time"], "price": highs_sorted[-1]["price"]}, # Top-right
        {"time": lows_sorted[-1]["time"], "price": lows_sorted[-1]["price"]},   # Bottom-right
        {"time": lows_sorted[0]["time"], "price": lows_sorted[0]["price"]},     # Bottom-left
    ]
    
    return order_polygon_anchors(anchors)


def build_boundaries(highs: List[Dict], lows: List[Dict]) -> Dict:
    """Build upper/lower boundaries for rendering"""
    if not highs or not lows:
        return {}
    
    # Sort by time for correct line drawing
    highs_sorted = sorted(highs, key=lambda x: x.get("time", 0))
    lows_sorted = sorted(lows, key=lambda x: x.get("time", 0))
    
    return {
        "upper": {
            "x1": highs_sorted[0]["time"],
            "y1": highs_sorted[0]["price"],
            "x2": highs_sorted[-1]["time"],
            "y2": highs_sorted[-1]["price"],
        },
        "lower": {
            "x1": lows_sorted[0]["time"],
            "y1": lows_sorted[0]["price"],
            "x2": lows_sorted[-1]["time"],
            "y2": lows_sorted[-1]["price"],
        },
    }


def build_pattern_window(anchors: List[Dict]) -> Dict:
    """Build time window for pattern (for zoom/focus)"""
    if not anchors:
        return {}
    
    times = [a.get("time", 0) for a in anchors]
    prices = [a.get("price", 0) for a in anchors]
    
    return {
        "start": min(times),
        "end": max(times),
        "price_high": max(prices),
        "price_low": min(prices),
    }


# ═══════════════════════════════════════════════════════════════
# LOOSE WEDGE DETECTOR
# ═══════════════════════════════════════════════════════════════

def detect_loose_wedge(pivots: List[Dict]) -> Optional[Dict]:
    """
    Detect developing wedge-like structure.
    
    Less strict than textbook wedge - allows for messier structure.
    """
    highs = [p for p in pivots if p.get("type") == "high"][-4:]
    lows = [p for p in pivots if p.get("type") == "low"][-4:]
    
    if len(highs) < 3 or len(lows) < 3:
        return None
    
    # Check if both lines are trending in same direction (wedge characteristic)
    high_drop = highs[0]["price"] - highs[-1]["price"]
    low_drop = lows[0]["price"] - lows[-1]["price"]
    
    # Falling wedge-like: both dropping
    if high_drop > 0 and low_drop > 0:
        # Check rough compression (end width < start width)
        start_width = abs(highs[0]["price"] - lows[0]["price"])
        end_width = abs(highs[-1]["price"] - lows[-1]["price"])
        
        if start_width > 0 and end_width / start_width < 0.95:  # Loose compression
            return make_pattern(
                p_type="loose_wedge",
                anchors=build_anchors(highs, lows),
                confidence=0.40,
                quality=0.35,
                mode="loose",
                bias="bullish",  # Falling wedge = bullish breakout expected
                meta={
                    "subtype": "falling",
                    "boundaries": build_boundaries(highs, lows),
                    "compression": end_width / start_width,
                },
            )
    
    # Rising wedge-like: both rising
    if high_drop < 0 and low_drop < 0:
        start_width = abs(highs[0]["price"] - lows[0]["price"])
        end_width = abs(highs[-1]["price"] - lows[-1]["price"])
        
        if start_width > 0 and end_width / start_width < 0.95:
            return make_pattern(
                p_type="loose_wedge",
                anchors=build_anchors(highs, lows),
                confidence=0.40,
                quality=0.35,
                mode="loose",
                bias="bearish",  # Rising wedge = bearish breakdown expected
                meta={
                    "subtype": "rising",
                    "boundaries": build_boundaries(highs, lows),
                    "compression": end_width / start_width,
                },
            )
    
    return None


# ═══════════════════════════════════════════════════════════════
# LOOSE TRIANGLE DETECTOR
# ═══════════════════════════════════════════════════════════════

def detect_loose_triangle(pivots: List[Dict]) -> Optional[Dict]:
    """
    Detect developing triangle-like structure.
    
    Triangle: one line flat-ish, other line sloping towards it.
    """
    highs = [p for p in pivots if p.get("type") == "high"][-4:]
    lows = [p for p in pivots if p.get("type") == "low"][-4:]
    
    if len(highs) < 3 or len(lows) < 3:
        return None
    
    # Calculate ranges
    high_range = abs(highs[0]["price"] - highs[-1]["price"])
    low_range = abs(lows[0]["price"] - lows[-1]["price"])
    avg_price = (highs[0]["price"] + lows[0]["price"]) / 2
    
    high_flat = high_range / avg_price < 0.03  # Within 3%
    low_flat = low_range / avg_price < 0.03
    
    low_rising = lows[-1]["price"] > lows[0]["price"]
    high_falling = highs[-1]["price"] < highs[0]["price"]
    
    # Ascending triangle: flat top, rising bottom
    if high_flat and low_rising:
        return make_pattern(
            p_type="loose_triangle",
            anchors=build_anchors(highs, lows),
            confidence=0.45,
            quality=0.40,
            mode="loose",
            bias="bullish",
            meta={
                "subtype": "ascending",
                "boundaries": build_boundaries(highs, lows),
            },
        )
    
    # Descending triangle: flat bottom, falling top
    if low_flat and high_falling:
        return make_pattern(
            p_type="loose_triangle",
            anchors=build_anchors(highs, lows),
            confidence=0.45,
            quality=0.40,
            mode="loose",
            bias="bearish",
            meta={
                "subtype": "descending",
                "boundaries": build_boundaries(highs, lows),
            },
        )
    
    # Symmetrical: both converging
    if high_falling and low_rising:
        return make_pattern(
            p_type="loose_triangle",
            anchors=build_anchors(highs, lows),
            confidence=0.42,
            quality=0.38,
            mode="loose",
            bias="neutral",
            meta={
                "subtype": "symmetrical",
                "boundaries": build_boundaries(highs, lows),
            },
        )
    
    return None


# ═══════════════════════════════════════════════════════════════
# LOOSE RANGE DETECTOR (always returns something)
# ═══════════════════════════════════════════════════════════════

def detect_loose_range(pivots: List[Dict]) -> Optional[Dict]:
    """
    Detect range/consolidation structure.
    
    This is the ultimate fallback - if we have pivots, we have a range.
    """
    highs = [p for p in pivots if p.get("type") == "high"][-3:]
    lows = [p for p in pivots if p.get("type") == "low"][-3:]
    
    if len(highs) < 2 or len(lows) < 2:
        return None
    
    # Calculate range characteristics
    resistance = max(h["price"] for h in highs)
    support = min(low["price"] for low in lows)
    range_width = resistance - support
    
    if range_width <= 0:
        return None
    
    return make_pattern(
        p_type="loose_range",
        anchors=build_anchors(highs, lows),
        confidence=0.30,
        quality=0.25,
        mode="loose",
        bias="neutral",
        meta={
            "resistance": resistance,
            "support": support,
            "range_width": range_width,
            "boundaries": build_boundaries(highs, lows),
        },
    )


# ═══════════════════════════════════════════════════════════════
# MAIN LOOSE DETECTION
# ═══════════════════════════════════════════════════════════════

def detect_loose_patterns(pivots: List[Dict]) -> List[Dict]:
    """
    Run all loose pattern detectors.
    
    Returns list of detected loose patterns, sorted by confidence.
    """
    patterns = []
    
    # Try each detector
    wedge = detect_loose_wedge(pivots)
    if wedge:
        patterns.append(wedge)
    
    triangle = detect_loose_triangle(pivots)
    if triangle:
        patterns.append(triangle)
    
    range_p = detect_loose_range(pivots)
    if range_p:
        patterns.append(range_p)
    
    # Sort by confidence
    patterns.sort(key=lambda x: x["confidence"], reverse=True)
    
    return patterns


# ═══════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════

def get_loose_pattern_engine():
    """Factory function for integration"""
    return {
        "detect_loose_patterns": detect_loose_patterns,
        "detect_loose_wedge": detect_loose_wedge,
        "detect_loose_triangle": detect_loose_triangle,
        "detect_loose_range": detect_loose_range,
        "PATTERN_PRIORITY": PATTERN_PRIORITY,
        "RENDER_PROFILE": RENDER_PROFILE,
    }
