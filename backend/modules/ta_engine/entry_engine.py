"""
Entry Engine — Trade Setup Builder

CRITICAL RULE:
Trade setup is generated ONLY when confidence_state = CLEAR

This is the difference between:
- "analysis for analysis sake"
- "actionable trading system"

For each pattern type:
- Entry level (breakout/confirmation)
- Stop loss (invalidation)
- Target (measured move)
- Risk/Reward ratio
"""

from typing import Dict, Optional


def build_trade_setup(
    dominant: Optional[Dict],
    ta_layers: Optional[Dict],
    confidence_state: str,
) -> Optional[Dict]:
    """
    Build trade setup ONLY if market is CLEAR.
    
    Args:
        dominant: Dominant pattern from TA Explorer
        ta_layers: Full 10-layer breakdown
        confidence_state: clear / weak / conflicted
    
    Returns:
        Trade setup dict or None if not tradeable
    """
    # ══════════════════════════════════════════════════════════════
    # GATE: NO TRADE IF NOT CLEAR
    # ══════════════════════════════════════════════════════════════
    if confidence_state != "clear":
        return {
            "available": False,
            "reason": _get_no_trade_reason(confidence_state),
            "advice": _get_advice(confidence_state),
        }
    
    if not dominant:
        return {
            "available": False,
            "reason": "No dominant pattern detected",
            "advice": "Wait for pattern formation",
        }
    
    pattern_type = dominant.get("type", "").lower()
    bias = dominant.get("bias", "neutral")
    
    # Get layers
    pattern_layer = ta_layers.get("layer_5_pattern", {}) if ta_layers else {}
    range_layer = ta_layers.get("layer_4_range", {}) if ta_layers else {}
    scenarios_layer = ta_layers.get("layer_8_scenarios", {}) if ta_layers else {}
    
    # ══════════════════════════════════════════════════════════════
    # PATTERN-SPECIFIC ENTRY LOGIC
    # ══════════════════════════════════════════════════════════════
    
    # INVERSE HEAD & SHOULDERS (bullish)
    if pattern_type == "inverse_head_shoulders":
        return _build_ihs_setup(pattern_layer, scenarios_layer)
    
    # HEAD & SHOULDERS (bearish)
    if pattern_type == "head_shoulders":
        return _build_hs_setup(pattern_layer, scenarios_layer)
    
    # DOUBLE TOP (bearish)
    if pattern_type == "double_top":
        return _build_double_top_setup(pattern_layer, scenarios_layer)
    
    # DOUBLE BOTTOM (bullish)
    if pattern_type == "double_bottom":
        return _build_double_bottom_setup(pattern_layer, scenarios_layer)
    
    # RANGE / ACTIVE RANGE (breakout either direction)
    if pattern_type in ["range", "active_range", "loose_range"]:
        return _build_range_setup(range_layer, scenarios_layer)
    
    # TRIANGLE patterns
    if "triangle" in pattern_type:
        return _build_triangle_setup(pattern_layer, scenarios_layer, bias)
    
    # WEDGE patterns
    if "wedge" in pattern_type:
        return _build_wedge_setup(pattern_layer, scenarios_layer, bias)
    
    # Generic directional pattern
    if bias in ["bullish", "bearish"]:
        return _build_generic_setup(dominant, scenarios_layer)
    
    return {
        "available": False,
        "reason": f"No entry logic for pattern: {pattern_type}",
        "advice": "Wait for clearer setup",
    }


def _get_no_trade_reason(confidence_state: str) -> str:
    """Get reason why trade is not available."""
    if confidence_state == "conflicted":
        return "Market is CONFLICTED — competing signals detected"
    if confidence_state == "weak":
        return "Signal is WEAK — insufficient confidence"
    if confidence_state == "uncertain":
        return "Market is UNCERTAIN — wait for clarity"
    return "Market conditions not suitable for trade"


