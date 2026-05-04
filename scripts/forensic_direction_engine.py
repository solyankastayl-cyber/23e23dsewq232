#!/usr/bin/env python3
"""
forensic_direction_engine.py — read-only audit of where the bullish bias
on bear markets actually originates.

After the previous two forensics:
  - resolver was cleared (FIX 1+2 produced no distribution change)
  - scenario targets are perfectly symmetric (asymmetry == 0 on all 50)

Only direction-call layer remains: contributions[] (per-engine bias) and
the aggregated `bias` field. This script extracts everything that IS
persisted in ta_prediction_history and tries to answer two questions:

  A) Did engines see STALE candles?
     staleness_sec = candle_close_ts_record - meta._live.last_candle_close_ts
     stale > 0 means engine's view lagged behind the prediction timestamp.

  B) Did momentum engine logic give bullish on a bearish ETH dump?
     Compare momentum.bias with future return_h6:
       momentum=bullish AND return_h6 < -threshold  => disagreement
       momentum=bearish AND return_h6 > +threshold  => disagreement

Also checks for duplicate snapshots (same symbol, same candle_close_ts,
near-identical entry_price) — these inflate apparent N without giving
new evidence.

Read-only. No writes. No services touched.
"""
from __future__ import annotations

import json
import os
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient


def safe_float(x):
    try:
        v = float(x)
        if v != v or v in (float("inf"), float("-inf")):
            return None
        return v
    except (TypeError, ValueError):
        return None


def fmt_pct(v, w=8):
    if v is None:
        return "—".rjust(w)
    return f"{v*100:+{w-1}.4f}%"


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
db = mc[os.environ.get("DB_NAME", "trading_os")]

records = list(db.ta_prediction_history.find(
    {"evaluation_state": "evaluated", "outcome": {"$ne": None}}
))
N = len(records)

# Aggregator-level direction call.
def predicted(r):
    b = r.get("bias")
    return {"bullish": "bull", "bearish": "bear",
            "neutral": "base"}.get(b)

def winning(r):
    return ((r.get("outcome") or {}).get("winning_scenario") or "").lower() or None


# ---------------------------------------------------------------------------
# Per-record extraction
# ---------------------------------------------------------------------------
rows = []
for r in records:
    contribs = r.get("contributions") or []
    by_engine = {c.get("engine"): c for c in contribs if isinstance(c, dict)}
    momentum = by_engine.get("momentum") or {}
    structure = by_engine.get("structure") or {}
    pattern = by_engine.get("pattern") or {}
    volatility = by_engine.get("volatility") or {}
    sentiment = by_engine.get("sentiment") or {}

    meta_live = ((r.get("meta") or {}).get("_live") or {})

    candle_ts = r.get("candle_close_ts")
    last_seen_ts = meta_live.get("last_candle_close_ts")
    staleness = None
    if isinstance(candle_ts, (int, float)) and isinstance(last_seen_ts, (int, float)):
        staleness = int(candle_ts) - int(last_seen_ts)

    rows.append({
        "_id": str(r.get("_id")),
        "prediction_id": r.get("prediction_id"),
        "symbol": r.get("symbol"),
        "timeframe": r.get("timeframe"),
        "candle_close_ts": candle_ts,
        "candle_close_iso": (datetime.fromtimestamp(candle_ts, tz=timezone.utc).isoformat()
                             if isinstance(candle_ts, (int, float)) else None),
        "last_candle_close_ts": last_seen_ts,
        "staleness_sec": staleness,
        "candles_received": meta_live.get("candles_received"),
        "tf_minutes": meta_live.get("tf_minutes"),
        "engine_source": meta_live.get("source"),
        "context_regime_hint": meta_live.get("context_regime_hint"),
        "context_volatility_label": meta_live.get("context_volatility_label"),
        "data_completeness_all": (
            all((meta_live.get("data_completeness") or {}).values())
            if meta_live.get("data_completeness") else None
        ),

        "entry_price": safe_float(r.get("entry_price")),
        "agg_bias": r.get("bias"),
        "predicted": predicted(r),
        "winning": winning(r),
        "agg_confidence": safe_float(r.get("confidence")),
        "dominant_engine": r.get("dominant_engine"),
        "interaction_type": ((r.get("interaction") or {}).get("type")
                             if isinstance(r.get("interaction"), dict) else None) or "none",

        # per-engine bias
        "momentum_bias": momentum.get("bias"),
        "momentum_score": safe_float(momentum.get("score")),
        "momentum_state": (momentum.get("raw") or {}).get("momentum_state"),
        "rsi_last": safe_float((momentum.get("raw") or {}).get("rsi_last")),
        "macd_hist_last": safe_float((momentum.get("raw") or {}).get("macd_hist_last")),
        "macd_slope": safe_float((momentum.get("raw") or {}).get("macd_slope")),
        "bull_score_mom": safe_float((momentum.get("raw") or {}).get("bull_score")),
        "bear_score_mom": safe_float((momentum.get("raw") or {}).get("bear_score")),

        "structure_bias": structure.get("bias"),
        "structure_score": safe_float(structure.get("score")),
        "structure_trend_dir": (structure.get("raw") or {}).get("trend_dir"),
        "structure_phase": (structure.get("raw") or {}).get("phase"),

        "pattern_bias": pattern.get("bias"),
        "pattern_score": safe_float(pattern.get("score")),
        "primary_pattern": ((pattern.get("raw") or {}).get("primary") or {}).get("name"),

        "volatility_bias": volatility.get("bias"),
        "sentiment_bias": sentiment.get("bias"),

        "return_h6": safe_float((r.get("outcome") or {}).get("return_h6")),
        "return_h1": safe_float((r.get("outcome") or {}).get("return_h1")),
        "max_fav": safe_float((r.get("outcome") or {}).get("max_favourable_move_pct")),
        "max_adv": safe_float((r.get("outcome") or {}).get("max_adverse_move_pct")),
        "vol_future_h6": safe_float((r.get("outcome") or {}).get("volatility_future_h6")),
    })


