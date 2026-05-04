#!/usr/bin/env python3
"""
SHORT Regime Drift Audit — forensic appendix to Phase C / Discovery reports.

For each resolved SHORT_TREND loss (both lanes), recompute at entry time:
  price / MA20 / MA50 / MA200, MA slopes (20-bar windows),
  distance price_vs_ma50, price_vs_ma200.

Hypothesis being tested:
  "SHORT was taken in a downtrend that had already reversed, and the regime
   detector was lagging behind the real market."

Evidence pattern to look for:
  * price > MA50 at entry (but SHORT was fired in DOWNTREND tag)
  * MA50 slope > 0 (rising) during SHORT entry
  * LONG winners on nearby timestamps for overlapping symbols

Read-only. NO changes to runtime. NO changes to strategy or router.
"""
from __future__ import annotations
import os, sys, math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

sys.path.insert(0, "/app/backend")
from pymongo import MongoClient
from modules.scanner.market_data.binance_provider import get_market_data_provider


MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("PHASE_B1_DB", "trading_os")


def tf_seconds(tf: str) -> int:
    tf = tf.upper()
    if tf.endswith("H"):
        return int(tf[:-1]) * 3600
    if tf.endswith("D"):
        return int(tf[:-1]) * 86400
    if tf.endswith("M"):
        return int(tf[:-1]) * 60
    return 3600