def _get_advice(confidence_state: str) -> str:
    """Get advice for current market state."""
    if confidence_state == "conflicted":
        return "Wait for one pattern to invalidate or confirm. Don't force trades in conflicted markets."
    if confidence_state == "weak":
        return "Consider smaller position size or wait for stronger confirmation."
    return "Monitor for pattern completion or new setup formation."


def _calculate_rr(entry: float, stop: float, target: float) -> float:
    """Calculate risk/reward ratio."""
    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk == 0:
        return 0
    return round(reward / risk, 2)


# ══════════════════════════════════════════════════════════════════════
# PATTERN-SPECIFIC SETUP BUILDERS
# ══════════════════════════════════════════════════════════════════════

def _build_ihs_setup(pattern: Dict, scenarios: Dict) -> Dict:
    """Inverse Head & Shoulders — LONG setup."""
    neckline = pattern.get("neckline") or pattern.get("breakout_level")
    right_shoulder = pattern.get("right_shoulder_price") or pattern.get("invalidation")
    
    if not neckline:
        # Fallback to scenarios
        neckline = scenarios.get("break_up", {}).get("trigger")
        
    if not right_shoulder:
        # Estimate: neckline - 5%
        right_shoulder = neckline * 0.95 if neckline else None
    
    if not neckline:
        return {
            "available": False,
            "reason": "Missing neckline level for Inverse H&S",
            "advice": "Wait for pattern to develop further",
        }
    
    # Target = neckline + (neckline - head)
    head = pattern.get("head_price")
    if head:
        height = neckline - head
        target = neckline + height
    else:
        # Fallback to scenario target
        target = scenarios.get("break_up", {}).get("target", neckline * 1.1)
    
    stop = right_shoulder or neckline * 0.95
    
    return {
        "available": True,
        "side": "LONG",
        "pattern": "Inverse Head & Shoulders",
        "entry": round(neckline, 2),
        "entry_type": "breakout",
        "stop": round(stop, 2),
        "target": round(target, 2),
        "rr_ratio": _calculate_rr(neckline, stop, target),
        "notes": [
            "Enter on neckline breakout",
            "Stop below right shoulder",
            "Target = measured move (height)",
        ],
    }


def _build_hs_setup(pattern: Dict, scenarios: Dict) -> Dict:
    """Head & Shoulders — SHORT setup."""
    neckline = pattern.get("neckline") or pattern.get("breakout_level")
    right_shoulder = pattern.get("right_shoulder_price") or pattern.get("invalidation")
    
    if not neckline:
        neckline = scenarios.get("break_down", {}).get("trigger")
        
    if not neckline:
        return {
            "available": False,
            "reason": "Missing neckline level for H&S",
            "advice": "Wait for pattern to develop further",
        }
    
    head = pattern.get("head_price")
    if head:
        height = head - neckline
        target = neckline - height
    else:
        target = scenarios.get("break_down", {}).get("target", neckline * 0.9)
    
    stop = right_shoulder or neckline * 1.05
    
    return {
        "available": True,
        "side": "SHORT",
        "pattern": "Head & Shoulders",
        "entry": round(neckline, 2),
        "entry_type": "breakdown",
        "stop": round(stop, 2),
        "target": round(target, 2),
        "rr_ratio": _calculate_rr(neckline, stop, target),
        "notes": [
            "Enter on neckline breakdown",
            "Stop above right shoulder",
            "Target = measured move (height)",
        ],
    }