# ---------------------------------------------------------------------------
# 0. Duplicate detection
# ---------------------------------------------------------------------------
def dup_key(row):
    return (row["symbol"], row["timeframe"],
            row["entry_price"],
            int(row["candle_close_ts"]) if row["candle_close_ts"] else None,
            row["return_h6"])

groups: Dict[Tuple, List[Dict]] = defaultdict(list)
for row in rows:
    groups[dup_key(row)].append(row)
unique_snapshots = len(groups)
duplicate_clusters = [(k, v) for k, v in groups.items() if len(v) > 1]


# ---------------------------------------------------------------------------
# 1. Staleness
# ---------------------------------------------------------------------------
stale_values = [r["staleness_sec"] for r in rows if r["staleness_sec"] is not None]


# ---------------------------------------------------------------------------
# 2. Disagreement: engine_bias vs reality
# ---------------------------------------------------------------------------
DIR_ABS = 0.005  # 0.5% over h6 — anything beyond this is a clear directional move
def reality_label(rh6):
    if rh6 is None:
        return None
    if rh6 > DIR_ABS:
        return "bull"
    if rh6 < -DIR_ABS:
        return "bear"
    return "flat"


for r in rows:
    r["reality"] = reality_label(r["return_h6"])


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def section(title):
    print()
    print("=" * 84)
    print(title)
    print("=" * 84)


section(f"DIRECTION ENGINE FORENSIC — N={N} records")
print(f"  unique (symbol, tf, entry_price, candle_close_ts, return_h6) snapshots: "
      f"{unique_snapshots}")
print(f"  duplicate clusters (>1 record): {len(duplicate_clusters)}")
if duplicate_clusters:
    print(f"\n  --- duplicate clusters (sample first 5) ---")
    for (k, v) in duplicate_clusters[:5]:
        sym, tf, ep, cts, rh = k
        print(f"    {sym} {tf} entry={ep} ts={cts} rh6={rh}  "
              f"→ {len(v)} duplicate records")

# ------------------------------------------------------------------
section("1) STALENESS  (entry candle_close_ts vs engine last_candle_close_ts)")
print(f"  records with both timestamps: {len(stale_values)}")
if stale_values:
    print(f"    min={min(stale_values)}s  max={max(stale_values)}s  "
          f"avg={statistics.mean(stale_values):.1f}s  "
          f"median={statistics.median(stale_values):.1f}s")
    nonzero = [v for v in stale_values if v != 0]
    print(f"    nonzero stale records: {len(nonzero)}/{len(stale_values)}")
    if nonzero:
        print("    distribution:")
        c = Counter(nonzero)
        for v, n in sorted(c.items())[:20]:
            print(f"      {v:>5}s : {n}")

