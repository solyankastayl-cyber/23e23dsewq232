#!/usr/bin/env python3
"""
predict_audit.py — Read-only honest audit of the TA Prediction Intelligence
predictive performance. Does NOT touch any service. Just SELECTs from Mongo
and computes the metrics that actually matter.

What it answers:
  1. Accuracy: of N evaluated predictions, how many called the direction right
     (predicted bias vs outcome.winning_scenario)?
  2. Calibration: when the system says "bull at p=0.6", does that bucket
     actually win 60% of the time?
  3. Brier score: mean squared error of the full 3-scenario probability
     vector vs one-hot outcome.
  4. Confidence quality: does HIGH `confidence` correlate with being right?
  5. By engine, symbol, timeframe.

No assumptions. No marketing. Just the numbers.
"""
import os
import math
import json
import statistics
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional
from pymongo import MongoClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def wilson(wins: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (centre - margin) / denom),
            min(1.0, (centre + margin) / denom))


def fmt_pct(x: Optional[float], width: int = 5) -> str:
    if x is None:
        return "—".rjust(width)
    return f"{x*100:>{width}.1f}%"


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
        "bias": 1, "confidence": 1, "conflict_ratio": 1,
        "dominant_engine": 1, "interaction": 1,
        "scenarios_calibrated": 1, "scenarios_original": 1,
        "outcome": 1, "created_at": 1,
        "decision_intelligence": 1,
    },
)
records: List[Dict[str, Any]] = list(cur)
N_total = len(records)


# ---------------------------------------------------------------------------
# Per-record derived fields
# ---------------------------------------------------------------------------
def winning_label(o: Dict[str, Any]) -> Optional[str]:
    if not isinstance(o, dict):
        return None
    w = o.get("winning_scenario")
    if w in ("bull", "bear", "base"):
        return w
    return None


def predicted_top(scenarios: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[float]]:
    """Return (top_scenario_name, its_probability)."""
    if not scenarios:
        return None, None
    best = max(scenarios, key=lambda s: s.get("probability") or 0.0)
    return best.get("name"), best.get("probability")


def scenario_probs(scenarios: List[Dict[str, Any]]) -> Dict[str, float]:
    out = {"bull": 0.0, "base": 0.0, "bear": 0.0}
    for s in scenarios or []:
        name = s.get("name")
        if name in out:
            out[name] = float(s.get("probability") or 0.0)
    return out


def bias_to_scenario(bias: Optional[str]) -> Optional[str]:
    if bias == "bullish":
        return "bull"
    if bias == "bearish":
        return "bear"
    if bias == "neutral":
        return "base"
    return None


# Augment records.
for r in records:
    r["winning"] = winning_label(r.get("outcome") or {})
    cal = r.get("scenarios_calibrated") or r.get("scenarios_original") or []
    r["top_name"], r["top_prob"] = predicted_top(cal)
    r["probs"] = scenario_probs(cal)
    r["bias_scenario"] = bias_to_scenario(r.get("bias"))


# Filter only those with a real outcome label.
records = [r for r in records if r["winning"]]
N = len(records)


# ---------------------------------------------------------------------------
# 1. DIRECTIONAL ACCURACY (3 ways, all reported, no cherry-picking)
# ---------------------------------------------------------------------------
# (a) bias == winning_scenario  (system's headline call vs reality)
# (b) top_scenario_in_calibrated == winning_scenario  (argmax of probs)
# (c) bull_or_bear vs base — directional vs flat call only
# ---------------------------------------------------------------------------
acc_bias = sum(1 for r in records if r["bias_scenario"] == r["winning"])
acc_top = sum(1 for r in records if r["top_name"] == r["winning"])

# Directional skill: filter base-out outcomes that the system can't "win"
# in a directional sense. Show both views for honesty.
dir_subset = [r for r in records if r["winning"] in ("bull", "bear")]
dir_acc_bias = sum(1 for r in dir_subset if r["bias_scenario"] == r["winning"])
dir_acc_top = sum(1 for r in dir_subset if r["top_name"] == r["winning"])