def _build_double_top_setup(pattern: Dict, scenarios: Dict) -> Dict:
    """Double Top — SHORT setup."""
    neckline = pattern.get("neckline") or pattern.get("valley_price")
    peak = pattern.get("peak_price") or pattern.get("invalidation")
    
    if not neckline:
        neckline = scenarios.get("break_down", {}).get("trigger")
        
    if not neckline:
        return {
            "available": False,
            "reason": "Missing neckline level for Double Top",
            "advice": "Wait for pattern to develop further",
        }
    
    if peak:
        height = peak - neckline
        target = neckline - height
    else:
        target = scenarios.get("break_down", {}).get("target", neckline * 0.9)
    
    stop = peak or neckline * 1.05
    
    return {
        "available": True,
        "side": "SHORT",
        "pattern": "Double Top",
        "entry": round(neckline, 2),
        "entry_type": "breakdown",
        "stop": round(stop, 2),
        "target": round(target, 2),
        "rr_ratio": _calculate_rr(neckline, stop, target),
        "notes": [
            "Enter on neckline breakdown",
            "Stop above second peak",
            "Target = measured move (height)",
        ],
    }


def _build_double_bottom_setup(pattern: Dict, scenarios: Dict) -> Dict:
    """Double Bottom — LONG setup."""
    neckline = pattern.get("neckline") or pattern.get("peak_price")
    bottom = pattern.get("bottom_price") or pattern.get("invalidation")
    
    if not neckline:
        neckline = scenarios.get("break_up", {}).get("trigger")
        
    if not neckline:
        return {
            "available": False,
            "reason": "Missing neckline level for Double Bottom",
            "advice": "Wait for pattern to develop further",
        }
    
    if bottom:
        height = neckline - bottom
        target = neckline + height
    else:
        target = scenarios.get("break_up", {}).get("target", neckline * 1.1)
    
    stop = bottom or neckline * 0.95
    
    return {
        "available": True,
        "side": "LONG",
        "pattern": "Double Bottom",
        "entry": round(neckline, 2),
        "entry_type": "breakout",
        "stop": round(stop, 2),
        "target": round(target, 2),
        "rr_ratio": _calculate_rr(neckline, stop, target),
        "notes": [
            "Enter on neckline breakout",
            "Stop below second bottom",
            "Target = measured move (height)",
        ],
    }


def _build_range_setup(range_layer: Dict, scenarios: Dict) -> Dict:
    """Range — BREAKOUT setup (either direction)."""
    top = range_layer.get("top")
    bottom = range_layer.get("bottom")
    
    if not top or not bottom:
        # Try scenarios
        top = scenarios.get("break_up", {}).get("trigger")
        bottom = scenarios.get("break_down", {}).get("trigger")
    
    if not top or not bottom:
        return {
            "available": False,
            "reason": "Missing range boundaries",
            "advice": "Wait for range to establish",
        }
    
    height = top - bottom
    target_up = scenarios.get("break_up", {}).get("target", top + height)
    target_down = scenarios.get("break_down", {}).get("target", bottom - height)
    
    # Stop inside range
    stop_long = bottom + (height * 0.3)  # 30% inside range
    stop_short = top - (height * 0.3)
    
    return {
        "available": True,
        "side": "BREAKOUT",
        "pattern": "Range",
        "long_setup": {
            "entry": round(top, 2),
            "stop": round(stop_long, 2),
            "target": round(target_up, 2),
            "rr_ratio": _calculate_rr(top, stop_long, target_up),
        },
        "short_setup": {
            "entry": round(bottom, 2),
            "stop": round(stop_short, 2),
            "target": round(target_down, 2),
            "rr_ratio": _calculate_rr(bottom, stop_short, target_down),
        },
        "notes": [
            "Wait for breakout confirmation (close outside range)",
            "Enter on retest of broken level",
            "Stop inside range",
            "Target = measured move (range height)",
        ],
    }