# ------------------------------------------------------------------
section("2) BTC / ETH SPLIT")
def by_sym(rs):
    return defaultdict(list, {s: [r for r in rs if r["symbol"] == s]
                              for s in {x["symbol"] for x in rs}})
sym_groups = by_sym(rows)
print(f"  {'symbol':<10} {'N':>3}  {'pred bull':>10} {'pred bear':>10} "
      f"{'real bull':>10} {'real bear':>10} {'real flat':>10}  "
      f"{'acc(pred)':>10}  {'avg stale':>10}")
for sym, members in sorted(sym_groups.items(), key=lambda kv: -len(kv[1])):
    n = len(members)
    pred = Counter(r["predicted"] for r in members)
    real = Counter(r["reality"] for r in members)
    acc = sum(1 for r in members if r["predicted"] == r["reality"]) / n if n else 0.0
    s_vals = [r["staleness_sec"] for r in members if r["staleness_sec"] is not None]
    avg_s = statistics.mean(s_vals) if s_vals else None
    print(f"  {sym:<10} {n:>3}  {pred.get('bull',0):>10} {pred.get('bear',0):>10} "
          f"{real.get('bull',0):>10} {real.get('bear',0):>10} {real.get('flat',0):>10}  "
          f"{acc*100:>9.1f}%  {(avg_s or 0):>9.1f}s")

# ------------------------------------------------------------------
section("3) ENGINE-LEVEL DISAGREEMENT WITH REALITY")
def disagreement(eng_bias_field):
    out = []
    for sym in sorted({r["symbol"] for r in rows}):
        sub = [r for r in rows if r["symbol"] == sym and r["reality"] in ("bull", "bear")]
        if not sub:
            continue
        # bullish engine but bear reality
        bull_eng_bear_real = sum(
            1 for r in sub
            if r.get(eng_bias_field) == "bullish" and r["reality"] == "bear"
        )
        bear_eng_bull_real = sum(
            1 for r in sub
            if r.get(eng_bias_field) == "bearish" and r["reality"] == "bull"
        )
        eng_bull = sum(1 for r in sub if r.get(eng_bias_field) == "bullish")
        eng_bear = sum(1 for r in sub if r.get(eng_bias_field) == "bearish")
        n = len(sub)
        out.append({
            "symbol": sym, "n": n,
            "eng_bull": eng_bull, "eng_bear": eng_bear,
            "bull_eng_bear_real": bull_eng_bear_real,
            "bear_eng_bull_real": bear_eng_bull_real,
        })
    return out

for label, field in [("AGGREGATOR", "agg_bias"),
                     ("MOMENTUM", "momentum_bias"),
                     ("STRUCTURE", "structure_bias"),
                     ("PATTERN", "pattern_bias")]:
    print(f"\n  --- {label} (field: {field}) ---")
    print(f"    {'symbol':<10} {'N':>3}  {'eng=bull':>9} {'eng=bear':>9}  "
          f"{'bull_eng×bear_real':>20}  {'bear_eng×bull_real':>20}")
    for d in disagreement(field):
        print(f"    {d['symbol']:<10} {d['n']:>3}  "
              f"{d['eng_bull']:>9} {d['eng_bear']:>9}  "
              f"{d['bull_eng_bear_real']:>20}  {d['bear_eng_bull_real']:>20}")

# ------------------------------------------------------------------
section("4) ETH ZOOM — every record (includes engine internals)")
eth = sorted([r for r in rows if r["symbol"] == "ETHUSDT"],
             key=lambda r: (r["candle_close_ts"] or 0, r["prediction_id"] or ""))
print(f"  N total ETH = {len(eth)}")
unique_eth_keys = {dup_key(r) for r in eth}
print(f"  unique ETH snapshots = {len(unique_eth_keys)}")
print()
print(f"  {'pid':<22} {'entry':>9} {'cts_iso':<22} {'stale':>5} "
      f"{'agg':<8} {'mom':<8} {'mom_state':<18} "
      f"{'rsi':>6} {'macdh':>9} {'slope':>7}  "
      f"{'rh6':>9}")
