"""
Pattern Lifecycle Engine
========================

Determines the LIVE STATE of a pattern relative to current price.

States:
  - "forming"        → pattern is building, no breakout yet
  - "confirmed_up"   → price broke above resistance/neckline
  - "confirmed_down" → price broke below support/neckline
  - "invalidated"    → pattern structure violated (price went wrong way for the type)

This is NOT a signal. It answers: "is this pattern alive or dead?"
"""

from typing import Dict, Optional


def build_lifecycle(pattern: Dict, current_price: float) -> Dict:
    """
    Determine lifecycle state for a pattern.

    Returns:
        {
            "state": "forming" | "confirmed_up" | "confirmed_down" | "invalidated",
            "label": str,
        }
    """
    if not pattern or not current_price:
        return {"state": "forming", "label": "Developing"}

    ptype = (pattern.get("type") or "").lower()
    if not ptype:
        return {"state": "forming", "label": "Developing"}

    top = _get_top(pattern)
    bottom = _get_bottom(pattern)
    neckline = _get_neckline(pattern)

    # ═══════ RANGE / RECTANGLE ═══════
    if ptype in ("rectangle", "range", "horizontal_channel", "active_range"):
        if top and current_price > top:
            return {"state": "confirmed_up", "label": "Breakout confirmed"}
        if bottom and current_price < bottom:
            return {"state": "confirmed_down", "label": "Breakdown confirmed"}
        return {"state": "forming", "label": "Range active"}

    # ═══════ TRIANGLES ═══════
    if ptype in ("symmetrical_triangle",):
        if top and current_price > top:
            return {"state": "confirmed_up", "label": "Triangle breakout"}
        if bottom and current_price < bottom:
            return {"state": "confirmed_down", "label": "Triangle breakdown"}
        return {"state": "forming", "label": "Compressing"}

    if ptype in ("ascending_triangle",):
        if top and current_price > top:
            return {"state": "confirmed_up", "label": "Flat resistance broken"}
        if bottom and current_price < bottom:
            return {"state": "invalidated", "label": "Rising support failed"}
        return {"state": "forming", "label": "Pressure building"}

    if ptype in ("descending_triangle",):
        if bottom and current_price < bottom:
            return {"state": "confirmed_down", "label": "Flat support broken"}
        if top and current_price > top:
            return {"state": "invalidated", "label": "Falling resistance failed"}
        return {"state": "forming", "label": "Pressure building"}

    # ═══════ DOUBLE / TRIPLE TOP ═══════
    if ptype in ("double_top", "triple_top"):
        if neckline and current_price < neckline:
            return {"state": "confirmed_down", "label": "Neckline broken"}
        if top and current_price > top:
            return {"state": "invalidated", "label": "Peak surpassed"}
        return {"state": "forming", "label": "Testing peaks"}

    # ═══════ DOUBLE / TRIPLE BOTTOM ═══════
    if ptype in ("double_bottom", "triple_bottom"):
        if neckline and current_price > neckline:
            return {"state": "confirmed_up", "label": "Neckline broken"}
        if bottom and current_price < bottom:
            return {"state": "invalidated", "label": "Valley breached"}
        return {"state": "forming", "label": "Testing lows"}

    # ═══════ HEAD & SHOULDERS ═══════
    if ptype in ("head_shoulders",):
        if neckline and current_price < neckline:
            return {"state": "confirmed_down", "label": "H&S neckline broken"}
        return {"state": "forming", "label": "Right shoulder forming"}

    if ptype in ("inverse_head_shoulders",):
        if neckline and current_price > neckline:
            return {"state": "confirmed_up", "label": "Inv H&S neckline broken"}
        return {"state": "forming", "label": "Right shoulder forming"}

    # ═══════ WEDGES ═══════
    if ptype in ("rising_wedge",):
        if bottom and current_price < bottom:
            return {"state": "confirmed_down", "label": "Wedge support broken"}
        if top and current_price > top:
            return {"state": "invalidated", "label": "Wedge resistance broken"}
        return {"state": "forming", "label": "Wedge narrowing"}

    if ptype in ("falling_wedge",):
        if top and current_price > top:
            return {"state": "confirmed_up", "label": "Wedge resistance broken"}
        if bottom and current_price < bottom:
            return {"state": "invalidated", "label": "Wedge support broken"}
        return {"state": "forming", "label": "Wedge narrowing"}

    # ═══════ CHANNELS ═══════
    if ptype in ("ascending_channel", "descending_channel"):
        if top and current_price > top:
            return {"state": "confirmed_up", "label": "Channel breakout"}
        if bottom and current_price < bottom:
            return {"state": "confirmed_down", "label": "Channel breakdown"}
        return {"state": "forming", "label": "Channel active"}

    # ═══════ FLAGS / PENNANTS ═══════
    if ptype in ("bull_flag", "pennant"):
        if top and current_price > top:
            return {"state": "confirmed_up", "label": "Flag breakout"}
        if bottom and current_price < bottom:
            return {"state": "invalidated", "label": "Bull flag failed"}
        return {"state": "forming", "label": "Consolidating"}

    if ptype in ("bear_flag",):
        if bottom and current_price < bottom:
            return {"state": "confirmed_down", "label": "Flag breakdown"}
        if top and current_price > top:
            return {"state": "invalidated", "label": "Bear flag failed"}
        return {"state": "forming", "label": "Consolidating"}

    return {"state": "forming", "label": "Developing"}


