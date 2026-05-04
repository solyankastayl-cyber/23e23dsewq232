"""
FORENSIC v2 — MFE / MAE + MFE(t) timeline   (read-only)

Phase: post-LIVE-2H baseline observation.

Extends forensic_mfe_mae.py with:

  - Phase tag detection (LIVE2_, LIVE2D_, LIVE2H_) — the analyzer already
    treats each case according to its own threshold pair; the new code
    just exposes the phase in the report so we can compare.
  - Per-trade MFE(t) timeline at fixed checkpoints 1, 5, 10, 20, 30 min
    since entry.  Used to characterise the "TIME_KILL" cluster:
      * if MFE grows monotonically past 30 min → TIME is too short
      * if MFE peaks early and decays            → trail / faster TP
      * if MFE never crosses ~0.20%             → TP=0.30% too far
  - Aggregate average MFE(t) curve per (phase × side × outcome).

No production code is touched. Output:

  /tmp/forensic_v2_mfe_mae.jsonl   per-trade records with timeline
  /tmp/forensic_v2_report.md       human-readable report
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
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "trading_os"
BINANCE_BASE = "https://api.binance.us/api/v3"
KLINES_INTERVAL = "1m"
CHECKPOINTS_MIN = [1, 5, 10, 20, 30]

# (TP%, SL%) per phase tag.
PHASE_THRESHOLDS = {
    # LIVE-2  (legacy ±0.30%)
    "LIVE2_TP_030":      (0.30, 0.30),
    "LIVE2_SL_030":      (0.30, 0.30),
    "LIVE2_TIME_30M":    (0.30, 0.30),
    # LIVE-2D (tightened ±0.15%)
    "LIVE2D_TP_015":     (0.15, 0.15),
    "LIVE2D_SL_015":     (0.15, 0.15),
    "LIVE2D_TIME_30M":   (0.15, 0.15),
    # LIVE-2H (current baseline regression ±0.30%, gates OFF)
    "LIVE2H_TP_030":     (0.30, 0.30),
    "LIVE2H_SL_030":     (0.30, 0.30),
    "LIVE2H_TIME_30M":   (0.30, 0.30),
}


def phase_of(close_reason: str) -> str:
    if close_reason.startswith("LIVE2H"):
        return "LIVE-2H"
    if close_reason.startswith("LIVE2D"):
        return "LIVE-2D"
    if close_reason.startswith("LIVE2_"):
        return "LIVE-2"
    return "OTHER"


OUT_JSONL = "/tmp/forensic_v2_mfe_mae.jsonl"
OUT_REPORT = "/tmp/forensic_v2_report.md"


# --------------------------------------------------------------------------
def get_db():
    return MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)[DB_NAME]


def fetch_real_closed_cases(db) -> List[Dict[str, Any]]:
    return list(db.trading_cases.find({
        "status": "CLOSED",
        "exit_rule": {"$in": ["TIME_EXIT", "TAKE_PROFIT", "STOP_LOSS"]},
    }).sort("opened_at", 1))


def to_utc_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


# --------------------------------------------------------------------------
_kline_cache: Dict[Tuple[str, int, int], List[List[Any]]] = {}
_last_call = [0.0]


def _rate_limit():
    e = time.time() - _last_call[0]
    if e < 0.12:
        time.sleep(0.12 - e)
    _last_call[0] = time.time()


def fetch_klines_1m(symbol: str, start_ms: int, end_ms: int) -> List[List[Any]]:
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
                "symbol": symbol, "interval": KLINES_INTERVAL,
                "startTime": start_ms, "endTime": end_ms, "limit": 1000,
            },
            timeout=15,
        )
        if r.status_code != 200:
            _kline_cache[key] = []
            return []
        data = r.json()
        if not isinstance(data, list):
            _kline_cache[key] = []
            return []
        _kline_cache[key] = data
        return data
    except Exception as e:
        print(f"[forensic-v2] klines error {symbol}: {e}")
        _kline_cache[key] = []
        return []


# --------------------------------------------------------------------------
def compute_regime_at(symbol: str, at_ms: int) -> str:
    """1m EMA20/50 regime at a UTC ms — same horizon as production gate."""
    start = at_ms - 90 * 60_000
    end = at_ms + 60_000
    bars = fetch_klines_1m(symbol, start, end)
    closes: List[float] = []
    for k in bars:
        if int(k[0]) > at_ms:
            break
        closes.append(float(k[4]))
    if len(closes) < 60:
        return "UNKNOWN"

    def ema(vs, p):
        kk = 2.0 / (p + 1)
        out = [vs[0]]
        for v in vs[1:]:
            out.append(v * kk + out[-1] * (1 - kk))
        return out

    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    last_close = closes[-1]
    last_e20 = e20[-1]
    last_e50 = e50[-1]
    prev_e20 = e20[-3] if len(e20) > 3 else e20[0]
    if last_close > last_e20 > last_e50 and last_e20 > prev_e20:
        return "UPTREND"
    if last_close < last_e20 < last_e50 and last_e20 < prev_e20:
        return "DOWNTREND"
    return "RANGE"


# --------------------------------------------------------------------------
def analyse_trade(trade: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    case_id = trade.get("case_id")
    symbol = trade.get("symbol")
    side = trade.get("side", "LONG")
    entry = float(trade.get("entry_price") or trade.get("avg_entry_price") or 0)
    exit_p = float(trade.get("exit_price") or trade.get("current_price") or 0)
    realized = float(trade.get("realized_pnl") or 0)
    realized_pct = trade.get("realized_pnl_pct")
    if realized_pct is None and entry > 0 and exit_p > 0:
        sign = 1 if side == "LONG" else -1
        realized_pct = (exit_p - entry) / entry * 100 * sign
    realized_pct = float(realized_pct or 0)

    op = trade.get("opened_at")
    cl = trade.get("closed_at")
    if not (case_id and symbol and entry > 0 and op and cl):
        return None

    op_ms = to_utc_ms(op)
    cl_ms = to_utc_ms(cl)
    duration_min = (cl_ms - op_ms) / 60_000.0
    if duration_min <= 0:
        return None

    # Always pull a fixed 32-min window so we can compute the timeline up to
    # 30 min even if the trade actually closed in 4 min (helpful for early
    # TP cases — we want to see "what if we held longer?").
    window_end_ms = max(cl_ms, op_ms + 32 * 60_000)
    klines = fetch_klines_1m(symbol, op_ms - 60_000, window_end_ms + 60_000)
    if not klines:
        return None

    bars = [
        (int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]))
        for k in klines
        if int(k[0]) >= op_ms - 60_000 and int(k[0]) <= window_end_ms
    ]
    if not bars:
        return None

    close_reason = trade.get("close_reason") or ""
    tp_pct, sl_pct = PHASE_THRESHOLDS.get(close_reason, (0.30, 0.30))
    if side == "LONG":
        tp_price = entry * (1 + tp_pct / 100.0)
        sl_price = entry * (1 - sl_pct / 100.0)
    else:
        tp_price = entry * (1 - tp_pct / 100.0)
        sl_price = entry * (1 + sl_pct / 100.0)

    # Walk bars chronologically. Track running MFE/MAE and timeline at
    # CHECKPOINTS_MIN.  Snapshot timeline values are taken using the LAST
    # bar whose openTime <= op_ms + cp*60_000 — i.e. all data available by
    # minute `cp` since entry.  IMPORTANT: timeline metrics are extended
    # past the actual trade close (as a "what if" curve), so we can ask
    # whether a longer TIME would have helped.
    mfe_extreme = entry
    mae_extreme = entry
    time_to_mfe_min: Optional[float] = None
    time_to_mae_min: Optional[float] = None
    tp_first_at_min: Optional[float] = None
    sl_first_at_min: Optional[float] = None

    timeline_mfe: Dict[int, float] = {}
    timeline_mae: Dict[int, float] = {}

    # These flags only consider the *real* lifetime of the trade for the
    # primary "which crossed first" question.
    real_close_ms = cl_ms

    for ot, _o, h, l, _c in bars:
        bar_min = (ot - op_ms) / 60_000.0
        if side == "LONG":
            if h > mfe_extreme:
                mfe_extreme = h
                time_to_mfe_min = bar_min
            if l < mae_extreme:
                mae_extreme = l
                time_to_mae_min = bar_min
            if ot <= real_close_ms:
                if tp_first_at_min is None and h >= tp_price:
                    tp_first_at_min = bar_min
                if sl_first_at_min is None and l <= sl_price:
                    sl_first_at_min = bar_min
        else:
            if l < mfe_extreme:
                mfe_extreme = l
                time_to_mfe_min = bar_min
            if h > mae_extreme:
                mae_extreme = h
                time_to_mae_min = bar_min
            if ot <= real_close_ms:
                if tp_first_at_min is None and l <= tp_price:
                    tp_first_at_min = bar_min
                if sl_first_at_min is None and h >= sl_price:
                    sl_first_at_min = bar_min

        # Timeline checkpoints
        for cp in CHECKPOINTS_MIN:
            if cp not in timeline_mfe and bar_min >= cp:
                if side == "LONG":
                    cur_mfe = (mfe_extreme - entry) / entry * 100.0
                    cur_mae = (entry - mae_extreme) / entry * 100.0
                else:
                    cur_mfe = (entry - mfe_extreme) / entry * 100.0
                    cur_mae = (mae_extreme - entry) / entry * 100.0
                timeline_mfe[cp] = round(cur_mfe, 4)
                timeline_mae[cp] = round(cur_mae, 4)

    # Fill any unfilled checkpoints with the final value.
    if timeline_mfe:
        last_cp = max(timeline_mfe)
        for cp in CHECKPOINTS_MIN:
            if cp not in timeline_mfe:
                timeline_mfe[cp] = timeline_mfe[last_cp]
                timeline_mae[cp] = timeline_mae[last_cp]

    if side == "LONG":
        mfe_pct = (mfe_extreme - entry) / entry * 100.0
        mae_pct = (entry - mae_extreme) / entry * 100.0
    else:
        mfe_pct = (entry - mfe_extreme) / entry * 100.0
        mae_pct = (mae_extreme - entry) / entry * 100.0

    if tp_first_at_min is not None and sl_first_at_min is not None:
        which_first = "TP" if tp_first_at_min < sl_first_at_min else "SL"
    elif tp_first_at_min is not None:
        which_first = "TP"
    elif sl_first_at_min is not None:
        which_first = "SL"
    else:
        which_first = "NONE"

    regime_at_entry = compute_regime_at(symbol, op_ms)

    return {
        "case_id": case_id,
        "symbol": symbol,
        "side": side,
        "phase": phase_of(close_reason),
        "opened_at": op.isoformat() if isinstance(op, datetime) else str(op),
        "closed_at": cl.isoformat() if isinstance(cl, datetime) else str(cl),
        "duration_min": round(duration_min, 2),
        "entry_price": entry,
        "exit_price": exit_p,
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
        "timeline_mfe": timeline_mfe,
        "timeline_mae": timeline_mae,
    }


# --------------------------------------------------------------------------
def render_report(records: List[Dict[str, Any]]) -> str:
    if not records:
        return "# Forensic v2\n\nNo records.\n"

    out: List[str] = []
    out.append("# FORENSIC v2 — MFE/MAE + Timeline (read-only)")
    out.append("")
    out.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    out.append(f"Total trades analysed: **{len(records)}**")
    out.append("")
    out.append("New: per-trade timeline at "
               f"{', '.join(str(c) + 'min' for c in CHECKPOINTS_MIN)} "
               "since entry. Past close, the timeline is a *what-if* "
               "(price continued post-exit) — useful to ask whether "
               "a longer TIME would have helped.")
    out.append("")
    out.append("---")
    out.append("")

    # ----- 1. Phase summary -----------------------------------------------
    by_phase: Dict[str, List[Dict]] = defaultdict(list)
    for r in records:
        by_phase[r["phase"]].append(r)
    out.append("## 1. Per-phase summary")
    out.append("")
    out.append(
        "| Phase | N | LONG | SHORT | WR | Avg PnL% | Avg MFE% | Avg MAE% |"
    )
    out.append(
        "|-------|---|------|-------|----|---------|----------|---------|"
    )
    for p, rs in sorted(by_phase.items()):
        n = len(rs)
        nl = sum(1 for r in rs if r["side"] == "LONG")
        ns = sum(1 for r in rs if r["side"] == "SHORT")
        wins = sum(1 for r in rs if r["realized_pnl_pct"] > 0)
        wr = wins / n * 100 if n else 0
        avg_pnl = mean([r["realized_pnl_pct"] for r in rs]) if rs else 0
        avg_mfe = mean([r["mfe_pct"] for r in rs]) if rs else 0
        avg_mae = mean([r["mae_pct"] for r in rs]) if rs else 0
        out.append(
            f"| **{p}** | {n} | {nl} | {ns} | {wr:.1f}% | "
            f"{avg_pnl:+.4f} | {avg_mfe:+.4f} | {avg_mae:+.4f} |"
        )
    out.append("")

    # ----- 2. Average MFE(t) curve per phase ------------------------------
    out.append("## 2. Average MFE(t) curve  per (phase × outcome)")
    out.append("")
    cps = CHECKPOINTS_MIN
    out.append(
        "| Phase | Outcome | N | "
        + " | ".join(f"MFE@{cp}min" for cp in cps)
        + " |"
    )
    out.append(
        "|---|---|---|"
        + "|".join(["---"] * len(cps))
        + "|"
    )
    for p, rs in sorted(by_phase.items()):
        for outcome_lbl, fil in [
            ("WIN", lambda r: r["realized_pnl_pct"] > 0),
            ("LOSS", lambda r: r["realized_pnl_pct"] < 0),
            ("ALL", lambda r: True),
        ]:
            sub = [r for r in rs if fil(r)]
            if not sub:
                continue
            row = [f"**{p}**", outcome_lbl, str(len(sub))]
            for cp in cps:
                vals = [
                    r["timeline_mfe"].get(cp)
                    for r in sub
                    if r["timeline_mfe"].get(cp) is not None
                ]
                row.append(f"{mean(vals):+.4f}" if vals else "—")
            out.append("| " + " | ".join(row) + " |")
    out.append("")

    # ----- 3. TIME_KILL focus ---------------------------------------------
    time_kill = [
        r for r in records
        if r["exit_rule"] == "TIME_EXIT"
        and r["mfe_pct"] < r["phase_tp_pct"]
        and r["mae_pct"] < r["phase_sl_pct"]
    ]
    out.append("## 3. TIME_KILL deep-dive")
    out.append("")
    out.append(f"Total TIME_KILL trades: **{len(time_kill)}** "
               f"(out of {len(records)})")
    if time_kill:
        out.append("")
        out.append("Average MFE timeline for TIME_KILL trades:")
        out.append("")
        out.append("| | " + " | ".join(f"MFE@{cp}min" for cp in cps) + " |")
        out.append("|---|" + "|".join(["---"] * len(cps)) + "|")
        row_w = [
            "**TIME_KILL avg MFE**"
        ]
        for cp in cps:
            vals = [
                r["timeline_mfe"].get(cp)
                for r in time_kill
                if r["timeline_mfe"].get(cp) is not None
            ]
            row_w.append(f"{mean(vals):+.4f}" if vals else "—")
        out.append("| " + " | ".join(row_w) + " |")
        row_w2 = ["**TIME_KILL avg MAE**"]
        for cp in cps:
            vals = [
                r["timeline_mae"].get(cp)
                for r in time_kill
                if r["timeline_mae"].get(cp) is not None
            ]
            row_w2.append(f"{mean(vals):+.4f}" if vals else "—")
        out.append("| " + " | ".join(row_w2) + " |")
        out.append("")

        # Trajectory diagnosis per trade
        out.append("Per-trade trajectory of TIME_KILL cluster:")
        out.append("")
        out.append("| case_id | side | phase | "
                   + " | ".join(f"MFE@{cp}" for cp in cps)
                   + " | trajectory |")
        out.append(
            "|---|---|---|" + "|".join(["---"] * (len(cps) + 1)) + "|"
        )
        for r in sorted(time_kill, key=lambda x: x["opened_at"]):
            row = [
                f"`{r['case_id'][:14]}`", r["side"], r["phase"]
            ]
            seq = []
            for cp in cps:
                v = r["timeline_mfe"].get(cp)
                row.append(f"{v:+.4f}" if v is not None else "—")
                if v is not None:
                    seq.append(v)
            traj = describe_trajectory(seq)
            row.append(traj)
            out.append("| " + " | ".join(row) + " |")
        out.append("")

        # Aggregate trajectory diagnosis
        traj_count: Counter = Counter()
        for r in time_kill:
            seq = [
                r["timeline_mfe"].get(cp)
                for cp in cps if r["timeline_mfe"].get(cp) is not None
            ]
            traj_count[describe_trajectory(seq)] += 1
        out.append("**TIME_KILL trajectory distribution:**")
        out.append("")
        for k, n in traj_count.most_common():
            out.append(
                f"- {k}: {n}/{len(time_kill)} "
                f"({n / len(time_kill) * 100:.1f}%)"
            )
        out.append("")

    # ----- 4. Decision signals --------------------------------------------
    out.append("## 4. Decision-ready signals")
    out.append("")
    if time_kill:
        avg_30 = mean(
            [r["timeline_mfe"].get(30, 0) for r in time_kill
             if r["timeline_mfe"].get(30) is not None]
        )
        out.append(
            f"- TIME_KILL avg MFE at **30 min** = **{avg_30:+.4f}%** "
        )
        out.append(
            "  - if << 0.30%  → TP=0.30% is unreachable in 30m window"
        )
        out.append(
            "  - if ≈ 0.30%   → just need a few extra minutes"
        )
        out.append(
            "  - if > 0.30%   → MFE was reached but TP was missed"
        )

    # ----- 5. By regime (sanity check) ------------------------------------
    by_reg: Dict[str, List[Dict]] = defaultdict(list)
    for r in records:
        by_reg[r["regime_at_entry"] or "UNKNOWN"].append(r)
    out.append("")
    out.append("## 5. By regime at entry (1m EMA20/50)")
    out.append("")
    out.append("| Regime | N | LONG | SHORT | Wins | WR | Avg PnL% |")
    out.append("|---|---|---|---|---|---|---|")
    for reg, rs in sorted(by_reg.items()):
        n = len(rs)
        nl = sum(1 for r in rs if r["side"] == "LONG")
        ns = sum(1 for r in rs if r["side"] == "SHORT")
        wins = sum(1 for r in rs if r["realized_pnl_pct"] > 0)
        wr = wins / n * 100 if n else 0
        avg_pnl = mean([r["realized_pnl_pct"] for r in rs]) if rs else 0
        out.append(
            f"| {reg} | {n} | {nl} | {ns} | {wins} | "
            f"{wr:.1f}% | {avg_pnl:+.4f} |"
        )
    out.append("")

    return "\n".join(out)


def describe_trajectory(seq: List[float]) -> str:
    """Classify an MFE timeline shape."""
    if len(seq) < 2:
        return "INSUFFICIENT_DATA"
    peak = max(seq)
    last = seq[-1]
    rising = all(seq[i] <= seq[i + 1] + 1e-9 for i in range(len(seq) - 1))
    if peak < 0.10:
        return "FLAT_NO_MOVE"           # market never gave us anything
    if rising and last >= peak * 0.95:
        return "RISING_LINEAR"          # would benefit from longer TIME
    if peak > 0.20 and last < peak * 0.6:
        return "PEAK_AND_DECAY"         # missed window, needs trailing
    if peak < 0.20:
        return "RISING_BUT_SHORT"       # 30m gives ≤0.20%, not enough
    return "MIXED"


# --------------------------------------------------------------------------
def main() -> int:
    db = get_db()
    print(f"[forensic-v2] DB={DB_NAME}")
    cases = fetch_real_closed_cases(db)
    print(f"[forensic-v2] real closed: {len(cases)}")
    records: List[Dict[str, Any]] = []
    for i, t in enumerate(cases, 1):
        try:
            r = analyse_trade(t)
        except Exception as e:
            print(f"[forensic-v2] error on {t.get('case_id')}: {e}")
            r = None
        if r is not None:
            records.append(r)
        if i % 10 == 0 or i == len(cases):
            print(f"[forensic-v2] {i}/{len(cases)} kept={len(records)}")

    with open(OUT_JSONL, "w") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")
    print(f"[forensic-v2] wrote {OUT_JSONL}")
    rep = render_report(records)
    with open(OUT_REPORT, "w") as f:
        f.write(rep)
    print(f"[forensic-v2] wrote {OUT_REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
