"""
Pattern Event Engine — Smart Replay Events
===========================================

Extracts key events from pattern history for event-driven replay:
- pattern_change: dominant pattern type changed
- breakout_up: lifecycle confirmed upward
- breakdown: lifecycle confirmed downward
- invalidation: pattern invalidated
- market_state_change: regime changed
- confidence_jump: significant confidence shift
"""

from typing import Dict, List, Optional
from copy import deepcopy


def extract_events(history_items: List[Dict]) -> List[Dict]:
    """
    Extract key events from history timeline.
    
    Args:
        history_items: List of snapshots (oldest first for proper comparison)
    
    Returns:
        List of event dicts
    """
    events = []
    prev = None
    
    for item in history_items:
        dom = item.get("dominant") or {}
        ts = item.get("timestamp")
        market_state = item.get("market_state")
        
        if not prev:
            prev = item
            continue
        
        prev_dom = prev.get("dominant") or {}
        prev_state = prev.get("market_state")
        
        # 1. Pattern type changed
        if prev_dom.get("type") != dom.get("type"):
            events.append({
                "type": "pattern_change",
                "timestamp": ts,
                "label": f"{_format_type(prev_dom.get('type'))} → {_format_type(dom.get('type'))}",
                "from_type": prev_dom.get("type"),
                "to_type": dom.get("type"),
            })
        
        # 2. Lifecycle changed
        prev_lc = prev_dom.get("lifecycle")
        curr_lc = dom.get("lifecycle")
        
        if prev_lc != curr_lc:
            if curr_lc == "confirmed_up":
                etype = "breakout_up"
                label = "Breakout ↑"
            elif curr_lc == "confirmed_down":
                etype = "breakdown"
                label = "Breakdown ↓"
            elif curr_lc == "invalidated":
                etype = "invalidation"
                label = "Invalidated ✕"
            else:
                etype = "lifecycle_change"
                label = f"{prev_lc or 'forming'} → {curr_lc or 'forming'}"
            
            events.append({
                "type": etype,
                "timestamp": ts,
                "label": label,
                "from_lifecycle": prev_lc,
                "to_lifecycle": curr_lc,
            })
        
        # 3. Market state changed
        if prev_state != market_state and prev_state and market_state:
            events.append({
                "type": "market_state_change",
                "timestamp": ts,
                "label": f"{prev_state} → {market_state}",
                "from_state": prev_state,
                "to_state": market_state,
            })
        
        # 4. Confidence jump (>=12% change)
        prev_conf = prev_dom.get("confidence") or 0
        curr_conf = dom.get("confidence") or 0
        
        if abs(curr_conf - prev_conf) >= 0.12:
            direction = "↑" if curr_conf > prev_conf else "↓"
            events.append({
                "type": "confidence_jump",
                "timestamp": ts,
                "label": f"Conf {direction} {round(prev_conf * 100)}% → {round(curr_conf * 100)}%",
                "from_confidence": prev_conf,
                "to_confidence": curr_conf,
            })
        
        prev = item
    
    return _dedupe_events(events)


def _format_type(ptype: Optional[str]) -> str:
    """Format pattern type for display."""
    if not ptype:
        return "None"
    return ptype.replace("_", " ").title()


def _dedupe_events(events: List[Dict]) -> List[Dict]:
    """Remove duplicate events at same timestamp."""
    out = []
    seen = set()
    
    for e in events:
        key = (e["type"], e["timestamp"])
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    
    return out


def get_event_icon(event_type: str) -> str:
    """Get icon for event type."""
    icons = {
        "breakout_up": "▲",
        "breakdown": "▼",
        "invalidation": "✕",
        "pattern_change": "⇄",
        "market_state_change": "◉",
        "confidence_jump": "◎",
        "lifecycle_change": "○",
    }
    return icons.get(event_type, "•")


def get_event_color(event_type: str) -> str:
    """Get color for event type."""
    colors = {
        "breakout_up": "#22c55e",
        "breakdown": "#ef4444",
        "invalidation": "#64748b",
        "pattern_change": "#f59e0b",
        "market_state_change": "#8b5cf6",
        "confidence_jump": "#06b6d4",
        "lifecycle_change": "#94a3b8",
    }
    return colors.get(event_type, "#64748b")


__all__ = ["extract_events", "get_event_icon", "get_event_color"]
