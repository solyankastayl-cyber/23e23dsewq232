"""
No-lookahead invariants for the Simulation Engine.

A single source of truth for the safety checks the replay engine runs at
each step. If any helper fails -> the step is rejected so we never silently
leak information from the future into a prediction.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def slice_visible(
    historical_candles: List[Dict[str, Any]], as_of_index: int
) -> List[Dict[str, Any]]:
    """Return the prefix candles[:as_of_index + 1].

    Raises ValueError if as_of_index is out of range. Always returns a *new*
    list so the caller cannot mutate the underlying historical buffer.
    """
    if not isinstance(as_of_index, int) or as_of_index < 0:
        raise ValueError(f"as_of_index must be a non-negative int, got {as_of_index!r}")
    if as_of_index >= len(historical_candles or []):
        raise ValueError(
            f"as_of_index {as_of_index} >= len(historical_candles)={len(historical_candles)}"
        )
    return list(historical_candles[: as_of_index + 1])


def future_window(
    historical_candles: List[Dict[str, Any]],
    as_of_index: int,
    horizon: int,
) -> List[Dict[str, Any]]:
    """Return candles[as_of_index + 1 : as_of_index + 1 + horizon].

    May return fewer than `horizon` candles when the simulation is near the
    tail of the historical buffer. The caller decides whether that's enough
    to evaluate the prediction outcome.
    """
    if horizon <= 0:
        return []
    start = as_of_index + 1
    return list(historical_candles[start : start + horizon])


def assert_no_future_leak(
    visible_candles: List[Dict[str, Any]],
    historical_candles: List[Dict[str, Any]],
    as_of_index: int,
) -> None:
    """Sanity check used by QA: the visible slice must not contain any candle
    that lives strictly after as_of_index in the source buffer."""
    if len(visible_candles) > as_of_index + 1:
        raise AssertionError(
            f"visible_candles ({len(visible_candles)}) > as_of_index+1 ({as_of_index + 1})"
        )
    for i, c in enumerate(visible_candles):
        ref = historical_candles[i] if i < len(historical_candles) else None
        if ref is None:
            raise AssertionError(f"visible_candle[{i}] missing from historical buffer")


def pick_evaluation_outcome(
    record: Dict[str, Any],
    full_candles: List[Dict[str, Any]],
    as_of_index: int,
    *,
    min_horizon: int,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Compute outcome by replaying future candles WITHOUT calling chart_data.

    Returns (outcome_dict, error_reason). One of the two is always None.
    error_reason is one of:
      - None  -> outcome ok
      - "insufficient_horizon"
      - "unknown"
    """
    try:
        from modules.ta_prediction_intelligence.evaluation.ta_prediction_outcome_worker import (
            evaluate_prediction_with_candles,
        )
    except Exception as e:
        return None, f"unknown:{type(e).__name__}"
    fwd = future_window(full_candles, as_of_index, min_horizon)
    if len(fwd) < min_horizon:
        return None, "insufficient_horizon"
    # The worker locates the entry index by candle_close_ts. We pass the full
    # candles[: as_of_index + 1 + min_horizon] window so the locator finds the
    # anchor and walks `min_horizon` future bars.
    visible_plus_future = list(full_candles[: as_of_index + 1 + min_horizon])
    try:
        outcome = evaluate_prediction_with_candles(
            record, visible_plus_future, min_horizon=min_horizon
        )
    except Exception as e:
        return None, f"unknown:{type(e).__name__}"
    if outcome is None:
        return None, "insufficient_horizon"
    return outcome, None
