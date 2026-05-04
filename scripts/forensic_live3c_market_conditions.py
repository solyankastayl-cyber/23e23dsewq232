#!/usr/bin/env python3
"""
forensic_live3c_market_conditions.py — Phase LIVE-3c read-only forensic.

Goal (architect directive): find a real source of edge by slicing closed
trades along ORTHOGONAL market-condition dimensions, NOT direction.

Three independent buckets are emitted, never combined:

    1. VOLATILITY      — 20-bar std of returns on 1h candles before entry.
    2. DISTANCE_TO_MA  — |entry_price - MA(5)| / MA(5) on 1h candles.
                         (NOTE: SimpleMA strategy uses 1m MA(5) live; the
                          1m candle history is NOT persisted in this DB,
                          so this is a 1h-MA proxy. Honest caveat below.)
    3. TIME_IN_TRADE   — closed_at - opened_at (seconds).

For each bucket: N, wins, WR, Wilson 95% CI, avg/median PnL, flag.
Statistical guards (do not lie about the data):
    * Wilson CI for WR.
    * INSUFFICIENT label when N<min_n (default 10).
    * NO_CONCLUSION for the whole view if total N<20.

Read-only against MongoDB. Writes only:
    /tmp/forensic_live3c_report.md
    /tmp/forensic_live3c.jsonl

Usage:
    python3 /app/scripts/forensic_live3c_market_conditions.py
    python3 /app/scripts/forensic_live3c_market_conditions.py \
        --phase LIVE-2H --exclude-pause-artefacts
    python3 /app/scripts/forensic_live3c_market_conditions.py --min-n 5

The script does NOT touch any system component. It does NOT recommend gate
changes by itself. It only surfaces buckets that may carry signal — you
(architect) decide if N≥20 + non-overlapping CIs warrant a multiplier.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient

PAUSE_ARTEFACTS = {"case-3cbabe9b6d08", "case-e9c8f0d50298"}
DEFAULT_MIN_N = 10
DEFAULT_TOTAL_N = 20

# ---------------------------------------------------------------------------
# Bucket definitions (per architect spec)
# ---------------------------------------------------------------------------
# Volatility: stdev of pct returns over last 20 1h candles before entry.
#   LOW  < 0.0015 (0.15%)
#   MID  0.0015 – 0.003
#   HIGH > 0.003
VOL_BUCKETS: List[Tuple[float, float, str]] = [
    (-1e9, 0.0015, "LOW  (<0.15%)"),
    (0.0015, 0.0030, "MID  [0.15%-0.3%)"),
    (0.0030, 1e9, "HIGH (>=0.3%)"),
]

# Distance to MA(5) on 1h. |entry - ma5_1h| / ma5_1h.
#   <0.2% / 0.2-0.5% / >0.5%
DIST_BUCKETS: List[Tuple[float, float, str]] = [
    (-1e9, 0.002, "<0.2%"),
    (0.002, 0.005, "[0.2-0.5%)"),
    (0.005, 1e9, ">=0.5%"),
]

# Time-in-trade in seconds.
#   <10 min, 10-30 min, >30 min
TIME_BUCKETS: List[Tuple[float, float, str]] = [
    (-1, 600, "<10 min"),
    (600, 1800, "[10-30 min)"),
    (1800, 1e12, ">=30 min"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _bucket_label(value: Optional[float],
                  buckets: List[Tuple[float, float, str]]) -> str:
    if value is None:
        return "UNKNOWN"
    for lo, hi, label in buckets:
        if lo <= value < hi:
            return label
    return buckets[-1][2]


def _wilson_interval(wins: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (centre - margin) / denom),
            min(1.0, (centre + margin) / denom))


def _to_dt(value: Any) -> Optional[datetime]:
    """Best-effort coerce of mixed timestamp shapes (ISO string, BSON datetime)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Data load
