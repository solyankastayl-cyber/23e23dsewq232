#!/usr/bin/env python3
"""
forensic_scenario_targets.py — read-only audit of scenario target geometry.

Purpose: after FIX-RESOLVER-1+2 left the bull/base/bear distribution
essentially unchanged (36→38 bull, 0→0 base), the bias source must be
upstream of the resolver. The most likely upstream lever is the
target/invalidation geometry coming out of scenario_builder.

This script answers, for each record in ta_prediction_history:

    bull_distance_pct = (bull_target - entry) / entry
    bear_distance_pct = (entry - bear_target) / entry
    asymmetry         = bull_distance_pct - bear_distance_pct

If asymmetry is systematically positive (bull farther) we expect MORE
bear wins (closer target hit first); if systematically negative (bull
closer) we expect MORE bull wins. ETH=0/12-bull is a special focus.

Strictly read-only. No Mongo writes. No service touched.
Outputs:
    /tmp/forensic_scenario_targets_report.md
    /tmp/forensic_scenario_targets.jsonl
    plus stdout digest tables.
"""
from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        v = float(x)
        if v != v or v in (float("inf"), float("-inf")):
            return None
        return v
    except (TypeError, ValueError):
        return None


def fmt_pct(v: Optional[float], width: int = 7) -> str:
    if v is None:
        return "—".rjust(width)
    return f"{v*100:+{width-1}.4f}%"


def quartiles(values: List[float]) -> Tuple[float, float, float]:
    """Return (q25, q50, q75) using linear interpolation."""
    if not values:
        return (0.0, 0.0, 0.0)
    s = sorted(values)
    n = len(s)
    def q(p: float) -> float:
        if n == 1:
            return s[0]
        idx = p * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return s[lo] + (s[hi] - s[lo]) * frac
    return (q(0.25), q(0.50), q(0.75))


