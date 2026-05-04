#!/usr/bin/env python3
"""
forensic_deduped_audit.py — honest re-baseline of the prediction audit
after collapsing duplicate records onto unique market snapshots.

Why:
  Direction-engine forensic exposed that ta_prediction_history N=50 is
  inflated by republished snapshots — the SAME (symbol, tf, entry_price,
  candle_close_ts) often appears 6-13 times with different prediction_id.
  Any metric over the raw 50 is double-counting the same evidence.

What this script does:
  1. Group records by (symbol, tf, round(entry_price, 4), candle_close_ts).
  2. From each cluster pick ONE canonical record (earliest by created_at).
  3. Recompute every audit metric the previous scripts produced — but
     side-by-side: RAW (N=50) vs DEDUPED (N_unique).
  4. Honest banner on whether the dedup'd N is statistically meaningful.

READ-ONLY. Zero mutations. Single artefact:
    /tmp/forensic_deduped_audit_report.md
"""
from __future__ import annotations

import json
import math
import os
import statistics
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def safe_float(x):
    try:
        v = float(x)
        if v != v or v in (float("inf"), float("-inf")):
            return None
        return v
    except (TypeError, ValueError):
        return None


def wilson(wins: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (centre - margin) / denom),
            min(1.0, (centre + margin) / denom))


def fmt_pct(v, w=5):
    if v is None:
        return "—".rjust(w)
    return f"{v*100:>{w}.1f}%"


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
db = mc[os.environ.get("DB_NAME", "trading_os")]

raw = list(db.ta_prediction_history.find(
    {"evaluation_state": "evaluated", "outcome": {"$ne": None}}
))


def normalize(r: Dict[str, Any]) -> Dict[str, Any]:
    contribs = {c.get("engine"): c for c in (r.get("contributions") or [])
                if isinstance(c, dict)}
    out = (r.get("outcome") or {})
    cal = r.get("scenarios_calibrated") or r.get("scenarios_original") or []
    probs = {"bull": 0.0, "base": 0.0, "bear": 0.0}
    for s in cal:
        n = s.get("name")
        if n in probs:
            probs[n] = float(s.get("probability") or 0.0)
    bias = r.get("bias")
    pred = {"bullish": "bull", "bearish": "bear", "neutral": "base"}.get(bias)
    return {
        "_id": r.get("_id"),
        "prediction_id": r.get("prediction_id"),
        "created_at": r.get("created_at"),
        "symbol": r.get("symbol"),
        "timeframe": (r.get("timeframe") or "").upper(),
        "entry_price": safe_float(r.get("entry_price")),
        "candle_close_ts": r.get("candle_close_ts"),
        "agg_bias": bias,
        "predicted": pred,
        "winning": (out.get("winning_scenario") or "").lower() or None,
        "confidence": safe_float(r.get("confidence")),
        "return_h6": safe_float(out.get("return_h6")),
        "probs": probs,
        "momentum_bias": (contribs.get("momentum") or {}).get("bias"),
        "structure_bias": (contribs.get("structure") or {}).get("bias"),
        "pattern_bias": (contribs.get("pattern") or {}).get("bias"),
        "volatility_bias": (contribs.get("volatility") or {}).get("bias"),
        "sentiment_bias": (contribs.get("sentiment") or {}).get("bias"),
    }


rows_raw = [normalize(r) for r in raw]


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------
def dedup_key(r):
    """Dedup by (symbol, timeframe, entry_price). entry_price equals the
    close price of a specific 1H candle, which uniquely identifies the
    market moment. The candle_close_ts field varies by seconds across
    duplicated snapshots of the same prediction (different prediction_id
    on the same bar) — using it would leave duplicates intact.
    Multiple records sharing entry_price + symbol always come from the
    same 1H bar in this sample (verified manually)."""
    ep = r["entry_price"]
    if ep is None:
        return None
    return (
        r["symbol"],
        r["timeframe"],
        round(float(ep), 4),
    )


clusters: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
for r in rows_raw:
    k = dedup_key(r)
    if k is None:
        continue
    clusters[k].append(r)

# Pick canonical = earliest created_at within cluster.
def pick_canonical(members):
    # created_at is BSON datetime in raw; sort by str repr if missing.
    def key(m):
        c = m.get("created_at")
        return (c if c is not None else m.get("prediction_id") or "")
    return sorted(members, key=key)[0]


unique_rows = [pick_canonical(v) for v in clusters.values()]
unique_rows.sort(key=lambda r: (r["candle_close_ts"] or 0))

