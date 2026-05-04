#!/usr/bin/env python3
"""
Regime Accuracy Matrix — v1 vs v2 vs outcome (Phase C.2 partial proof)
======================================================================

READ-ONLY analysis script. Touches NOTHING in runtime.

Inputs:
  * MongoDB `shadow_trades` collection (for a given experiment_id lane).
  * For trades created AFTER the v2 deployment: uses stored `regime_debug`.
  * For LEGACY trades (no regime_debug): backfills v2 by re-fetching the
    historical klines from Binance US up to `entry_time` and running the
    SAME v2 detector. v1 is trusted from `trade.features.regime` (that is
    what the router actually used at entry time).

Outputs (stdout):
  * SHORT (SELL side) matrix: v1 × v2 × outcome (win / loss)
  * LONG  (BUY  side) matrix: v1 × v2 × outcome (win / loss)
  * Key numbers:
      - % SHORT-loss where v2 != DOWNTREND   ← primary question
      - % LONG-win  where v1 == UPTREND == v2
  * Binary verdict: does v2 explain SHORT losses? (yes / inconclusive / no)

Usage:
  python3 backend/scripts/regime_accuracy_matrix.py \\
      [--experiment phase_c_real_regime_run] \\
      [--lane phase_c] \\
      [--include-experiment discovery_matrix_live] \\
      [--no-backfill]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pymongo import MongoClient

sys.path.insert(0, '/app/backend')
try:
    from dotenv import load_dotenv
    load_dotenv('/app/backend/.env')
except Exception:
    pass

from modules.regime.market_regime_v2 import (  # noqa: E402
    detect_regime_v2,
    rolling_mean_series,
    calc_slope,
)

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("PHASE_B1_DB", "trading_os")

BINANCE_US_BASE = "https://api.binance.us/api/v3"

# Timeframe mapping — mirrors binance_provider._TF_MAP semantics.
TF_MAP = {
    "1M":  "1m", "3M":  "3m", "5M":  "5m", "15M": "15m", "30M": "30m",
    "1H":  "1h", "2H":  "2h", "4H":  "4h", "6H":  "6h", "8H":  "8h",
    "12H": "12h", "1D":  "1d", "3D":  "3d", "1W":  "1w",
}


# ---------------------------------------------------------------------------
#  Historical fetch (endTime-aware) — needed for legacy backfill
# ---------------------------------------------------------------------------
def fetch_klines_before(
    symbol: str,
    timeframe: str,
    end_time_ms: int,
    limit: int = 260,
) -> List[Dict[str, Any]]:
    """Get up to `limit` candles with closeTime <= end_time_ms."""
    interval = TF_MAP.get(timeframe.upper())
    if interval is None:
        return []
    url = f"{BINANCE_US_BASE}/klines"
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "endTime": int(end_time_ms),
        "limit": int(min(limit, 1000)),
    }
    try:
        resp = httpx.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        raw = resp.json()
        if not isinstance(raw, list):
            return []
        out = []
        for k in raw:
            out.append({
                "time": int(k[0]) // 1000,
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })
        out.sort(key=lambda c: c["time"])
        return out
    except Exception as e:
        print(f"    [fetch] {symbol} {timeframe} error: {e}")
        return []


# ---------------------------------------------------------------------------
#  Backfill v2 regime for a single legacy trade
# ---------------------------------------------------------------------------
def compute_v2_for_trade(trade: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Returns a regime_debug-like dict or None if insufficient data."""
    entry_time = trade.get("entry_time")
    if not isinstance(entry_time, datetime):
        return None
    end_ms = int(entry_time.timestamp() * 1000)
    symbol = trade.get("symbol")
    timeframe = trade.get("timeframe") or "1H"
    if not symbol:
        return None

    candles = fetch_klines_before(symbol, timeframe, end_ms, limit=260)
    if len(candles) < 50:
        return None

    closes = [c["close"] for c in candles]
    price = closes[-1]
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    ma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else ma50
    if ma50 is None:
        return None

    ma50_series = rolling_mean_series(closes, window=50, n=6)
    ma200_series = rolling_mean_series(closes, window=200, n=6) if len(closes) >= 205 else []
    ma50_slope = calc_slope(ma50_series, window=5) if ma50_series else 0.0
    ma200_slope = calc_slope(ma200_series, window=5) if ma200_series else 0.0

    v2 = detect_regime_v2(
        price=price, ma20=ma20, ma50=ma50, ma200=ma200,
        ma50_slope=ma50_slope, ma200_slope=ma200_slope,
    )
    return {
        "v2": v2.regime,
        "v2_reason": v2.reason,
        "price": price,
        "ma50": ma50,
        "ma200": ma200,
        "ma50_slope": ma50_slope,
        "ma200_slope": ma200_slope,
        "backfilled": True,
    }


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------
def _side_bucket(side: str) -> str:
    s = (side or "").upper()
    if s in ("SELL", "SHORT"):
        return "SHORT"
    if s in ("BUY", "LONG"):
        return "LONG"
    return "OTHER"