def _build_triangle_setup(pattern: Dict, scenarios: Dict, bias: str) -> Dict:
    """Triangle — BREAKOUT setup."""
    if bias == "bullish":
        entry = scenarios.get("break_up", {}).get("trigger")
        target = scenarios.get("break_up", {}).get("target")
        stop = scenarios.get("break_down", {}).get("trigger")
        side = "LONG"
    elif bias == "bearish":
        entry = scenarios.get("break_down", {}).get("trigger")
        target = scenarios.get("break_down", {}).get("target")
        stop = scenarios.get("break_up", {}).get("trigger")
        side = "SHORT"
    else:
        # Neutral — both directions
        return _build_range_setup(
            {"top": scenarios.get("break_up", {}).get("trigger"),
             "bottom": scenarios.get("break_down", {}).get("trigger")},
            scenarios
        )
    
    if not entry:
        return {
            "available": False,
            "reason": "Missing triangle boundaries",
            "advice": "Wait for triangle to develop",
        }
    
    return {
        "available": True,
        "side": side,
        "pattern": "Triangle",
        "entry": round(entry, 2) if entry else None,
        "entry_type": "breakout",
        "stop": round(stop, 2) if stop else None,
        "target": round(target, 2) if target else None,
        "rr_ratio": _calculate_rr(entry, stop, target) if all([entry, stop, target]) else 0,
        "notes": [
            f"Triangle suggests {bias} bias",
            "Enter on breakout confirmation",
            "Stop on opposite side",
        ],
    }


def _build_wedge_setup(pattern: Dict, scenarios: Dict, bias: str) -> Dict:
    """Wedge — usually reversal pattern."""
    # Rising wedge = bearish, Falling wedge = bullish (usually)
    if bias == "bearish":
        entry = scenarios.get("break_down", {}).get("trigger")
        target = scenarios.get("break_down", {}).get("target")
        stop = scenarios.get("break_up", {}).get("trigger")
        side = "SHORT"
    else:
        entry = scenarios.get("break_up", {}).get("trigger")
        target = scenarios.get("break_up", {}).get("target")
        stop = scenarios.get("break_down", {}).get("trigger")
        side = "LONG"
    
    if not entry:
        return {
            "available": False,
            "reason": "Missing wedge boundaries",
            "advice": "Wait for wedge to develop",
        }
    
    return {
        "available": True,
        "side": side,
        "pattern": "Wedge",
        "entry": round(entry, 2) if entry else None,
        "entry_type": "breakout",
        "stop": round(stop, 2) if stop else None,
        "target": round(target, 2) if target else None,
        "rr_ratio": _calculate_rr(entry, stop, target) if all([entry, stop, target]) else 0,
        "notes": [
            f"Wedge suggests {bias} reversal",
            "Enter on breakout confirmation",
            "Stop on opposite side",
        ],
    }


def _build_generic_setup(dominant: Dict, scenarios: Dict) -> Dict:
    """Generic directional setup based on bias."""
    bias = dominant.get("bias", "neutral")
    
    if bias == "bullish":
        entry = scenarios.get("break_up", {}).get("trigger")
        target = scenarios.get("break_up", {}).get("target")
        stop = scenarios.get("break_down", {}).get("trigger")
        side = "LONG"
    elif bias == "bearish":
        entry = scenarios.get("break_down", {}).get("trigger")
        target = scenarios.get("break_down", {}).get("target")
        stop = scenarios.get("break_up", {}).get("trigger")
        side = "SHORT"
    else:
        return {
            "available": False,
            "reason": "Neutral bias — no directional setup",
            "advice": "Wait for bias to develop",
        }
    
    if not entry:
        return {
            "available": False,
            "reason": "Missing entry levels",
            "advice": "Wait for clearer levels",
        }
    
    return {
        "available": True,
        "side": side,
        "pattern": dominant.get("type", "Unknown").replace("_", " ").title(),
        "entry": round(entry, 2) if entry else None,
        "entry_type": "breakout",
        "stop": round(stop, 2) if stop else None,
        "target": round(target, 2) if target else None,
        "rr_ratio": _calculate_rr(entry, stop, target) if all([entry, stop, target]) else 0,
        "notes": [
            f"{bias.title()} bias detected",
            "Enter on level breakout",
            "Manage risk carefully",
        ],
    }