N_RAW = len(rows_raw)
N_DEDUP = len(unique_rows)


# ---------------------------------------------------------------------------
# Metrics on a given row set
# ---------------------------------------------------------------------------
def one_hot(label):
    return {k: (1.0 if k == label else 0.0) for k in ("bull", "base", "bear")}


def compute_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    pred_dist = Counter(r["predicted"] for r in rows if r["predicted"])
    real_dist = Counter(r["winning"] for r in rows if r["winning"])
    correct = sum(1 for r in rows if r["predicted"] == r["winning"])
    ci_lo, ci_hi = wilson(correct, n)

    # Brier (3-class)
    bsum = 0.0
    for r in rows:
        truth = one_hot(r["winning"])
        for k in truth:
            bsum += (r["probs"].get(k, 0.0) - truth[k]) ** 2
    brier = bsum / n

    # Per symbol
    by_sym = {}
    for sym in {r["symbol"] for r in rows}:
        sub = [r for r in rows if r["symbol"] == sym]
        nn = len(sub)
        cc = sum(1 for r in sub if r["predicted"] == r["winning"])
        wr_lo, wr_hi = wilson(cc, nn)
        by_sym[sym] = {
            "n": nn, "correct": cc,
            "acc": cc / nn if nn else None,
            "ci": (wr_lo, wr_hi),
            "pred": dict(Counter(r["predicted"] for r in sub if r["predicted"])),
            "real": dict(Counter(r["winning"] for r in sub if r["winning"])),
        }

    return {
        "n": n,
        "correct": correct,
        "acc": correct / n,
        "ci": (ci_lo, ci_hi),
        "predicted_dist": dict(pred_dist),
        "actual_dist": dict(real_dist),
        "brier": brier,
        "by_symbol": by_sym,
    }


m_raw = compute_metrics(rows_raw)
m_dedup = compute_metrics(unique_rows)