# ---------------------------------------------------------------------------
def _load_closed_cases(
    db, strategy: Optional[str], exclude_artefacts: bool
) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {"status": "CLOSED", "realized_pnl_pct": {"$ne": None}}
    if strategy:
        q["strategy"] = strategy
    if exclude_artefacts:
        q["case_id"] = {"$nin": list(PAUSE_ARTEFACTS)}
    proj = {
        "_id": 0,
        "case_id": 1, "side": 1, "strategy": 1, "symbol": 1,
        "opened_at": 1, "closed_at": 1, "entry_price": 1,
        "realized_pnl_pct": 1, "decision_id": 1,
    }
    return list(db["trading_cases"].find(q, proj).sort("opened_at", 1))


def _load_phase_map(db, case_ids: List[str]) -> Dict[str, str]:
    if not case_ids:
        return {}

    def _derive(reason: Optional[str], fallback: Optional[str]) -> str:
        r = (reason or "").upper()
        if r.startswith("LIVE2H"):
            return "LIVE-2H"
        if r.startswith("LIVE2D"):
            return "LIVE-2D"
        if r.startswith("LIVE2_"):
            return "LIVE-2"
        return fallback or "UNKNOWN"

    out: Dict[str, str] = {}
    cur = db["position_exit_events"].find(
        {"case_id": {"$in": case_ids}, "event": "POSITION_CLOSED"},
        {"_id": 0, "case_id": 1, "phase": 1, "closed_at": 1, "close_reason": 1},
    ).sort("closed_at", -1)
    for ev in cur:
        cid = ev.get("case_id")
        if cid and cid not in out:
            out[cid] = _derive(ev.get("close_reason"), ev.get("phase"))
    return out


def _load_btc_1h_closes(db) -> List[Tuple[datetime, float]]:
    """Return chronologically sorted [(ts, close)] for BTCUSDT 1h candles."""
    cur = db["candles"].find(
        {"symbol": "BTCUSDT", "timeframe": "1h"},
        {"_id": 0, "timestamp": 1, "close": 1},
    )
    rows: List[Tuple[datetime, float]] = []
    for c in cur:
        ts = _to_dt(c.get("timestamp"))
        close = c.get("close")
        if ts is None or close is None:
            continue
        try:
            rows.append((ts, float(close)))
        except (TypeError, ValueError):
            continue
    rows.sort(key=lambda x: x[0])
    return rows


# ---------------------------------------------------------------------------
# Market-condition computation
# ---------------------------------------------------------------------------
def _slice_pre_entry(
    closes: List[Tuple[datetime, float]],
    opened_at: datetime,
    n: int = 20,
) -> List[float]:
    """Return up to N most-recent closes strictly before opened_at."""
    pre = [c for ts, c in closes if ts < opened_at]
    return pre[-n:]


def _volatility(returns: List[float]) -> Optional[float]:
    if len(returns) < 5:
        return None
    try:
        return statistics.pstdev(returns)
    except statistics.StatisticsError:
        return None


def _compute_metrics(
    case: Dict[str, Any],
    closes: List[Tuple[datetime, float]],
) -> Dict[str, Any]:
    """Read-only feature derivation per case."""
    opened = _to_dt(case.get("opened_at"))
    closed = _to_dt(case.get("closed_at"))
    entry = case.get("entry_price")
    metrics: Dict[str, Any] = {
        "volatility_1h_20": None,
        "ma5_1h": None,
        "distance_to_ma5_1h": None,
        "time_in_trade_sec": None,
        "candles_used": 0,
    }
    if entry is not None:
        try:
            entry_f = float(entry)
        except (TypeError, ValueError):
            entry_f = None
        if entry_f and opened:
            window = _slice_pre_entry(closes, opened, n=20)
            metrics["candles_used"] = len(window)
            if len(window) >= 6:
                rets = [
                    (window[i] - window[i - 1]) / window[i - 1]
                    for i in range(1, len(window))
                    if window[i - 1]
                ]
                metrics["volatility_1h_20"] = _volatility(rets)
            if len(window) >= 5:
                ma5 = sum(window[-5:]) / 5.0
                metrics["ma5_1h"] = ma5
                if ma5:
                    metrics["distance_to_ma5_1h"] = abs(entry_f - ma5) / ma5
    if opened and closed:
        delta = (closed - opened).total_seconds()
        if delta >= 0:
            metrics["time_in_trade_sec"] = delta
    return metrics


