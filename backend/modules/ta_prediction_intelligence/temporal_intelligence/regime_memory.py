"""
Regime Memory — stability / flip frequency / current-state duration.

Uses the integer-coded volatility_state from the feature snapshot
(0=compression, 1=normal, 2=expansion, 3=chaos). Pure + stateless.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _safe_int(x, default=-1):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def regime_stats(history: List[Any]) -> Dict[str, Any]:
    if not history:
        return {
            "regime_stability_score": 0.0,
            "regime_flip_frequency": 0.0,
            "regime_duration_bars": 0,
        }
    regimes = []
    for x in history:
        if not isinstance(x, dict):
            continue
        feats = x.get("features") or {}
        regimes.append(_safe_int(feats.get("volatility_state"), -1))
    if not regimes:
        return {
            "regime_stability_score": 0.0,
            "regime_flip_frequency": 0.0,
            "regime_duration_bars": 0,
        }
    current = regimes[-1]
    duration = 0
    for r in reversed(regimes):
        if r == current:
            duration += 1
        else:
            break
    flips = sum(1 for a, b in zip(regimes[:-1], regimes[1:]) if a != b)
    denom = max(len(regimes) - 1, 1)
    flip_frequency = flips / denom
    stability = max(0.0, 1.0 - flip_frequency)
    return {
        "regime_stability_score": round(stability, 4),
        "regime_flip_frequency": round(flip_frequency, 4),
        "regime_duration_bars": int(duration),
    }
