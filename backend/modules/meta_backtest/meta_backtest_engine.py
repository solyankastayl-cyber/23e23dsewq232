"""
Meta Backtest Engine (Pass 4.1)
================================

Tests whether the META decision math actually has edge — NOT TA, NOT hypothesis.

  candles → [for each i ≥ warmup]
              ├─ ta = build_ta_state(candles[:i+1])    (fast, no lookahead)
              ├─ prediction = build_single_forecast(...) (uses prediction_core)
              ├─ combined = build_combined(ta, prediction, hypothesis=None)
              ├─ meta = build_meta_decision(combined, {"status": "HEALTHY"})
              └─ if meta["should_trade"]:
                     pnl_t = (close[i+1] - close[i]) / close[i] × dir_sign
                     equity *= (1 + pnl_t × allocation)

Honest constraints:
  * NO lookahead — only candles[:i+1] used at step i.
  * Hypothesis intentionally None — we test Meta in isolation.
  * Simple PnL (1-bar forward, no stops) — first we prove the SIGNAL.
  * Per-score-bucket aggregation surfaces correlation: score↑ → pnl↑.

Output:
  {
    "trades": int, "win_rate": float, "profit_factor": float,
    "expectancy": float, "equity": float,
    "score_buckets": [{"range":"0.5-0.7","trades":n,"win_rate":..,"avg_pnl":..}],
    "by_direction": {"bullish": {...}, "bearish": {...}},
    ...
  }
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from modules.analysis.combined_analysis_service import build_combined
from modules.meta.meta_scoring_engine import build_meta_decision
from modules.prediction_core import (
    PredictionInput,
    build_single_forecast,
    baseline_vol_for_tf,
)


# ════════════════════════════════════════════════════════════════════════════
# 1. LIGHTWEIGHT TA STATE (pure-function, no lookahead)
# ════════════════════════════════════════════════════════════════════════════

def _ema(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    k = 2.0 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema


def _rsi(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains.append(max(0.0, delta))
        losses.append(max(0.0, -delta))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(0.0, delta)
        loss = max(0.0, -delta)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _atr_pct(candles: List[Dict[str, float]], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h = float(candles[i]["high"])
        l = float(candles[i]["low"])
        cp = float(candles[i - 1]["close"])
        tr = max(h - l, abs(h - cp), abs(l - cp))
        trs.append(tr)
    atr = sum(trs[-period:]) / period
    last = float(candles[-1]["close"])
    return atr / last if last else 0.0


def build_ta_state(candles: List[Dict[str, float]]) -> Optional[Dict[str, Any]]:
    """
    Lightweight TA bias from a candle slice. Honest defaults:
      * insufficient data → None
      * no clear direction → neutral with confidence=0
    """
    if not candles or len(candles) < 60:
        return None

    closes = [float(c["close"]) for c in candles]
    last = closes[-1]

    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    rsi = _rsi(closes, 14)
    atr_p = _atr_pct(candles, 14)

    if ema20 is None or ema50 is None:
        return None

    # Direction: trend filter (price vs EMA20 + EMA20 vs EMA50)
    above_ema20 = last > ema20
    above_ema50 = last > ema50
    ema_up = ema20 > ema50

    if above_ema20 and above_ema50 and ema_up:
        direction = "bullish"
    elif (not above_ema20) and (not above_ema50) and (not ema_up):
        direction = "bearish"
    else:
        direction = "neutral"

    # Confidence: EMA spread (relative) + RSI agreement, all in 0..1
    if direction == "neutral":
        confidence = 0.0
    else:
        spread = abs(ema20 - ema50) / max(1e-9, last)
        spread_score = min(1.0, spread / max(1e-6, atr_p * 1.5))  # 1 ATR spread → 0.67
        rsi_score = 0.0
        if rsi is not None:
            if direction == "bullish":
                rsi_score = max(0.0, min(1.0, (rsi - 50.0) / 30.0))   # 50→0, 80→1
            else:
                rsi_score = max(0.0, min(1.0, (50.0 - rsi) / 30.0))
        confidence = max(0.0, min(1.0, 0.4 * spread_score + 0.6 * rsi_score))

    summary = (
        f"EMA20{'>' if ema_up else '<'}EMA50, "
        f"price{'>' if above_ema20 else '<'}EMA20, "
        f"RSI14={rsi:.1f}" if rsi is not None else f"EMA20{'>' if ema_up else '<'}EMA50"
    )

    return {
        "direction": direction,
        "confidence": round(confidence, 4),
        "strength": "strong" if confidence > 0.7 else "moderate" if confidence > 0.4 else "weak",
        "summary": summary,
        "_internals": {"ema20": ema20, "ema50": ema50, "rsi": rsi, "atr_pct": atr_p},
    }


# ════════════════════════════════════════════════════════════════════════════
# 2. PREDICTION (uses shared prediction_core, no lookahead)
# ════════════════════════════════════════════════════════════════════════════

def build_prediction_block(
    candles: List[Dict[str, float]],
    timeframe: str,
    ta_state: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not candles or not ta_state:
        return None

    current_price = float(candles[-1]["close"])
    if current_price <= 0:
        return None

    # Volatility from real returns (last ~30 closes)
    vol = 0.0
    closes = [float(c["close"]) for c in candles[-31:]]
    if len(closes) >= 5:
        rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1]]
        if rets:
            mean = sum(rets) / len(rets)
            var = sum((r - mean) ** 2 for r in rets) / max(1, len(rets) - 1)
            vol = max(0.0, min(0.15, var ** 0.5))

    canon_dir = {"bullish": "LONG", "bearish": "SHORT"}.get(ta_state["direction"], "NEUTRAL")

    inp = PredictionInput(
        direction=canon_dir,
        confidence=float(ta_state["confidence"]),
        strength=float(ta_state["confidence"]),  # use same as a clean proxy
        volatility=vol,
        horizon_days=0,
        timeframe=timeframe.upper(),
    )
    res = build_single_forecast(
        inp,
        current_price=current_price,
        history=candles,
        symbol="BTCUSDT",
        timeframe=timeframe.upper(),
    )
    if not res or not res.get("ok"):
        return None
    targets = res.get("targets") or {}
    return {
        "direction": res.get("direction"),
        "confidence": float(res.get("confidence") or 0.0),
        "expected_move_pct": targets.get("expected_move_pct"),
        "target_price": targets.get("target_price"),
    }


# ════════════════════════════════════════════════════════════════════════════
# 3. SIMULATION
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class _Trade:
    i: int
    direction: str
    score: float
    allocation: float
    pnl: float
    quality: str


def _direction_sign(d: str) -> int:
    return 1 if d == "bullish" else -1 if d == "bearish" else 0


def _allocation_for_mode(score: float, base_alloc: float, mode: str) -> float:
    """
    Map (strategy_score, base_allocation) → effective_allocation under a chosen mode.

    Modes:
      "A"             — baseline:  use base_alloc as-is (current Meta).
      "inverted"      — anti-confidence (Pass 4.1 quick test).
      "calibrated"    — per-bucket override (Pass 4.1 quick test).
      "regime_aware"  — Pass 4.2: classify regime from score, allocation by regime.

    Note: regime_aware uses (score → uncertain/balanced/overheated), and the
    direction-flip logic for overheated is applied at the trade-loop level
    (see run_meta_backtest), since allocation alone cannot flip direction.
    """
    s = max(0.0, min(1.0, float(score)))
    m = (mode or "A").lower()
    if m in ("a", "baseline", ""):
        return base_alloc
    if m == "inverted":
        if s < 0.30:   return 0.0
        if s < 0.50:   return 0.50
        if s < 0.70:   return 0.25
        if s < 0.85:   return 0.10
        return 0.0
    if m == "calibrated":
        if 0.30 <= s < 0.50:   return 0.50
        if 0.50 <= s < 0.70:   return 0.10
        if s >= 0.70:          return 0.0
        return 0.10
    if m == "regime_aware":
        # Pass 4.2 — allocation per regime (direction flip handled in main loop).
        # 4.2.1 finding from backtest: balanced regime is TOXIC (PF<0.1 on 4H)
        #   → cut to 0 allocation. uncertain is the main edge zone.
        regime = classify_regime(s)
        if regime == "uncertain":   return 0.50    # ← main edge zone
        if regime == "balanced":    return 0.0     # ← TOXIC, skip
        if regime == "overheated":  return 0.30    # FADE the trend (direction flips below)
        return 0.0
    return base_alloc


def classify_regime(score: float) -> str:
    """
    Pass 4.2 — turn strategy_score into a market regime label.

      score < 0.50    → "uncertain"  (noisy / undecided)
      0.50–0.70       → "balanced"   (mid-conviction; least edge in our backtest)
      ≥ 0.70          → "overheated" (system "too sure" — fade the trend)
    """
    s = max(0.0, min(1.0, float(score)))
    if s < 0.50:
        return "uncertain"
    if s < 0.70:
        return "balanced"
    return "overheated"


def _direction_for_regime(ta_direction: str, regime: str) -> str:
    """
    Pass 4.2 step 2 — direction selection by regime.

      uncertain   → follow TA (we have no other info)
      balanced    → follow TA (low conviction zone, just halve allocation)
      overheated  → FADE the trend (reverse TA direction)
    """
    if regime == "overheated":
        if ta_direction == "bullish":
            return "bearish"
        if ta_direction == "bearish":
            return "bullish"
        return "neutral"
    return ta_direction


# ════════════════════════════════════════════════════════════════════════════
# 4.2 — KILL SELF-REFERENCE + HYPOTHESIS BOOSTER (in combined assembly)
# ════════════════════════════════════════════════════════════════════════════

def _build_combined_for_backtest(
    symbol: str,
    timeframe: str,
    ta: Dict[str, Any],
    prediction: Dict[str, Any],
    hypothesis: Optional[Dict[str, Any]],
    *,
    self_reference_fix: bool = False,
) -> Dict[str, Any]:
    """
    Backtest-only build_combined wrapper.

    self_reference_fix: returns the unmodified combined. The penalty is
    applied at the META level (strategy_score *= 0.85) so quality tiers
    are preserved (we keep MEDIUM trades but with reduced effective score).
    See run_meta_backtest for the actual application point.
    """
    return build_combined(symbol, timeframe, ta, prediction, hypothesis)


_SELF_REFERENCE_PENALTY = 0.85   # honest 15% downgrade for self-derived prediction


def _apply_hypothesis_booster(
    score: float,
    hypothesis_pf: Optional[float],
) -> float:
    """
    Pass 4.2 step 4 — coarse booster from hypothesis empirical PF.

      PF > 2  → score × 1.20 (clamped to 1.0)
      PF < 1  → score × 0.80
      otherwise → unchanged
    """
    if hypothesis_pf is None:
        return score
    pf = float(hypothesis_pf)
    if pf > 2.0:
        return min(1.0, score * 1.20)
    if pf < 1.0:
        return score * 0.80
    return score


def run_meta_backtest(
    candles: List[Dict[str, float]],
    *,
    symbol: str = "BTCUSDT",
    timeframe: str = "4H",
    warmup: int = 100,
    health_status: str = "healthy",
    mode: str = "A",
    self_reference_fix: bool = False,
    hypothesis_pf: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Full Meta backtest with optional R&D toggles.

    NO LOOKAHEAD. mode controls allocation policy; regime_aware also flips
    direction in overheated regimes. self_reference_fix mutes prediction's
    direction when feeding agreement (honest decoupling). hypothesis_pf
    plugs a coarse historical booster (Pass 4.2 step 4).
    """
    if not candles or len(candles) <= warmup + 5:
        return {"ok": False, "reason": "not enough candles", "mode": mode}

    trades: List[_Trade] = []
    equity = 1.0
    skips = {"no_ta": 0, "no_pred": 0, "should_not_trade": 0, "alloc_zero_under_mode": 0}
    regime_counts = {"uncertain": 0, "balanced": 0, "overheated": 0}
    regime_pnl = {"uncertain": [], "balanced": [], "overheated": []}

    for i in range(warmup, len(candles) - 1):
        slice_ = candles[: i + 1]

        ta = build_ta_state(slice_)
        if not ta:
            skips["no_ta"] += 1
            continue

        prediction = build_prediction_block(slice_, timeframe, ta)
        if not prediction:
            skips["no_pred"] += 1
            continue

        # ─── COMBINED + META ───────────────────────────────────────────
        combined = build_combined(symbol, timeframe, ta, prediction, hypothesis=None)
        meta = build_meta_decision(combined, {"status": health_status})

        # ─── SELF-REFERENCE PENALTY (Pass 4.2 step 3) ──────────────────
        # We honestly admit prediction is TA-derived → downgrade score by 15%.
        raw_score = meta["strategy_score"]
        if self_reference_fix:
            raw_score = raw_score * _SELF_REFERENCE_PENALTY

        # ─── HYPOTHESIS BOOSTER (Pass 4.2 step 4) ──────────────────────
        boosted_score = _apply_hypothesis_booster(raw_score, hypothesis_pf)

        if not meta["should_trade"]:
            skips["should_not_trade"] += 1
            continue

        # ─── REGIME LABEL (for analytics + direction flip) ─────────────
        regime = classify_regime(boosted_score)
        regime_counts[regime] += 1

        # ─── ALLOCATION ────────────────────────────────────────────────
        eff_alloc = _allocation_for_mode(boosted_score, meta["allocation"], mode)
        if eff_alloc <= 0.0:
            skips["alloc_zero_under_mode"] += 1
            continue

        # ─── DIRECTION (regime-aware can flip) ─────────────────────────
        ta_dir = meta["final_bias"]
        if mode == "regime_aware":
            chosen_dir = _direction_for_regime(ta_dir, regime)
        else:
            chosen_dir = ta_dir

        sign = _direction_sign(chosen_dir)
        if sign == 0:
            continue

        # ─── PnL realisation ───────────────────────────────────────────
        entry = float(candles[i]["close"])
        exit_p = float(candles[i + 1]["close"])
        if entry <= 0:
            continue
        change = (exit_p - entry) / entry
        pnl = change * sign

        equity *= 1.0 + pnl * eff_alloc
        regime_pnl[regime].append(pnl)
        trades.append(_Trade(
            i=i,
            direction=chosen_dir,
            score=boosted_score,
            allocation=eff_alloc,
            pnl=pnl,
            quality=meta["quality"],
        ))

    out = _aggregate_stats(trades, equity, skips, len(candles), warmup)
    out["mode"] = mode
    out["self_reference_fix"] = self_reference_fix
    out["hypothesis_pf"] = hypothesis_pf

    # Regime breakdown — Pass 4.2 transparency
    regime_summary = {}
    for r, pnls in regime_pnl.items():
        if not pnls:
            regime_summary[r] = {"trades": 0}
            continue
        wins = [p for p in pnls if p > 0]
        regime_summary[r] = {
            "trades": len(pnls),
            "win_rate": round(len(wins) / len(pnls), 4),
            "avg_pnl": round(sum(pnls) / len(pnls), 6),
            "pf": _safe_pf(pnls),
        }
    out["regime_breakdown"] = regime_summary
    return out