# ---------------------------------------------------------------------------
# Bucket aggregation (single-dimension, per architect rule)
# ---------------------------------------------------------------------------
def _aggregate(
    rows: List[Dict[str, Any]],
    field: str,
    buckets: List[Tuple[float, float, str]],
    min_n: int,
) -> List[Dict[str, Any]]:
    by_label: Dict[str, List[Dict[str, Any]]] = {b[2]: [] for b in buckets}
    by_label["UNKNOWN"] = []
    for r in rows:
        label = _bucket_label(r.get(field), buckets)
        by_label.setdefault(label, []).append(r)

    summaries = []
    for _, _, label in buckets:
        members = by_label.get(label, [])
        n = len(members)
        if n == 0:
            summaries.append({
                "bucket": label, "n": 0, "wins": 0, "wr": None,
                "wr_ci_lo": None, "wr_ci_hi": None,
                "avg_pnl": None, "median_pnl": None, "sum_pnl": None,
                "long_n": 0, "short_n": 0, "insufficient": True,
                "value_min": None, "value_max": None,
            })
            continue
        pnls = [r["realized_pnl_pct"] for r in members]
        vals = [r.get(field) for r in members if r.get(field) is not None]
        wins = sum(1 for p in pnls if p > 0)
        long_n = sum(1 for r in members
                     if r["side"].upper() in ("LONG", "BUY"))
        short_n = sum(1 for r in members
                      if r["side"].upper() in ("SHORT", "SELL"))
        wr = wins / n
        ci_lo, ci_hi = _wilson_interval(wins, n)
        summaries.append({
            "bucket": label,
            "n": n, "wins": wins, "wr": round(wr, 4),
            "wr_ci_lo": round(ci_lo, 4), "wr_ci_hi": round(ci_hi, 4),
            "avg_pnl": round(statistics.mean(pnls), 4),
            "median_pnl": round(statistics.median(pnls), 4),
            "sum_pnl": round(sum(pnls), 4),
            "long_n": long_n, "short_n": short_n,
            "insufficient": n < min_n,
            "value_min": min(vals) if vals else None,
            "value_max": max(vals) if vals else None,
        })

    unk = by_label.get("UNKNOWN", [])
    if unk:
        n = len(unk)
        pnls = [r["realized_pnl_pct"] for r in unk]
        wins = sum(1 for p in pnls if p > 0)
        ci_lo, ci_hi = _wilson_interval(wins, n)
        summaries.append({
            "bucket": "UNKNOWN", "n": n, "wins": wins,
            "wr": round(wins / n, 4),
            "wr_ci_lo": round(ci_lo, 4), "wr_ci_hi": round(ci_hi, 4),
            "avg_pnl": round(statistics.mean(pnls), 4),
            "median_pnl": round(statistics.median(pnls), 4),
            "sum_pnl": round(sum(pnls), 4),
            "long_n": sum(1 for r in unk
                          if r["side"].upper() in ("LONG", "BUY")),
            "short_n": sum(1 for r in unk
                           if r["side"].upper() in ("SHORT", "SELL")),
            "insufficient": True,
            "value_min": None, "value_max": None,
        })
    return summaries


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def _fmt_pnl(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:+.4f}%"


def _fmt_value(field: str, value: Optional[float]) -> str:
    if value is None:
        return "—"
    if field == "volatility_1h_20":
        return f"{value * 100:.3f}%"
    if field == "distance_to_ma5_1h":
        return f"{value * 100:.3f}%"
    if field == "time_in_trade_sec":
        m = value / 60.0
        if m < 60:
            return f"{m:.1f}m"
        return f"{m / 60.0:.2f}h"
    return f"{value:.4f}"


