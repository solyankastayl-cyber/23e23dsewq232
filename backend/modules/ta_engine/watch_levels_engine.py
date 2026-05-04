"""
Watch Levels Engine — "What to Watch" Layer
=============================================

Calculates breakout / breakdown price levels based on pattern types.
NOT a signal — an observational lens.

Input: ctx = {"dominant": {...}, "alternatives": [...]}
Output: list of { "type": "breakout_up"|"breakdown_down", "price": float, "label": str }
"""

from typing import Dict, List, Optional


def build_watch_levels(ctx: Dict) -> List[Dict]:
    """
    Build actionable watch levels from dominant pattern.
    
    Lifecycle-aware:
    - forming: show both breakout + breakdown
    - confirmed_up: only show upward continuation levels
    - confirmed_down: only show downward continuation levels
    - invalidated: empty (no levels to watch)
    
    Returns list of:
        {
            "type": "breakout_up" | "breakdown_down",
            "price": float,
            "label": str  (human-readable)
        }
    """
    dom = ctx.get("dominant") or {}
    t = (dom.get("type") or "").lower()
    
    if not t:
        return []
    
    # Lifecycle filter
    lifecycle = dom.get("lifecycle", "forming")
    if lifecycle == "invalidated":
        return []  # Dead pattern — nothing to watch
    
    levels = []
    
    # ═══════════════════════════════════════════════════════════════
    # RANGE / RECTANGLE — watch top and bottom
    # ═══════════════════════════════════════════════════════════════
    if t in ("rectangle", "range", "horizontal_channel"):
        top = _get_top(dom)
        bottom = _get_bottom(dom)
        if top:
            levels.append({
                "type": "breakout_up",
                "price": round(top, 2),
                "label": "Range top breakout",
            })
        if bottom:
            levels.append({
                "type": "breakdown_down",
                "price": round(bottom, 2),
                "label": "Range bottom breakdown",
            })
    
    # ═══════════════════════════════════════════════════════════════
    # TRIANGLES — apex breakout/breakdown
    # ═══════════════════════════════════════════════════════════════
    elif t in ("symmetrical_triangle",):
        top = _get_top(dom)
        bottom = _get_bottom(dom)
        if top:
            levels.append({
                "type": "breakout_up",
                "price": round(top, 2),
                "label": "Triangle upper breakout",
            })
        if bottom:
            levels.append({
                "type": "breakdown_down",
                "price": round(bottom, 2),
                "label": "Triangle lower breakdown",
            })
    
    elif t in ("ascending_triangle",):
        top = _get_top(dom)
        if top:
            levels.append({
                "type": "breakout_up",
                "price": round(top, 2),
                "label": "Flat resistance breakout",
            })
        bottom = _get_bottom(dom)
        if bottom:
            levels.append({
                "type": "breakdown_down",
                "price": round(bottom, 2),
                "label": "Rising support breakdown",
            })
    
    elif t in ("descending_triangle",):
        bottom = _get_bottom(dom)
        if bottom:
            levels.append({
                "type": "breakdown_down",
                "price": round(bottom, 2),
                "label": "Flat support breakdown",
            })
        top = _get_top(dom)
        if top:
            levels.append({
                "type": "breakout_up",
                "price": round(top, 2),
                "label": "Falling resistance breakout",
            })
    
    # ═══════════════════════════════════════════════════════════════
    # DOUBLE / TRIPLE TOP — neckline breakdown
    # ═══════════════════════════════════════════════════════════════
    elif t in ("double_top", "triple_top"):
        neckline = _get_neckline(dom)
        if neckline:
            levels.append({
                "type": "breakdown_down",
                "price": round(neckline, 2),
                "label": "Neckline breakdown",
            })
        top = _get_top(dom)
        if top:
            levels.append({
                "type": "breakout_up",
                "price": round(top, 2),
                "label": "Peak invalidation",
            })
    
    # ═══════════════════════════════════════════════════════════════
    # DOUBLE / TRIPLE BOTTOM — neckline breakout
    # ═══════════════════════════════════════════════════════════════
    elif t in ("double_bottom", "triple_bottom"):
        neckline = _get_neckline(dom)
        if neckline:
            levels.append({
                "type": "breakout_up",
                "price": round(neckline, 2),
                "label": "Neckline breakout",
            })
        bottom = _get_bottom(dom)
        if bottom:
            levels.append({
                "type": "breakdown_down",
                "price": round(bottom, 2),
                "label": "Valley invalidation",
            })
    
    # ═══════════════════════════════════════════════════════════════
    # HEAD & SHOULDERS — neckline
    # ═══════════════════════════════════════════════════════════════
    elif t in ("head_shoulders",):
        neckline = _get_neckline(dom)
        if neckline:
            levels.append({
                "type": "breakdown_down",
                "price": round(neckline, 2),
                "label": "H&S neckline breakdown",
            })
    
    elif t in ("inverse_head_shoulders",):
        neckline = _get_neckline(dom)
        if neckline:
            levels.append({
                "type": "breakout_up",
                "price": round(neckline, 2),
                "label": "Inv H&S neckline breakout",
            })
    
    # ═══════════════════════════════════════════════════════════════
    # WEDGES — breakout/breakdown opposite to wedge direction
    # ═══════════════════════════════════════════════════════════════
    elif t in ("rising_wedge",):
        bottom = _get_bottom(dom)
        if bottom:
            levels.append({
                "type": "breakdown_down",
                "price": round(bottom, 2),
                "label": "Wedge support breakdown",
            })
    
    elif t in ("falling_wedge",):
        top = _get_top(dom)
        if top:
            levels.append({
                "type": "breakout_up",
                "price": round(top, 2),
                "label": "Wedge resistance breakout",
            })
    
    # ═══════════════════════════════════════════════════════════════
    # CHANNELS — breakout or continuation
    # ═══════════════════════════════════════════════════════════════
    elif t in ("ascending_channel", "descending_channel"):
        top = _get_top(dom)
        bottom = _get_bottom(dom)
        if top:
            levels.append({
                "type": "breakout_up",
                "price": round(top, 2),
                "label": "Channel top breakout",
            })
        if bottom:
            levels.append({
                "type": "breakdown_down",
                "price": round(bottom, 2),
                "label": "Channel bottom breakdown",
            })
    
    # ═══════════════════════════════════════════════════════════════
    # FLAGS / PENNANTS
    # ═══════════════════════════════════════════════════════════════
    elif t in ("bull_flag", "pennant"):
        top = _get_top(dom)
        if top:
            levels.append({
                "type": "breakout_up",
                "price": round(top, 2),
                "label": "Flag breakout",
            })
    
    elif t in ("bear_flag",):
        bottom = _get_bottom(dom)
        if bottom:
            levels.append({
                "type": "breakdown_down",
                "price": round(bottom, 2),
                "label": "Flag breakdown",
            })
    
    # ═══════════════════════════════════════════════════════════════
    # LIFECYCLE FILTER — remove irrelevant levels for confirmed state
    # ═══════════════════════════════════════════════════════════════
    if lifecycle == "confirmed_up":
        levels = [lvl for lvl in levels if lvl["type"] == "breakout_up"]
        for lvl in levels:
            lvl["label"] = lvl["label"] + " (confirmed)"
    elif lifecycle == "confirmed_down":
        levels = [lvl for lvl in levels if lvl["type"] == "breakdown_down"]
        for lvl in levels:
            lvl["label"] = lvl["label"] + " (confirmed)"
    
    return levels