for r in eth:
    pid = (r["prediction_id"] or "")[:22]
    cts = r.get("candle_close_iso") or "—"
    stale = r["staleness_sec"]
    stale_s = "—" if stale is None else f"{stale:>5}"
    print(f"  {pid:<22} {r['entry_price']:>9.2f} {cts[:19]:<22} {stale_s:>5} "
          f"{(r['agg_bias'] or '—'):<8} "
          f"{(r['momentum_bias'] or '—'):<8} "
          f"{str(r['momentum_state'] or '—'):<18} "
          f"{(r['rsi_last'] or 0):>6.1f} "
          f"{(r['macd_hist_last'] or 0):>9.4f} "
          f"{(r['macd_slope'] or 0):>7.3f}  "
          f"{fmt_pct(r['return_h6']):>9}")

# ------------------------------------------------------------------
section("5) SAME for unique-only ETH (collapsing duplicates)")
seen_keys = set()
unique_eth = []
for r in eth:
    k = dup_key(r)
    if k not in seen_keys:
        seen_keys.add(k)
        unique_eth.append(r)
print(f"  unique ETH snapshots: {len(unique_eth)}")
for r in unique_eth:
    pid = (r["prediction_id"] or "")[:22]
    cts = r.get("candle_close_iso") or "—"
    stale = r["staleness_sec"]
    stale_s = "—" if stale is None else f"{stale:>5}"
    print(f"  {pid:<22} {r['entry_price']:>9.2f} {cts[:19]:<22} {stale_s:>5} "
          f"agg={r['agg_bias']:<8} mom={r['momentum_bias']:<8} "
          f"state={r['momentum_state']:<18} "
          f"rsi={r['rsi_last']:>5.1f} macdh={r['macd_hist_last']:>+8.4f} "
          f"slope={r['macd_slope']:>+6.3f} "
          f"rh6={fmt_pct(r['return_h6']):>9} "
          f"max_adv={fmt_pct(r['max_adv']):>9}")

# ------------------------------------------------------------------
section("6) SAME for unique-only BTC")
btc = sorted([r for r in rows if r["symbol"] == "BTCUSDT"],
             key=lambda r: (r["candle_close_ts"] or 0, r["prediction_id"] or ""))
seen_keys = set()
unique_btc = []
for r in btc:
    k = dup_key(r)
    if k not in seen_keys:
        seen_keys.add(k)
        unique_btc.append(r)
print(f"  total BTC = {len(btc)}, unique snapshots = {len(unique_btc)}")
for r in unique_btc:
    pid = (r["prediction_id"] or "")[:22]
    cts = r.get("candle_close_iso") or "—"
    stale = r["staleness_sec"]
    stale_s = "—" if stale is None else f"{stale:>5}"
    print(f"  {pid:<22} {r['entry_price']:>10.1f} {cts[:19]:<22} {stale_s:>5} "
          f"agg={r['agg_bias']:<8} mom={r['momentum_bias']:<8} "
          f"rsi={r['rsi_last']:>5.1f} macdh={r['macd_hist_last']:>+9.3f} "
          f"slope={r['macd_slope']:>+7.3f} "
          f"rh6={fmt_pct(r['return_h6']):>9} "
          f"agg_bias_match={'✓' if r['predicted'] == r['reality'] else '✗'}")

# ------------------------------------------------------------------
section("7) MOMENTUM RAW METRICS — distribution by reality")
def mom_dist_by(reality):
    sub = [r for r in rows if r["reality"] == reality]
    rsis = [r["rsi_last"] for r in sub if r["rsi_last"] is not None]
    macdhs = [r["macd_hist_last"] for r in sub if r["macd_hist_last"] is not None]
    slopes = [r["macd_slope"] for r in sub if r["macd_slope"] is not None]
    bull_score = [r["bull_score_mom"] for r in sub if r["bull_score_mom"] is not None]
    bear_score = [r["bear_score_mom"] for r in sub if r["bear_score_mom"] is not None]
    states = Counter(r["momentum_state"] for r in sub if r["momentum_state"])
    return {"n": len(sub),
            "rsi": (statistics.mean(rsis) if rsis else None,
                    min(rsis) if rsis else None, max(rsis) if rsis else None),
            "macdh": (statistics.mean(macdhs) if macdhs else None,
                      min(macdhs) if macdhs else None, max(macdhs) if macdhs else None),
            "slope": (statistics.mean(slopes) if slopes else None,
                      min(slopes) if slopes else None, max(slopes) if slopes else None),
            "bull_s": statistics.mean(bull_score) if bull_score else None,
            "bear_s": statistics.mean(bear_score) if bear_score else None,
            "states": dict(states.most_common())}
