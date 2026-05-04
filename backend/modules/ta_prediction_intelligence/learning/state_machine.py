"""
Explicit state machines for trend/momentum/volatility transitions.

Inputs to classify_* are numeric features already produced by engines.
Output of detect_*_transition is a non-negative int from the allowed
transitions codebook (0 = none / disallowed / noise / unchanged).

No randomness. Pure functions.
"""
from __future__ import annotations

from typing import Optional

from .feature_schema import (
    MOMENTUM_TRANSITIONS_CODED,
    TREND_TRANSITIONS_CODED,
    VOLATILITY_TRANSITIONS_CODED,
)

# ────────────────────────────────────────────────────────────────
# Classifiers. Thresholds are deliberate & conservative; they live here,
# not inside engines, because this layer is for LEARNING only — engines
# already publish their own bias/confidence via contributions.
# ────────────────────────────────────────────────────────────────


def classify_trend_state(
    trend_strength: Optional[float],
    trend_maturity: Optional[float] = None,
    exhaustion_flag: Optional[int] = None,
) -> str:
    """Return one of {range, weak_trend, strong_trend, exhaustion}.

    Rules:
      * exhaustion_flag=1 AND |trend_strength|>=0.4 → exhaustion
      * trend_maturity>=0.85 AND |trend_strength|>=0.5 → exhaustion
      * |trend_strength| < 0.20 → range
      * |trend_strength| < 0.55 → weak_trend
      * else → strong_trend
    """
    ts = 0.0 if trend_strength is None else float(trend_strength)
    tm = 0.0 if trend_maturity is None else float(trend_maturity)
    ex = 0 if exhaustion_flag is None else int(exhaustion_flag)
    a = abs(ts)
    if ex == 1 and a >= 0.4:
        return "exhaustion"
    if tm >= 0.85 and a >= 0.5:
        return "exhaustion"
    if a < 0.20:
        return "range"
    if a < 0.55:
        return "weak_trend"
    return "strong_trend"


def classify_momentum_state(
    rsi: Optional[float],
    macd_hist: Optional[float],
    exhaustion_flag: Optional[int] = None,
    momentum_alignment: Optional[float] = None,
) -> str:
    """Return one of {flat, building, strong, exhaust}.

    * exhaustion_flag=1 → exhaust
    * |macd|<0.05 AND 0.40<rsi<0.60 → flat
    * |macd|>=0.15 OR rsi>=0.70 OR rsi<=0.30 → strong
    * else → building
    """
    r = 0.5 if rsi is None else float(rsi)
    m = 0.0 if macd_hist is None else abs(float(macd_hist))
    ex = 0 if exhaustion_flag is None else int(exhaustion_flag)
    if ex == 1:
        return "exhaust"
    if m < 0.05 and 0.40 < r < 0.60:
        return "flat"
    if m >= 0.15 or r >= 0.70 or r <= 0.30:
        return "strong"
    return "building"


def classify_volatility_state(
    atr_pct: Optional[float],
    compression_ratio: Optional[float],
    expansion_flag: Optional[int] = None,
    explosive_bar_flag: Optional[int] = None,
) -> str:
    """Return one of {compression, normal, expansion, chaos}.

    * explosive_bar_flag=1 AND expansion_flag=1 → chaos
    * compression_ratio<0.60 → compression
    * expansion_flag=1 → expansion
    * else → normal
    """
    cr = 1.0 if compression_ratio is None else float(compression_ratio)
    ef = 0 if expansion_flag is None else int(expansion_flag)
    xb = 0 if explosive_bar_flag is None else int(explosive_bar_flag)
    if xb == 1 and ef == 1:
        return "chaos"
    if cr < 0.60:
        return "compression"
    if ef == 1:
        return "expansion"
    return "normal"


# ────────────────────────────────────────────────────────────────
# Transition detection. Pure function: (prev_state, curr_state) → code.
# ────────────────────────────────────────────────────────────────

def _lookup(prev: Optional[str], curr: Optional[str], table: dict) -> int:
    if prev is None or curr is None:
        return 0
    if prev == curr:
        return 0
    return int(table.get((prev, curr), 0))


def detect_trend_transition(prev: Optional[str], curr: Optional[str]) -> int:
    return _lookup(prev, curr, TREND_TRANSITIONS_CODED)


def detect_momentum_transition(prev: Optional[str], curr: Optional[str]) -> int:
    return _lookup(prev, curr, MOMENTUM_TRANSITIONS_CODED)


def detect_volatility_transition(prev: Optional[str], curr: Optional[str]) -> int:
    return _lookup(prev, curr, VOLATILITY_TRANSITIONS_CODED)