def _bucket_table(field: str, title: str,
                  summary: List[Dict[str, Any]],
                  total_n: int, min_total: int) -> str:
    lines = [f"### {title}",
             f"_field={field}; total N={total_n}_"]
    if total_n < min_total:
        lines.append(
            f"\n> ⚠ NO_CONCLUSION: total N={total_n} < {min_total}. "
            "Numbers descriptive only."
        )
    lines.append("")
    lines.append(
        "| bucket            | N  | LONG | SHORT | WR     | WR 95% CI         "
        "| range             | avg PnL    | median PnL | flag         |"
    )
    lines.append(
        "|-------------------|----|------|-------|--------|-------------------"
        "|-------------------|------------|------------|--------------|"
    )
    for b in summary:
        if b["n"] == 0:
            lines.append(
                f"| {b['bucket']:<17} |  0 |   0  |   0   | —      | —"
                f"                | —                 | —          | —          | EMPTY        |"
            )
            continue
        flag = "INSUFFICIENT" if b["insufficient"] else "ok"
        rng = "—"
        if b["value_min"] is not None and b["value_max"] is not None:
            rng = (
                f"[{_fmt_value(field, b['value_min'])}, "
                f"{_fmt_value(field, b['value_max'])}]"
            )
        lines.append(
            f"| {b['bucket']:<17} | {b['n']:>2} | {b['long_n']:>4} | "
            f"{b['short_n']:>5} | {b['wr'] * 100:5.1f}% | "
            f"[{b['wr_ci_lo'] * 100:5.1f}, {b['wr_ci_hi'] * 100:5.1f}] | "
            f"{rng:<17} | {_fmt_pnl(b['avg_pnl'])} | "
            f"{_fmt_pnl(b['median_pnl'])} | {flag:<12} |"
        )
    return "\n".join(lines)