for rl in ("bull", "bear", "flat"):
    d = mom_dist_by(rl)
    print(f"\n  reality={rl}  N={d['n']}")
    print(f"    RSI       avg={d['rsi'][0] or 0:.2f} range=[{(d['rsi'][1] or 0):.2f}, "
          f"{(d['rsi'][2] or 0):.2f}]")
    print(f"    MACD hist avg={(d['macdh'][0] or 0):+.4f} range=[{(d['macdh'][1] or 0):+.4f}, "
          f"{(d['macdh'][2] or 0):+.4f}]")
    print(f"    MACD slope avg={(d['slope'][0] or 0):+.4f}")
    print(f"    bull_score={d['bull_s'] or 0:.3f}  bear_score={d['bear_s'] or 0:.3f}")
    print(f"    momentum_state: {d['states']}")

# ------------------------------------------------------------------
section("8) AGGREGATOR vs ENGINES on bear-reality records (where the lie lives)")
sub = [r for r in rows if r["reality"] == "bear"]
print(f"  bear-reality records N={len(sub)}")
print(f"  what each engine SAID at that moment:")
for fld in ("momentum_bias", "structure_bias", "pattern_bias",
            "volatility_bias", "sentiment_bias", "agg_bias"):
    c = Counter(r.get(fld) for r in sub)
    print(f"    {fld:<18} {dict(c)}")

# ------------------------------------------------------------------
section("9) VERDICT")
# Stale check
nonzero_stale = [v for v in stale_values if v and v > 60]  # >60s lag
if not stale_values:
    print("  STALENESS: insufficient data (timestamps missing).")
elif not nonzero_stale:
    print(f"  STALENESS: NO stale data ({len(stale_values)}/{len(stale_values)} "
          f"records had engine.last_candle_close_ts == prediction.candle_close_ts).")
    print(f"             → Hypothesis A (stale candles) is REJECTED.")
else:
    print(f"  STALENESS: {len(nonzero_stale)}/{len(stale_values)} records had >60s lag. "
          f"Investigate.")

# Engine-vs-reality on ETH
eth_bear_real = [r for r in rows if r["symbol"] == "ETHUSDT" and r["reality"] == "bear"]
eth_mom_bull = sum(1 for r in eth_bear_real if r["momentum_bias"] == "bullish")
print()
print(f"  ETH bear-reality records: {len(eth_bear_real)}")
print(f"     momentum claimed bullish: {eth_mom_bull}/{len(eth_bear_real)}")
if len(eth_bear_real) and eth_mom_bull == len(eth_bear_real):
    print(f"     → momentum engine was 100% bullish on bear-real ETH. "
          f"BUT see RSI/MACD distribution — those indicators reflect PAST momentum; "
          f"flash crash AFTER candle_close_ts cannot be predicted by them.")
print(f"     unique ETH snapshots: {len(unique_eth)} "
      f"(N={len(eth)} duplicated records)")

# Comparison BTC vs ETH momentum metrics
btc_rsi = [r["rsi_last"] for r in rows if r["symbol"] == "BTCUSDT" and r["rsi_last"] is not None]
eth_rsi = [r["rsi_last"] for r in rows if r["symbol"] == "ETHUSDT" and r["rsi_last"] is not None]
if btc_rsi and eth_rsi:
    print()
    print(f"  RSI comparison (just to check thresholds aren't BTC-tuned):")
    print(f"    BTC: avg={statistics.mean(btc_rsi):.2f}  range=[{min(btc_rsi):.2f}, "
          f"{max(btc_rsi):.2f}]  N={len(btc_rsi)}")
    print(f"    ETH: avg={statistics.mean(eth_rsi):.2f}  range=[{min(eth_rsi):.2f}, "
          f"{max(eth_rsi):.2f}]  N={len(eth_rsi)}")

# ------------------------------------------------------------------
# Persist
# ------------------------------------------------------------------
out_jsonl = "/tmp/forensic_direction_engine.jsonl"
with open(out_jsonl, "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write(json.dumps(r, default=str) + "\n")

print()
print(f"  artefacts: {out_jsonl}")