# ═══════════════════════════════════════════════════════════════
# PRICE EXTRACTION HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_top(dom: Dict) -> Optional[float]:
    for key in ("resistance", "top", "upper_price", "breakout_price",
                "upper_boundary", "high", "invalidation"):
        val = dom.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    upper = dom.get("upper_line") or {}
    for key in ("end_price", "start_price", "price"):
        val = upper.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    for pts_key in ("anchor_points", "points"):
        pts = dom.get(pts_key) or {}
        upper_pts = pts.get("upper") or []
        if isinstance(upper_pts, list) and upper_pts:
            prices = [p.get("value") or p.get("price") for p in upper_pts if isinstance(p, dict)]
            prices = [p for p in prices if isinstance(p, (int, float))]
            if prices:
                return float(max(prices))
    anchors = dom.get("anchors") or []
    if isinstance(anchors, list) and len(anchors) >= 2:
        prices = [a.get("price") for a in anchors
                  if isinstance(a, dict) and isinstance(a.get("price"), (int, float))]
        if prices:
            return float(max(prices))
    return None


def _get_bottom(dom: Dict) -> Optional[float]:
    for key in ("support", "bottom", "lower_price", "invalidation_price",
                "lower_boundary", "low", "breakout_level"):
        val = dom.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    lower = dom.get("lower_line") or {}
    for key in ("end_price", "start_price", "price"):
        val = lower.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    for pts_key in ("anchor_points", "points"):
        pts = dom.get(pts_key) or {}
        lower_pts = pts.get("lower") or []
        if isinstance(lower_pts, list) and lower_pts:
            prices = [p.get("value") or p.get("price") for p in lower_pts if isinstance(p, dict)]
            prices = [p for p in prices if isinstance(p, (int, float))]
            if prices:
                return float(min(prices))
    anchors = dom.get("anchors") or []
    if isinstance(anchors, list) and len(anchors) >= 2:
        prices = [a.get("price") for a in anchors
                  if isinstance(a, dict) and isinstance(a.get("price"), (int, float))]
        if prices:
            return float(min(prices))
    return None


def _get_neckline(dom: Dict) -> Optional[float]:
    for key in ("neckline", "neckline_price", "neck"):
        val = dom.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return float(val)
    anchors = dom.get("anchors") or []
    if isinstance(anchors, list) and len(anchors) >= 3:
        prices = [a.get("price") for a in anchors
                  if isinstance(a, dict) and isinstance(a.get("price"), (int, float))]
        if len(prices) >= 3:
            t = (dom.get("type") or "").lower()
            if "top" in t:
                return float(min(prices))
            elif "bottom" in t:
                return float(max(prices))
    bl = dom.get("breakout_level")
    if isinstance(bl, (int, float)) and bl > 0:
        return float(bl)
    return None


__all__ = ["build_lifecycle"]