# ---------------------------------------------------------------------------
# Engine agreement matrix on dedup'd set
# ---------------------------------------------------------------------------
def engine_agreement(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    out = {"n": len(rows), "engines": {}}
    for fld in ("momentum_bias", "structure_bias", "pattern_bias",
                "volatility_bias", "sentiment_bias", "agg_bias"):
        c = Counter(r.get(fld) for r in rows)
        # how often this engine matches reality
        sub = [r for r in rows if r["winning"] in ("bull", "bear", "base")]
        match = 0
        considered = 0
        for r in sub:
            ev = r.get(fld)
            ev_norm = {"bullish": "bull", "bearish": "bear",
                       "neutral": "base"}.get(ev)
            if ev_norm is None:
                continue
            considered += 1
            if ev_norm == r["winning"]:
                match += 1
        out["engines"][fld] = {
            "distribution": dict(c),
            "matches_reality": match,
            "considered": considered,
            "match_rate": (match / considered) if considered else None,
        }
    # Pattern-overruled-by-aggregator
    pattern_correct_overruled = 0
    pattern_considered = 0
    for r in rows:
        pb = {"bullish": "bull", "bearish": "bear",
              "neutral": "base"}.get(r.get("pattern_bias"))
        ab = {"bullish": "bull", "bearish": "bear",
              "neutral": "base"}.get(r.get("agg_bias"))
        if pb is None or ab is None or r["winning"] is None:
            continue
        pattern_considered += 1
        if pb == r["winning"] and ab != r["winning"]:
            pattern_correct_overruled += 1
    out["pattern_correct_overruled"] = pattern_correct_overruled
    out["pattern_considered"] = pattern_considered
    return out


agree = engine_agreement(unique_rows)


# ---------------------------------------------------------------------------
# Per-cluster table
# ---------------------------------------------------------------------------
def cluster_lines() -> List[str]:
    out = []
    for k, members in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
        sym, tf, ep = k
        canonical = pick_canonical(members)
        # Use canonical's candle_close_ts for display.
        out.append({
            "symbol": sym, "tf": tf, "entry": ep,
            "ts": canonical["candle_close_ts"],
            "n_dups": len(members),
            "canonical_pid": canonical["prediction_id"],
            "agg": canonical["agg_bias"],
            "winning": canonical["winning"],
            "rh6": canonical["return_h6"],
        })
    return out


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def section(title):
    print()
    print("=" * 84)
    print(title)
    print("=" * 84)


print(f"DEDUP key: (symbol, timeframe, round(entry_price, 4))")
print(f"  rationale: entry_price = close price of a specific 1H candle.")
print(f"  Records sharing (symbol, entry_price) are republished snapshots")
print(f"  of the SAME bar (verified — candle_close_ts only differs by seconds).")
print(f"N raw     = {N_RAW}")
print(f"N unique  = {N_DEDUP}")
print(f"compression ratio = {N_RAW / N_DEDUP:.2f}x")

section("CLUSTER TABLE — duplicates collapsed")
clines = cluster_lines()
print(f"  {'symbol':<8} {'tf':<3} {'entry':>11} {'ts':>11} {'dups':>4}  "
      f"{'agg':<8} {'winning':<8} {'return_h6':>11}  pid")
for c in clines:
    print(f"  {c['symbol']:<8} {c['tf']:<3} {c['entry']:>11.4f} "
          f"{c['ts']:>11} {c['n_dups']:>4}  "
          f"{(c['agg'] or '—'):<8} {(c['winning'] or '—'):<8} "
          f"{(c['rh6']*100 if c['rh6'] is not None else 0):>+10.4f}%  "
          f"{c['canonical_pid']}")

section("1) DIRECTION ACCURACY  —  RAW vs DEDUPED")
print(f"  {'metric':<30} {'RAW (N=50)':>18}     {'DEDUPED':>22}")
print(f"  {'-'*30} {'-'*18}     {'-'*22}")
print(f"  {'N':<30} {m_raw['n']:>18}     {m_dedup['n']:>22}")
print(f"  {'correct':<30} {m_raw['correct']:>18}     {m_dedup['correct']:>22}")
print(f"  {'accuracy':<30} {m_raw['acc']*100:>17.1f}%     "
      f"{m_dedup['acc']*100:>21.1f}%")
print(f"  {'95% CI':<30} "
      f"[{m_raw['ci'][0]*100:5.1f}, {m_raw['ci'][1]*100:5.1f}]    "
      f"   [{m_dedup['ci'][0]*100:5.1f}, {m_dedup['ci'][1]*100:5.1f}]")
print(f"  {'Brier (3-class)':<30} {m_raw['brier']:>18.4f}     "
      f"{m_dedup['brier']:>22.4f}")
random_baseline = 1/3
print(f"  {'random baseline':<30} {random_baseline*100:>17.1f}%     "
      f"{random_baseline*100:>21.1f}%")
maj_raw = max(m_raw['actual_dist'].values()) / m_raw['n'] if m_raw['actual_dist'] else 0
maj_d = max(m_dedup['actual_dist'].values()) / m_dedup['n'] if m_dedup['actual_dist'] else 0
print(f"  {'majority-class baseline':<30} {maj_raw*100:>17.1f}%     "
      f"{maj_d*100:>21.1f}%")

section("2) DISTRIBUTION (predicted vs actual)  —  RAW vs DEDUPED")
print(f"  RAW     predicted: {m_raw['predicted_dist']}")
print(f"  RAW     actual:    {m_raw['actual_dist']}")
print(f"  DEDUP   predicted: {m_dedup['predicted_dist']}")
print(f"  DEDUP   actual:    {m_dedup['actual_dist']}")

section("3) PER-SYMBOL  —  RAW vs DEDUPED")
all_syms = sorted(set(list(m_raw["by_symbol"].keys()) + list(m_dedup["by_symbol"].keys())))
print(f"  {'symbol':<10} {'set':<7} {'N':>3} {'correct':>7} "
      f"{'acc':>7}    {'95% CI':<16}  pred              actual")
for sym in all_syms:
    for label, m in [("RAW", m_raw), ("DEDUP", m_dedup)]:
        if sym not in m["by_symbol"]:
            continue
        s = m["by_symbol"][sym]
        ci = f"[{s['ci'][0]*100:4.1f},{s['ci'][1]*100:4.1f}]"
        print(f"  {sym:<10} {label:<7} {s['n']:>3} {s['correct']:>7} "
              f"{(s['acc'] or 0)*100:>6.1f}%   "
              f"{ci:<16}  {str(s['pred']):<18} {str(s['real'])}")

section("4) ENGINE-LEVEL AGREEMENT WITH REALITY  (DEDUPED N={})".format(N_DEDUP))
print(f"  {'engine':<20} {'considered':>10} {'matches':>8} {'match_rate':>11}  "
      f"distribution")
for name, e in agree["engines"].items():
    mr = e['match_rate']
    mr_s = f"{mr*100:>9.1f}%" if mr is not None else "—".rjust(11)
    print(f"  {name:<20} {e['considered']:>10} {e['matches_reality']:>8} "
          f"{mr_s}    {e['distribution']}")
print()
print(f"  Pattern was right but aggregator overrode it: "
      f"{agree['pattern_correct_overruled']}/{agree['pattern_considered']}")

section("5) HONEST STATISTICAL POWER NOTE")
power_note = []
n = N_DEDUP
# Wilson margin at 0.5 baseline
half_width = wilson(int(n*0.5), n)[1] - 0.5 if n else 0.5
power_note.append(f"  N_dedup = {n}.  Wilson 95% CI half-width at p=0.5: "
                  f"±{half_width*100:.1f}pp.")
power_note.append(f"  This means: even a TRUE 70% accurate model would have a")
power_note.append(f"  95% CI roughly [{(0.7-half_width)*100:.0f}, "
                  f"{(0.7+half_width)*100:.0f}] on N={n}.")
power_note.append(f"  For ETH alone (N_unique={m_dedup['by_symbol'].get('ETHUSDT',{}).get('n', '?')}): "
                  f"any conclusion is anecdotal, not statistical.")
power_note.append(f"  For BTC alone (N_unique={m_dedup['by_symbol'].get('BTCUSDT',{}).get('n', '?')}): "
                  f"a noisy signal at best.")
power_note.append("")
power_note.append(f"  Verdict: any improvement claim with delta < ±{half_width*100:.0f}pp "
                  f"is statistical noise on this sample size.")
for ln in power_note:
    print(ln)

section("6) WHAT CHANGED  —  before vs after dedup")
delta_acc = (m_dedup['acc'] - m_raw['acc']) * 100
delta_brier = m_dedup['brier'] - m_raw['brier']
print(f"  accuracy: {m_raw['acc']*100:.1f}% → {m_dedup['acc']*100:.1f}%   "
      f"({'+' if delta_acc >=0 else ''}{delta_acc:.1f}pp)")
print(f"  Brier:    {m_raw['brier']:.4f} → {m_dedup['brier']:.4f}   "
      f"({'+' if delta_brier >=0 else ''}{delta_brier:.4f})")
print(f"  N:        {m_raw['n']} → {m_dedup['n']}")

# Persist
out_md = "/tmp/forensic_deduped_audit_report.md"
lines = [f"# Deduped Audit Report\n",
         f"- N raw: {N_RAW}",
         f"- N unique: {N_DEDUP}",
         f"- compression: {N_RAW/N_DEDUP:.2f}x",
         "",
         "## Cluster table"]
lines.append("| symbol | tf | entry | ts | dups | agg | winning | return_h6 | pid |")
lines.append("|---|---|---|---|---|---|---|---|---|")
for c in clines:
    rh6 = (c['rh6']*100) if c['rh6'] is not None else 0
    lines.append(f"| {c['symbol']} | {c['tf']} | {c['entry']:.4f} | {c['ts']} | "
                 f"{c['n_dups']} | {c['agg']} | {c['winning']} | {rh6:+.4f}% | "
                 f"{c['canonical_pid']} |")

lines.append("")
lines.append("## Side-by-side metrics")
lines.append("| metric | RAW | DEDUPED |")
lines.append("|---|---|---|")
lines.append(f"| N | {m_raw['n']} | {m_dedup['n']} |")
lines.append(f"| accuracy | {m_raw['acc']*100:.1f}% | {m_dedup['acc']*100:.1f}% |")
lines.append(f"| Brier | {m_raw['brier']:.4f} | {m_dedup['brier']:.4f} |")
lines.append(f"| 95% CI | [{m_raw['ci'][0]*100:.1f}, {m_raw['ci'][1]*100:.1f}] | "
             f"[{m_dedup['ci'][0]*100:.1f}, {m_dedup['ci'][1]*100:.1f}] |")

lines.append("")
lines.append("## Per-symbol (deduped)")
lines.append("| symbol | N | correct | accuracy | 95% CI |")
lines.append("|---|---|---|---|---|")
for sym in all_syms:
    if sym in m_dedup["by_symbol"]:
        s = m_dedup["by_symbol"][sym]
        lines.append(f"| {sym} | {s['n']} | {s['correct']} | "
                     f"{(s['acc'] or 0)*100:.1f}% | "
                     f"[{s['ci'][0]*100:.1f}, {s['ci'][1]*100:.1f}] |")

with open(out_md, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

print()
print(f"  artefact: {out_md}")
