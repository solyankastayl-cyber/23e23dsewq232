"""
Market Regime Detector — SHADOW V2 (Phase C.2)
==============================================

Second "eye" of the system. Runs ALONGSIDE the V1 detector, but:
  * It does NOT affect Router.
  * It does NOT affect Strategy selection.
  * It does NOT influence execution in any way.
  * It is logged only, and persisted per-signal into `shadow_trades.regime_debug`.

Rules (V2, minimal, intentionally NOT fancy):
  - UPTREND    : price > ma50  AND ma50_slope > 0  AND ma200_slope >= 0
  - DOWNTREND  : price < ma50  AND ma50_slope < 0  AND ma200_slope <= 0
  - RANGE      : everything else (including transitional / mixed tapes)

Motivation:
  Forensic audit of Phase C TRUTH lane proved that V1 can classify a market
  as DOWNTREND while BOTH MA50 and MA200 are already rising and price is
  already above MA50. That is a logically impossible state: the market is
  in early recovery, not downtrend. V2 explicitly requires slope agreement,
  so recovery phases fall into RANGE instead of silently feeding SHORT.

Integration Contract:
  * This module must not import anything from `market_regime.py` besides the
    raw RegimeType enum (optional). It keeps V2 fully independent.
  * Callers must compute `ma50_slope` and `ma200_slope` from the SAME candle
    window used by V1 to keep the comparison apples-to-apples.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
#  Result container
# ---------------------------------------------------------------------------
@dataclass
class RegimeV2Result:
    """Lightweight result. We intentionally do NOT return a MarketRegime to
    avoid ANY chance of v2 leaking into the router."""
    regime: str                       # "UPTREND" | "DOWNTREND" | "RANGE" | "UNKNOWN"
    price: Optional[float]
    ma20: Optional[float]
    ma50: Optional[float]
    ma200: Optional[float]
    ma50_slope: Optional[float]
    ma200_slope: Optional[float]
    reason: str                       # short human-readable tag

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
#  Slope helpers (no external deps)
# ---------------------------------------------------------------------------
def rolling_mean_series(closes: Sequence[float], window: int, n: int = 6) -> List[float]:
    """
    Last `n` chronological values of the rolling mean of size `window`.

    Example with closes length 205, window=50, n=6:
        returns list of 6 MA50 points, corresponding to the last 6 candles
        (oldest-first, newest-last).
    """
    if not closes or window <= 0 or n <= 0:
        return []
    if len(closes) < window + n - 1:
        return []
    out: List[float] = []
    for i in range(n):
        # newest MA is at the end; iterate oldest -> newest
        end = len(closes) - (n - 1 - i)
        start = end - window
        if start < 0:
            return []
        out.append(sum(closes[start:end]) / window)
    return out


def calc_slope(series: Sequence[float], window: int = 5) -> float:
    """
    Simple finite-difference slope over the last `window` bars of the series.
    Returns absolute price-units delta: series[-1] - series[-(window+1)].

    If the series is too short, returns 0.0 (treated as flat -> falls into RANGE).
    """
    if not series or len(series) < window + 1:
        return 0.0
    return float(series[-1] - series[-(window + 1)])


# ---------------------------------------------------------------------------
#  Core detector
# ---------------------------------------------------------------------------
def detect_regime_v2(
    price: Optional[float],
    ma20: Optional[float],
    ma50: Optional[float],
    ma200: Optional[float],
    ma50_slope: Optional[float],
    ma200_slope: Optional[float],
) -> RegimeV2Result:
    """
    Shadow regime classifier.

    Returns RegimeV2Result. NEVER raises on malformed input — returns UNKNOWN
    so callers can log and move on without killing the pipeline.
    """
    # --- guard: need price and ma50 at minimum -----------------------------
    if price is None or ma50 is None:
        return RegimeV2Result(
            regime="UNKNOWN",
            price=price, ma20=ma20, ma50=ma50, ma200=ma200,
            ma50_slope=ma50_slope, ma200_slope=ma200_slope,
            reason="insufficient_data",
        )

    # slope defaults to 0 (flat) if unknown — forces RANGE classification
    s50 = ma50_slope if ma50_slope is not None else 0.0
    s200 = ma200_slope if ma200_slope is not None else 0.0
    ma200_eff = ma200 if ma200 is not None else ma50

    # --- strict UPTREND ----------------------------------------------------
    if price > ma50 and s50 > 0 and s200 >= 0:
        return RegimeV2Result(
            regime="UPTREND",
            price=price, ma20=ma20, ma50=ma50, ma200=ma200_eff,
            ma50_slope=s50, ma200_slope=s200,
            reason="price>ma50 & slope50>0 & slope200>=0",
        )

    # --- strict DOWNTREND --------------------------------------------------
    if price < ma50 and s50 < 0 and s200 <= 0:
        return RegimeV2Result(
            regime="DOWNTREND",
            price=price, ma20=ma20, ma50=ma50, ma200=ma200_eff,
            ma50_slope=s50, ma200_slope=s200,
            reason="price<ma50 & slope50<0 & slope200<=0",
        )

    # --- RANGE (transitional / mixed / recovery) --------------------------
    return RegimeV2Result(
        regime="RANGE",
        price=price, ma20=ma20, ma50=ma50, ma200=ma200_eff,
        ma50_slope=s50, ma200_slope=s200,
        reason="no_directional_agreement",
    )
