"""
Sequence Patterns — detect 4 strong multi-bar sequences in recent history.

The feature snapshots encode interaction_type and volatility_state as INT
codes from feature_schema. We decode back to names before matching so rules
read naturally.

Returns (sequence_name, confidence) or (None, 0.0). At most one pattern.
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from ..learning.feature_schema import (
    INTERACTION_TYPE_CODES,
    VOLATILITY_STATE_CODES,
)

_INTERACTION_REVERSE = {v: k for k, v in INTERACTION_TYPE_CODES.items()}
_VOLATILITY_REVERSE = {v: k for k, v in VOLATILITY_STATE_CODES.items()}


def _decode_interaction(code: Any) -> str:
    try:
        return _INTERACTION_REVERSE.get(int(code), "none")
    except (TypeError, ValueError):
        return "none"


def _decode_volatility(code: Any) -> str:
    try:
        return _VOLATILITY_REVERSE.get(int(code), "normal")
    except (TypeError, ValueError):
        return "normal"


def _contains_ordered(seq: List[str], pattern: List[str]) -> bool:
    idx = 0
    for item in seq:
        if item == pattern[idx]:
            idx += 1
            if idx == len(pattern):
                return True
    return False


def detect_sequence(history: List[Any]) -> Tuple[Optional[str], float]:
    if not history or len(history) < 4:
        return None, 0.0
    tail = history[-6:]
    interactions: List[str] = []
    volatilities: List[str] = []
    for snap in tail:
        feats = (snap or {}).get("features") or {}
        interactions.append(_decode_interaction(feats.get("interaction_type")))
        volatilities.append(_decode_volatility(feats.get("volatility_state")))

    # 1) compression → breakout → pullback → trend_continuation
    if _contains_ordered(
        interactions,
        ["compression", "breakout", "pullback", "trend_continuation"],
    ):
        return "compression_breakout_pullback_continuation", 0.85

    # 2) trend → early_reversal → rejection  (classic reversal prelude)
    if _contains_ordered(
        interactions,
        ["trend_continuation", "early_reversal", "rejection"],
    ):
        return "trend_divergence_rejection_reversal", 0.80

    # 3) repeated rejection at the same supply/demand (>=2 in last 3)
    if interactions[-3:].count("rejection") >= 2:
        return "repeated_rejection_pressure", 0.70

    # 4) sustained chaos regime (>=2 chaos prints in last 3 bars)
    if volatilities[-3:].count("chaos") >= 2:
        return "high_volatility_instability", 0.75

    return None, 0.0
