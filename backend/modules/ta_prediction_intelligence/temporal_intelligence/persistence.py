"""
Signal Persistence — how many consecutive snapshots the current value of
a feature has been unchanged.

Works uniformly for integer enums (trend_phase, momentum_state, interaction_type)
and for any other discretely-valued feature. Pure + stateless.
"""
from __future__ import annotations

from typing import Any, List


def count_persistence(history: List[Any], key: str) -> int:
    if not history:
        return 0
    last_feats = (history[-1] or {}).get("features") or {}
    current = last_feats.get(key)
    if current is None:
        return 0
    n = 0
    for snap in reversed(history):
        feats = (snap or {}).get("features") or {}
        if feats.get(key) == current:
            n += 1
        else:
            break
    return int(n)