def extract_targets(scenarios: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    """Pull (bull_target, bear_target, bull_inv, bear_inv) from scenario list."""
    out = {"t_bull": None, "t_bear": None, "inv_bull": None, "inv_bear": None,
           "p_bull": None, "p_base": None, "p_bear": None}
    for s in scenarios or []:
        name = str(s.get("name") or "").lower()
        if name == "bull":
            out["t_bull"] = safe_float(s.get("target_price"))
            out["inv_bull"] = safe_float(s.get("invalidation_price"))
            out["p_bull"] = safe_float(s.get("probability"))
        elif name == "bear":
            out["t_bear"] = safe_float(s.get("target_price"))
            out["inv_bear"] = safe_float(s.get("invalidation_price"))
            out["p_bear"] = safe_float(s.get("probability"))
        elif name == "base":
            out["p_base"] = safe_float(s.get("probability"))
    return out


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
mc = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
db = mc[os.environ.get("DB_NAME", "trading_os")]

cur = db.ta_prediction_history.find(
    {"evaluation_state": "evaluated", "outcome": {"$ne": None}},
    {
        "_id": 0,
        "prediction_id": 1, "symbol": 1, "timeframe": 1,
        "entry_price": 1,
        "bias": 1, "confidence": 1, "dominant_engine": 1, "interaction": 1,
        "scenarios_calibrated": 1, "scenarios_interaction_adjusted": 1,
        "scenarios_original": 1, "outcome": 1,
    },
)
records = list(cur)
N = len(records)


# ---------------------------------------------------------------------------
# Per-record derived rows
# ---------------------------------------------------------------------------
def make_row(r: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    entry = safe_float(r.get("entry_price"))
    if entry is None or entry <= 0:
        return None

    # Use the same scenario list the resolver actually consumes.
    scenarios = (
        r.get("scenarios_interaction_adjusted")
        or r.get("scenarios_original")
        or []
    )
    # Calibrated set may carry the same targets — check it independently
    # for cross-validation.
    cal = r.get("scenarios_calibrated") or []

    t = extract_targets(scenarios)
    t_cal = extract_targets(cal)

    bull_dist = None
    bear_dist = None
    if t["t_bull"] is not None:
        bull_dist = (t["t_bull"] - entry) / entry
    if t["t_bear"] is not None:
        bear_dist = (entry - t["t_bear"]) / entry
    asymmetry = (
        (bull_dist - bear_dist) if (bull_dist is not None and bear_dist is not None)
        else None
    )
    inv_bull_dist = (
        (entry - t["inv_bull"]) / entry if t["inv_bull"] is not None else None
    )
    inv_bear_dist = (
        (t["inv_bear"] - entry) / entry if t["inv_bear"] is not None else None
    )

    outcome = r.get("outcome") or {}
    interaction = r.get("interaction") or {}
    interaction_type = (
        interaction.get("type") if isinstance(interaction, dict) else None
    ) or "none"

    bias = r.get("bias")
    if bias == "bullish":
        predicted = "bull"
    elif bias == "bearish":
        predicted = "bear"
    elif bias == "neutral":
        predicted = "base"
    else:
        predicted = None

    return {
        "prediction_id": r.get("prediction_id"),
        "symbol": r.get("symbol"),
        "timeframe": r.get("timeframe"),
        "dominant_engine": r.get("dominant_engine"),
        "interaction_type": interaction_type,
        "confidence": safe_float(r.get("confidence")),
        "entry_price": entry,
        "t_bull": t["t_bull"],
        "t_bear": t["t_bear"],
        "inv_bull": t["inv_bull"],
        "inv_bear": t["inv_bear"],
        "bull_distance_pct": bull_dist,
        "bear_distance_pct": bear_dist,
        "asymmetry": asymmetry,
        "inv_bull_distance_pct": inv_bull_dist,
        "inv_bear_distance_pct": inv_bear_dist,
        "p_bull": t["p_bull"],
        "p_base": t["p_base"],
        "p_bear": t["p_bear"],
        "p_bull_cal": t_cal["p_bull"],
        "p_bear_cal": t_cal["p_bear"],
        "p_base_cal": t_cal["p_base"],
        "winning_scenario": (outcome.get("winning_scenario") or "").lower() or None,
        "predicted_scenario": predicted,
        "return_h6": safe_float(outcome.get("return_h6")),
        "max_fav_pct": safe_float(outcome.get("max_favourable_move_pct")),
        "max_adv_pct": safe_float(outcome.get("max_adverse_move_pct")),
        "vol_future_h6": safe_float(outcome.get("volatility_future_h6")),
    }


rows = [r for r in (make_row(rec) for rec in records) if r]
N_rows = len(rows)


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------
def _agg(members: List[Dict[str, Any]], field: str) -> Dict[str, Optional[float]]:
    vals = [m[field] for m in members if m.get(field) is not None]
    if not vals:
        return {"avg": None, "median": None, "min": None, "max": None,
                "q25": None, "q75": None, "n": 0}
    q25, q50, q75 = quartiles(vals)
    return {
        "avg": statistics.mean(vals),
        "median": q50,
        "min": min(vals),
        "max": max(vals),
        "q25": q25,
        "q75": q75,
        "n": len(vals),
    }


def group_by(rows: List[Dict[str, Any]], key: str) -> Dict[Any, List[Dict[str, Any]]]:
    g: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        g[r.get(key) or "—"].append(r)
    return g


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------
def fmt_agg(a: Dict[str, Optional[float]]) -> str:
    if a["n"] == 0:
        return "—"
    return (f"avg={fmt_pct(a['avg'],8)} "
            f"med={fmt_pct(a['median'],8)} "
            f"q25={fmt_pct(a['q25'],8)} "
            f"q75={fmt_pct(a['q75'],8)} "
            f"min={fmt_pct(a['min'],8)} "
            f"max={fmt_pct(a['max'],8)}")


def print_section(title: str):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_dim_table(title: str, groups: Dict[Any, List[Dict[str, Any]]]):
    print(f"\n--- {title} ---")
    print(f"  {'group':<14} {'N':>3}   "
          f"{'avg bull_dist':>15} {'avg bear_dist':>15} {'avg asymmetry':>15}  "
          f"{'med asym':>10}")
    for k, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        b = _agg(members, "bull_distance_pct")
        be = _agg(members, "bear_distance_pct")
        sy = _agg(members, "asymmetry")
        print(f"  {str(k):<14} {len(members):>3}   "
              f"{fmt_pct(b['avg']):>15} {fmt_pct(be['avg']):>15} "
              f"{fmt_pct(sy['avg']):>15}  "
              f"{fmt_pct(sy['median']):>10}")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
print_section(f"SCENARIO TARGET GEOMETRY — N={N_rows}/{N} replayable")
if N_rows == 0:
    print("Nothing to inspect.")
    raise SystemExit(0)

# 1) Overall summary
print_section("1) OVERALL — bull_distance, bear_distance, asymmetry")
print(f"  bull_distance_pct (entry → t_bull, positive)")
print(f"     {fmt_agg(_agg(rows, 'bull_distance_pct'))}")
print(f"  bear_distance_pct (entry → t_bear, positive)")
print(f"     {fmt_agg(_agg(rows, 'bear_distance_pct'))}")
print(f"  asymmetry = bull_dist - bear_dist")
print(f"     {fmt_agg(_agg(rows, 'asymmetry'))}")
print(f"  invalidation_bull_dist (entry → inv_bull)")
print(f"     {fmt_agg(_agg(rows, 'inv_bull_distance_pct'))}")
print(f"  invalidation_bear_dist (inv_bear → entry)")
print(f"     {fmt_agg(_agg(rows, 'inv_bear_distance_pct'))}")

# 2) By symbol
print_section("2) BY SYMBOL  (red flag: ETH = 0 bull wins / 12)")
sym_groups = group_by(rows, "symbol")
for sym, members in sorted(sym_groups.items(), key=lambda kv: -len(kv[1])):
    out_count = defaultdict(int)
    pred_count = defaultdict(int)
    for m in members:
        out_count[m["winning_scenario"] or "—"] += 1
        pred_count[m["predicted_scenario"] or "—"] += 1
    print(f"\n  --- {sym}  N={len(members)} ---")
    print(f"  outcome  : {dict(out_count)}")
    print(f"  predicted: {dict(pred_count)}")
    b = _agg(members, "bull_distance_pct")
    be = _agg(members, "bear_distance_pct")
    sy = _agg(members, "asymmetry")
    iv_b = _agg(members, "inv_bull_distance_pct")
    iv_be = _agg(members, "inv_bear_distance_pct")
    print(f"  bull_dist   {fmt_agg(b)}")
    print(f"  bear_dist   {fmt_agg(be)}")
    print(f"  asymmetry   {fmt_agg(sy)}")
    print(f"  inv_bull_d  {fmt_agg(iv_b)}")
    print(f"  inv_bear_d  {fmt_agg(iv_be)}")

# 3) By outcome (winning_scenario)
print_section("3) BY OUTCOME (winning_scenario)")
print_dim_table("by winning_scenario", group_by(rows, "winning_scenario"))

# 4) By predicted bias
print_section("4) BY PREDICTED BIAS (system's call, before outcome)")
print_dim_table("by predicted_scenario", group_by(rows, "predicted_scenario"))

# 5) By dominant_engine
print_section("5) BY DOMINANT ENGINE")
print_dim_table("by dominant_engine", group_by(rows, "dominant_engine"))

# 6) By interaction_type
print_section("6) BY INTERACTION TYPE")
print_dim_table("by interaction_type", group_by(rows, "interaction_type"))

# 7) Cross — symbol × outcome
print_section("7) CROSS — symbol × outcome (where geometry meets reality)")
print(f"  {'symbol':<10} {'outcome':<6} {'N':>3}  "
      f"{'avg bull_d':>11} {'avg bear_d':>11} {'avg asym':>10}")
for sym, mem in sorted(sym_groups.items()):
    by_out = group_by(mem, "winning_scenario")
    for out_label, sub in sorted(by_out.items()):
        b = _agg(sub, "bull_distance_pct")
        be = _agg(sub, "bear_distance_pct")
        sy = _agg(sub, "asymmetry")
        print(f"  {sym:<10} {str(out_label):<6} {len(sub):>3}  "
              f"{fmt_pct(b['avg']):>11} {fmt_pct(be['avg']):>11} "
              f"{fmt_pct(sy['avg']):>10}")

# 8) Mechanical edge: who would have won if first-touch were random
# Useful sanity check: if bull/bear distances are equal, expected p_bull_win = 0.5;
# if bull is closer, expected p_bull_win > 0.5 mechanically.
print_section("8) MECHANICAL FIRST-TOUCH PROBABILITY (geometric)")
print(f"  If price walks a symmetric random walk and only bull/bear targets")
print(f"  matter (no invalidation), prob bull hit FIRST equals")
print(f"     bear_dist / (bull_dist + bear_dist)")
print(f"  This is the geometric prior. Compare to the actual bull win rate.")
print()
geom = []
for m in rows:
    bd = m["bull_distance_pct"]
    sd = m["bear_distance_pct"]
    if bd is None or sd is None or bd <= 0 or sd <= 0:
        continue
    p_geom = sd / (bd + sd)
    geom.append({
        "p_bull_geom": p_geom,
        "actual_bull": m["winning_scenario"] == "bull",
    })
if geom:
    avg_geom_bull_p = sum(g["p_bull_geom"] for g in geom) / len(geom)
    actual_bull_rate = sum(1 for g in geom if g["actual_bull"]) / len(geom)
    print(f"  N samples with valid geometry: {len(geom)}")
    print(f"  Avg geometric P(bull hits first):  {avg_geom_bull_p*100:5.1f}%")
    print(f"  Actual bull-win rate:              {actual_bull_rate*100:5.1f}%")
    delta = (actual_bull_rate - avg_geom_bull_p) * 100
    if abs(delta) < 5:
        verdict = "≈ matches geometric prior — bias is GEOMETRY"
    elif delta > 5:
        verdict = "ABOVE geometric prior — extra bull bias from market drift / engines"
    else:
        verdict = "BELOW geometric prior — bear pressure dominates"
    print(f"  Δ = {delta:+.1f}pp   →   {verdict}")
    # Per symbol.
    by_sym = defaultdict(list)
    for m, g in zip([x for x in rows
                     if x["bull_distance_pct"] is not None
                     and x["bear_distance_pct"] is not None
                     and x["bull_distance_pct"] > 0
                     and x["bear_distance_pct"] > 0], geom):
        by_sym[m["symbol"]].append((m, g))
    print()
    for sym, items in by_sym.items():
        avg_geom = sum(g["p_bull_geom"] for _, g in items) / len(items)
        actual = sum(1 for _, g in items if g["actual_bull"]) / len(items)
        print(f"    {sym:<10} N={len(items):<3}  "
              f"geom P(bull)={avg_geom*100:5.1f}%   "
              f"actual bull rate={actual*100:5.1f}%   "
              f"Δ={(actual - avg_geom)*100:+5.1f}pp")

# 9) Per-record listing — extreme asymmetries
print_section("9) TOP 10 LARGEST ASYMMETRIES")
print(f"  asymmetry > 0 → bull target FARTHER, bear hit easier")
print(f"  asymmetry < 0 → bull target CLOSER, bull hit easier")
ranked = sorted(
    [r for r in rows if r["asymmetry"] is not None],
    key=lambda r: abs(r["asymmetry"]),
    reverse=True,
)
print()
print(f"  {'pid':<22} {'sym':<8} {'pred':<5} {'out':<5} {'bull_d':>9} "
      f"{'bear_d':>9} {'asym':>9}")
for r in ranked[:10]:
    pid = (r["prediction_id"] or "")[:22]
    print(f"  {pid:<22} {r['symbol']:<8} "
          f"{(r['predicted_scenario'] or '—'):<5} "
          f"{(r['winning_scenario'] or '—'):<5} "
          f"{fmt_pct(r['bull_distance_pct']):>9} "
          f"{fmt_pct(r['bear_distance_pct']):>9} "
          f"{fmt_pct(r['asymmetry']):>9}")

# 10) ETH zoom (red flag)
print_section("10) ETH ZOOM — full record listing (the 0/12 anomaly)")
eth = [r for r in rows if r["symbol"] == "ETHUSDT"]
if eth:
    print(f"  {'pid':<22} {'pred':<5} {'out':<5} {'bull_d':>9} "
          f"{'bear_d':>9} {'asym':>9} {'ret_h6':>9} {'engine':<10}")
    for r in eth:
        pid = (r["prediction_id"] or "")[:22]
        rh = r["return_h6"]
        rh_s = fmt_pct(rh, 8) if rh is not None else "—".rjust(8)
        print(f"  {pid:<22} "
              f"{(r['predicted_scenario'] or '—'):<5} "
              f"{(r['winning_scenario'] or '—'):<5} "
              f"{fmt_pct(r['bull_distance_pct']):>9} "
              f"{fmt_pct(r['bear_distance_pct']):>9} "
              f"{fmt_pct(r['asymmetry']):>9} "
              f"{rh_s:>9} "
              f"{(r['dominant_engine'] or '—'):<10}")
else:
    print("  no ETH rows.")


# ---------------------------------------------------------------------------
# Persist artefacts
# ---------------------------------------------------------------------------
out_jsonl = "/tmp/forensic_scenario_targets.jsonl"
with open(out_jsonl, "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write(json.dumps(r, default=str) + "\n")

# Markdown summary.
md_lines = [f"# Scenario Target Geometry — N={N_rows}\n"]
md_lines.append("## 1) Overall\n")
def md_agg(label, field):
    a = _agg(rows, field)
    if a["n"] == 0:
        return f"- **{label}**: N=0\n"
    return (f"- **{label}**: avg={a['avg']*100:+.4f}%  "
            f"med={a['median']*100:+.4f}%  "
            f"q25={a['q25']*100:+.4f}%  q75={a['q75']*100:+.4f}%  "
            f"min={a['min']*100:+.4f}%  max={a['max']*100:+.4f}%  N={a['n']}\n")
md_lines.append(md_agg("bull_distance_pct", "bull_distance_pct"))
md_lines.append(md_agg("bear_distance_pct", "bear_distance_pct"))
md_lines.append(md_agg("asymmetry (bull - bear)", "asymmetry"))
md_lines.append(md_agg("inv_bull_distance_pct", "inv_bull_distance_pct"))
md_lines.append(md_agg("inv_bear_distance_pct", "inv_bear_distance_pct"))
md_lines.append("\n## 2) By symbol\n")
md_lines.append("| symbol | N | avg bull_d | avg bear_d | avg asym | bull_wr |")
md_lines.append("|---|---|---|---|---|---|")
for sym, members in sorted(sym_groups.items(), key=lambda kv: -len(kv[1])):
    b = _agg(members, "bull_distance_pct")
    be = _agg(members, "bear_distance_pct")
    sy = _agg(members, "asymmetry")
    bw = sum(1 for m in members if m["winning_scenario"] == "bull")
    md_lines.append(f"| {sym} | {len(members)} | {fmt_pct(b['avg'])} | "
                    f"{fmt_pct(be['avg'])} | {fmt_pct(sy['avg'])} | "
                    f"{bw}/{len(members)} = {bw/len(members)*100:.1f}% |")

with open("/tmp/forensic_scenario_targets_report.md", "w", encoding="utf-8") as fh:
    fh.write("\n".join(md_lines))

print()
print("=" * 80)
print(f"artefacts:")
print(f"  /tmp/forensic_scenario_targets_report.md")
print(f"  /tmp/forensic_scenario_targets.jsonl")
