"""
FORENSIC MFE/MAE ANALYZER  (read-only)

Phase: FIX-ENTRY / pre-decision diagnostic.

Goal: prove WHY recent SimpleMA trades closed in loss before touching the
entry logic. Per Architect's directive — no code in production paths is
modified, no DB writes, no UI. We only:

  1. Read CLOSED cases that participated in real exit logic
     (exit_rule in {TIME_EXIT, TAKE_PROFIT, STOP_LOSS}).
  2. For each, fetch 1m klines from Binance US (same provider used in
     mark_price_updater) covering [opened_at, closed_at].
  3. Compute per-trade:
        MFE%  (Maximum Favorable Excursion)
        MAE%  (Maximum Adverse Excursion)
        time_to_MFE / time_to_MAE
        whether the TP-edge or SL-edge would have been crossed first
        (chronologically) for that trade's phase threshold.
  4. Tag a regime at entry by computing EMA20/EMA50 on 1m baseline
     (60+ bars before entry) — same logic the production gate uses.
  5. Classify each trade into one of:
        - LATE_ENTRY            : MAE >= half SL within first 2 min, no MFE
        - WRONG_DIRECTION       : MAE > 2x MFE, never approached TP
        - EXIT_TOO_TIGHT        : MFE >= TP_threshold but trade still
                                  closed at loss/time (we left $ on table)
        - EXIT_TOO_LOOSE        : MFE < 0.5*TP, MAE < SL, killed by TIME
        - SL_FIRST              : SL crossed before TP — fair stop
        - TP_FIRST              : TP reached first — winner
        - NEUTRAL               : nothing decisive

Outputs (read-only — files only, no Mongo writes):
  /tmp/forensic_mfe_mae.jsonl    -- one record per trade
  /tmp/forensic_report.md        -- human-readable summary

Run:
  python /app/scripts/forensic_mfe_mae.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import mean, median
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pymongo import MongoClient


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "trading_os"

BINANCE_BASE = "https://api.binance.us/api/v3"
KLINES_INTERVAL = "1m"

# Map close_reason → (TP%, SL%) thresholds used for that phase.
# We keep this strictly informational; the script does NOT change production
# values, only consults them when classifying TP/SL crossings.
PHASE_THRESHOLDS = {
    # LIVE-2  (older,  ±0.30%)
    "LIVE2_TP_030":      (0.30, 0.30),
    "LIVE2_SL_030":      (0.30, 0.30),
    "LIVE2_TIME_30M":    (0.30, 0.30),
    # LIVE-2D (current, ±0.15%)
    "LIVE2D_TP_015":     (0.15, 0.15),
    "LIVE2D_SL_015":     (0.15, 0.15),
    "LIVE2D_TIME_30M":   (0.15, 0.15),
}

OUT_JSONL = "/tmp/forensic_mfe_mae.jsonl"
OUT_REPORT = "/tmp/forensic_report.md"


# --------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------
def get_db():
    return MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)[DB_NAME]


def fetch_real_closed_cases(db) -> List[Dict[str, Any]]:
    """All CLOSED cases whose exit was driven by the real exit manager."""
    cursor = db.trading_cases.find({
        "status": "CLOSED",
        "exit_rule": {"$in": ["TIME_EXIT", "TAKE_PROFIT", "STOP_LOSS"]},
    }).sort("opened_at", 1)
    return list(cursor)


def to_utc_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


# --------------------------------------------------------------------------
# Klines fetch with cache + rate limiting
# --------------------------------------------------------------------------
_kline_cache: Dict[Tuple[str, int, int], List[List[Any]]] = {}
_last_call = [0.0]


def _rate_limit():
    elapsed = time.time() - _last_call[0]
    if elapsed < 0.12:
        time.sleep(0.12 - elapsed)
    _last_call[0] = time.time()


def fetch_klines_1m(
    symbol: str, start_ms: int, end_ms: int
) -> List[List[Any]]:
    """
    Fetch 1m klines from Binance US.
    Returns raw list; each kline = [openTime, O, H, L, C, V, closeTime, ...].
    Cached by (symbol, bucket_minute_start, bucket_minute_end).
    """
    # Round to whole minute boundaries to maximise cache hits across calls.
    start_ms = (start_ms // 60_000) * 60_000
    end_ms = ((end_ms // 60_000) + 1) * 60_000

    key = (symbol, start_ms, end_ms)
    if key in _kline_cache:
        return _kline_cache[key]

    _rate_limit()
    try:
        r = httpx.get(
            f"{BINANCE_BASE}/klines",
            params={
                "symbol": symbol,
                "interval": KLINES_INTERVAL,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000,
            },
            timeout=15,
        )
        if r.status_code != 200:
            print(
                f"[forensic] klines HTTP {r.status_code} for {symbol} "
                f"{start_ms}-{end_ms}"
            )
            _kline_cache[key] = []
            return []
        data = r.json()
        if not isinstance(data, list):
            _kline_cache[key] = []
            return []
        _kline_cache[key] = data
        return data
    except Exception as e:
        print(f"[forensic] klines error {symbol}: {e}")
        _kline_cache[key] = []
        return []


# --------------------------------------------------------------------------
# Per-trade analytics
# --------------------------------------------------------------------------
def analyse_trade(trade: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Compute MFE / MAE / chronology / regime for one trade."""
    case_id = trade.get("case_id")
    symbol = trade.get("symbol")
    side = trade.get("side", "LONG")
    entry = float(trade.get("entry_price") or trade.get("avg_entry_price") or 0.0)
    exit_p = float(trade.get("exit_price") or trade.get("current_price") or 0.0)
    qty = float(trade.get("qty") or 0.0)
    realized = float(trade.get("realized_pnl") or 0.0)
    realized_pct = trade.get("realized_pnl_pct")
    if realized_pct is None and entry > 0 and exit_p > 0:
        sign = 1.0 if side == "LONG" else -1.0
        realized_pct = (exit_p - entry) / entry * 100.0 * sign
    realized_pct = float(realized_pct or 0.0)

    op = trade.get("opened_at")
    cl = trade.get("closed_at")
    if not (case_id and symbol and entry > 0 and op and cl):
        return None

    op_ms = to_utc_ms(op)
    cl_ms = to_utc_ms(cl)
    duration_min = (cl_ms - op_ms) / 60_000.0
    if duration_min <= 0:
        return None

    # Trade window — pad ±60s so 1m bucket containing entry/exit is always in.
    klines_window = fetch_klines_1m(symbol, op_ms - 60_000, cl_ms + 60_000)
    if not klines_window:
        return None

    # Filter to bars whose openTime ∈ [op_ms - 60s, cl_ms].
    bars: List[Tuple[int, float, float, float, float]] = []
    for k in klines_window:
        ot = int(k[0])
        # Inclusive of the bar containing the entry minute.
        if ot < op_ms - 60_000:
            continue
        if ot > cl_ms:
            continue
        bars.append(
            (ot, float(k[1]), float(k[2]), float(k[3]), float(k[4]))
        )

    if not bars:
        return None

    # Compute MFE / MAE / chronology of TP-edge vs SL-edge crossing.
    close_reason = trade.get("close_reason") or ""
    tp_pct, sl_pct = PHASE_THRESHOLDS.get(close_reason, (0.15, 0.15))
    if side == "LONG":
        tp_price = entry * (1 + tp_pct / 100.0)
        sl_price = entry * (1 - sl_pct / 100.0)
    else:  # SHORT
        tp_price = entry * (1 - tp_pct / 100.0)
        sl_price = entry * (1 + sl_pct / 100.0)

    mfe_extreme = entry      # best-favorable price reached
    mae_extreme = entry      # worst-adverse price reached
    time_to_mfe_min: Optional[float] = None
    time_to_mae_min: Optional[float] = None
    tp_first_at_min: Optional[float] = None  # first bar where TP crossed
    sl_first_at_min: Optional[float] = None  # first bar where SL crossed

    for ot, _o, h, l, _c in bars:
        bar_min = (ot - op_ms) / 60_000.0  # minutes since entry
        if side == "LONG":
            # favorable = up
            if h > mfe_extreme:
                mfe_extreme = h
                time_to_mfe_min = bar_min
            if l < mae_extreme:
                mae_extreme = l
                time_to_mae_min = bar_min
            if tp_first_at_min is None and h >= tp_price:
                tp_first_at_min = bar_min
            if sl_first_at_min is None and l <= sl_price:
                sl_first_at_min = bar_min
        else:  # SHORT — favorable = down
            if l < mfe_extreme:
                mfe_extreme = l
                time_to_mfe_min = bar_min
            if h > mae_extreme:
                mae_extreme = h
                time_to_mae_min = bar_min
            if tp_first_at_min is None and l <= tp_price:
                tp_first_at_min = bar_min
            if sl_first_at_min is None and h >= sl_price:
                sl_first_at_min = bar_min

    if side == "LONG":
        mfe_pct = (mfe_extreme - entry) / entry * 100.0
        mae_pct = (entry - mae_extreme) / entry * 100.0
    else:
        mfe_pct = (entry - mfe_extreme) / entry * 100.0
        mae_pct = (mae_extreme - entry) / entry * 100.0

    # Which threshold was hit first chronologically?
    if tp_first_at_min is not None and sl_first_at_min is not None:
        which_first = "TP" if tp_first_at_min < sl_first_at_min else "SL"
    elif tp_first_at_min is not None:
        which_first = "TP"
    elif sl_first_at_min is not None:
        which_first = "SL"
    else:
        which_first = "NONE"

    # ------------------------- regime at entry ------------------------------
    regime_at_entry = compute_regime_at(symbol, op_ms)

    # ------------------------- diagnosis classifier -------------------------
    diag = classify_diagnosis(
        side=side,
        mfe_pct=mfe_pct,
        mae_pct=mae_pct,
        tp_pct=tp_pct,
        sl_pct=sl_pct,
        which_first=which_first,
        time_to_mae_min=time_to_mae_min,
        realized_pct=realized_pct,
        exit_rule=trade.get("exit_rule") or "",
    )

    return {
        "case_id": case_id,
        "symbol": symbol,
        "side": side,
        "opened_at": op.isoformat() if isinstance(op, datetime) else str(op),
        "closed_at": cl.isoformat() if isinstance(cl, datetime) else str(cl),
        "duration_min": round(duration_min, 2),
        "entry_price": entry,
        "exit_price": exit_p,
        "qty": qty,
        "exit_rule": trade.get("exit_rule"),
        "close_reason": close_reason,
        "phase_tp_pct": tp_pct,
        "phase_sl_pct": sl_pct,
        "realized_pnl": round(realized, 6),
        "realized_pnl_pct": round(realized_pct, 4),
        "mfe_pct": round(mfe_pct, 4),
        "mae_pct": round(mae_pct, 4),
        "time_to_mfe_min": (
            round(time_to_mfe_min, 2) if time_to_mfe_min is not None else None
        ),
        "time_to_mae_min": (
            round(time_to_mae_min, 2) if time_to_mae_min is not None else None
        ),
        "tp_first_at_min": (
            round(tp_first_at_min, 2) if tp_first_at_min is not None else None
        ),
        "sl_first_at_min": (
            round(sl_first_at_min, 2) if sl_first_at_min is not None else None
        ),
        "which_threshold_first": which_first,
        "hit_tp_possible": mfe_pct >= tp_pct,
        "hit_sl_possible": mae_pct >= sl_pct,
        "regime_at_entry": regime_at_entry,
        "diagnosis": diag,
        "n_bars_observed": len(bars),
    }