# ═══════════════════════════════════════════════════════════════
# HELPERS — extract price levels from pattern dict
# ═══════════════════════════════════════════════════════════════

def _get_top(dom: Dict) -> Optional[float]:
    """Extract top/resistance price from pattern."""
    # Try direct numeric keys
    for key in ("resistance", "top", "upper_price", "breakout_price",
                "upper_boundary", "high", "invalidation"):
        val = dom.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    
    # Try nested upper_line
    upper = dom.get("upper_line") or {}
    for key in ("end_price", "start_price", "price"):
        val = upper.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    
    # Try anchor_points.upper or points.upper
    for pts_key in ("anchor_points", "points"):
        pts = dom.get(pts_key) or {}
        upper_pts = pts.get("upper") or []
        if isinstance(upper_pts, list) and len(upper_pts) > 0:
            # Take max price among upper points
            prices = [p.get("value") or p.get("price") for p in upper_pts if isinstance(p, dict)]
            prices = [p for p in prices if isinstance(p, (int, float))]
            if prices:
                return float(max(prices))
    
    # Try anchors list (render_contract) — take max price
    anchors = dom.get("anchors") or []
    if isinstance(anchors, list) and len(anchors) >= 2:
        prices = [a.get("price") for a in anchors if isinstance(a, dict) and isinstance(a.get("price"), (int, float))]
        if prices:
            return float(max(prices))
    
    # Try dict-style anchors (p1, p2)
    if isinstance(anchors, dict):
        for key in ("p1", "p2"):
            pt = anchors.get(key) or {}
            price = pt.get("price")
            if isinstance(price, (int, float)) and price > 0:
                return float(price)
    
    return None


