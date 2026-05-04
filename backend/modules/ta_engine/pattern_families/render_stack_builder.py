"""
Render Stack Builder - Multi-Pattern Visualization
===================================================
Show 1 dominant + 2 secondary patterns

Updated: Now handles both patterns_ranked list AND direct dominant pattern
"""

from typing import List, Dict, Optional
from .pattern_render_builder import build_render_contract


def build_render_stack(
    patterns_ranked: List[Dict] = None,
    active_range: Optional[Dict] = None,
    candles: List[Dict] = None,
    dominant_pattern: Optional[Dict] = None,  # NEW: direct dominant from response
    alternative_patterns: List[Dict] = None,  # NEW: alternatives
) -> List[Dict]:
    """
    Build render stack from ranked patterns OR direct dominant.
    
    Returns max 3 render objects:
    - 1 dominant (full visibility)
    - 2 secondary (reduced visibility)
    """
    stack = []
    
    # 1. ACTIVE RANGE always dominates
    if active_range and (active_range.get("top") or active_range.get("resistance")):
        range_contract = _build_range_contract(active_range, candles)
        if range_contract:
            stack.append({
                "role": "dominant",
                "opacity": 1.0,
                "line_width": 2.5,
                "contract": range_contract,
                "type": "range",
            })
    
    # 2. Handle patterns_ranked (if provided)
    candidates = patterns_ranked[:3] if patterns_ranked else []
    
    # 3. If no candidates but have dominant_pattern, use it
    if not candidates and dominant_pattern:
        # Check if dominant_pattern is already a render contract (has anchors)
        if dominant_pattern.get("anchors") and dominant_pattern.get("display_approved"):
            # It's already a ready render contract - use directly
            stack.append({
                "role": "dominant",
                "opacity": 1.0,
                "line_width": 2.5,
                "contract": dominant_pattern,  # Use as-is
                "type": dominant_pattern.get("type", "unknown"),
            })
        else:
            # Try to build contract from raw pattern
            contract = build_render_contract(dominant_pattern, None, candles)
            if contract and not stack:  # Only add if no range already
                stack.append({
                    "role": "dominant",
                    "opacity": 1.0,
                    "line_width": 2.5,
                    "contract": contract,
                    "type": dominant_pattern.get("type", "unknown"),
                })
        
        # Add alternatives as secondary
        if alternative_patterns:
            for i, alt in enumerate(alternative_patterns[:2]):
                # Check if alt is already a render contract
                if alt.get("anchors") and alt.get("display_approved"):
                    alt_contract = alt
                else:
                    alt_contract = build_render_contract(alt, None, candles)
                if not alt_contract:
                    continue
                if stack and _is_redundant(stack[0].get("contract"), alt_contract):
                    continue
                stack.append({
                    "role": "secondary",
                    "opacity": 0.4 if i == 0 else 0.25,
                    "line_width": 1.5 if i == 0 else 1.0,
                    "contract": alt_contract,
                    "type": alt.get("type", "unknown"),
                })
        return stack
    
    # 4. Process patterns_ranked list
    if not stack and candidates:
        first = candidates[0]
        contract = build_render_contract(first, None, candles)
        
        if contract:
            stack.append({
                "role": "dominant",
                "opacity": 1.0,
                "line_width": 2.5,
                "contract": contract,
                "type": first.get("type", "unknown"),
            })
        candidates = candidates[1:]
    
    # 5. Add secondary patterns (max 2)
    for i, pattern in enumerate(candidates[:2]):
        contract = build_render_contract(pattern, None, candles)
        if not contract:
            continue
        if stack and _is_redundant(stack[0].get("contract"), contract):
            continue
        stack.append({
            "role": "secondary",
            "opacity": 0.4 if i == 0 else 0.25,
            "line_width": 1.5 if i == 0 else 1.0,
            "contract": contract,
            "type": pattern.get("type", "unknown"),
        })
    
    return stack


def _build_range_contract(r: Dict, candles: List[Dict] = None) -> Optional[Dict]:
    """Build render contract for range."""
    top = r.get("top") or r.get("resistance")
    bottom = r.get("bottom") or r.get("support")
    
    if top is None or bottom is None:
        return None
    
    start_time = r.get("start_time") or r.get("left_time")
    end_time = r.get("end_time") or r.get("right_time")
    
    if candles and not start_time:
        start_time = candles[0].get("time", candles[0].get("timestamp"))
    if candles and not end_time:
        end_time = candles[-1].get("time", candles[-1].get("timestamp"))
    
    return {
        "type": "range",
        "render_mode": "box",
        "box": {"top": float(top), "bottom": float(bottom)},
        "window": {"start": _norm_time(start_time), "end": _norm_time(end_time)},
        "labels": [
            {"kind": "resistance", "price": float(top)},
            {"kind": "support", "price": float(bottom)},
        ],
    }


def _is_redundant(dominant: Optional[Dict], candidate: Optional[Dict]) -> bool:
    """Check if candidate is too similar to dominant."""
    if not dominant or not candidate:
        return False
    
    dom_type = dominant.get("type", "")
    cand_type = candidate.get("type", "")
    
    if dom_type == cand_type:
        return True
    
    similar_groups = [
        {"range", "rectangle", "horizontal_channel"},
        {"double_top", "triple_top"},
        {"double_bottom", "triple_bottom"},
    ]
    
    for group in similar_groups:
        if dom_type in group and cand_type in group:
            return True
    
    return False


def _norm_time(t) -> Optional[int]:
    """Normalize timestamp to seconds."""
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return int(t / 1000) if t > 9999999999 else int(t)
    return None


__all__ = ["build_render_stack"]