# --------------------------------------------------------------------------
# Regime computation (mirrors production EMA20/50 logic)
# --------------------------------------------------------------------------
def compute_regime_at(symbol: str, at_ms: int) -> str:
    """
    Compute UPTREND / DOWNTREND / RANGE at given UTC ms using 1m EMA20/50 —
    same horizon the live regime detector uses for its gate.

    UPTREND   : close > EMA20 > EMA50 AND EMA20_slope > 0
    DOWNTREND : close < EMA20 < EMA50 AND EMA20_slope < 0
    Otherwise : RANGE
    """
    # 80 bars of 1m history for stable EMA50.
    start = at_ms - 90 * 60_000
    end = at_ms + 60_000
    bars = fetch_klines_1m(symbol, start, end)
    closes: List[float] = []
    for k in bars:
        ot = int(k[0])
        if ot > at_ms:
            break
        closes.append(float(k[4]))
    if len(closes) < 60:
        return "UNKNOWN"

    def ema(values: List[float], period: int) -> List[float]:
        k = 2.0 / (period + 1)
        out = [values[0]]
        for v in values[1:]:
            out.append(v * k + out[-1] * (1 - k))
        return out

    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    last_close = closes[-1]
    last_e20 = e20[-1]
    last_e50 = e50[-1]
    prev_e20 = e20[-3] if len(e20) > 3 else e20[0]
    slope_up = last_e20 > prev_e20
    slope_dn = last_e20 < prev_e20

    if last_close > last_e20 > last_e50 and slope_up:
        return "UPTREND"
    if last_close < last_e20 < last_e50 and slope_dn:
        return "DOWNTREND"
    return "RANGE"


