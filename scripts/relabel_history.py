#!/usr/bin/env python3
"""
relabel_history.py — Dry-run re-evaluation of `ta_prediction_history`
outcomes after FIX-RESOLVER-1+2.

What this does (read-only by default):
  1. Load every record with evaluation_state == 'evaluated'.
  2. For each, fetch the SAME future_candles the worker would have used:
     same `candles` collection, same _locate_entry_idx logic, same
     MIN_HORIZON_CANDLES horizon. No approximation.
  3. Run the NEW (FIX-RESOLVER-1+2) resolver and capture both:
       new_label  — what the production resolver returns
       reason     — which branch of the resolver fired
                    {bull_target, bear_target, within_bar_tie,
                     dual_invalidation, fallback_return_h6,
                     fallback_no_data, no_targets_no_h6}
  4. Sanity check: a debug copy of the resolver runs in parallel and
     MUST return the same label as the production resolver. If they ever
     diverge, the script aborts (the debug copy is wrong).
  5. Print:
       a) OLD vs NEW class distribution
       b) Changed-records table (only diffs)
       c) Reason histogram (which fix actually moved labels)
       d) Per-(symbol, tf) breakdown
       e) 10 sample diffs

Writes to Mongo only when --apply is passed.

Usage:
    python3 /app/scripts/relabel_history.py             # dry-run
    python3 /app/scripts/relabel_history.py --apply     # write outcome
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, "/app/backend")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "trading_os")

from pymongo import MongoClient  # noqa: E402

from modules.ta_prediction_intelligence.evaluation.ta_prediction_outcome_worker import (  # noqa: E402
    DIR_THRESHOLD_PCT,
    MIN_HORIZON_CANDLES,
    _candle_field,
    _locate_entry_idx,
    _safe_float,
    evaluate_prediction_with_candles,
    resolve_winning_scenario,
)


# ---------------------------------------------------------------------------
# Debug resolver — same logic as production v2, but returns a reason tag.
#
# This is a paper trail. Production runtime uses resolve_winning_scenario.
# We assert label equality at every record to guarantee we did not drift.
# ---------------------------------------------------------------------------
def resolver_with_reason(
    entry_price: float,
    scenarios: List[Dict[str, Any]],
    future_candles: List[Dict[str, Any]],
    return_h6: Optional[float],
    *,
    dir_threshold_pct: float = DIR_THRESHOLD_PCT,
) -> Tuple[str, str]:
    if entry_price is None or entry_price <= 0 or not future_candles:
        return ("base", "fallback_no_data")

    scen_by_name = {
        str(s.get("name") or "").lower(): s for s in (scenarios or [])
    }
    bull = scen_by_name.get("bull") or {}
    bear = scen_by_name.get("bear") or {}

    t_bull = _safe_float(bull.get("target_price"), 0.0) or None
    inv_bull = _safe_float(bull.get("invalidation_price"), 0.0) or None
    t_bear = _safe_float(bear.get("target_price"), 0.0) or None
    inv_bear = _safe_float(bear.get("invalidation_price"), 0.0) or None

    has_targets = any(v is not None for v in (t_bull, t_bear, inv_bull, inv_bear))
    if has_targets:
        bull_dead = False
        bear_dead = False
        for c in future_candles:
            hi = _candle_field(c, "high")
            lo = _candle_field(c, "low")

            bull_target_hit = (
                t_bull is not None and hi is not None and hi >= t_bull
            )
            bear_target_hit = (
                t_bear is not None and lo is not None and lo <= t_bear
            )
            if bull_target_hit and bear_target_hit:
                return ("base", "within_bar_tie")
            if bull_target_hit:
                return ("bull", "bull_target")
            if bear_target_hit:
                return ("bear", "bear_target")
            if (not bull_dead and inv_bull is not None
                    and lo is not None and lo <= inv_bull):
                bull_dead = True
            if (not bear_dead and inv_bear is not None
                    and hi is not None and hi >= inv_bear):
                bear_dead = True
            if bull_dead and bear_dead:
                return ("base", "dual_invalidation")

    # No resolution within horizon → return_h6 fallback (intentionally
    # untouched by FIX-RESOLVER-1+2; will be revisited as Bug #3).
    if return_h6 is None:
        return ("base", "fallback_no_data")
    thr = abs(dir_threshold_pct)
    if return_h6 > thr:
        return ("bull", "fallback_return_h6")
    if return_h6 < -thr:
        return ("bear", "fallback_return_h6")
    return ("base", "no_targets_no_h6" if not has_targets else "fallback_return_h6")


# ---------------------------------------------------------------------------
# Mongo helpers
# ---------------------------------------------------------------------------
def get_db():
    return MongoClient(
        os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
        serverSelectionTimeoutMS=5000,
    )[os.environ.get("DB_NAME", "trading_os")]


def load_evaluated_records(db) -> List[Dict[str, Any]]:
    cur = db.ta_prediction_history.find(
        {"evaluation_state": "evaluated", "outcome": {"$ne": None}},
        {
            "_id": 1, "prediction_id": 1, "symbol": 1, "timeframe": 1,
            "entry_price": 1, "candle_close_ts": 1,
            "scenarios_interaction_adjusted": 1, "scenarios_original": 1,
            "outcome": 1,
        },
    )
    return list(cur)


def load_candles(db, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
    """Pull all candles for (symbol, tf) sorted ascending by timestamp.

    The worker uses chart_data_service which is backed by this same
    `candles` collection in this environment, so this is the canonical
    source for replaying the evaluation.

    timeframe matching is case-insensitive: history records store '1H'
    but the candles collection stores '1h'. We try both, take whatever
    has data.
    """
    tf_variants = [timeframe, timeframe.lower(), timeframe.upper()]
    seen = set()
    tf_variants = [t for t in tf_variants if not (t in seen or seen.add(t))]
    for tf_try in tf_variants:
        cur = db.candles.find(
            {"symbol": symbol, "timeframe": tf_try},
            {"_id": 0, "timestamp": 1, "open": 1, "high": 1, "low": 1, "close": 1},
        ).sort("timestamp", 1)
        rows = list(cur)
        if rows:
            return rows
    return []


# ---------------------------------------------------------------------------
# Per-record processing
# ---------------------------------------------------------------------------
def _candle_close_ts_of_index(
    candles: List[Dict[str, Any]], idx: int, timeframe: str,
) -> Optional[int]:
    """Helper: replicate close_ts of the candle at idx, for diagnostics."""
    if idx < 0 or idx >= len(candles):
        return None
    try:
        from modules.ta_prediction_intelligence.live_adapter import (
            _candle_close_ts_seconds,
        )
        return _candle_close_ts_seconds(candles[idx], timeframe)
    except Exception:
        return None


def process_record(
    rec: Dict[str, Any],
    candles_by_pair: Dict[Tuple[str, str], List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Replay one historical record. Pure read.

    Returns a dict with: id, prediction_id, symbol, tf, old, new, reason,
    return_h6, future_used, change, status.
    """
    symbol = rec.get("symbol") or ""
    tf = (rec.get("timeframe") or "").upper()
    candles = candles_by_pair.get((symbol, tf), [])
    old_outcome = rec.get("outcome") or {}
    old_label = (old_outcome.get("winning_scenario") or "").lower() or None

    out_base = {
        "_id": rec["_id"],
        "prediction_id": rec.get("prediction_id"),
        "symbol": symbol,
        "tf": tf,
        "old": old_label,
        "new": None,
        "reason": None,
        "return_h6": old_outcome.get("return_h6"),
        "vol_future_h6": old_outcome.get("volatility_future_h6"),
        "future_used": 0,
        "change": None,
        "status": "ok",
    }

    if not candles:
        out_base["status"] = "no_candles_for_pair"
        return out_base

    entry = _safe_float(rec.get("entry_price"))
    ts = rec.get("candle_close_ts")
    if entry <= 0 or not ts:
        out_base["status"] = "bad_record"
        return out_base

    idx = _locate_entry_idx(candles, int(ts), timeframe=tf)
    if idx < 0:
        out_base["status"] = "entry_not_locatable"
        return out_base
    future = candles[idx + 1: idx + 1 + MIN_HORIZON_CANDLES]
    out_base["future_used"] = len(future)
    if len(future) < MIN_HORIZON_CANDLES:
        out_base["status"] = "insufficient_future_now"
        return out_base

    scenarios = (
        rec.get("scenarios_interaction_adjusted")
        or rec.get("scenarios_original")
        or []
    )

    # Run BOTH resolvers and assert agreement on label.
    return_h6_for_replay = old_outcome.get("return_h6")
    new_label_prod = resolve_winning_scenario(
        entry_price=entry,
        scenarios_interaction_adjusted=scenarios,
        future_candles=future,
        return_h6=return_h6_for_replay,
    )
    new_label_dbg, reason = resolver_with_reason(
        entry_price=entry,
        scenarios=scenarios,
        future_candles=future,
        return_h6=return_h6_for_replay,
    )
    if new_label_prod != new_label_dbg:
        # This is a programmer error: debug copy drifted. Hard fail.
        raise RuntimeError(
            f"resolver drift on prediction_id={rec.get('prediction_id')!r}: "
            f"prod={new_label_prod!r} dbg={new_label_dbg!r}"
        )

    out_base["new"] = new_label_prod
    out_base["reason"] = reason
    out_base["change"] = (old_label != new_label_prod)
    return out_base


