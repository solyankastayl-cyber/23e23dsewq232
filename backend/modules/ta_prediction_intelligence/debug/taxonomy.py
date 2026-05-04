"""
Error taxonomy — locked per spec.

Every evaluated prediction receives EXACTLY ONE primary error type from
`ErrorType`. Classification rules are deterministic and pure.

Thresholds are explicit constants. Bumping them requires explicit
architect approval and a debug-layer version bump (DEBUG_VERSION).
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Tuple

DEBUG_VERSION = "v1"
DEBUG_BUILDER_VERSION = "1.0.0"

# ─── Thresholds (locked) ─────────────────────────────────────────────────
# pct = signed fraction (0.001 = 0.10%).
SMALL_MOVE_THRESHOLD: float = 0.0010              # |return_h6| below this → noise
HIGH_VOLATILITY_THRESHOLD: float = 0.0050         # realised stdev/log-return per-bar
HIGH_CONFLICT_THRESHOLD: float = 0.40             # conflict_ratio for chaotic
OVERCONFIDENT_THRESHOLD: float = 0.65             # decision_confidence above which a wrong call is OVERCONFIDENT
UNDERCONFIDENT_THRESHOLD: float = 0.40            # decision_confidence below which a correct call is UNDERCONFIDENT
TIMING_ADVERSE_THRESHOLD: float = 0.0050          # MAE within h6 considered "large"

# decision.signal_strength == "no_edge" → "ignored" by Tier-1 metrics
# but we still emit a debug record (error_type = LOW_SIGNAL_NOISE,
# meta.no_edge_ignored = True).

# Map decision.primary_scenario → integer direction sign.
_SCENARIO_TO_SIGN: Dict[str, int] = {
    "bull": +1,
    "bear": -1,
    "base": 0,
    "none": 0,
}


def _scenario_sign(name: Optional[str]) -> int:
    return _SCENARIO_TO_SIGN.get((name or "").lower(), 0)


def _return_sign(value: Optional[float]) -> int:
    if value is None:
        return 0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0
    if v > SMALL_MOVE_THRESHOLD:
        return +1
    if v < -SMALL_MOVE_THRESHOLD:
        return -1
    return 0


class ErrorType(str, Enum):
    CORRECT = "correct"
    WRONG_DIRECTION = "wrong_direction"
    WRONG_SCENARIO = "wrong_scenario"
    OVERCONFIDENT = "overconfident"
    UNDERCONFIDENT = "underconfident"
    LOW_SIGNAL_NOISE = "low_signal_noise"
    CHAOTIC_MARKET = "chaotic_market"
    TIMING_ERROR = "timing_error"


def _entry_timing_bad(
    return_h1: Optional[float],
    return_h6: Optional[float],
    max_adverse_move_pct: Optional[float],
) -> bool:
    """Direction is right at h6 but the trade went hard against in h1
    AND adverse excursion was material.
    """
    if return_h6 is None or return_h1 is None or max_adverse_move_pct is None:
        return False
    try:
        h1 = float(return_h1)
        h6 = float(return_h6)
        mae = float(max_adverse_move_pct)
    except (TypeError, ValueError):
        return False
    # h1 sign opposite of h6 sign AND adverse move >= TIMING_ADVERSE_THRESHOLD
    if h6 == 0 or h1 == 0:
        return False
    if (h1 > 0) == (h6 > 0):
        return False
    return abs(mae) >= TIMING_ADVERSE_THRESHOLD


def classify_error(record: Dict[str, Any]) -> Tuple[ErrorType, Dict[str, Any]]:
    """
    Pure classification. Returns (ErrorType, classification_meta).

    Inputs:
        record:
            evaluation_state == "evaluated"
            outcome.return_h1 / return_h3 / return_h6
            outcome.max_favourable_move_pct / max_adverse_move_pct
            outcome.volatility_future_h6
            outcome.winning_scenario
            decision_intelligence.primary_scenario / decision_confidence /
                signal_strength / risk_level
            conflict_ratio (top-level)

    Output:
        (error_type, meta) where meta carries derived facts that downstream
        layers need (real_dir, pred_dir, scenario_correct, ...).
    """
    outcome = record.get("outcome") or {}
    decision = record.get("decision_intelligence") or {}

    return_h1 = outcome.get("return_h1")
    return_h6 = outcome.get("return_h6")
    mae_pct = outcome.get("max_adverse_move_pct")
    vol_future = outcome.get("volatility_future_h6")
    winning = str(outcome.get("winning_scenario") or "").lower()

    primary_scenario = str(decision.get("primary_scenario") or "none").lower()
    decision_confidence = float(decision.get("decision_confidence") or 0.0)
    signal_strength = str(decision.get("signal_strength") or "").lower()
    conflict_ratio = float(record.get("conflict_ratio") or 0.0)

    pred_dir = _scenario_sign(primary_scenario)
    real_dir = _return_sign(return_h6)
    scenario_correct = (winning == primary_scenario) and primary_scenario in ("bull", "base", "bear")
    correct_direction = (pred_dir == real_dir) and pred_dir != 0

    meta: Dict[str, Any] = {
        "pred_dir": pred_dir,
        "real_dir": real_dir,
        "scenario_correct": scenario_correct,
        "correct_direction": correct_direction,
        "signal_strength": signal_strength,
        "primary_scenario": primary_scenario,
        "winning_scenario": winning,
        "decision_confidence": decision_confidence,
        "return_h6": return_h6,
        "return_h1": return_h1,
        "max_adverse_move_pct": mae_pct,
        "volatility_future_h6": vol_future,
        "conflict_ratio": conflict_ratio,
        "thresholds": {
            "small_move": SMALL_MOVE_THRESHOLD,
            "high_volatility": HIGH_VOLATILITY_THRESHOLD,
            "high_conflict": HIGH_CONFLICT_THRESHOLD,
            "overconfident": OVERCONFIDENT_THRESHOLD,
            "underconfident": UNDERCONFIDENT_THRESHOLD,
            "timing_adverse": TIMING_ADVERSE_THRESHOLD,
        },
    }

    # Spec rule: signal_strength == "no_edge" → not a real prediction.
    # Map to LOW_SIGNAL_NOISE with no_edge_ignored=True so Tier-1 metrics
    # exclude it cleanly.
    if signal_strength == "no_edge":
        meta["no_edge_ignored"] = True
        return ErrorType.LOW_SIGNAL_NOISE, meta

    # Rule 1 (locked): noise dominates.
    if return_h6 is not None and abs(float(return_h6)) < SMALL_MOVE_THRESHOLD:
        return ErrorType.LOW_SIGNAL_NOISE, meta

    # Rule 2: chaotic market.
    if (
        conflict_ratio > HIGH_CONFLICT_THRESHOLD
        and vol_future is not None
        and float(vol_future) >= HIGH_VOLATILITY_THRESHOLD
    ):
        return ErrorType.CHAOTIC_MARKET, meta

    # Rule 3: direction wrong.
    if pred_dir != real_dir and pred_dir != 0:
        if decision_confidence > OVERCONFIDENT_THRESHOLD:
            return ErrorType.OVERCONFIDENT, meta
        return ErrorType.WRONG_DIRECTION, meta

    # If primary is base (sign=0), real_dir might still differ; treat as
    # scenario miss because direction sign isn't actionable.
    if pred_dir == 0 and real_dir != 0:
        # Predicted base but actual move is directional; this is a scenario error
        # (winning_scenario will reflect the move direction).
        return ErrorType.WRONG_SCENARIO, meta

    # Rule 4: scenario miss (e.g. predicted bull, real_dir bull, but winning was base).
    if not scenario_correct:
        return ErrorType.WRONG_SCENARIO, meta

    # Rule 5: direction correct + scenario correct.
    if correct_direction or (pred_dir == 0 and real_dir == 0):
        if decision_confidence < UNDERCONFIDENT_THRESHOLD:
            return ErrorType.UNDERCONFIDENT, meta
        if _entry_timing_bad(return_h1, return_h6, mae_pct):
            return ErrorType.TIMING_ERROR, meta
        return ErrorType.CORRECT, meta

    # Defensive: shouldn't reach here.
    return ErrorType.WRONG_SCENARIO, meta