# --------------------------------------------------------------------------
# Diagnosis classifier
# --------------------------------------------------------------------------
def classify_diagnosis(
    *,
    side: str,
    mfe_pct: float,
    mae_pct: float,
    tp_pct: float,
    sl_pct: float,
    which_first: str,
    time_to_mae_min: Optional[float],
    realized_pct: float,
    exit_rule: str,
) -> str:
    # 1. Genuine winner — TP boundary touched first.
    if which_first == "TP" and exit_rule == "TAKE_PROFIT":
        return "TP_FIRST"
    # 2. Fair stop — SL boundary touched first.
    if which_first == "SL" and exit_rule == "STOP_LOSS":
        return "SL_FIRST"
    # 3. We had favorable excursion >= TP, but the exit caught a loss
    #    (we were green and gave it back).
    if mfe_pct >= tp_pct and realized_pct < 0:
        return "EXIT_TOO_TIGHT_OR_MISSED_TP"
    # 4. Adverse hit fast — likely late entry.
    if (
        time_to_mae_min is not None
        and time_to_mae_min <= 2.0
        and mae_pct >= sl_pct * 0.5
        and mfe_pct < tp_pct * 0.5
    ):
        return "LATE_ENTRY"
    # 5. Wrong direction — MAE much larger than MFE.
    if mae_pct > 0 and mae_pct >= max(2.0 * mfe_pct, sl_pct):
        return "WRONG_DIRECTION"
    # 6. Killed by TIME with no decisive move.
    if exit_rule == "TIME_EXIT" and mfe_pct < tp_pct and mae_pct < sl_pct:
        return "EXIT_TOO_LOOSE_TIME_KILL"
    return "NEUTRAL"


