"""
Price-action features — block 6 (10 features), pure candle geometry.

All outputs are scalar numbers; never None. When candles are missing or
short, returns schema defaults so downstream coerce_to_schema is idempotent.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _num(x: Any) -> Optional[float]:
    try:
        v = float(x)
        if v != v:  # NaN
            return None
        return v
    except (TypeError, ValueError):
        return None


def _ohlc(c: Any):
    if isinstance(c, dict):
        return _num(c.get("open")), _num(c.get("high")), _num(c.get("low")), _num(c.get("close"))
    return None, None, None, None


def compute_price_action(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return the 10 price-action features defined in feature_schema.

    All values are floats or ints in the schema's declared ranges.
    """
    defaults: Dict[str, Any] = {
        "range_pct_10": 0.0,
        "body_ratio_mean_5": 0.0,
        "upper_wick_ratio": 0.0,
        "lower_wick_ratio": 0.0,
        "close_pos_in_range": 0.5,
        "consecutive_up": 0,
        "consecutive_down": 0,
        "volatility_cluster_flag": 0,
        "gap_flag": 0,
        "inside_bar_streak": 0,
    }
    if not candles:
        return defaults

    parsed = [_ohlc(c) for c in candles]
    parsed = [p for p in parsed if None not in p]
    if len(parsed) < 2:
        return defaults

    last_o, last_h, last_l, last_c = parsed[-1]

    # range_pct_10: mean (high-low)/close over last 10 bars
    window10 = parsed[-10:]
    vals = [(h - lo) / c for (_, h, lo, c) in window10 if c > 0]
    range_pct_10 = float(sum(vals) / len(vals)) if vals else 0.0

    # body_ratio_mean_5: mean |close-open|/(high-low) last 5
    window5 = parsed[-5:]
    body_ratios = []
    for (o, h, lo, c) in window5:
        rng = h - lo
        if rng > 0:
            body_ratios.append(abs(c - o) / rng)
    body_ratio_mean_5 = float(sum(body_ratios) / len(body_ratios)) if body_ratios else 0.0

    # wick ratios: last 5 mean
    up_wicks, dn_wicks = [], []
    for (o, h, lo, c) in window5:
        rng = h - lo
        if rng > 0:
            up_wicks.append((h - max(o, c)) / rng)
            dn_wicks.append((min(o, c) - lo) / rng)
    upper_wick_ratio = float(sum(up_wicks) / len(up_wicks)) if up_wicks else 0.0
    lower_wick_ratio = float(sum(dn_wicks) / len(dn_wicks)) if dn_wicks else 0.0

    # close_pos_in_range: last bar
    rng_last = last_h - last_l
    close_pos_in_range = float((last_c - last_l) / rng_last) if rng_last > 0 else 0.5

    # consecutive up/down over the last 10 closes
    consecutive_up = 0
    consecutive_down = 0
    for i in range(len(parsed) - 1, 0, -1):
        c_curr = parsed[i][3]
        c_prev = parsed[i - 1][3]
        if c_curr > c_prev and consecutive_down == 0:
            consecutive_up += 1
            if consecutive_up >= 20:
                break
        elif c_curr < c_prev and consecutive_up == 0:
            consecutive_down += 1
            if consecutive_down >= 20:
                break
        else:
            break

    # volatility clustering: std of last 10 returns vs std of prior 10 returns
    volatility_cluster_flag = 0
    if len(parsed) >= 21:
        closes = [c for (_, _, _, c) in parsed]
        rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1] > 0]
        if len(rets) >= 20:
            r1 = rets[-10:]
            r0 = rets[-20:-10]
            def _std(arr):
                m = sum(arr) / len(arr)
                return (sum((x - m) ** 2 for x in arr) / len(arr)) ** 0.5
            s1 = _std(r1)
            s0 = _std(r0)
            if s0 > 0 and s1 > s0 * 1.5:
                volatility_cluster_flag = 1

    # gap flag: |open_now - close_prev| > 0.003 * close_prev (approx 0.3% micro-gap)
    prev_o, prev_h, prev_l, prev_c = parsed[-2]
    gap_flag = 1 if prev_c > 0 and abs(last_o - prev_c) > 0.003 * prev_c else 0

    # inside-bar streak: current and each prior bar strictly inside the one before
    inside_bar_streak = 0
    for i in range(len(parsed) - 1, 0, -1):
        ci = parsed[i]
        cp = parsed[i - 1]
        if ci[1] < cp[1] and ci[2] > cp[2]:
            inside_bar_streak += 1
            if inside_bar_streak >= 20:
                break
        else:
            break

    return {
        "range_pct_10": range_pct_10,
        "body_ratio_mean_5": body_ratio_mean_5,
        "upper_wick_ratio": upper_wick_ratio,
        "lower_wick_ratio": lower_wick_ratio,
        "close_pos_in_range": close_pos_in_range,
        "consecutive_up": consecutive_up,
        "consecutive_down": consecutive_down,
        "volatility_cluster_flag": int(volatility_cluster_flag),
        "gap_flag": int(gap_flag),
        "inside_bar_streak": int(inside_bar_streak),
    }
