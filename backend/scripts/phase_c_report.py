#!/usr/bin/env python3
"""
Phase C / Discovery — unified truth report.

Reads env vars:
  STDOUT_LOG    path to the structured log (phase_c_out.log or discovery_out.log)
  EXPERIMENT    experiment_id to filter shadow_trades
  TAG           structured-line prefix ("PHASE_C" or "DISCOVERY")
  MONGO_URL, PHASE_B1_DB
"""
from __future__ import annotations
import os, re, sys
from collections import Counter, defaultdict

from pymongo import MongoClient


STDOUT_LOG = os.environ["STDOUT_LOG"]
EXPERIMENT = os.environ["EXPERIMENT"]
TAG = os.environ.get("TAG", "PHASE_C")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("PHASE_B1_DB", "trading_os")

mc = MongoClient(MONGO_URL)
db = mc[DB_NAME]

try:
    with open(STDOUT_LOG) as f:
        log_text = f.read()
except Exception:
    log_text = ""


# 1) Totals
total = db.shadow_trades.count_documents({"experiment_id": EXPERIMENT})
resolved = db.shadow_trades.count_documents(
    {"experiment_id": EXPERIMENT, "horizons.resolved": True}
)
open_ = total - resolved
print("1. TOTALS")
print(f"   trades total   : {total}")
print(f"   trades resolved: {resolved}")
print(f"   trades open    : {open_}")
print()

# 2) By strategy (created / resolved / wins / avg pnl)
by_strat = Counter()
by_strat_resolved = Counter()
wins_by_strat = Counter()
pnls_by_strat: dict[str, list[float]] = defaultdict(list)
for d in db.shadow_trades.find(
    {"experiment_id": EXPERIMENT},
    {"features.strategy": 1, "horizons": 1},
):
    strat = (d.get("features") or {}).get("strategy")
    by_strat[strat] += 1
    h = (d.get("horizons") or [])
    if h and h[0].get("resolved"):
        by_strat_resolved[strat] += 1
        pnl = h[0].get("pnl")
        if pnl is not None:
            pnls_by_strat[strat].append(float(pnl))
            if pnl > 0:
                wins_by_strat[strat] += 1
print("2. BY STRATEGY")
print(f"   {'strategy':15s}  created  resolved  wins   winrate   avg_pnl")
for s in ("SHORT_TREND", "LONG_PULLBACK", "LONG_BREAKOUT"):
    c = by_strat.get(s, 0)
    r = by_strat_resolved.get(s, 0)
    w = wins_by_strat.get(s, 0)
    pnls = pnls_by_strat.get(s, [])
    wr = f"{100 * w / r:.2f}%" if r else "—"
    avg = f"{100 * sum(pnls) / len(pnls):+.3f}%" if pnls else "—"
    print(f"   {s:15s}  {c:7d}  {r:8d}  {w:4d}  {wr:>8s}  {avg:>9s}")
other = [k for k in by_strat if k not in ("SHORT_TREND", "LONG_PULLBACK", "LONG_BREAKOUT")]
if other:
    print(f"   other           : {[(k, by_strat[k]) for k in other]}")
print()

# 3) By regime (cycles in which regime observed ≥ once)
dt_c = ut_c = rg_c = 0
for m in re.finditer(r"regime_detections:\s*\{([^}]*)\}", log_text):
    s = m.group(1)
    if "'DOWNTREND'" in s: dt_c += 1
    if "'UPTREND'"   in s: ut_c += 1
    if "'RANGE'"     in s: rg_c += 1
total_cycles = log_text.count(f"[{TAG}] cycle=")
print("3. BY REGIME (cycles in which regime observed ≥ once)")
print(f"   total cycles   : {total_cycles}")
print(f"   DOWNTREND      : {dt_c}")
print(f"   UPTREND        : {ut_c}")
print(f"   RANGE          : {rg_c}")
print()

