"""
State Evolution — trend / momentum / volatility directional evolution.

Each classifier returns a short string from a fixed vocabulary:
  * trend_evolution      ∈ {unknown, flat, stable, strengthening, weakening, reversing}
  * momentum_evolution   ∈ {unknown, stable, accelerating, decelerating}
  * volatility_evolution ∈ {unknown, stable, expanding, compressing}

Inputs are lists of FeatureSnapshot dicts (as stored by HybridTemporalBuffer).
All classifiers are pure, deterministic, and tolerant of missing fields.
"""
from __future__ import annotations

from typing import Any, List

from .types import MIN_HISTORY


def _feat(snapshot: Any, key: str, default: float = 0.0) -> float:
    if not isinstance(snapshot, dict):
        return default
    feats = snapshot.get("features") or {}
    v = feats.get(key, default)
    try:
        v = float(v)
        if v != v:  # NaN
            return default
        return v
    except (TypeError, ValueError):
        return default


def _avg(xs):
    return sum(xs) / len(xs) if xs else 0.0


def trend_evolution(history: List[Any]) -> str:
    if not history or len(history) < MIN_HISTORY:
        return "unknown"
    series = [_feat(x, "trend_strength") for x in history]
    recent = _avg(series[-3:])
    previous = _avg(series[-min(8, len(series)): -3]) if len(series) > 3 else 0.0
    delta = recent - previous
    if abs(recent) < 0.15 and abs(previous) < 0.15:
        return "flat"
    # Reversing: sign flip AND both magnitudes non-trivial.
    if recent * previous < 0 and abs(recent) >= 0.15 and abs(previous) >= 0.15:
        return "reversing"
    if delta > 0.10:
        return "strengthening"
    if delta < -0.10:
        return "weakening"
    return "stable"


def momentum_evolution(history: List[Any]) -> str:
    if not history or len(history) < MIN_HISTORY:
        return "unknown"
    series = [_feat(x, "macd_slope_5") for x in history]
    recent = _avg(series[-3:])
    previous = _avg(series[-min(8, len(series)): -3]) if len(series) > 3 else 0.0
    # Avoid division surprises: compare magnitudes with explicit thresholds.
    if abs(recent) < 0.02 and abs(previous) < 0.02:
        return "stable"
    if previous == 0:
        return "accelerating" if abs(recent) > 0.02 else "stable"
    ratio = recent / previous
    # Both positive or both negative → magnitude change matters.
    if ratio > 1.25 and recent * previous > 0:
        return "accelerating"
    if 0 < ratio < 0.75 and recent * previous > 0:
        return "decelerating"
    # Sign flipped is also a form of deceleration/new acceleration; we call it
    # decelerating of the prior direction.
    if recent * previous < 0:
        return "decelerating"
    return "stable"


def volatility_evolution(history: List[Any]) -> str:
    if not history or len(history) < MIN_HISTORY:
        return "unknown"
    series = [_feat(x, "atr_pct") for x in history]
    recent = _avg(series[-3:])
    previous = _avg(series[-min(8, len(series)): -3]) if len(series) > 3 else 0.0
    if recent == 0 and previous == 0:
        return "stable"
    if previous == 0:
        return "expanding" if recent > 0 else "stable"
    if recent > previous * 1.25:
        return "expanding"
    if recent < previous * 0.80:
        return "compressing"
    return "stable"