# Random baseline: 1/3 if uniform; or weight by class prior.
class_prior: Dict[str, int] = defaultdict(int)
for r in records:
    class_prior[r["winning"]] += 1
prior_p = {k: v / N for k, v in class_prior.items()}
# Dummy baselines.
majority_class = max(class_prior.items(), key=lambda kv: kv[1])[0]
acc_majority = sum(1 for r in records if r["winning"] == majority_class)
acc_random = N / 3.0  # expected if uniform


# ---------------------------------------------------------------------------
# 2. BRIER SCORE (multiclass)
# ---------------------------------------------------------------------------
def one_hot(label: str) -> Dict[str, float]:
    return {k: (1.0 if k == label else 0.0) for k in ("bull", "base", "bear")}


brier_sum = 0.0
brier_count = 0
for r in records:
    truth = one_hot(r["winning"])
    p = r["probs"]
    sq = sum((p[k] - truth[k]) ** 2 for k in truth)
    brier_sum += sq
    brier_count += 1
brier = (brier_sum / brier_count) if brier_count else None
# Reference: a uniform-1/3 forecast gives Brier = 2/3 ≈ 0.667.
# A perfect classifier = 0. A degenerate single-class predictor = 2.0.


# ---------------------------------------------------------------------------
# 3. CALIBRATION CURVE (per scenario, binned predicted prob vs hit rate)
# ---------------------------------------------------------------------------
def calibration_table(scenario: str) -> List[Dict[str, Any]]:
    bins = [
        (0.00, 0.10), (0.10, 0.20), (0.20, 0.30), (0.30, 0.40),
        (0.40, 0.50), (0.50, 0.60), (0.60, 0.70), (0.70, 0.80),
        (0.80, 0.90), (0.90, 1.01),
    ]
    out = []
    for lo, hi in bins:
        members = [r for r in records if lo <= r["probs"][scenario] < hi]
        n = len(members)
        wins = sum(1 for r in members if r["winning"] == scenario)
        avg_pred = (sum(r["probs"][scenario] for r in members) / n) if n else None
        hit = (wins / n) if n else None
        ci_lo, ci_hi = wilson(wins, n)
        out.append({
            "bin": f"[{lo:.2f},{hi:.2f})",
            "n": n, "wins": wins,
            "avg_pred": avg_pred,
            "hit_rate": hit,
            "ci": (ci_lo, ci_hi) if n else (None, None),
            "gap": (avg_pred - hit) if (avg_pred is not None and hit is not None) else None,
        })
    return out