# 4) SHORT winrate vs Batch 6
pnls = pnls_by_strat.get("SHORT_TREND", [])
print("4. SHORT EDGE (vs Batch 6 baseline: 83.7% WR)")
if pnls:
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    flat = sum(1 for p in pnls if p == 0)
    print(f"   resolved        : {len(pnls)}")
    print(f"   wins/loss/flat  : {wins}/{losses}/{flat}")
    print(f"   winrate         : {100 * wins / len(pnls):.2f}%")
    print(f"   avg pnl         : {100 * sum(pnls) / len(pnls):+.3f}%")
    delta_wr = 100 * wins / len(pnls) - 83.7
    print(f"   delta vs Batch6 : {delta_wr:+.2f}pp")
else:
    print("   (no resolved SHORT trades yet — edge not measurable)")
print()

# 5) LONG activity
lp_total = by_strat.get("LONG_PULLBACK", 0)
lb_total = by_strat.get("LONG_BREAKOUT", 0)
print("5. LONG SIGNALS")
print(f"   LONG_PULLBACK  created: {lp_total:4d}  resolved: {by_strat_resolved.get('LONG_PULLBACK', 0):4d}")
print(f"   LONG_BREAKOUT  created: {lb_total:4d}  resolved: {by_strat_resolved.get('LONG_BREAKOUT', 0):4d}")
if lp_total + lb_total > 0:
    # where did LONGs come from? (symbol/tf breakdown)
    long_sym_tf = Counter()
    for d in db.shadow_trades.find(
        {"experiment_id": EXPERIMENT, "features.strategy": {"$in": ["LONG_PULLBACK", "LONG_BREAKOUT"]}},
        {"symbol": 1, "timeframe": 1, "features.strategy": 1},
    ):
        long_sym_tf[(d.get("symbol"), d.get("timeframe"), (d.get("features") or {}).get("strategy"))] += 1
    print("   long breakdown (symbol × tf × strategy):")
    for (sym, tf, strat), cnt in sorted(long_sym_tf.items(), key=lambda x: -x[1])[:10]:
        print(f"     {sym:10s}  {tf:4s}  {strat:15s}  x {cnt}")
print()

# 6) Symbol concentration
sym_counter = Counter()
for d in db.shadow_trades.find({"experiment_id": EXPERIMENT}, {"symbol": 1}):
    sym_counter[d.get("symbol")] += 1
print("6. SYMBOL CONCENTRATION")
if total > 0:
    top = sym_counter.most_common(10)
    for sym, cnt in top:
        pct = 100 * cnt / total
        print(f"   {sym:12s} : {cnt:4d}  ({pct:5.2f}%)")
    top1 = top[0][1] / total
    flag = "  ⚠️  (concentration!)" if top1 >= 0.9 else ""
    print(f"   top1 share     : {top1 * 100:.2f}%{flag}")
else:
    print("   (no trades)")
print()

# 7) Restarts / process deaths
starts   = len(re.findall(r"\[PROCESS\] STARTED", log_text))
sigterms = len(re.findall(r"\[PROCESS\] SIG(?:TERM|INT|HUP) received", log_text))
exits    = len(re.findall(r"\[PROCESS\] EXIT", log_text))
silent = max(0, starts - 1 - sigterms)
print("7. RESTARTS / PROCESS DEATHS")
print(f"   total STARTED banners     : {starts}")
print(f"   clean SIGTERM/INT/HUP     : {sigterms}")
print(f"   clean EXIT (atexit)       : {exits}")
print(f"   silent kills (sandbox)    : {silent}")
print(f"   process_deaths (total)    : {max(0, starts - 1)}")
print()

# Latest cumulative
cum = None
for m in re.finditer(rf"\[{TAG}_CUMULATIVE\]\s+(.*)", log_text):
    cum = m.group(1)
if cum:
    print(f"Latest [{TAG}_CUMULATIVE]:")
    print(f"  {cum.strip()}")