# ════════════════════════════════════════════════════════════════════════════
# 4. METRICS
# ════════════════════════════════════════════════════════════════════════════

def _aggregate_stats(
    trades: List[_Trade], equity: float, skips: Dict[str, int],
    total_candles: int, warmup: int,
) -> Dict[str, Any]:
    n = len(trades)
    if n == 0:
        return {
            "ok": True,
            "trades": 0,
            "equity": round(equity, 4),
            "skips": skips,
            "candles_evaluated": total_candles - warmup - 1,
            "reason": "no signals fired",
        }

    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / n
    gross_p = sum(wins)
    gross_l = abs(sum(losses))
    pf = (gross_p / gross_l) if gross_l > 0 else float("inf")
    expectancy = sum(pnls) / n
    avg_alloc = sum(t.allocation for t in trades) / n

    # ─── Score buckets — correlation surface ───
    bucket_defs = [
        (0.30, 0.50, "0.30-0.50"),
        (0.50, 0.70, "0.50-0.70"),
        (0.70, 0.85, "0.70-0.85"),
        (0.85, 1.01, "0.85-1.00"),
    ]
    buckets = []
    for lo, hi, label in bucket_defs:
        sub = [t for t in trades if lo <= t.score < hi]
        if not sub:
            buckets.append({"range": label, "trades": 0})
            continue
        sub_pnls = [t.pnl for t in sub]
        sub_wins = [p for p in sub_pnls if p > 0]
        buckets.append({
            "range": label,
            "trades": len(sub),
            "win_rate": round(len(sub_wins) / len(sub), 4),
            "avg_pnl": round(sum(sub_pnls) / len(sub), 6),
            "pf": _safe_pf(sub_pnls),
        })

    # ─── By direction ───
    by_dir = {}
    for d in ("bullish", "bearish"):
        sub = [t for t in trades if t.direction == d]
        if not sub:
            by_dir[d] = {"trades": 0}
            continue
        sub_pnls = [t.pnl for t in sub]
        sub_wins = [p for p in sub_pnls if p > 0]
        by_dir[d] = {
            "trades": len(sub),
            "win_rate": round(len(sub_wins) / len(sub), 4),
            "avg_pnl": round(sum(sub_pnls) / len(sub), 6),
            "pf": _safe_pf(sub_pnls),
        }

    # ─── By quality ───
    by_q = {}
    for q in ("HIGH", "MEDIUM", "LOW"):
        sub = [t for t in trades if t.quality == q]
        if not sub:
            by_q[q] = {"trades": 0}
            continue
        sub_pnls = [t.pnl for t in sub]
        sub_wins = [p for p in sub_pnls if p > 0]
        by_q[q] = {
            "trades": len(sub),
            "win_rate": round(len(sub_wins) / len(sub), 4),
            "avg_pnl": round(sum(sub_pnls) / len(sub), 6),
        }

    # ─── Drawdown / Sharpe ───
    eq_curve = [1.0]
    for p, t in zip(pnls, trades):
        eq_curve.append(eq_curve[-1] * (1.0 + p * t.allocation))
    peak = eq_curve[0]
    dd = 0.0
    for v in eq_curve:
        peak = max(peak, v)
        dd = min(dd, (v - peak) / peak)
    max_dd = -dd

    if n > 1:
        mean = expectancy
        var = sum((p - mean) ** 2 for p in pnls) / (n - 1)
        std = var ** 0.5
        sharpe = (mean / std) * math.sqrt(n) if std > 0 else 0.0
    else:
        sharpe = 0.0

    # ─── Pearson correlation: score vs pnl (the "moment of truth") ───
    pearson_score_pnl = _pearson([t.score for t in trades], pnls)

    return {
        "ok": True,
        "trades": n,
        "win_rate": round(win_rate, 4),
        "profit_factor": (round(pf, 4) if pf != float("inf") else "inf"),
        "expectancy": round(expectancy, 6),
        "equity": round(equity, 4),
        "max_drawdown": round(max_dd, 4),
        "sharpe_proxy": round(sharpe, 3),
        "avg_allocation": round(avg_alloc, 3),
        "score_pnl_correlation": round(pearson_score_pnl, 4),
        "score_buckets": buckets,
        "by_direction": by_dir,
        "by_quality": by_q,
        "skips": skips,
        "candles_evaluated": total_candles - warmup - 1,
    }


def _safe_pf(pnls: List[float]) -> Any:
    p = sum(x for x in pnls if x > 0)
    l = abs(sum(x for x in pnls if x <= 0))
    if l == 0:
        return "inf" if p > 0 else 0.0
    return round(p / l, 4)


def _pearson(xs: List[float], ys: List[float]) -> float:
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx > 0 and dy > 0 else 0.0