def ma(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def slope(values: List[float], period: int = 20) -> Optional[float]:
    """Simple linear-slope estimator: (last - first) / period over the last N samples."""
    if len(values) < period:
        return None
    first = values[-period]
    last = values[-1]
    return (last - first) / period


def compute_at_entry(symbol: str, tf: str, entry_ts: datetime) -> Dict[str, Any]:
    """Fetch recent candles and compute MAs at entry time (candle whose close_time >= entry_ts)."""
    provider = get_market_data_provider()
    try:
        candles = provider.get_candles(symbol, tf, limit=300)
    except Exception as e:
        return {"error": f"fetch_error: {e}"}
    if not candles:
        return {"error": "no_candles"}

    # Find the candle AT entry time — the first candle whose 'time' <= entry_ts_unix but (next candle time > entry_ts_unix)
    entry_unix = int(entry_ts.replace(tzinfo=timezone.utc).timestamp())
    target_idx: Optional[int] = None
    for i, c in enumerate(candles):
        t = int(c.get("time", 0))
        if t <= entry_unix:
            target_idx = i
        else:
            break

    if target_idx is None:
        return {"error": "entry_before_candle_history"}

    closes = [float(c["close"]) for c in candles[: target_idx + 1]]
    price = closes[-1]
    ma20 = ma(closes, 20)
    ma50 = ma(closes, 50)
    ma200 = ma(closes, 200)

    # slopes on closes series
    ma50_series = [ma(closes[: i + 1], 50) for i in range(len(closes))]
    ma50_series = [v for v in ma50_series if v is not None]
    ma200_series = [ma(closes[: i + 1], 200) for i in range(len(closes))]
    ma200_series = [v for v in ma200_series if v is not None]
    ma50_slope = slope(ma50_series, period=20) if ma50_series else None
    ma200_slope = slope(ma200_series, period=20) if ma200_series else None

    dist_ma50 = (price - ma50) / ma50 if ma50 else None
    dist_ma200 = (price - ma200) / ma200 if ma200 else None

    return {
        "price": price,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "ma50_slope": ma50_slope,
        "ma200_slope": ma200_slope,
        "dist_price_ma50": dist_ma50,
        "dist_price_ma200": dist_ma200,
        "candle_ts": int(candles[target_idx]["time"]),
    }


def _fmt_pct(v: Optional[float]) -> str:
    if v is None:
        return "    —"
    return f"{v * 100:+6.2f}%"


def _fmt_slope(v: Optional[float]) -> str:
    if v is None:
        return "      —"
    return f"{v:+8.4f}"


def _fmt_float(v: Optional[float]) -> str:
    if v is None:
        return "    —"
    return f"{v:9.4f}"


def dump_short_losses() -> None:
    mc = MongoClient(MONGO_URL)
    db = mc[DB_NAME]

    print("=" * 140)
    print("SHORT REGIME DRIFT AUDIT — Phase C.forensic")
    print("=" * 140)
    print("Target: every SHORT_TREND loss across BOTH lanes (phase_c + discovery)")
    print("Hypothesis: were SHORTs taken INSIDE a real downtrend, or DURING an already-started recovery?")
    print("Signal of lagging regime: price > MA50, MA50/MA200 slopes > 0 at entry.")
    print()

    cursor = db.shadow_trades.find({
        "features.strategy": "SHORT_TREND",
        "horizons.resolved": True,
        "horizons.pnl": {"$lt": 0},
    }).sort([("entry_time", 1)])

    rows = []
    for d in cursor:
        h = (d.get("horizons") or [{}])[0]
        f = d.get("features") or {}
        entry_ts = d["entry_time"]
        if isinstance(entry_ts, str):
            entry_ts = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
        ctx = compute_at_entry(d["symbol"], d.get("timeframe", "1H"), entry_ts)
        rows.append({
            "experiment": d["experiment_id"],
            "symbol": d["symbol"],
            "tf": d.get("timeframe"),
            "entry_ts": entry_ts,
            "entry": float(d["entry_price"]),
            "exit": float(h.get("exit_price")) if h.get("exit_price") is not None else None,
            "pnl": float(h["pnl"]),
            "regime_at_gen": f.get("regime"),
            "regime_conf": f.get("regime_confidence"),
            "short_ma": f.get("short_ma"),
            "long_ma": f.get("long_ma"),
            "trend_ma": f.get("trend_ma"),
            "ctx": ctx,
        })

    if not rows:
        print("  (no SHORT losses found)")
        return

    print(
        f"{'lane':12s} {'symbol':9s} {'tf':4s} {'entry_ts':20s} "
        f"{'pnl':>7s}  {'regime':10s} "
        f"{'price':>10s} {'ma20':>10s} {'ma50':>10s} {'ma200':>10s} "
        f"{'dist_ma50':>10s} {'dist_ma200':>11s} "
        f"{'ma50_slope':>12s} {'ma200_slope':>13s}"
    )
    print("-" * 140)

    # Aggregators
    tests = {
        "price>ma50_at_entry": 0,
        "price>ma200_at_entry": 0,
        "ma50_rising": 0,
        "ma200_rising": 0,
        "both_rising": 0,
        "all_four_bullish": 0,
    }
    n = 0

    for r in rows:
        ctx = r["ctx"]
        if "error" in ctx:
            print(f"  {r['symbol']} {r['tf']} {r['entry_ts']}  ERROR: {ctx['error']}")
            continue
        n += 1
        lane = "phase_c" if r["experiment"] == "phase_c_real_regime_run" else "discovery"
        dm50 = ctx["dist_price_ma50"]
        dm200 = ctx["dist_price_ma200"]
        ms50 = ctx["ma50_slope"]
        ms200 = ctx["ma200_slope"]

        price_above_ma50 = dm50 is not None and dm50 > 0
        price_above_ma200 = dm200 is not None and dm200 > 0
        ma50_up = ms50 is not None and ms50 > 0
        ma200_up = ms200 is not None and ms200 > 0

        if price_above_ma50: tests["price>ma50_at_entry"] += 1
        if price_above_ma200: tests["price>ma200_at_entry"] += 1
        if ma50_up: tests["ma50_rising"] += 1
        if ma200_up: tests["ma200_rising"] += 1
        if ma50_up and ma200_up: tests["both_rising"] += 1
        if price_above_ma50 and price_above_ma200 and ma50_up and ma200_up:
            tests["all_four_bullish"] += 1

        print(
            f"{lane:12s} {r['symbol']:9s} {r['tf']:4s} {r['entry_ts'].strftime('%Y-%m-%d %H:%M'):20s} "
            f"{r['pnl'] * 100:+6.2f}%  {str(r['regime_at_gen'])[:10]:10s} "
            f"{_fmt_float(ctx['price'])} {_fmt_float(ctx['ma20'])} {_fmt_float(ctx['ma50'])} {_fmt_float(ctx['ma200'])} "
            f"{_fmt_pct(dm50):>10s} {_fmt_pct(dm200):>11s} "
            f"{_fmt_slope(ms50):>12s} {_fmt_slope(ms200):>13s}"
        )

    print()
    print("=" * 140)
    print(f"SUMMARY — N={n} SHORT losses audited")
    print(f"  price > ma50  at entry        : {tests['price>ma50_at_entry']} / {n}  ({100 * tests['price>ma50_at_entry'] / n:.0f}%)")
    print(f"  price > ma200 at entry        : {tests['price>ma200_at_entry']} / {n}  ({100 * tests['price>ma200_at_entry'] / n:.0f}%)")
    print(f"  MA50  rising (slope > 0)      : {tests['ma50_rising']} / {n}  ({100 * tests['ma50_rising'] / n:.0f}%)")
    print(f"  MA200 rising (slope > 0)      : {tests['ma200_rising']} / {n}  ({100 * tests['ma200_rising'] / n:.0f}%)")
    print(f"  both MA50+MA200 rising        : {tests['both_rising']} / {n}  ({100 * tests['both_rising'] / n:.0f}%)")
    print(f"  ALL 4 bullish at entry        : {tests['all_four_bullish']} / {n}  ({100 * tests['all_four_bullish'] / n:.0f}%)")
    print()
    print("Interpretation key:")
    print("  - If most SHORTs have price > ma50 AND ma50 slope > 0 → regime detector LAGGING (SHORT in early recovery)")
    print("  - If SHORTs have price < ma50 AND ma50 slope < 0     → regime detector CORRECT (SHORT in real downtrend)")
    print("  - If mixed → situation-dependent, need per-symbol drill")


def compare_long_wins_vs_short_losses() -> None:
    """Section 2: overlapping (symbol, tf) — do LONG wins appear near SHORT losses?"""
    mc = MongoClient(MONGO_URL)
    db = mc[DB_NAME]

    print()
    print("=" * 140)
    print("SECTION 2 — LONG winners vs SHORT losers on the SAME (symbol, timeframe)")
    print("=" * 140)

    short_losses = list(db.shadow_trades.find({
        "features.strategy": "SHORT_TREND",
        "horizons.resolved": True,
        "horizons.pnl": {"$lt": 0},
    }))
    long_wins = list(db.shadow_trades.find({
        "features.strategy": "LONG_PULLBACK",
        "horizons.resolved": True,
        "horizons.pnl": {"$gt": 0},
    }))

    by_pair_short = {}
    for t in short_losses:
        k = (t["symbol"], t.get("timeframe"))
        by_pair_short.setdefault(k, []).append(t)

    by_pair_long = {}
    for t in long_wins:
        k = (t["symbol"], t.get("timeframe"))
        by_pair_long.setdefault(k, []).append(t)

    overlap = set(by_pair_short.keys()) & set(by_pair_long.keys())
    if not overlap:
        print("  (no (symbol, tf) overlap between SHORT losers and LONG winners yet)")
        print(f"  SHORT losses pairs : {sorted(by_pair_short.keys())}")
        print(f"  LONG  wins pairs   : {sorted(by_pair_long.keys())}")
    else:
        for pair in sorted(overlap):
            sym, tf = pair
            print(f"\n  {sym} {tf}:")
            for t in by_pair_short[pair]:
                h = (t.get("horizons") or [{}])[0]
                print(f"    SHORT-LOSS  {t['entry_time']}  entry=${float(t['entry_price']):.4f}  pnl={h['pnl']*100:+.2f}%  exp={t['experiment_id'][:10]}")
            for t in by_pair_long[pair]:
                h = (t.get("horizons") or [{}])[0]
                print(f"    LONG-WIN    {t['entry_time']}  entry=${float(t['entry_price']):.4f}  pnl={h['pnl']*100:+.2f}%  exp={t['experiment_id'][:10]}")


if __name__ == "__main__":
    dump_short_losses()
    compare_long_wins_vs_short_losses()
