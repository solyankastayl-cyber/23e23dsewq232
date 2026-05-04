#!/usr/bin/env python3
"""
monitor_live3d_gate.py — read-only post-activation monitor for LIVE-3d.

Reports the three metrics the architect asked to watch after enabling
volatility_low_skip_enabled:

    1. SKIP RATE — vol_gate_events / total_signal_attempts
       (sweet spot 20–40%; <10% = too soft, >60% = too aggressive)

    2. WHAT IS SKIPPED — distribution of skipped signals by side, regime,
       and volatility value. Sanity check: are we cutting LOW vol only,
       not random signals?

    3. SURVIVING TRADE BEHAVIOUR — for execution_jobs admitted AFTER
       activation, joined to trading_cases via decision_id: avg PnL,
       WR, time-in-trade. Compared against pre-activation baseline.

Activation timestamp is read from
    regime_controls.confidence_adjustment.volatility_low_skip_enabled_at
so the script self-determines the observation window.

Read-only against MongoDB. Output: stdout digest + /tmp/live3d_monitor.md.

Usage:
    python3 /app/scripts/monitor_live3d_gate.py
    python3 /app/scripts/monitor_live3d_gate.py --since 2026-05-02T22:14:49Z
"""
from __future__ import annotations

import argparse
import math
import os
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient


def _wilson(wins: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (centre - margin) / denom),
            min(1.0, (centre + margin) / denom))


def _to_dt(value: Any) -> Optional[datetime]:
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


def _resolve_activation_ts(db, override: Optional[str]) -> datetime:
    if override:
        ts = _to_dt(override)
        if ts:
            return ts
    doc = db["regime_controls"].find_one({"control": "confidence_adjustment"}) or {}
    ts = _to_dt(doc.get("volatility_low_skip_enabled_at"))
    if ts:
        return ts
    # Fallback: use 1h ago if not set
    return datetime.now(timezone.utc).replace(microsecond=0)


def _bin_volatility(value: Optional[float]) -> str:
    if value is None:
        return "UNKNOWN"
    if value < 0.0015:
        return "LOW (<0.15%)"
    if value < 0.0030:
        return "MID [0.15%-0.3%)"
    return "HIGH (>=0.3%)"


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
def _count_total_attempts(db, since: datetime) -> Dict[str, int]:
    """All signal-attempt outcomes since activation."""
    enq = db["execution_jobs"].count_documents(
        {"createdAt": {"$gte": since}, "payload.strategy": "SIMPLE_MA"}
    )
    if enq == 0:  # legacy schema — try without filter then look at recent
        enq = db["execution_jobs"].count_documents({"createdAt": {"$gte": since}})
    vol_skip = db["vol_gate_events"].count_documents({"timestamp": {"$gte": since}})
    conf_skip = db["conf_gate_events"].count_documents({"timestamp": {"$gte": since}})
    regime_skip = db["regime_guard_events"].count_documents(
        {"timestamp": {"$gte": since}}
    )
    return {
        "enqueued_signals": enq,
        "vol_gate_skip": vol_skip,
        "conf_gate_skip": conf_skip,
        "regime_gate_skip": regime_skip,
        "total_attempts": enq + vol_skip + conf_skip + regime_skip,
    }


def _vol_gate_breakdown(db, since: datetime) -> Dict[str, Any]:
    cur = db["vol_gate_events"].find(
        {"timestamp": {"$gte": since}, "phase": "LIVE-3d"},
        {"_id": 0, "side": 1, "volatility_1h_20": 1, "ma5_1h": 1,
         "distance_to_ma5_1h": 1, "symbol": 1, "timestamp": 1},
    )
    rows = list(cur)
    by_side: Dict[str, int] = {}
    by_symbol: Dict[str, int] = {}
    vol_values: List[float] = []
    for r in rows:
        s = (r.get("side") or "UNKNOWN").upper()
        by_side[s] = by_side.get(s, 0) + 1
        sym = r.get("symbol") or "UNKNOWN"
        by_symbol[sym] = by_symbol.get(sym, 0) + 1
        v = r.get("volatility_1h_20")
        if v is not None:
            vol_values.append(float(v))
    return {
        "total": len(rows),
        "by_side": by_side,
        "by_symbol": by_symbol,
        "vol_stats": {
            "min": round(min(vol_values), 6) if vol_values else None,
            "max": round(max(vol_values), 6) if vol_values else None,
            "mean": round(statistics.mean(vol_values), 6) if vol_values else None,
            "median": round(statistics.median(vol_values), 6) if vol_values else None,
            "all_below_0_0015": all(v < 0.0015 for v in vol_values) if vol_values else None,
        },
        "samples": rows[:5],
    }