def _get_bottom(dom: Dict) -> Optional[float]:
    """Extract bottom/support price from pattern."""
    # Try direct numeric keys
    for key in ("support", "bottom", "lower_price", "invalidation_price",
                "lower_boundary", "low", "breakout_level"):
        val = dom.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    
    # Try nested lower_line
    lower = dom.get("lower_line") or {}
    for key in ("end_price", "start_price", "price"):
        val = lower.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    
    # Try anchor_points.lower or points.lower
    for pts_key in ("anchor_points", "points"):
        pts = dom.get(pts_key) or {}
        lower_pts = pts.get("lower") or []
        if isinstance(lower_pts, list) and len(lower_pts) > 0:
            prices = [p.get("value") or p.get("price") for p in lower_pts if isinstance(p, dict)]
            prices = [p for p in prices if isinstance(p, (int, float))]
            if prices:
                return float(min(prices))
    
    # Try anchors list (render_contract) — take min price
    anchors = dom.get("anchors") or []
    if isinstance(anchors, list) and len(anchors) >= 2:
        prices = [a.get("price") for a in anchors if isinstance(a, dict) and isinstance(a.get("price"), (int, float))]
        if prices:
            return float(min(prices))
    
    # Try dict-style anchors.valley
    if isinstance(anchors, dict):
        valley = anchors.get("valley") or {}
        price = valley.get("price")
        if isinstance(price, (int, float)) and price > 0:
            return float(price)
    
    return None


def _get_neckline(dom: Dict) -> Optional[float]:
    """Extract neckline price from pattern (double top/bottom, H&S)."""
    for key in ("neckline", "neckline_price", "neck"):
        val = dom.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    
    # For double top/bottom, neckline is the valley between peaks
    # Try anchors — typically the middle anchor is the neckline
    anchors = dom.get("anchors") or []
    if isinstance(anchors, list) and len(anchors) >= 3:
        prices = [a.get("price") for a in anchors if isinstance(a, dict) and isinstance(a.get("price"), (int, float))]
        if len(prices) >= 3:
            # For double_top, neckline = min (valley between peaks)
            # For double_bottom, neckline = max (peak between valleys)
            t = (dom.get("type") or "").lower()
            if "top" in t:
                return float(min(prices))
            elif "bottom" in t:
                return float(max(prices))
    
    # Try anchor_points.valley or points
    for pts_key in ("anchor_points", "points"):
        pts = dom.get(pts_key) or {}
        valley = pts.get("valley") or pts.get("neckline") or {}
        if isinstance(valley, dict):
            price = valley.get("price") or valley.get("value")
            if isinstance(price, (int, float)) and price > 0:
                return float(price)
    
    # Try breakout_level as neckline for bottom patterns
    bl = dom.get("breakout_level")
    if isinstance(bl, (int, float)) and bl > 0:
        return float(bl)
    
    return None


__all__ = ["build_watch_levels"]