# ---------------------------------------------------------------------------
# Apply (gated by --apply)
# ---------------------------------------------------------------------------
def apply_changes(db, results: List[Dict[str, Any]]) -> int:
    """Persist new winning_scenario back into outcome. Idempotent."""
    n = 0
    for r in results:
        if r["status"] != "ok" or not r["change"]:
            continue
        db.ta_prediction_history.update_one(
            {"_id": r["_id"]},
            {"$set": {
                "outcome.winning_scenario": r["new"],
                "outcome.relabel_reason": r["reason"],
                "outcome.relabeled_at": datetime.now(timezone.utc).isoformat(),
                "outcome.relabel_resolver_version": "v2_fix1_fix2",
            }},
        )
        n += 1
    return n


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def fmt_dist(c: Counter, total: int) -> str:
    parts = []
    for k in ("bull", "base", "bear"):
        v = c.get(k, 0)
        pct = (v / total * 100.0) if total else 0.0
        parts.append(f"{k}={v} ({pct:.1f}%)")
    return "  ".join(parts)


def fmt_truncate(s: Any, n: int) -> str:
    s = str(s) if s is not None else "—"
    return s if len(s) <= n else s[: n - 1] + "…"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Persist new winning_scenario back to Mongo. "
                             "Without this flag the script is read-only.")
    parser.add_argument("--samples", type=int, default=10,
                        help="Number of changed-record samples to print.")
    args = parser.parse_args()

    db = get_db()
    print(f"[relabel] DB={db.name}")
    print(f"[relabel] resolver: v2 (FIX-RESOLVER-1+2), "
          f"horizon={MIN_HORIZON_CANDLES} candles, "
          f"DIR_THRESHOLD_PCT={DIR_THRESHOLD_PCT} (untouched)")
    print(f"[relabel] mode: {'APPLY (will write)' if args.apply else 'DRY-RUN (read-only)'}")
    print()

    records = load_evaluated_records(db)
    print(f"[relabel] loaded {len(records)} evaluated records")

    # Pre-load candles per (symbol, tf) once.
    pairs = sorted({
        (r.get("symbol") or "", (r.get("timeframe") or "").upper())
        for r in records
    })
    candles_by_pair: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for sym, tf in pairs:
        candles_by_pair[(sym, tf)] = load_candles(db, sym, tf)
        print(f"[relabel]   candles {sym} {tf}: "
              f"{len(candles_by_pair[(sym, tf)])}")
    print()

    results = [process_record(r, candles_by_pair) for r in records]

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    status_count = Counter(r["status"] for r in results)
    ok_results = [r for r in results if r["status"] == "ok"]
    n_ok = len(ok_results)

    old_dist = Counter(r["old"] for r in ok_results if r["old"])
    new_dist = Counter(r["new"] for r in ok_results if r["new"])
    changed = [r for r in ok_results if r["change"]]
    unchanged = [r for r in ok_results if not r["change"]]
    reason_count = Counter(r["reason"] for r in ok_results)
    reason_count_changed = Counter(r["reason"] for r in changed)

    print("=" * 78)
    print("STATUS BREAKDOWN")
    print("=" * 78)
    for k, v in status_count.most_common():
        print(f"  {k:<32} {v}")
    print(f"  → replayable (ok): {n_ok}/{len(records)}")

    print()
    print("=" * 78)
    print("OLD vs NEW DISTRIBUTION")
    print("=" * 78)
    print(f"OLD: {fmt_dist(old_dist, n_ok)}")
    print(f"NEW: {fmt_dist(new_dist, n_ok)}")
    deltas = []
    for k in ("bull", "base", "bear"):
        d = new_dist.get(k, 0) - old_dist.get(k, 0)
        deltas.append(f"{k}={d:+d}")
    print(f"Δ:   " + "  ".join(deltas))

    print()
    print("=" * 78)
    print("REASON HISTOGRAM")
    print("=" * 78)
    print(f"  All replayable records (N={n_ok}):")
    for k, v in reason_count.most_common():
        print(f"    {k:<22} {v:>3}  ({v/n_ok*100:5.1f}%)")
    if changed:
        print(f"\n  Among CHANGED records only (N={len(changed)}):")
        for k, v in reason_count_changed.most_common():
            print(f"    {k:<22} {v:>3}  ({v/len(changed)*100:5.1f}%)")

    print()
    print("=" * 78)
    print("PER (symbol × tf)")
    print("=" * 78)
    by_pair: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for r in ok_results:
        by_pair[(r["symbol"], r["tf"])].append(r)
    print(f"  {'symbol':<10} {'tf':<4} {'N':>3}  "
          f"{'OLD bull/base/bear':>20}  {'NEW bull/base/bear':>20}  changed")
    for (sym, tf), rows in sorted(by_pair.items(), key=lambda x: -len(x[1])):
        oc = Counter(r["old"] for r in rows if r["old"])
        nc = Counter(r["new"] for r in rows if r["new"])
        ch = sum(1 for r in rows if r["change"])
        print(f"  {sym:<10} {tf:<4} {len(rows):>3}  "
              f"{oc.get('bull',0)}/{oc.get('base',0)}/{oc.get('bear',0):<14}  "
              f"{nc.get('bull',0)}/{nc.get('base',0)}/{nc.get('bear',0):<14}  "
              f"{ch}")

    print()
    print("=" * 78)
    print(f"CHANGED RECORDS — {len(changed)}/{n_ok} ({(len(changed)/n_ok*100 if n_ok else 0):.1f}%)")
    print("=" * 78)
    if changed:
        print(f"  {'prediction_id':<24} {'sym':<8} {'tf':<4} "
              f"{'old':<5} {'new':<5} {'return_h6':>10} {'vol_h6':>9}  "
              f"reason")
        print(f"  {'-'*24} {'-'*8} {'-'*4} {'-'*5} {'-'*5} {'-'*10} {'-'*9}  "
              f"{'-'*22}")
        for r in changed:
            rh6 = r["return_h6"]
            v6 = r["vol_future_h6"]
            rh6s = f"{rh6*100:+8.4f}%" if isinstance(rh6, (int, float)) else "—"
            v6s = f"{v6:.5f}" if isinstance(v6, (int, float)) else "—"
            print(f"  {fmt_truncate(r['prediction_id'], 24):<24} "
                  f"{r['symbol']:<8} {r['tf']:<4} "
                  f"{(r['old'] or '—'):<5} {(r['new'] or '—'):<5} "
                  f"{rh6s:>10} {v6s:>9}  {r['reason']}")

    print()
    print("=" * 78)
    print(f"SAMPLE DIFFS (up to {args.samples})")
    print("=" * 78)
    for r in changed[: args.samples]:
        print(f"  pid={r['prediction_id']}  {r['symbol']} {r['tf']}  "
              f"{r['old']} → {r['new']}   reason={r['reason']}   "
              f"return_h6={r['return_h6']}  vol_future_h6={r['vol_future_h6']}")

    print()
    print("=" * 78)
    print("VERDICT (mechanical reading)")
    print("=" * 78)
    base_old = old_dist.get("base", 0)
    base_new = new_dist.get("base", 0)
    bull_old = old_dist.get("bull", 0)
    bull_new = new_dist.get("bull", 0)
    bear_old = old_dist.get("bear", 0)
    bear_new = new_dist.get("bear", 0)
    print(f"  base:  {base_old} → {base_new}  ({base_new - base_old:+d})")
    print(f"  bull:  {bull_old} → {bull_new}  ({bull_new - bull_old:+d})")
    print(f"  bear:  {bear_old} → {bear_new}  ({bear_new - bear_old:+d})")
    if base_new <= base_old and base_old == 0:
        print("  ⚠  base count did NOT grow — fix did not move the needle.")
    elif base_new > base_old:
        print(f"  ✓  base grew by {base_new - base_old} (factor "
              f"{(base_new / max(base_old, 1)):.1f}x).")
    if bull_new < bull_old:
        print(f"  ✓  bull shrank by {bull_old - bull_new} — the within-bar "
              f"bias has been removed from those records.")
    elif bull_new == bull_old:
        print("  ↔  bull unchanged — no within-bar tie hit, deeper issue.")

    if args.apply:
        n_written = apply_changes(db, results)
        print()
        print(f"[relabel] APPLIED {n_written} updates to Mongo.")
    else:
        print()
        print("[relabel] DRY-RUN: no Mongo writes. Re-run with --apply "
              "to persist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
