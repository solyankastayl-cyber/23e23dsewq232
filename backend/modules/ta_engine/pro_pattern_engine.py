"""
PRO PATTERN ENGINE — Full Production-Level Pattern Detection
=============================================================

This is the final orchestration layer that combines:
1. STRICT patterns (textbook accuracy)
2. LOOSE patterns (human interpretation)
3. RANKING (what to show)
4. LIFECYCLE (forming/breakout/breakdown)
5. MULTI-PATTERN (primary + alternatives)

Output: Always has something to show, never empty.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from modules.ta_engine.anchor_pattern_engine import (
    detect_strong_pivots, 
    calculate_atr,
    detect_patterns as detect_strict_anchor_patterns,
)
from modules.ta_engine.loose_pattern_engine import (
    detect_loose_patterns,
    make_pattern,
    build_anchors,
    build_boundaries,
    PATTERN_PRIORITY,
    RENDER_PROFILE,
)


# ═══════════════════════════════════════════════════════════════
# DOUBLE TOP DETECTOR (strict)
# ═══════════════════════════════════════════════════════════════

def detect_double_top(pivots: List[Dict]) -> Optional[Dict]:
    """
    Detect double top pattern.
    
    Requirements:
    - Two highs at similar level (within 1.5%)
    - A valley between them
    - Both highs must be significant
    """
    highs = [p for p in pivots if p.get("type") == "high"]
    lows = [p for p in pivots if p.get("type") == "low"]
    
    if len(highs) < 2 or len(lows) < 1:
        return None
    
    # Get last two highs
    h1, h2 = highs[-2], highs[-1]
    
    # Check if prices are similar (within 1.5%)
    price_diff = abs(h1["price"] - h2["price"]) / h1["price"]
    if price_diff > 0.015:
        return None
    
    # Find middle low (neckline)
    h1_idx = h1.get("index", 0)
    h2_idx = h2.get("index", 0)
    
    middle_lows = [low for low in lows if h1_idx < low.get("index", 0) < h2_idx]
    if not middle_lows:
        return None
    
    neckline = min(middle_lows, key=lambda x: x["price"])
    
    # Check that neckline is significantly below the tops
    drop_from_top = (h1["price"] - neckline["price"]) / h1["price"]
    if drop_from_top < 0.02:  # At least 2% drop
        return None
    
    anchors = [
        {"time": h1["time"], "price": h1["price"]},
        {"time": h2["time"], "price": h2["price"]},
        {"time": neckline["time"], "price": neckline["price"]},
    ]
    
    return make_pattern(
        p_type="double_top",
        anchors=anchors,
        confidence=0.72,
        quality=0.72,
        mode="strict",
        bias="bearish",
        meta={
            "neckline": neckline["price"],
            "target": neckline["price"] - (h1["price"] - neckline["price"]),
            "boundaries": {
                "resistance": max(h1["price"], h2["price"]),
                "neckline": neckline["price"],
            },
        },
    )


# ═══════════════════════════════════════════════════════════════
# DOUBLE BOTTOM DETECTOR (strict)
# ═══════════════════════════════════════════════════════════════

def detect_double_bottom(pivots: List[Dict]) -> Optional[Dict]:
    """
    Detect double bottom pattern (inverse of double top).
    """
    highs = [p for p in pivots if p.get("type") == "high"]
    lows = [p for p in pivots if p.get("type") == "low"]
    
    if len(lows) < 2 or len(highs) < 1:
        return None
    
    # Get last two lows
    l1, l2 = lows[-2], lows[-1]
    
    # Check if prices are similar (within 1.5%)
    price_diff = abs(l1["price"] - l2["price"]) / l1["price"]
    if price_diff > 0.015:
        return None
    
    # Find middle high (neckline)
    l1_idx = l1.get("index", 0)
    l2_idx = l2.get("index", 0)
    
    middle_highs = [h for h in highs if l1_idx < h.get("index", 0) < l2_idx]
    if not middle_highs:
        return None
    
    neckline = max(middle_highs, key=lambda x: x["price"])
    
    # Check that neckline is significantly above the bottoms
    rise_from_bottom = (neckline["price"] - l1["price"]) / l1["price"]
    if rise_from_bottom < 0.02:
        return None
    
    anchors = [
        {"time": l1["time"], "price": l1["price"]},
        {"time": l2["time"], "price": l2["price"]},
        {"time": neckline["time"], "price": neckline["price"]},
    ]
    
    return make_pattern(
        p_type="double_bottom",
        anchors=anchors,
        confidence=0.72,
        quality=0.72,
        mode="strict",
        bias="bullish",
        meta={
            "neckline": neckline["price"],
            "target": neckline["price"] + (neckline["price"] - l1["price"]),
            "boundaries": {
                "support": min(l1["price"], l2["price"]),
                "neckline": neckline["price"],
            },
        },
    )


# ═══════════════════════════════════════════════════════════════
# HEAD & SHOULDERS DETECTOR (strict)
# ═══════════════════════════════════════════════════════════════

def detect_head_shoulders(pivots: List[Dict]) -> Optional[Dict]:
    """
    Detect head & shoulders pattern.
    
    Requirements:
    - Three highs: middle (head) higher than both shoulders
    - Two shoulders at similar level (within 3%)
    - Clear neckline from two valleys
    """
    highs = [p for p in pivots if p.get("type") == "high"]
    lows = [p for p in pivots if p.get("type") == "low"]
    
    if len(highs) < 3 or len(lows) < 2:
        return None
    
    # Get last three highs
    h1, h2, h3 = highs[-3], highs[-2], highs[-1]
    
    # Head must be higher than both shoulders
    if not (h2["price"] > h1["price"] and h2["price"] > h3["price"]):
        return None
    
    # Shoulders must be at similar level (within 3%)
    shoulders_diff = abs(h1["price"] - h3["price"]) / h1["price"]
    if shoulders_diff > 0.03:
        return None
    
    # Find neckline lows between shoulders
    h1_idx = h1.get("index", 0)
    h3_idx = h3.get("index", 0)
    
    neck_lows = [low for low in lows if h1_idx < low.get("index", 0) < h3_idx]
    if len(neck_lows) < 2:
        return None
    
    # Take the two lowest points for neckline
    neck_lows_sorted = sorted(neck_lows, key=lambda x: x["price"])
    nl1, nl2 = neck_lows_sorted[0], neck_lows_sorted[1]
    
    # Ensure nl1 comes before nl2 chronologically
    if nl1.get("index", 0) > nl2.get("index", 0):
        nl1, nl2 = nl2, nl1
    
    anchors = [
        {"time": h1["time"], "price": h1["price"]},     # Left shoulder
        {"time": h2["time"], "price": h2["price"]},     # Head
        {"time": h3["time"], "price": h3["price"]},     # Right shoulder
        {"time": nl1["time"], "price": nl1["price"]},   # Neckline left
        {"time": nl2["time"], "price": nl2["price"]},   # Neckline right
    ]
    
    neckline_avg = (nl1["price"] + nl2["price"]) / 2
    height = h2["price"] - neckline_avg
    
    return make_pattern(
        p_type="head_shoulders",
        anchors=anchors,
        confidence=0.76,
        quality=0.75,
        mode="strict",
        bias="bearish",
        meta={
            "head": h2["price"],
            "left_shoulder": h1["price"],
            "right_shoulder": h3["price"],
            "neckline": neckline_avg,
            "target": neckline_avg - height,
            "neckline_points": [
                {"time": nl1["time"], "price": nl1["price"]},
                {"time": nl2["time"], "price": nl2["price"]},
            ],
        },
    )


# ═══════════════════════════════════════════════════════════════
# INVERSE HEAD & SHOULDERS DETECTOR (strict)
# ═══════════════════════════════════════════════════════════════

def detect_inverse_head_shoulders(pivots: List[Dict]) -> Optional[Dict]:
    """
    Detect inverse head & shoulders (bullish reversal).
    """
    highs = [p for p in pivots if p.get("type") == "high"]
    lows = [p for p in pivots if p.get("type") == "low"]
    
    if len(lows) < 3 or len(highs) < 2:
        return None
    
    # Get last three lows
    l1, l2, l3 = lows[-3], lows[-2], lows[-1]
    
    # Head must be lower than both shoulders
    if not (l2["price"] < l1["price"] and l2["price"] < l3["price"]):
        return None
    
    # Shoulders must be at similar level (within 3%)
    shoulders_diff = abs(l1["price"] - l3["price"]) / l1["price"]
    if shoulders_diff > 0.03:
        return None
    
    # Find neckline highs between shoulders
    l1_idx = l1.get("index", 0)
    l3_idx = l3.get("index", 0)
    
    neck_highs = [h for h in highs if l1_idx < h.get("index", 0) < l3_idx]
    if len(neck_highs) < 2:
        return None
    
    neck_highs_sorted = sorted(neck_highs, key=lambda x: x["price"], reverse=True)
    nh1, nh2 = neck_highs_sorted[0], neck_highs_sorted[1]
    
    if nh1.get("index", 0) > nh2.get("index", 0):
        nh1, nh2 = nh2, nh1
    
    anchors = [
        {"time": l1["time"], "price": l1["price"]},     # Left shoulder
        {"time": l2["time"], "price": l2["price"]},     # Head
        {"time": l3["time"], "price": l3["price"]},     # Right shoulder
        {"time": nh1["time"], "price": nh1["price"]},   # Neckline left
        {"time": nh2["time"], "price": nh2["price"]},   # Neckline right
    ]
    
    neckline_avg = (nh1["price"] + nh2["price"]) / 2
    height = neckline_avg - l2["price"]
    
    return make_pattern(
        p_type="inverse_head_shoulders",
        anchors=anchors,
        confidence=0.76,
        quality=0.75,
        mode="strict",
        bias="bullish",
        meta={
            "head": l2["price"],
            "left_shoulder": l1["price"],
            "right_shoulder": l3["price"],
            "neckline": neckline_avg,
            "target": neckline_avg + height,
            "neckline_points": [
                {"time": nh1["time"], "price": nh1["price"]},
                {"time": nh2["time"], "price": nh2["price"]},
            ],
        },
    )


# ═══════════════════════════════════════════════════════════════
# RANKING ENGINE
# ═══════════════════════════════════════════════════════════════

def rank_score(pattern: Dict) -> float:
    """
    Calculate ranking score for a pattern.
    
    Formula: 45% confidence + 35% quality + 20% priority
    """
    priority_weight = PATTERN_PRIORITY.get(pattern.get("type", ""), 1) / 10.0
    
    return (
        pattern.get("confidence", 0) * 0.45 +
        pattern.get("quality", 0) * 0.35 +
        priority_weight * 0.20
    )


def sort_patterns(patterns: List[Dict]) -> List[Dict]:
    """Sort patterns by rank score (highest first)"""
    for p in patterns:
        p["rank_score"] = rank_score(p)
    
    return sorted(patterns, key=lambda x: x.get("rank_score", 0), reverse=True)


# ═══════════════════════════════════════════════════════════════
# MULTI-PATTERN STACK
# ═══════════════════════════════════════════════════════════════

def build_pattern_stack(strict_patterns: List[Dict], loose_patterns: List[Dict]) -> Dict:
    """
    Build pattern stack with primary and alternatives.
    
    Strict patterns always win over loose patterns at same rank.
    """
    all_patterns = []
    
    # Add strict patterns first (they have priority)
    if strict_patterns:
        all_patterns.extend(strict_patterns)
    
    # Add loose patterns as fallback
    if loose_patterns:
        all_patterns.extend(loose_patterns)
    
    # Rank all patterns
    ranked = sort_patterns(all_patterns)
    
    primary = ranked[0] if ranked else None
    alternatives = ranked[1:3] if len(ranked) > 1 else []
    
    return {
        "primary": primary,
        "alternatives": alternatives,
        "all_patterns": ranked,
        "strict_count": len(strict_patterns) if strict_patterns else 0,
        "loose_count": len(loose_patterns) if loose_patterns else 0,
    }


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE ENGINE
# ═══════════════════════════════════════════════════════════════

def attach_lifecycle(pattern: Dict, current_price: float) -> Dict:
    """
    Determine pattern lifecycle state.
    
    States:
    - forming: Pattern still developing
    - breakout: Bullish breakout occurred
    - breakdown: Bearish breakdown occurred
    - invalidated: Pattern failed
    """
    if not pattern:
        return pattern
    
    p_type = pattern.get("type", "")
    anchors = pattern.get("anchors", [])
    
    if not anchors:
        pattern["state"] = "forming"
        return pattern
    
    # Calculate levels
    prices = [a.get("price", 0) for a in anchors if a.get("price")]
    if not prices:
        pattern["state"] = "forming"
        return pattern
    
    upper_level = max(prices)
    lower_level = min(prices)
    
    state = "forming"
    
    # Bullish patterns: breakout above upper level
    if p_type in ["falling_wedge", "ascending_triangle", "double_bottom", 
                   "inverse_head_shoulders", "loose_triangle", "loose_wedge"]:
        if pattern.get("bias") == "bullish":
            if current_price > upper_level * 1.01:  # 1% buffer
                state = "breakout"
            elif current_price < lower_level * 0.98:
                state = "invalidated"
    
    # Bearish patterns: breakdown below lower level
    if p_type in ["rising_wedge", "descending_triangle", "double_top",
                   "head_shoulders"]:
        if pattern.get("bias") == "bearish":
            if current_price < lower_level * 0.99:
                state = "breakdown"
            elif current_price > upper_level * 1.02:
                state = "invalidated"
    
    pattern["state"] = state
    return pattern


# ═══════════════════════════════════════════════════════════════
# MAIN PRO ENGINE ORCHESTRATION
# ═══════════════════════════════════════════════════════════════

def run_pro_pattern_engine(candles: List[Dict], current_price: float = None) -> Dict:
    """
    Main entry point for PRO pattern detection.
    
    Combines strict + loose patterns with ranking and lifecycle.
    Always returns something to display.
    """
    if len(candles) < 20:
        return _build_empty_result()
    
    # Get current price if not provided
    if current_price is None:
        current_price = candles[-1].get("close", 0)
    
    # Build pivots
    atr = calculate_atr(candles)
    pivots_raw = detect_strong_pivots(candles, atr)
    
    # Convert Pivot objects to dicts
    pivots = []
    for p in pivots_raw:
        if hasattr(p, 'type'):
            pivots.append({
                "type": p.type,
                "time": p.time,
                "price": p.price,
                "index": p.index,
            })
        else:
            pivots.append(p)
    
    if len(pivots) < 4:
        return _build_empty_result()
    
    # Detect STRICT patterns
    strict_patterns = []
    
    strict_detectors = [
        detect_double_top,
        detect_double_bottom,
        detect_head_shoulders,
        detect_inverse_head_shoulders,
    ]
    
    for detector in strict_detectors:
        try:
            result = detector(pivots)
            if result:
                strict_patterns.append(result)
        except Exception as e:
            print(f"[ProEngine] Detector error: {e}")
    
    # Also try anchor engine patterns
    try:
        anchor_patterns = detect_strict_anchor_patterns(candles)
        for ap in anchor_patterns:
            if ap.is_valid:
                strict_patterns.append({
                    "type": ap.pattern_type,
                    "anchors": ap.anchors,
                    "confidence": ap.confidence,
                    "quality": ap.confidence * 0.9,
                    "priority": PATTERN_PRIORITY.get(ap.pattern_type, 5),
                    "mode": "strict",
                    "bias": "bullish" if "falling" in ap.pattern_type or "ascending" in ap.pattern_type else "bearish",
                    "meta": {
                        "boundaries": {
                            "upper": ap.upper[0] if ap.upper else {},
                            "lower": ap.lower[0] if ap.lower else {},
                        },
                        "window": ap.window,
                    },
                    "render_profile": RENDER_PROFILE["strict"],
                })
    except Exception as e:
        print(f"[ProEngine] Anchor engine error: {e}")
    
    # Detect LOOSE patterns (always)
    loose_patterns = detect_loose_patterns(pivots)
    
    # Build pattern stack
    stack = build_pattern_stack(strict_patterns, loose_patterns)
    
    # Attach lifecycle to primary and alternatives
    if stack.get("primary"):
        stack["primary"] = attach_lifecycle(stack["primary"], current_price)
    
    stack["alternatives"] = [
        attach_lifecycle(p, current_price) for p in stack.get("alternatives", [])
    ]
    
    return stack


def _build_empty_result() -> Dict:
    """Build empty result when no patterns possible"""
    return {
        "primary": None,
        "alternatives": [],
        "all_patterns": [],
        "strict_count": 0,
        "loose_count": 0,
    }


# ═══════════════════════════════════════════════════════════════
# UI OUTPUT CONTRACT
# ═══════════════════════════════════════════════════════════════

def build_ui_pattern_payload(stack: Dict) -> Dict:
    """
    Build UI-ready payload from pattern stack.
    
    This is what gets sent to the frontend.
    """
    primary = stack.get("primary")
    
    if not primary:
        return {
            "analysis_mode": "structure",
            "pattern": None,
            "alternatives": [],
            "meta": {
                "strict_count": stack.get("strict_count", 0),
                "loose_count": stack.get("loose_count", 0),
            },
        }
    
    return {
        "analysis_mode": "figure",
        "pattern": primary,
        "alternatives": stack.get("alternatives", []),
        "pattern_meta": {
            "label": primary.get("type", "").replace("_", " ").title(),
            "state": primary.get("state", "forming"),
            "confidence": primary.get("confidence", 0),
            "quality": primary.get("quality", 0),
            "rank_score": primary.get("rank_score", 0),
            "mode": primary.get("mode", "loose"),
            "bias": primary.get("bias", "neutral"),
            "render_profile": primary.get("render_profile", RENDER_PROFILE["loose"]),
        },
        "meta": {
            "strict_count": stack.get("strict_count", 0),
            "loose_count": stack.get("loose_count", 0),
        },
    }


# ═══════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════

def get_pro_pattern_engine():
    """Factory function for integration"""
    return {
        "run": run_pro_pattern_engine,
        "build_ui_payload": build_ui_pattern_payload,
        "detect_double_top": detect_double_top,
        "detect_double_bottom": detect_double_bottom,
        "detect_head_shoulders": detect_head_shoulders,
        "detect_inverse_head_shoulders": detect_inverse_head_shoulders,
    }