def _surviving_trades_metrics(db, since: datetime) -> Dict[str, Any]:
    """Trades admitted after activation: link execution_jobs.decision_id ↔
    trading_cases.decision_id. Compute pnl/WR/time-in-trade on closed ones.
    """
    jobs = list(db["execution_jobs"].find(
        {
            "createdAt": {"$gte": since},
            "payload.adjusted_confidence": {"$exists": True},
        },
        {"_id": 0, "payload.decision_id": 1,
         "payload.adjusted_confidence": 1,
         "payload.volatility_1h_20": 1,
         "payload.regime_at_entry": 1,
         "payload.side": 1,
         "createdAt": 1, "status": 1},
    ))
    decision_ids = [
        (j.get("payload") or {}).get("decision_id")
        for j in jobs
        if (j.get("payload") or {}).get("decision_id")
    ]
    cases = []
    if decision_ids:
        cases = list(db["trading_cases"].find(
            {"decision_id": {"$in": decision_ids}, "status": "CLOSED",
             "realized_pnl_pct": {"$ne": None}},
            {"_id": 0, "case_id": 1, "decision_id": 1, "side": 1,
             "opened_at": 1, "closed_at": 1, "realized_pnl_pct": 1},
        ))
    summary: Dict[str, Any] = {
        "post_activation_jobs": len(jobs),
        "post_activation_jobs_with_market_ctx": sum(
            1 for j in jobs
            if (j.get("payload") or {}).get("volatility_1h_20") is not None
        ),
        "post_activation_closed_trades": len(cases),
        "by_status": {},
        "metrics": {},
    }
    for j in jobs:
        st = j.get("status") or "unknown"
        summary["by_status"][st] = summary["by_status"].get(st, 0) + 1
    if cases:
        pnls = [c["realized_pnl_pct"] for c in cases]
        wins = sum(1 for p in pnls if p > 0)
        ci_lo, ci_hi = _wilson(wins, len(cases))
        ttts = []
        for c in cases:
            o = _to_dt(c.get("opened_at"))
            cl = _to_dt(c.get("closed_at"))
            if o and cl:
                ttts.append((cl - o).total_seconds())
        summary["metrics"] = {
            "n_closed": len(cases),
            "wins": wins,
            "wr": round(wins / len(cases), 4),
            "wr_ci": [round(ci_lo, 4), round(ci_hi, 4)],
            "avg_pnl": round(statistics.mean(pnls), 4),
            "median_pnl": round(statistics.median(pnls), 4),
            "sum_pnl": round(sum(pnls), 4),
            "avg_time_in_trade_sec": round(statistics.mean(ttts), 1) if ttts else None,
            "median_time_in_trade_sec": round(statistics.median(ttts), 1) if ttts else None,
        }
    return summary