def _outcome(pnl: Optional[float]) -> str:
    if pnl is None:
        return "unresolved"
    return "win" if pnl > 0 else ("loss" if pnl < 0 else "flat")


def _get_resolved_pnl(trade: Dict[str, Any]) -> Optional[float]:
    horizons = trade.get("horizons", []) or []
    for h in horizons:
        if h.get("resolved"):
            return h.get("pnl")
    return None


# ---------------------------------------------------------------------------
#  Matrix build + print
# ---------------------------------------------------------------------------
def _fmt_row(label: str, counts: Dict[Tuple[str, str, str], int], v1_regime: str) -> str:
    parts = []
    for v2 in ("UPTREND", "RANGE", "DOWNTREND", "UNKNOWN"):
        w = counts.get((v1_regime, v2, "win"), 0)
        l = counts.get((v1_regime, v2, "loss"), 0)
        f = counts.get((v1_regime, v2, "flat"), 0)
        parts.append(f"v2={v2:<9} W={w:<3} L={l:<3} F={f:<3}")
    return f"  v1={v1_regime:<9} | " + "  ".join(parts)


def print_matrix(bucket: str, counts: Dict[Tuple[str, str, str], int]) -> None:
    print(f"\n=== {bucket} side — v1 × v2 × outcome ===")
    total = sum(counts.values())
    print(f"  total resolved: {total}")
    if total == 0:
        print("  (no resolved trades for this side)")
        return
    for v1 in ("UPTREND", "RANGE", "DOWNTREND", "UNKNOWN"):
        if any(k[0] == v1 for k in counts):
            print(_fmt_row(bucket, counts, v1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", default="phase_c_real_regime_run",
                    help="Primary experiment_id to analyze (default: phase_c_real_regime_run)")
    ap.add_argument("--include-experiment", action="append", default=[],
                    help="Additional experiment_id to include (repeatable)")
    ap.add_argument("--no-backfill", action="store_true",
                    help="Skip Binance backfill for legacy trades (v1 stats only)")
    args = ap.parse_args()

    experiments = [args.experiment] + list(args.include_experiment)

    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]

    print("=" * 72)
    print(" REGIME ACCURACY MATRIX — v1 vs v2 vs outcome")
    print("=" * 72)
    print(f" experiments: {experiments}")
    print(f" backfill   : {'OFF' if args.no_backfill else 'ON (Binance US)'}")
    print("=" * 72)

    # counts[(v1, v2, outcome)] = int, scoped per side
    short_counts: Dict[Tuple[str, str, str], int] = defaultdict(int)
    long_counts: Dict[Tuple[str, str, str], int] = defaultdict(int)

    short_loss_total = 0
    short_loss_v2_not_downtrend = 0
    long_win_total = 0
    long_win_v1_v2_both_uptrend = 0

    backfilled_ok = 0
    backfilled_fail = 0
    from_stored = 0
    no_v2_skipped = 0

    cursor = db.shadow_trades.find({
        "experiment_id": {"$in": experiments},
        "horizons.resolved": True,
    })

    trades = list(cursor)
    print(f"\nFetched {len(trades)} resolved trades.")

    for idx, t in enumerate(trades, 1):
        side_bucket = _side_bucket(t.get("side"))
        if side_bucket == "OTHER":
            continue
        pnl = _get_resolved_pnl(t)
        outcome = _outcome(pnl)
        if outcome == "unresolved":
            continue

        # v1: always from features (what the router actually saw at entry)
        features = t.get("features", {}) or {}
        v1 = features.get("regime") or "UNKNOWN"

        # v2: prefer stored regime_debug, else backfill
        rdbg = t.get("regime_debug")
        if isinstance(rdbg, dict) and rdbg.get("v2"):
            v2 = rdbg.get("v2")
            from_stored += 1
        elif args.no_backfill:
            no_v2_skipped += 1
            continue
        else:
            # Throttle to be polite to Binance
            if idx % 8 == 0:
                time.sleep(0.6)
            bf = compute_v2_for_trade(t)
            if bf is None:
                backfilled_fail += 1
                continue
            v2 = bf["v2"]
            backfilled_ok += 1

        key = (v1, v2, outcome)
        if side_bucket == "SHORT":
            short_counts[key] += 1
            if outcome == "loss":
                short_loss_total += 1
                if v2 != "DOWNTREND":
                    short_loss_v2_not_downtrend += 1
        else:  # LONG
            long_counts[key] += 1
            if outcome == "win":
                long_win_total += 1
                if v1 == "UPTREND" and v2 == "UPTREND":
                    long_win_v1_v2_both_uptrend += 1

    # ------- Report --------------------------------------------------------
    print(f"\nCoverage:")
    print(f"  v2 from stored regime_debug : {from_stored}")
    print(f"  v2 from backfill (Binance)  : {backfilled_ok}")
    print(f"  v2 backfill failed          : {backfilled_fail}")
    print(f"  skipped (--no-backfill)     : {no_v2_skipped}")

    print_matrix("SHORT", short_counts)
    print_matrix("LONG", long_counts)

    # ------- Key numbers ---------------------------------------------------
    print("\n" + "=" * 72)
    print(" KEY ANSWERS")
    print("=" * 72)

    pct_short_loss_v2_not_down = (
        (100.0 * short_loss_v2_not_downtrend / short_loss_total)
        if short_loss_total else 0.0
    )
    print(f" Q1. SHORT-loss where v2 != DOWNTREND : "
          f"{short_loss_v2_not_downtrend} / {short_loss_total} "
          f"({pct_short_loss_v2_not_down:.1f}%)")

    pct_long_win_both_up = (
        (100.0 * long_win_v1_v2_both_uptrend / long_win_total)
        if long_win_total else 0.0
    )
    print(f" Q2. LONG-win  where v1==UPTREND AND v2==UPTREND : "
          f"{long_win_v1_v2_both_uptrend} / {long_win_total} "
          f"({pct_long_win_both_up:.1f}%)")

    # ------- Verdict -------------------------------------------------------
    print("\n" + "=" * 72)
    print(" VERDICT")
    print("=" * 72)
    if short_loss_total == 0:
        verdict = "INCONCLUSIVE — no resolved SHORT losses yet."
    elif pct_short_loss_v2_not_down >= 70.0:
        verdict = "YES — v2 explains SHORT losses (majority of SHORT-loss happens in non-DOWNTREND per v2)."
    elif pct_short_loss_v2_not_down >= 40.0:
        verdict = "LIKELY — strong but not decisive; keep accumulating."
    else:
        verdict = "NO — SHORT losses mostly confirmed as DOWNTREND by v2 too; detector is not the root cause."

    print(f" {verdict}")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    sys.exit(main())
