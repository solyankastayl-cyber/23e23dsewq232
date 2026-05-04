"""
History Overlay Builder
=======================

Selects which historical patterns to show as "ghosts" on the chart.

Rules:
- Only confirmed or invalidated patterns
- Maximum 2 overlays
- No current forming patterns
"""

from typing import Dict, List


def build_history_overlay(history_items: List[Dict], max_overlays: int = 2) -> List[Dict]:
    """
    Build history overlay from stored snapshots.

    Args:
        history_items: List of history snapshots (newest first)
        max_overlays: Maximum number of ghost overlays

    Returns:
        List of overlay items for rendering
    """
    overlays = []

    for item in history_items:
        dom = item.get("dominant") or {}
        rc = item.get("render_contract")

        # Skip if no render contract
        if not rc:
            continue

        lifecycle = dom.get("lifecycle")

        # Only include confirmed or invalidated
        if lifecycle not in ("confirmed_up", "confirmed_down", "invalidated"):
            continue

        # Determine opacity based on lifecycle
        if lifecycle == "invalidated":
            opacity = 0.06
        else:
            opacity = 0.12

        overlays.append({
            "timestamp": item.get("timestamp"),
            "type": dom.get("type"),
            "lifecycle": lifecycle,
            "event_type": item.get("event_type", "unknown"),
            "contract": rc,
            "opacity": opacity,
            "market_state": item.get("market_state"),
        })

        if len(overlays) >= max_overlays:
            break

    return overlays


def get_key_events(history_items: List[Dict], limit: int = 5) -> List[Dict]:
    """
    Extract key market events for timeline display.

    Args:
        history_items: List of history snapshots
        limit: Maximum events to return

    Returns:
        List of key events
    """
    events = []

    for item in history_items:
        event_type = item.get("event_type")
        dom = item.get("dominant") or {}

        # Skip regular updates
        if event_type == "update":
            continue

        events.append({
            "timestamp": item.get("timestamp"),
            "event_type": event_type,
            "type": dom.get("type"),
            "lifecycle": dom.get("lifecycle"),
            "market_state": item.get("market_state"),
            "confidence": dom.get("confidence"),
        })

        if len(events) >= limit:
            break

    return events


__all__ = ["build_history_overlay", "get_key_events"]
