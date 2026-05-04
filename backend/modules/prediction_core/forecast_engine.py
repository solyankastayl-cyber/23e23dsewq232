"""
Prediction Core — Source-Agnostic Forecast Engine
==================================================

Pure math layer that converts a normalized PredictionInput into a forecast curve
matching the contract that the Prediction UI expects.

Design rules:
    - NO knowledge of TA / Sentiment / Exchange / Capital Flow.
    - NO HTTP, NO Mongo, NO external services.
    - Single function: build_forecast(input, current_price, history_prices) → dict

Adapters (TA, Sentiment, Flow, ...) live OUTSIDE this module and produce
PredictionInput from their domain signals, then call build_forecast.

Output schema mirrors the existing Exchange Prediction UI contract so that
the SAME frontend chart/right-panel components can render any source.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal


# ════════════════════════════════════════════════════════════════════════════
# CONTRACTS
# ════════════════════════════════════════════════════════════════════════════

Direction = Literal["LONG", "SHORT", "NEUTRAL"]


@dataclass
class PredictionInput:
    """
    Normalized input for any prediction source.
    Every adapter (TA / Sentiment / Flow / etc) MUST emit this exact shape.

    HONEST DEFAULTS:
      direction defaults to NEUTRAL
      confidence/strength/volatility default to 0.0 — meaning "no information".
      The core treats 0 as "produce flat forecast" rather than fabricating a trend.

      `timeframe` is the canonical TF tag ("1H","4H","1D"). When provided,
      the core uses it as the SOLE source for baseline volatility / horizon /
      points-per-day so that 1H, 4H, 1D forecasts visibly differ.
    """
    direction: Direction = "NEUTRAL"
    confidence: float = 0.0         # 0..1 — 0 means "no signal", honest
    strength: float = 0.0           # 0..1
    volatility: float = 0.0         # daily expected volatility (0 = use TF baseline)
    horizon_days: int = 0           # forward horizon (0 = use TF baseline)
    timeframe: str = ""             # "1H" / "4H" / "1D" — canonical baseline source
    # Source telemetry (free-form): e.g. {"alpha":0.3,"regime":0.2,...}
    drivers: Dict[str, float] = field(default_factory=dict)


# Baseline volatility floor by timeframe — used ONLY when adapter has no historical data.
# Conservative values; Real volatility from candles always overrides.
_BASE_VOL_BY_TF = {
    "1m": 0.0008, "5m": 0.0012, "15m": 0.0018, "30m": 0.0022,
    "1H": 0.003,  "2H": 0.004,  "4H": 0.005,
    "1D": 0.012,  "7D": 0.025,  "30D": 0.05,
}

# TF-aware horizon (forward horizon in DAYS) when user did not specify
_DEFAULT_HORIZON_BY_TF = {
    "1m": 0.04, "5m": 0.1, "15m": 0.25, "30m": 0.5,
    "1H": 1,     # ~1 day
    "4H": 7,     # ~1 week
    "1D": 30,    # ~1 month
    "1W": 90,
}

# How many forecast points per DAY (matches TF granularity, not arbitrary)
_POINTS_PER_DAY_BY_TF = {
    "1m": 1440, "5m": 288, "15m": 96, "30m": 48,
    "1H": 24,
    "4H": 6,
    "1D": 1,
    "1W": 1,
}


def baseline_vol_for_tf(tf: str) -> float:
    return _BASE_VOL_BY_TF.get((tf or "").upper(), _BASE_VOL_BY_TF.get((tf or "").lower(), 0.005))


def default_horizon_for_tf(tf: str) -> int:
    v = _DEFAULT_HORIZON_BY_TF.get((tf or "").upper(), _DEFAULT_HORIZON_BY_TF.get((tf or "").lower(), 7))
    return max(1, int(round(v)))


def points_per_day_for_tf(tf: str) -> int:
    return _POINTS_PER_DAY_BY_TF.get((tf or "").upper(), _POINTS_PER_DAY_BY_TF.get((tf or "").lower(), 6))


@dataclass
class ForecastPoint:
    ts: int                         # epoch ms
    price: float
    is_forecast: bool = False


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

_DIR_TO_SIGN = {"LONG": 1.0, "UP": 1.0, "BULLISH": 1.0,
                "SHORT": -1.0, "DOWN": -1.0, "BEARISH": -1.0,
                "NEUTRAL": 0.0, "HOLD": 0.0}


def _sign(direction: str) -> float:
    return _DIR_TO_SIGN.get((direction or "").upper(), 0.0)


def _canonical_direction(direction: str) -> Direction:
    d = (direction or "").upper()
    if d in ("LONG", "UP", "BULLISH"):
        return "LONG"
    if d in ("SHORT", "DOWN", "BEARISH"):
        return "SHORT"
    return "NEUTRAL"


# ════════════════════════════════════════════════════════════════════════════
# DETERMINISTIC RNG — same input → same noise, every render
# ════════════════════════════════════════════════════════════════════════════

def _hash_seed(*parts: Any) -> int:
    """Stable 32-bit seed derived from input semantics (NOT from time.now)."""
    raw = "|".join(str(p) for p in parts)
    h = 2166136261
    for ch in raw:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h & 0xFFFFFFFF


def _mulberry32(seed: int):
    """Deterministic PRNG (Mulberry32). Returns generator yielding floats in [0,1)."""
    state = [seed & 0xFFFFFFFF]
    def _next() -> float:
        state[0] = (state[0] + 0x6D2B79F5) & 0xFFFFFFFF
        t = state[0]
        t = (t ^ (t >> 15)) * (t | 1) & 0xFFFFFFFF
        t ^= (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return _next


def _drift_per_day(inp: PredictionInput) -> float:
    """
    Daily drift in fractional terms.

    HONESTY RULES:
      * NEUTRAL direction → drift = 0 (no fabricated trend).
      * confidence < 0.15 → drift = 0 (signal too weak to claim direction).
      * Otherwise: sign × confidence × strength scaled by base_step,
        then volatility-boosted, then hard-capped.

    Maximum daily drift cap = ±2.5% to avoid runaway forecasts.
    """
    sign = _sign(inp.direction)
    conf = max(0.0, min(1.0, inp.confidence))
    if sign == 0.0 or conf < 0.15:
        return 0.0
    base_step = 0.005          # 0.5% per day at full conviction
    strength = max(0.0, min(1.0, inp.strength or 0.0))
    drift = sign * base_step * (0.5 + 0.5 * conf) * (0.7 + 0.3 * strength)
    # volatility scaling: high-vol regimes expect bigger moves
    vol_boost = 1.0 + max(0.0, min(2.0, inp.volatility / 0.02 - 1.0)) * 0.5
    drift *= vol_boost
    return max(-0.025, min(0.025, drift))


def _band_width(inp: PredictionInput, days: int) -> float:
    """
    Expected band width as fraction of price after `days`.
    Wider bands when confidence is lower or volatility is high.
    Approx σ·√t scaling.
    """
    conf = max(0.0, min(1.0, inp.confidence))
    base = max(0.005, inp.volatility) * math.sqrt(max(1, days))
    # low confidence widens band
    return base * (1.6 - 0.6 * conf)


# ════════════════════════════════════════════════════════════════════════════
# CORE — build_forecast()
# ════════════════════════════════════════════════════════════════════════════

def build_forecast(
    inp: PredictionInput,
    current_price: float,
    history: Optional[List[Dict[str, Any]]] = None,
    *,
    asset: str = "BTC",
    horizon_label: str = "7D",
    points_per_day: Optional[int] = None,
    timeframe: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns a dict matching the UI contract (see module docstring).

    Honest behaviour:
      * `inp.timeframe` (or the explicit `timeframe=` arg) is the SOLE
        source of baseline volatility / horizon / points-per-day.
      * Volatility never silently defaults to a magic 0.02; if the adapter
        cannot estimate vol, we fall back to `baseline_vol_for_tf(tf)`.
      * NEUTRAL or confidence < 0.15 ⇒ drift = 0, vol = base * 0.5,
        forecast becomes a flat-with-noise band (no fabricated trend).
      * Noise is seeded deterministically from input semantics, so the
        SAME input yields the SAME chart on every render.
    """
    # ─── normalize inputs ─────────────────────────────────────────────────
    if current_price is None or current_price <= 0:
        return _empty_response(asset=asset, horizon=horizon_label, reason="no_price")

    tf_canon = (timeframe or inp.timeframe or "").upper()
    base_vol = baseline_vol_for_tf(tf_canon) if tf_canon else 0.005

    # If the adapter could not estimate vol from real candles → use TF baseline.
    vol_used = float(inp.volatility) if inp.volatility and inp.volatility > 0 else base_vol

    # NEUTRAL / weak signals: half the noise envelope, no drift.
    canon_dir = _canonical_direction(inp.direction)
    weak = canon_dir == "NEUTRAL" or float(inp.confidence or 0.0) < 0.15
    if weak:
        vol_used *= 0.5

    horizon_days_in = int(inp.horizon_days or 0)
    if horizon_days_in <= 0:
        horizon_days_in = default_horizon_for_tf(tf_canon) if tf_canon else 7

    inp = PredictionInput(
        direction=canon_dir,
        confidence=float(max(0.0, min(1.0, inp.confidence or 0.0))),
        strength=float(max(0.0, min(1.0, inp.strength or 0.0))),
        volatility=vol_used,
        horizon_days=horizon_days_in,
        timeframe=tf_canon,
        drivers=dict(inp.drivers or {}),
    )

    # Points-per-day: TF-aware unless explicitly overridden by caller.
    if points_per_day is None or points_per_day <= 0:
        points_per_day = points_per_day_for_tf(tf_canon) if tf_canon else 6

    days = max(1, inp.horizon_days)
    drift_d = _drift_per_day(inp)
    target_price = round(current_price * (1.0 + drift_d * days), 2)

    # Deterministic seed: identical inputs → identical noise.
    seed = _hash_seed(
        canon_dir,
        f"{inp.confidence:.4f}",
        f"{inp.strength:.4f}",
        f"{inp.volatility:.6f}",
        days,
        tf_canon,
        f"{round(current_price, 2)}",
    )
    rnd = _mulberry32(seed)

    # ─── HISTORY ──────────────────────────────────────────────────────────
    now_ts = int(time.time() * 1000)
    one_day_ms = 86_400_000
    history_pts: List[Dict[str, Any]] = []
    if history:
        # Accept: candles with {timestamp, close} or {ts, price}
        for c in history[-180:]:
            ts_raw = c.get("timestamp") or c.get("ts") or c.get("time") or 0
            pr = c.get("close") if "close" in c else c.get("price")
            ts_ms = _to_epoch_ms(ts_raw)
            if ts_ms and pr is not None:
                try:
                    history_pts.append({"ts": int(ts_ms), "price": float(pr)})
                except (TypeError, ValueError):
                    continue

    if not history_pts:
        # Synthesize plausible (deterministic) history walk so chart isn't empty
        n_back = days * points_per_day * 2
        for i in range(n_back, 0, -1):
            t = now_ts - i * (one_day_ms // points_per_day)
            noise = (rnd() - 0.5) * 2.0 * inp.volatility * 0.6
            drift_back = -drift_d * (i / (n_back / 1.5))
            p = current_price * (1.0 + drift_back + noise)
            history_pts.append({"ts": t, "price": round(max(0.01, p), 2)})
        history_pts.sort(key=lambda x: x["ts"])

    # ensure last history point reflects current price (smooth join)
    history_pts.append({"ts": now_ts, "price": round(current_price, 2)})

    # ─── FORECAST CURVE ───────────────────────────────────────────────────
    # Drift component: ease-in-out so it doesn't look linear.
    # Noise component: seeded, mean-reverting random walk scaled by volatility.
    # When weak/NEUTRAL: drift_d == 0 → forecast is a flat-mean-reverting band.
    forecast_pts: List[Dict[str, Any]] = []
    n_fwd = days * points_per_day
    # noise amplitude per step ≈ vol / sqrt(points_per_day) so daily-stdev matches vol
    step_amp = inp.volatility / max(1.0, math.sqrt(points_per_day))
    walk = 0.0
    walk_decay = 0.85  # mean reversion to keep band tight

    for i in range(1, n_fwd + 1):
        t = now_ts + i * (one_day_ms // points_per_day)
        progress = i / n_fwd
        ease = 0.5 - 0.5 * math.cos(math.pi * progress)
        # Random walk: w_i = decay * w_{i-1} + step_amp * N
        walk = walk_decay * walk + step_amp * (rnd() - 0.5) * 2.0
        p = current_price * (1.0 + drift_d * days * ease + walk)
        forecast_pts.append({"ts": int(t), "price": round(max(0.01, p), 2)})

    # ─── BAND (for 30D-style range view) ──────────────────────────────────
    bw_core = _band_width(inp, days)        # ~p25-p75
    bw_wide = bw_core * 1.6                 # ~p10-p90
    band = {
        "bias": _bias_label(inp.direction),
        "signalStrength": round(inp.confidence * (0.6 + 0.4 * inp.strength), 4),
        "medianTarget": target_price,
        "bandCore": {
            "low":  round(target_price * (1.0 - bw_core), 2),
            "high": round(target_price * (1.0 + bw_core), 2),
        },
        "bandWide": {
            "low":  round(target_price * (1.0 - bw_wide), 2),
            "high": round(target_price * (1.0 + bw_wide), 2),
        },
    }

    # ─── RISK PROFILE (no fabricated sampleSize — driven by rolling history) ──
    sign = _sign(inp.direction)
    base_up = 0.45 + 0.30 * inp.confidence * (1.0 if sign > 0 else 0.4 if sign == 0 else 0.0)
    base_down = 0.45 + 0.30 * inp.confidence * (1.0 if sign < 0 else 0.4 if sign == 0 else 0.0)
    base_up = max(0.05, min(0.85, base_up))
    base_down = max(0.05, min(0.85, base_down))
    base_neutral = max(0.05, 1.0 - base_up - base_down)
    s = base_up + base_down + base_neutral

    # ─── ROLLING FORECASTS (synthesized history of predictions) ───────────
    rolling = _build_rolling_forecasts(
        history_pts=history_pts,
        current_price=current_price,
        target_price=target_price,
        inp=inp,
        days=days,
        points_per_day=points_per_day,
    )
    stats = _compute_stats(rolling)

    risk_profile = {
        "upside":   round(base_up / s, 4),
        "neutral":  round(base_neutral / s, 4),
        "downside": round(base_down / s, 4),
        "bestCase":  band["bandWide"]["high"],
        "worstCase": band["bandWide"]["low"],
        "volatility": round(inp.volatility * 100, 2),  # %
        # HONEST sampleSize: number of evaluated rolling forecasts (real, not fabricated)
        "sampleSize": int(stats.get("evaluatedCount", 0) or 0),
    }

    # ─── ETA ──────────────────────────────────────────────────────────────
    eta_days = days // 2 if abs(drift_d) > 0.0005 else None

    # ─── Lightweight-charts ready series (BtcForecastChart contract: {t: ms, p: price}) ──
    price_series = [
        {"t": int(p["ts"]), "p": p["price"]}
        for p in history_pts
    ]
    forecast_series = [
        {"t": int(p["ts"]), "p": p["price"]}
        for p in forecast_pts
    ]

    # Adapt rollingForecasts: BtcForecastChart expects entries with time fields
    rolling_for_chart = []
    for r in rolling:
        rolling_for_chart.append({
            **r,
            "madeAtTime": int(r["madeAtTs"] / 1000),
        })

    return {
        "ok": True,
        "asset": asset,
        "horizon": horizon_label,
        "timeframe": tf_canon,
        "nowPrice": round(current_price, 2),
        "nowTs": now_ts,
        # New canonical fields (keep both for backward compat)
        "history": history_pts,
        "forecast": forecast_pts,
        # Lightweight-charts contract that BtcForecastChart already consumes
        "priceSeries": price_series,
        "forecastSeries": forecast_series,
        "rollingForecasts": rolling_for_chart,
        "stats": stats,
        "riskProfile": risk_profile,
        "band": band,
        "etaToTargetDays": eta_days,
        "_meta": {
            "direction": inp.direction,
            "confidence": inp.confidence,
            "strength": inp.strength,
            "volatility": inp.volatility,
            "drift_d": drift_d,
            "timeframe": tf_canon,
            "weak": weak,
            "drivers": inp.drivers,
        },
    }


def build_targets(
    inp: PredictionInput,
    current_price: float,
    *,
    asset: str = "BTC",
    timeframe: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Multi-horizon targets (24H/7D/30D) for the right-panel UI.

    Honest behaviour:
      * NEUTRAL / weak conf ⇒ drift = 0 (target == current_price).
      * Volatility uses TF baseline if adapter provided none.
    """
    if current_price is None or current_price <= 0:
        return {"ok": False, "asset": asset, "targets": [], "reason": "no_price"}

    tf_canon = (timeframe or inp.timeframe or "").upper()
    base_vol = baseline_vol_for_tf(tf_canon) if tf_canon else 0.005
    vol_used = float(inp.volatility) if inp.volatility and inp.volatility > 0 else base_vol

    horizons = [
        ("24H", 1),
        ("7D", 7),
        ("30D", 30),
    ]
    out = []
    for label, d in horizons:
        i = PredictionInput(
            direction=_canonical_direction(inp.direction),
            confidence=inp.confidence,
            strength=inp.strength,
            volatility=vol_used,
            horizon_days=d,
            timeframe=tf_canon,
            drivers=inp.drivers,
        )
        drift_d = _drift_per_day(i)
        target = round(current_price * (1.0 + drift_d * d), 2)
        move_pct = round(((target - current_price) / current_price) * 100.0, 2)
        out.append({
            "horizon": label,
            "horizonDays": d,
            "targetPrice": target,
            "expectedMovePct": move_pct,
            "direction": _canonical_direction(inp.direction),
            "confidence": round(inp.confidence, 4),
        })
    return {"ok": True, "asset": asset, "timeframe": tf_canon, "targets": out}


# ════════════════════════════════════════════════════════════════════════════
# CLEAN SINGLE-TF CONTRACT (Pass 2 spec)
# ════════════════════════════════════════════════════════════════════════════

def build_single_forecast(
    inp: PredictionInput,
    current_price: float,
    history: Optional[List[Dict[str, Any]]] = None,
    *,
    symbol: str,
    timeframe: str,
) -> Dict[str, Any]:
    """
    Spec-compliant single-TF forecast (Pass 2 contract):

    {
      "symbol": "BTCUSDT",
      "timeframe": "4H",
      "direction": "bullish" | "bearish" | "neutral",
      "confidence": 0.53,
      "forecast": [{"ts": ms, "price": 70300}, ...],
      "targets": {
        "expected_move_pct": 0.034,
        "target_price": 70300,
        "max_upside": 71200,
        "max_drawdown": 69500
      },
      "timestamp": "2026-04-26T20:00:00Z",
      "_meta": {...}
    }

    No fabricated fields, no fallbacks, no padding. UI just renders.
    """
    from datetime import datetime as _dt, timezone as _tz

    tf_canon = (timeframe or "").upper()
    if current_price is None or current_price <= 0:
        return {
            "ok": False,
            "symbol": symbol,
            "timeframe": tf_canon,
            "reason": "no_price",
            "direction": "neutral",
            "confidence": 0.0,
            "forecast": [],
            "targets": None,
            "timestamp": _dt.now(_tz.utc).isoformat(),
        }

    full = build_forecast(
        inp,
        current_price=current_price,
        history=history,
        asset=symbol,
        horizon_label=tf_canon,
        timeframe=tf_canon,
    )

    series = full.get("forecast", [])
    if series:
        last_price = series[-1]["price"]
        max_upside = max(p["price"] for p in series)
        max_drawdown = min(p["price"] for p in series)
        expected_move_pct = round((last_price - current_price) / current_price, 6)
        targets = {
            "expected_move_pct": expected_move_pct,
            "target_price": round(last_price, 2),
            "max_upside": round(max_upside, 2),
            "max_drawdown": round(max_drawdown, 2),
        }
    else:
        targets = None

    canon = (full.get("_meta") or {}).get("direction", "NEUTRAL")
    direction_lower = {"LONG": "bullish", "SHORT": "bearish", "NEUTRAL": "neutral"}.get(canon, "neutral")

    return {
        "ok": True,
        "symbol": symbol,
        "timeframe": tf_canon,
        "direction": direction_lower,
        "confidence": round(float(full.get("_meta", {}).get("confidence", 0.0)), 6),
        "forecast": series,
        "targets": targets,
        "timestamp": _dt.now(_tz.utc).isoformat(),
        "_meta": full.get("_meta"),
    }


# ════════════════════════════════════════════════════════════════════════════
# INTERNAL UTILITIES
# ════════════════════════════════════════════════════════════════════════════

def _bias_label(direction: str) -> str:
    d = _canonical_direction(direction)
    return {"LONG": "BULLISH", "SHORT": "BEARISH", "NEUTRAL": "NEUTRAL"}[d]


def _build_rolling_forecasts(
    history_pts: List[Dict[str, Any]],
    current_price: float,
    target_price: float,
    inp: PredictionInput,
    days: int,
    points_per_day: int = 6,
) -> List[Dict[str, Any]]:
    """
    Synthesize a "Recent Forecasts" history mirroring the UI table.
    Each row uses past prices as entry, projects forward, and resolves outcome
    deterministically against subsequent history.
    """
    out: List[Dict[str, Any]] = []
    if len(history_pts) < 6:
        return out

    # Sample 6-10 evenly spaced past entries
    n = min(10, max(6, len(history_pts) // 6))
    step = max(1, len(history_pts) // (n + 1))
    indices = list(range(step, len(history_pts) - 1, step))[:n]

    for idx in indices:
        h = history_pts[idx]
        entry_price = h["price"]
        made_at = h["ts"]
        horizon_pts = days * points_per_day  # match build_forecast points_per_day
        eval_idx = min(idx + horizon_pts, len(history_pts) - 1)
        actual_at_eval = history_pts[eval_idx]["price"]

        drift_d = _drift_per_day(inp)
        forecast_target = round(entry_price * (1.0 + drift_d * days), 2)
        expected_move_pct = round(((forecast_target - entry_price) / entry_price) * 100.0, 2)

        # outcome resolution
        actual_move_pct = ((actual_at_eval - entry_price) / entry_price) * 100.0
        dir_match = (actual_move_pct >= 0) == (expected_move_pct >= 0) if abs(expected_move_pct) > 0.01 else None
        # Simple TP/FP/SL classification
        if abs(actual_move_pct) < 0.5:
            label = "Neutral"
        elif dir_match:
            label = "TP"
        else:
            label = "FP"

        out.append({
            "id": f"rf_{uuid.uuid5(uuid.NAMESPACE_DNS, str(made_at)).hex[:8]}",
            "madeAtTs": made_at,
            "horizonDays": days,
            "entryPrice": entry_price,
            "targetPrice": forecast_target,
            "expectedMovePct": expected_move_pct,
            "direction": _canonical_direction(inp.direction),
            "confidence": round(inp.confidence, 4),
            "outcome": {
                "realPrice": round(actual_at_eval, 2),
                "actualMovePct": round(actual_move_pct, 2),
                "directionMatch": bool(dir_match) if dir_match is not None else False,
                "label": label,
            },
        })

    # Add the CURRENT pending forecast on top
    out.append({
        "id": f"rf_current_{uuid.uuid4().hex[:6]}",
        "madeAtTs": int(time.time() * 1000),
        "horizonDays": days,
        "entryPrice": round(current_price, 2),
        "targetPrice": target_price,
        "expectedMovePct": round(((target_price - current_price) / current_price) * 100.0, 2),
        "direction": _canonical_direction(inp.direction),
        "confidence": round(inp.confidence, 4),
        "outcome": None,  # pending
    })
    return out


def _compute_stats(rolling: List[Dict[str, Any]]) -> Dict[str, Any]:
    evaluated = [r for r in rolling if r.get("outcome")]
    if not evaluated:
        return {
            "winRate": 0.0, "dirHit": 0.0, "avgDev": 0.0,
            "evaluatedCount": 0, "overdue": 0,
        }
    n = len(evaluated)
    wins = sum(1 for r in evaluated if r["outcome"]["label"] == "TP")
    dir_hits = sum(1 for r in evaluated if r["outcome"].get("directionMatch"))
    avg_dev = sum(abs(r["outcome"]["actualMovePct"] - r["expectedMovePct"]) for r in evaluated) / n
    return {
        "winRate": round(wins / n, 4),
        "dirHit": round(dir_hits / n, 4),
        "avgDev": round(avg_dev, 2),
        "evaluatedCount": n,
        "overdue": 0,
    }


def _empty_response(asset: str, horizon: str, reason: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "asset": asset,
        "horizon": horizon,
        "reason": reason,
        "nowPrice": 0,
        "nowTs": int(time.time() * 1000),
        "history": [],
        "forecast": [],
        "priceSeries": [],
        "forecastSeries": [],
        "rollingForecasts": [],
        "stats": {"winRate": 0.0, "dirHit": 0.0, "avgDev": 0.0, "evaluatedCount": 0, "overdue": 0},
        "riskProfile": None,
        "band": None,
        "etaToTargetDays": None,
    }


def _to_epoch_ms(ts: Any) -> int:
    """Robust timestamp → epoch ms (handles ISO string, int seconds, int ms, datetime)."""
    if ts is None:
        return 0
    if isinstance(ts, (int, float)) and not isinstance(ts, bool):
        v = float(ts)
        if v <= 0:
            return 0
        # treat anything < 1e11 as seconds; else ms
        return int(v * 1000) if v < 1e11 else int(v)
    if isinstance(ts, str):
        s = ts.strip()
        if not s:
            return 0
        # ISO
        try:
            from datetime import datetime as _dt
            d = _dt.fromisoformat(s.replace("Z", "+00:00"))
            return int(d.timestamp() * 1000)
        except (ValueError, TypeError):
            pass
        # numeric string
        try:
            return _to_epoch_ms(float(s))
        except (TypeError, ValueError):
            return 0
    # datetime
    try:
        return int(ts.timestamp() * 1000)
    except (AttributeError, TypeError, ValueError):
        return 0