def _digest(field: str, title: str, summary: List[Dict[str, Any]]) -> str:
    lines = [f"--- {title} ---"]
    for b in summary:
        if b["n"] == 0:
            continue
        flag = "INSUFFICIENT" if b["insufficient"] else "ok"
        rng = (
            f"[{_fmt_value(field, b['value_min'])}, "
            f"{_fmt_value(field, b['value_max'])}]"
            if b["value_min"] is not None else "—"
        )
        lines.append(
            f"  {b['bucket']:<18} N={b['n']:<2} L={b['long_n']:<2} "
            f"S={b['short_n']:<2}  WR={b['wr'] * 100:5.1f}%  "
            f"CI=[{b['wr_ci_lo'] * 100:5.1f},{b['wr_ci_hi'] * 100:5.1f}]  "
            f"avg={b['avg_pnl']:+.4f}%  med={b['median_pnl']:+.4f}%  "
            f"rng={rng}  [{flag}]"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", default="SIMPLE_MA")
    parser.add_argument("--phase", default=None)
    parser.add_argument("--exclude-pause-artefacts", action="store_true")
    parser.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    parser.add_argument("--min-total-n", type=int, default=DEFAULT_TOTAL_N)
    args = parser.parse_args()

    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "trading_os")
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)
    db = client[db_name]

    print(f"[forensic-live3c] DB={db_name}")

    cases = _load_closed_cases(db, args.strategy, args.exclude_pause_artefacts)
    print(f"[forensic-live3c] loaded {len(cases)} closed cases "
          f"(strategy={args.strategy})")

    phase_map = _load_phase_map(db, [c["case_id"] for c in cases])
    for c in cases:
        c["phase"] = phase_map.get(c["case_id"])
    if args.phase:
        cases = [c for c in cases if c.get("phase") == args.phase]
        print(f"[forensic-live3c] after phase filter '{args.phase}': "
              f"N={len(cases)}")

    closes = _load_btc_1h_closes(db)
    print(f"[forensic-live3c] BTCUSDT 1h closes: {len(closes)}")

    rows: List[Dict[str, Any]] = []
    for c in cases:
        m = _compute_metrics(c, closes)
        row = {
            "case_id": c["case_id"], "side": c["side"], "phase": c.get("phase"),
            "opened_at": str(c.get("opened_at")),
            "closed_at": str(c.get("closed_at")),
            "entry_price": c.get("entry_price"),
            "realized_pnl_pct": c["realized_pnl_pct"],
            **m,
        }
        rows.append(row)

    out_jsonl = "/tmp/forensic_live3c.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=str) + "\n")

    # Per-dimension aggregates (independent, per architect rule).
    vol_summary = _aggregate(rows, "volatility_1h_20", VOL_BUCKETS, args.min_n)
    dist_summary = _aggregate(rows, "distance_to_ma5_1h", DIST_BUCKETS,
                              args.min_n)
    time_summary = _aggregate(rows, "time_in_trade_sec", TIME_BUCKETS,
                              args.min_n)

    # Build markdown report.
    now = datetime.now(timezone.utc).isoformat()
    parts: List[str] = []
    parts.append(
        f"# LIVE-3c — Market-Condition Forensic\n\n"
        f"_generated {now}; strategy={args.strategy}; "
        f"phase_filter={args.phase or 'ALL'}; "
        f"exclude_pause_artefacts={args.exclude_pause_artefacts}; "
        f"min_bucket_n={args.min_n}; min_total_n={args.min_total_n}_\n"
    )
    parts.append(
        "## Honest caveats\n"
        "- **1m candle history is NOT persisted** in this DB. SimpleMA runs "
        "live on 1m prices, but only 1h candles are stored. Volatility and "
        "distance-to-MA are therefore computed on **1h** data, which is a "
        "*market-condition* proxy, not a strict re-creation of what SimpleMA "
        "saw at entry.\n"
        "- Time-in-trade is exact (closed_at - opened_at).\n"
        "- Each dimension is reported INDEPENDENTLY. Combinations are NOT "
        "explored here — searching combinations on N=25 is unsafe.\n"
        "- This script does NOT recommend any gate or multiplier change. "
        "It surfaces buckets only.\n"
    )

    parts.append(
        _bucket_table(
            "volatility_1h_20",
            "1) VOLATILITY (1h × 20-bar stdev of pct returns, pre-entry)",
            vol_summary, len(rows), args.min_total_n,
        )
    )
    parts.append("")
    parts.append(
        _bucket_table(
            "distance_to_ma5_1h",
            "2) DISTANCE_TO_MA (|entry - MA(5,1h)| / MA, 1h-proxy)",
            dist_summary, len(rows), args.min_total_n,
        )
    )
    parts.append("")
    parts.append(
        _bucket_table(
            "time_in_trade_sec",
            "3) TIME_IN_TRADE (closed_at - opened_at, seconds)",
            time_summary, len(rows), args.min_total_n,
        )
    )

    parts.append(
        "\n## How to read\n"
        "- A bucket is a **candidate edge** when: N ≥ min_n AND its WR is "
        "≥10pp away from another bucket's WR AND Wilson 95% CIs do NOT "
        "overlap.\n"
        "- Soft signal: monotonic improvement across buckets even with "
        "overlapping CIs (warrants more N before acting).\n"
        "- No signal: WR/avg_pnl roughly flat across buckets.\n"
        "- ANY conclusion requires total N ≥ min_total_n (default 20). "
        "Below that, treat as descriptive only.\n"
    )

    out_md = "/tmp/forensic_live3c_report.md"
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))

    # Stdout digest.
    print()
    print("=" * 78)
    print("LIVE-3c MARKET-CONDITION FORENSIC — digest")
    print("=" * 78)
    print(
        f"strategy={args.strategy} phase={args.phase or 'ALL'} "
        f"exclude_artefacts={args.exclude_pause_artefacts} "
        f"min_n={args.min_n} min_total_n={args.min_total_n}"
    )
    print(f"rows={len(rows)} (BTC 1h candles loaded={len(closes)})")
    print()
    print(_digest("volatility_1h_20",
                  "VOLATILITY (1h × 20-bar stdev pre-entry)", vol_summary))
    print()
    print(_digest("distance_to_ma5_1h",
                  "DISTANCE_TO_MA (1h-MA(5) proxy)", dist_summary))
    print()
    print(_digest("time_in_trade_sec",
                  "TIME_IN_TRADE", time_summary))
    print()
    print(f"report  → {out_md}")
    print(f"per-trade → {out_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