def reliability_metrics(table: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    """Expected Calibration Error (ECE) and Maximum Calibration Error (MCE)."""
    total_n = sum(b["n"] for b in table)
    if total_n == 0:
        return {"ECE": None, "MCE": None}
    ece = 0.0
    mce = 0.0
    for b in table:
        if b["n"] == 0 or b["gap"] is None:
            continue
        gap = abs(b["gap"])
        ece += (b["n"] / total_n) * gap
        if gap > mce:
            mce = gap
    return {"ECE": ece, "MCE": mce}


cal_bull = calibration_table("bull")
cal_base = calibration_table("base")
cal_bear = calibration_table("bear")
rel_bull = reliability_metrics(cal_bull)
rel_base = reliability_metrics(cal_base)
rel_bear = reliability_metrics(cal_bear)


# ---------------------------------------------------------------------------
# 4. CONFIDENCE FIELD QUALITY
# ---------------------------------------------------------------------------
# r["confidence"] is the system's headline confidence number (0..1).
# Question: does higher headline conf -> higher accuracy of the bias call?
# ---------------------------------------------------------------------------
def conf_buckets() -> List[Dict[str, Any]]:
    bins = [(0.0, 0.45), (0.45, 0.55), (0.55, 0.65), (0.65, 0.75), (0.75, 1.01)]
    out = []
    for lo, hi in bins:
        members = [r for r in records
                   if r.get("confidence") is not None
                   and lo <= float(r["confidence"]) < hi]
        n = len(members)
        right = sum(1 for r in members if r["bias_scenario"] == r["winning"])
        ci_lo, ci_hi = wilson(right, n)
        out.append({
            "bin": f"[{lo:.2f},{hi:.2f})",
            "n": n,
            "acc": (right / n) if n else None,
            "ci": (ci_lo, ci_hi),
            "avg_conf": (statistics.mean(float(r["confidence"]) for r in members) if n else None),
        })
    return out


conf_table = conf_buckets()


# ---------------------------------------------------------------------------
# 5. BY ENGINE / SYMBOL / TIMEFRAME / INTERACTION
# ---------------------------------------------------------------------------
def group_acc(field: str) -> List[Dict[str, Any]]:
    groups: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        if field == "interaction":
            it = r.get("interaction") or {}
            key = it.get("type") if isinstance(it, dict) else None
            key = key or "none"
        else:
            key = r.get(field) or "unknown"
        groups[key].append(r)
    rows = []
    for k, members in groups.items():
        n = len(members)
        right = sum(1 for r in members if r["bias_scenario"] == r["winning"])
        right_top = sum(1 for r in members if r["top_name"] == r["winning"])
        # Brier on this subset.
        bsum = 0.0
        for r in members:
            t = one_hot(r["winning"])
            p = r["probs"]
            bsum += sum((p[x] - t[x]) ** 2 for x in t)
        bsubset = bsum / n if n else None
        ci_lo, ci_hi = wilson(right, n)
        rows.append({
            "key": k, "n": n,
            "acc_bias": right / n if n else None,
            "acc_top": right_top / n if n else None,
            "ci": (ci_lo, ci_hi),
            "brier": bsubset,
        })
    rows.sort(key=lambda x: -x["n"])
    return rows


by_engine = group_acc("dominant_engine")
by_symbol = group_acc("symbol")
by_timeframe = group_acc("timeframe")
by_interaction = group_acc("interaction")


# ---------------------------------------------------------------------------
# 6. CLASS DISTRIBUTION (so we don't get fooled by class imbalance)
# ---------------------------------------------------------------------------
predicted_dist: Dict[str, int] = defaultdict(int)
actual_dist: Dict[str, int] = defaultdict(int)
for r in records:
    predicted_dist[r["bias_scenario"] or "none"] += 1
    actual_dist[r["winning"]] += 1


# ---------------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------------
def print_section(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


print_section("TA PREDICTION INTELLIGENCE — HONEST AUDIT")
print(f"Total evaluated predictions in DB: N = {N}")
if N == 0:
    print("\nNothing to evaluate. Aborting.")
    raise SystemExit(0)
print(f"Outcome class distribution (the truth):")
for k in ("bull", "base", "bear"):
    n = actual_dist.get(k, 0)
    print(f"   {k:<5} N={n:>3}  ({n/N*100:5.1f}%)  prior_p={n/N:.3f}")
print(f"Predicted class distribution (the system's bias call):")
for k in ("bull", "base", "bear", "none"):
    n = predicted_dist.get(k, 0)
    if n:
        print(f"   {k:<5} N={n:>3}  ({n/N*100:5.1f}%)")

print_section("1) DIRECTIONAL ACCURACY")
ci_bias_lo, ci_bias_hi = wilson(acc_bias, N)
ci_top_lo, ci_top_hi = wilson(acc_top, N)
print(f"  Headline `bias` call vs winning_scenario:")
print(f"     accuracy = {acc_bias}/{N} = {acc_bias/N*100:.1f}%   "
      f"95% CI [{ci_bias_lo*100:.1f}, {ci_bias_hi*100:.1f}]")
print(f"  Argmax of `scenarios_calibrated` vs winning_scenario:")
print(f"     accuracy = {acc_top}/{N} = {acc_top/N*100:.1f}%   "
      f"95% CI [{ci_top_lo*100:.1f}, {ci_top_hi*100:.1f}]")
print()
print(f"  Baselines:")
print(f"     uniform random:     {1/3*100:5.1f}%")
print(f"     majority class ({majority_class}): {acc_majority/N*100:.1f}% "
      f"({acc_majority}/{N})")
if dir_subset:
    dN = len(dir_subset)
    print(f"\n  Directional-only subset (excluding actual {{base}} outcomes), N={dN}:")
    print(f"     bias-call accuracy: {dir_acc_bias}/{dN} = "
          f"{dir_acc_bias/dN*100:.1f}%")
    print(f"     argmax accuracy:    {dir_acc_top}/{dN} = "
          f"{dir_acc_top/dN*100:.1f}%")
    print(f"     random directional baseline: 50.0%")

print_section("2) BRIER SCORE (multiclass, lower is better)")
print(f"  Brier = {brier:.4f}   on N={brier_count}")
print(f"  Reference points:")
print(f"     0.000  perfect")
print(f"     0.667  uniform-1/3 forecaster")
print(f"     2.000  worst case (always wrong, prob=1)")
print(f"  Verdict: {'BETTER than uniform' if brier < 0.667 else 'WORSE than uniform'}"
      f" by {abs(0.667-brier)*100:.1f}pp")

print_section("3) CALIBRATION CURVES (predicted prob vs actual hit rate)")
def print_cal(name: str, table: List[Dict[str, Any]],
              rel: Dict[str, Optional[float]]):
    print(f"\n  --- scenario: {name.upper()} ---")
    print(f"  ECE = "
          f"{rel['ECE']*100:.1f}pp   MCE = {rel['MCE']*100:.1f}pp"
          if rel['ECE'] is not None else "  ECE/MCE: insufficient data")
    print(f"  {'bin':<14} {'N':>3} {'W':>2}  {'avg_pred':>9}  "
          f"{'hit_rate':>9}  {'95% CI':>16}  {'gap':>7}")
    for b in table:
        if b["n"] == 0:
            continue
        ci = (f"[{b['ci'][0]*100:5.1f},{b['ci'][1]*100:5.1f}]"
              if b['ci'][0] is not None else "—")
        gap = (f"{b['gap']*100:+6.1f}pp" if b['gap'] is not None else "—")
        print(f"  {b['bin']:<14} {b['n']:>3} {b['wins']:>2}  "
              f"{fmt_pct(b['avg_pred'],8)}  {fmt_pct(b['hit_rate'],8)}  "
              f"{ci:>16}  {gap:>7}")

print_cal("bull", cal_bull, rel_bull)
print_cal("base", cal_base, rel_base)
print_cal("bear", cal_bear, rel_bear)

print_section("4) HEADLINE `confidence` FIELD QUALITY")
print(f"  Does higher reported confidence -> higher bias-call accuracy?")
print(f"  {'bin':<16} {'N':>3}  {'avg_conf':>9}  {'acc':>9}  {'95% CI':>16}")
for b in conf_table:
    if b["n"] == 0:
        continue
    ci = f"[{b['ci'][0]*100:5.1f},{b['ci'][1]*100:5.1f}]"
    print(f"  {b['bin']:<16} {b['n']:>3}  {fmt_pct(b['avg_conf'],8)}  "
          f"{fmt_pct(b['acc'],8)}  {ci:>16}")

print_section("5) BREAKDOWN BY DIMENSION")
def print_breakdown(title: str, rows: List[Dict[str, Any]]):
    print(f"\n  --- {title} ---")
    print(f"  {'key':<20} {'N':>3}  {'acc_bias':>9}  {'acc_top':>9}  "
          f"{'95% CI (bias)':>16}  {'brier':>7}")
    for r in rows:
        ci = f"[{r['ci'][0]*100:5.1f},{r['ci'][1]*100:5.1f}]"
        br = f"{r['brier']:.3f}" if r['brier'] is not None else "—"
        print(f"  {str(r['key']):<20} {r['n']:>3}  "
              f"{fmt_pct(r['acc_bias'],8)}  {fmt_pct(r['acc_top'],8)}  "
              f"{ci:>16}  {br:>7}")

print_breakdown("by dominant_engine", by_engine)
print_breakdown("by symbol", by_symbol)
print_breakdown("by timeframe", by_timeframe)
print_breakdown("by interaction.type", by_interaction)

print_section("6) WHAT THE NUMBERS MEAN (plain reading)")
verdict_bias = "WORSE" if (acc_bias/N) < 1/3 else ("BETTER" if (acc_bias/N) > 1/3 else "EQUAL TO")
verdict_brier = "WORSE" if brier > 0.667 else ("BETTER" if brier < 0.667 else "EQUAL TO")
print(f"  Sample size: N={N} evaluated predictions in `ta_prediction_history`.")
print(f"  Direction call accuracy: {acc_bias/N*100:.1f}% ({verdict_bias} than 1/3 random).")
print(f"  Probability calibration:")
ece_avg = []
for nm, rel in (("bull", rel_bull), ("base", rel_base), ("bear", rel_bear)):
    if rel['ECE'] is not None:
        print(f"     {nm}: ECE={rel['ECE']*100:5.1f}pp, MCE={rel['MCE']*100:5.1f}pp")
        ece_avg.append(rel['ECE'])
if ece_avg:
    avg = sum(ece_avg)/len(ece_avg)
    print(f"     avg ECE across scenarios = {avg*100:.1f}pp")
    print(f"     interpretation: ECE<5pp = well-calibrated, "
          f"5-15pp = miscalibrated, >15pp = strongly miscalibrated")
print(f"  Brier score: {brier:.4f} ({verdict_brier} than uniform-1/3 forecaster).")

# Check headline confidence monotonicity.
non_empty = [b for b in conf_table if b["n"] > 0]
mono = "n/a"
if len(non_empty) >= 2:
    accs = [b["acc"] for b in non_empty]
    deltas = [accs[i+1]-accs[i] for i in range(len(accs)-1)]
    if all(d >= -0.01 for d in deltas):
        mono = "MONOTONIC ↑ (higher conf → higher accuracy, as it should)"
    elif all(d <= 0.01 for d in deltas):
        mono = "MONOTONIC ↓ (higher conf → LOWER accuracy — calibration broken)"
    else:
        mono = "NON-MONOTONIC (confidence does not track accuracy reliably)"
print(f"  Headline `confidence` field monotonicity: {mono}")

# Final flat verdict.
print_section("BOTTOM LINE")
print(f"  N = {N} (this is the total ground we can stand on)")
print(f"  Direction accuracy: {acc_bias/N*100:.1f}%   "
      f"95% CI [{ci_bias_lo*100:.1f}, {ci_bias_hi*100:.1f}]")
print(f"  Brier (3-class):     {brier:.3f}   (uniform = 0.667, perfect = 0)")
ece_vals = [r['ECE'] for r in (rel_bull, rel_base, rel_bear) if r['ECE'] is not None]
if ece_vals:
    print(f"  Avg ECE:            {sum(ece_vals)/len(ece_vals)*100:.1f}pp")
print()
print(f"  `confidence` column meaning (current):")
print(f"     it is the AGGREGATOR's blended bias score, NOT the calibrated")
print(f"     probability of the top scenario being right.")
print(f"     For 'how sure should I be?' the right number is the top")
print(f"     scenario's `probability` in scenarios_calibrated[].")
print()