def _baseline_metrics(db, until: datetime) -> Dict[str, Any]:
    """Pre-activation baseline: closed SIMPLE_MA trades opened before since."""
    cases = list(db["trading_cases"].find(
        {"status": "CLOSED", "strategy": "SIMPLE_MA",
         "realized_pnl_pct": {"$ne": None},
         "opened_at": {"$lt": until}},
        {"_id": 0, "case_id": 1, "side": 1, "opened_at": 1, "closed_at": 1,
         "realized_pnl_pct": 1},
    ))
    if not cases:
        return {"n_closed": 0}
    pnls = [c["realized_pnl_pct"] for c in cases]
    wins = sum(1 for p in pnls if p > 0)
    ci_lo, ci_hi = _wilson(wins, len(cases))
    ttts = []
    for c in cases:
        o = _to_dt(c.get("opened_at"))
        cl = _to_dt(c.get("closed_at"))
        if o and cl:
            ttts.append((cl - o).total_seconds())
    return {
        "n_closed": len(cases),
        "wins": wins,
        "wr": round(wins / len(cases), 4),
        "wr_ci": [round(ci_lo, 4), round(ci_hi, 4)],
        "avg_pnl": round(statistics.mean(pnls), 4),
        "median_pnl": round(statistics.median(pnls), 4),
        "sum_pnl": round(sum(pnls), 4),
        "avg_time_in_trade_sec": round(statistics.mean(ttts), 1) if ttts else None,
        "median_time_in_trade_sec": round(statistics.median(ttts), 1) if ttts else None,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def _classify_skip_rate(rate: Optional[float]) -> str:
    if rate is None:
        return "no signal yet"
    if rate < 0.10:
        return "TOO SOFT (<10%)"
    if rate <= 0.40:
        return "SWEET SPOT (10–40%)"
    if rate <= 0.60:
        return "AGGRESSIVE (40–60%)"
    return "TOO AGGRESSIVE (>60%)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", default=None,
                    help="ISO timestamp override (default: read from controls)")
    ap.add_argument("--symbol", default=None,
                    help="filter (currently informational only)")
    args = ap.parse_args()

    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "trading_os")
    db = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)[db_name]

    activated_at = _resolve_activation_ts(db, args.since)
    now = datetime.now(timezone.utc)
    elapsed_min = (now - activated_at).total_seconds() / 60.0

    counts = _count_total_attempts(db, activated_at)
    skip_rate = (
        counts["vol_gate_skip"] / counts["total_attempts"]
        if counts["total_attempts"] else None
    )

    breakdown = _vol_gate_breakdown(db, activated_at)
    surviving = _surviving_trades_metrics(db, activated_at)
    baseline = _baseline_metrics(db, activated_at)

    # ---------- stdout digest ----------
    print("=" * 78)
    print("LIVE-3d GATE MONITOR  —  digest")
    print("=" * 78)
    print(f"activation_ts: {activated_at.isoformat()}")
    print(f"now:           {now.isoformat()}")
    print(f"elapsed:       {elapsed_min:.1f} minutes "
          f"({elapsed_min / 60.0:.1f} hours)")
    print()

    print("--- 1) SKIP RATE ---")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    if skip_rate is not None:
        print(f"  SKIP_RATE = vol_gate_skip / total_attempts = "
              f"{skip_rate * 100:.1f}%  →  [{_classify_skip_rate(skip_rate)}]")
    else:
        print("  SKIP_RATE = n/a (no attempts yet)")
    print()

    print("--- 2) WHAT IS SKIPPED ---")
    print(f"  vol_gate_events total: {breakdown['total']}")
    if breakdown["total"] > 0:
        print(f"  by_side: {breakdown['by_side']}")
        print(f"  by_symbol: {breakdown['by_symbol']}")
        vs = breakdown["vol_stats"]
        print(f"  vol stats: min={vs['min']} median={vs['median']} "
              f"max={vs['max']} mean={vs['mean']}")
        all_below = vs.get("all_below_0_0015")
        sanity = "✓ all below 0.0015 (correct)" if all_below \
            else "⚠ NOT all below 0.0015 (gate misfire?)"
        print(f"  sanity check: {sanity}")
    print()

    print("--- 3) SURVIVING TRADES ---")
    print(f"  post_activation_jobs: {surviving['post_activation_jobs']}")
    print(f"  jobs_with_market_ctx: {surviving['post_activation_jobs_with_market_ctx']}")
    print(f"  by_status: {surviving['by_status']}")
    print(f"  closed_trades: {surviving['post_activation_closed_trades']}")
    if surviving["metrics"]:
        m = surviving["metrics"]
        print(
            f"  POST  N={m['n_closed']:<2}  WR={m['wr'] * 100:5.1f}%  "
            f"CI=[{m['wr_ci'][0] * 100:.1f},{m['wr_ci'][1] * 100:.1f}]  "
            f"avg_pnl={m['avg_pnl']:+.4f}%  median_pnl={m['median_pnl']:+.4f}%  "
            f"avg_ttt={m['avg_time_in_trade_sec']}s"
        )
    if baseline.get("n_closed"):
        b = baseline
        print(
            f"  BASE  N={b['n_closed']:<2}  WR={b['wr'] * 100:5.1f}%  "
            f"CI=[{b['wr_ci'][0] * 100:.1f},{b['wr_ci'][1] * 100:.1f}]  "
            f"avg_pnl={b['avg_pnl']:+.4f}%  median_pnl={b['median_pnl']:+.4f}%  "
            f"avg_ttt={b['avg_time_in_trade_sec']}s"
        )
        if surviving["metrics"]:
            m = surviving["metrics"]
            wr_diff = (m["wr"] - b["wr"]) * 100
            pnl_diff = m["avg_pnl"] - b["avg_pnl"]
            print(
                f"  Δ      WR={wr_diff:+.1f}pp  avg_pnl_diff={pnl_diff:+.4f}%"
            )
    print()

    # ---------- markdown report ----------
    md_lines = [
        "# LIVE-3d Gate Monitor\n",
        f"_generated {now.isoformat()}_  ",
        f"_activation_ts {activated_at.isoformat()}_  ",
        f"_elapsed {elapsed_min:.1f} minutes_\n",
        "## 1) Skip rate",
        f"- enqueued_signals: **{counts['enqueued_signals']}**",
        f"- vol_gate_skip: **{counts['vol_gate_skip']}**",
        f"- conf_gate_skip: {counts['conf_gate_skip']}",
        f"- regime_gate_skip: {counts['regime_gate_skip']}",
        f"- total_attempts: {counts['total_attempts']}",
        f"- **skip_rate = "
        f"{(skip_rate * 100):.1f}%**  → "
        f"[{_classify_skip_rate(skip_rate)}]" if skip_rate is not None
        else "- skip_rate: n/a",
        "",
        "## 2) What is skipped",
        f"- total: {breakdown['total']}",
        f"- by_side: {breakdown['by_side']}",
        f"- by_symbol: {breakdown['by_symbol']}",
        f"- vol stats: {breakdown['vol_stats']}",
        "",
        "## 3) Surviving trades vs baseline",
    ]
    if baseline.get("n_closed"):
        md_lines.append(
            f"- BASELINE (pre-activation): N={baseline['n_closed']}, "
            f"WR={baseline['wr'] * 100:.1f}%, avg_pnl={baseline['avg_pnl']:+.4f}%"
        )
    if surviving["metrics"]:
        m = surviving["metrics"]
        md_lines.append(
            f"- POST-ACTIVATION: N={m['n_closed']}, "
            f"WR={m['wr'] * 100:.1f}%, avg_pnl={m['avg_pnl']:+.4f}%"
        )
    else:
        md_lines.append("- POST-ACTIVATION: no closed trades yet")

    out_md = "/tmp/live3d_monitor.md"
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md_lines))
    print(f"report → {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