# --------------------------------------------------------------------------
# Aggregate report
# --------------------------------------------------------------------------
def render_report(records: List[Dict[str, Any]]) -> str:
    if not records:
        return "# Forensic MFE/MAE Report\n\nNo records analysed.\n"

    def fmt(x):
        if x is None:
            return "—"
        if isinstance(x, float):
            return f"{x:+.4f}"
        return str(x)

    lines: List[str] = []
    lines.append("# FORENSIC MFE/MAE REPORT — read-only diagnostic")
    lines.append("")
    lines.append(
        f"Generated: {datetime.now(timezone.utc).isoformat()}"
    )
    lines.append(f"Total trades analysed: **{len(records)}**")
    lines.append("")
    lines.append("Source: `trading_cases` where exit_rule ∈ "
                 "{TIME_EXIT, TAKE_PROFIT, STOP_LOSS}.")
    lines.append("Price source: Binance US 1m klines (read-only).")
    lines.append("Regime: EMA20/50 on 1m close at entry minute.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- Section 1: outcome by side ----------------------------------------
    by_side: Dict[str, List[Dict]] = defaultdict(list)
    for r in records:
        by_side[r["side"]].append(r)

    lines.append("## 1. Outcome by side")
    lines.append("")
    lines.append(
        "| Side | N | Wins | Losses | WR | Avg PnL% | Avg MFE% | Avg MAE% |"
    )
    lines.append("|------|---|------|--------|----|---------|----------|---------|")
    for side, rs in by_side.items():
        n = len(rs)
        wins = sum(1 for r in rs if r["realized_pnl_pct"] > 0)
        losses = sum(1 for r in rs if r["realized_pnl_pct"] < 0)
        wr = wins / n * 100 if n else 0
        avg_pnl = mean([r["realized_pnl_pct"] for r in rs]) if rs else 0
        avg_mfe = mean([r["mfe_pct"] for r in rs]) if rs else 0
        avg_mae = mean([r["mae_pct"] for r in rs]) if rs else 0
        lines.append(
            f"| {side} | {n} | {wins} | {losses} | {wr:.1f}% | "
            f"{avg_pnl:+.4f} | {avg_mfe:+.4f} | {avg_mae:+.4f} |"
        )
    lines.append("")

    # --- Section 2: by regime -----------------------------------------------
    by_reg: Dict[str, List[Dict]] = defaultdict(list)
    for r in records:
        by_reg[r["regime_at_entry"] or "UNKNOWN"].append(r)
    lines.append("## 2. Outcome by regime at entry (EMA20/50, 1m)")
    lines.append("")
    lines.append(
        "| Regime | N | LONG | SHORT | Wins | Avg PnL% | Avg MFE% | Avg MAE% |"
    )
    lines.append(
        "|--------|---|------|-------|------|---------|----------|---------|"
    )
    for reg, rs in sorted(by_reg.items()):
        n = len(rs)
        nl = sum(1 for r in rs if r["side"] == "LONG")
        ns = sum(1 for r in rs if r["side"] == "SHORT")
        wins = sum(1 for r in rs if r["realized_pnl_pct"] > 0)
        avg_pnl = mean([r["realized_pnl_pct"] for r in rs]) if rs else 0
        avg_mfe = mean([r["mfe_pct"] for r in rs]) if rs else 0
        avg_mae = mean([r["mae_pct"] for r in rs]) if rs else 0
        lines.append(
            f"| {reg} | {n} | {nl} | {ns} | {wins} | "
            f"{avg_pnl:+.4f} | {avg_mfe:+.4f} | {avg_mae:+.4f} |"
        )
    lines.append("")

    # --- Section 3: TP/SL crossing chronology ------------------------------
    n_total = len(records)
    n_tp_possible = sum(1 for r in records if r["hit_tp_possible"])
    n_sl_possible = sum(1 for r in records if r["hit_sl_possible"])
    n_tp_first = sum(1 for r in records if r["which_threshold_first"] == "TP")
    n_sl_first = sum(1 for r in records if r["which_threshold_first"] == "SL")
    n_neither = sum(
        1 for r in records if r["which_threshold_first"] == "NONE"
    )
    lines.append("## 3. TP / SL crossings (per phase threshold)")
    lines.append("")
    lines.append(f"- Trades where MFE reached TP threshold: "
                 f"**{n_tp_possible}/{n_total}** "
                 f"({n_tp_possible / n_total * 100:.1f}%)")
    lines.append(f"- Trades where MAE reached SL threshold: "
                 f"**{n_sl_possible}/{n_total}** "
                 f"({n_sl_possible / n_total * 100:.1f}%)")
    lines.append(f"- TP touched **first** chronologically: "
                 f"**{n_tp_first}/{n_total}** "
                 f"({n_tp_first / n_total * 100:.1f}%)")
    lines.append(f"- SL touched **first** chronologically: "
                 f"**{n_sl_first}/{n_total}** "
                 f"({n_sl_first / n_total * 100:.1f}%)")
    lines.append(f"- Neither boundary touched (TIME exit territory): "
                 f"**{n_neither}/{n_total}** "
                 f"({n_neither / n_total * 100:.1f}%)")
    lines.append("")

    # --- Section 4: timing of MFE / MAE ------------------------------------
    mfe_times = [r["time_to_mfe_min"] for r in records
                 if r["time_to_mfe_min"] is not None]
    mae_times = [r["time_to_mae_min"] for r in records
                 if r["time_to_mae_min"] is not None]
    lines.append("## 4. Timing of extremes (minutes since entry)")
    lines.append("")
    if mfe_times:
        lines.append(f"- time_to_MFE — median: {median(mfe_times):.2f} min, "
                     f"avg: {mean(mfe_times):.2f} min")
    if mae_times:
        lines.append(f"- time_to_MAE — median: {median(mae_times):.2f} min, "
                     f"avg: {mean(mae_times):.2f} min")
    n_immediate_mae = sum(
        1 for r in records
        if r["time_to_mae_min"] is not None and r["time_to_mae_min"] <= 1.0
    )
    lines.append(f"- Trades where MAE happened within first ≤1 min: "
                 f"**{n_immediate_mae}/{n_total}** "
                 f"({n_immediate_mae / n_total * 100:.1f}%) — proxy for "
                 "*late entry / immediate adverse move*")
    lines.append("")

    # --- Section 5: diagnosis distribution ---------------------------------
    diag_count = Counter(r["diagnosis"] for r in records)
    lines.append("## 5. Diagnosis distribution")
    lines.append("")
    lines.append("| Diagnosis | N | % |")
    lines.append("|-----------|---|---|")
    for d, n in diag_count.most_common():
        lines.append(f"| {d} | {n} | {n / n_total * 100:.1f}% |")
    lines.append("")

    # --- Section 6: by phase / threshold -----------------------------------
    by_phase: Dict[str, List[Dict]] = defaultdict(list)
    for r in records:
        key = f"TP±{r['phase_tp_pct']}/SL±{r['phase_sl_pct']}"
        by_phase[key].append(r)
    lines.append("## 6. By phase threshold (TP/SL %)")
    lines.append("")
    lines.append(
        "| Threshold | N | Wins | Avg MFE% | Avg MAE% | "
        "MFE≥TP n | SL_first n |"
    )
    lines.append(
        "|-----------|---|------|----------|---------|----------|------------|"
    )
    for k, rs in by_phase.items():
        n = len(rs)
        wins = sum(1 for r in rs if r["realized_pnl_pct"] > 0)
        avg_mfe = mean([r["mfe_pct"] for r in rs])
        avg_mae = mean([r["mae_pct"] for r in rs])
        n_tp = sum(1 for r in rs if r["hit_tp_possible"])
        n_sl_first = sum(1 for r in rs if r["which_threshold_first"] == "SL")
        lines.append(
            f"| {k} | {n} | {wins} | {avg_mfe:+.4f} | {avg_mae:+.4f} | "
            f"{n_tp} | {n_sl_first} |"
        )
    lines.append("")

    # --- Section 7: per-trade table ----------------------------------------
    lines.append("## 7. Per-trade detail")
    lines.append("")
    lines.append(
        "| case_id | side | regime | dur_min | rPnL% | MFE% | MAE% | "
        "t→MFE | t→MAE | first | exit_rule | diagnosis |"
    )
    lines.append(
        "|---------|------|--------|---------|-------|------|------|"
        "-------|-------|-------|-----------|-----------|"
    )
    for r in sorted(records, key=lambda x: x["opened_at"]):
        lines.append(
            f"| `{r['case_id'][:14]}` | {r['side']} | {r['regime_at_entry']} | "
            f"{r['duration_min']:.1f} | {r['realized_pnl_pct']:+.4f} | "
            f"{r['mfe_pct']:+.4f} | {r['mae_pct']:+.4f} | "
            f"{fmt(r['time_to_mfe_min'])} | {fmt(r['time_to_mae_min'])} | "
            f"{r['which_threshold_first']} | {r['exit_rule']} | "
            f"{r['diagnosis']} |"
        )
    lines.append("")

    # --- Section 8: verdict-ready signals ----------------------------------
    lines.append("## 8. Decision signals (per architect's framework)")
    lines.append("")
    n_mfe_ge_tp = sum(1 for r in records if r["hit_tp_possible"])
    n_mae_first_loss = sum(
        1 for r in records
        if r["which_threshold_first"] == "SL"
        and r["realized_pnl_pct"] < 0
    )
    n_short_favor_far_tp = sum(
        1 for r in records
        if r["side"] == "SHORT"
        and r["mfe_pct"] > 0
        and r["mfe_pct"] < r["phase_tp_pct"]
        and r["realized_pnl_pct"] < 0
    )
    lines.append(
        f"- **A) MFE ≥ TP rate**: {n_mfe_ge_tp}/{n_total} "
        f"({n_mfe_ge_tp / n_total * 100:.1f}%). "
        f"If << ~30% → entry is the bottleneck (signal too late or wrong dir)."
    )
    lines.append(
        f"- **B) SL-first AND closed in loss**: {n_mae_first_loss}/{n_total} "
        f"({n_mae_first_loss / n_total * 100:.1f}%). "
        "Pure entry quality killer."
    )
    lines.append(
        f"- **C) SHORTs with favorable move but TP unreached**: "
        f"{n_short_favor_far_tp}/"
        f"{sum(1 for r in records if r['side'] == 'SHORT')} SHORTs. "
        "Suggests TP calibration may help."
    )
    lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    db = get_db()
    print(f"[forensic] connected DB={DB_NAME}")

    cases = fetch_real_closed_cases(db)
    print(f"[forensic] real closed cases to analyse: {len(cases)}")

    records: List[Dict[str, Any]] = []
    skipped = 0
    for i, t in enumerate(cases, 1):
        try:
            rec = analyse_trade(t)
        except Exception as e:
            print(f"[forensic] error on {t.get('case_id')}: {e}")
            rec = None
        if rec is None:
            skipped += 1
            continue
        records.append(rec)
        if i % 10 == 0 or i == len(cases):
            print(f"[forensic] progress {i}/{len(cases)} (kept={len(records)}, "
                  f"skipped={skipped})")

    # Persist raw records.
    with open(OUT_JSONL, "w") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")
    print(f"[forensic] wrote {len(records)} records → {OUT_JSONL}")

    report = render_report(records)
    with open(OUT_REPORT, "w") as f:
        f.write(report)
    print(f"[forensic] wrote report → {OUT_REPORT}")

    # Print compact summary tail to stdout.
    print("\n" + "=" * 70)
    print("REPORT (first 120 lines):")
    print("=" * 70)
    for line in report.splitlines()[:120]:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
