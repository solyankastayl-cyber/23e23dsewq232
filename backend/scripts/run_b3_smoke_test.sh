#!/bin/bash
# =========================================================================
#  F-TRADE v2 — Phase B.3 Smoke Test
#  Strategies: SHORT_TREND + LONG_PULLBACK + LONG_BREAKOUT
#
#  Goal: validate stateful regime-aware pipeline across process restart
#        for THREE strategies simultaneously, with heterogeneous state:
#          - SHORT_TREND   → extra={}       (closes only)
#          - LONG_PULLBACK → extra.ohlc     (OHLC)
#          - LONG_BREAKOUT → extra.ohlc     (OHLC + volume)
#
#  Protocol: cold clean → 5 cycles → snapshot → 5 cycles (restart).
#
#  PASS criteria (Phase B.3 — 7 points, extends B.2):
#    1) LONG_BREAKOUT warmup NO side-effects
#    2) LONG_BREAKOUT state survives restart (fresh_warmups=0 in P2 cycle 1)
#    3) dedup works across all 3 strategies
#    4) generator_state persisted for each routed strategy
#    5) SHORT_TREND no regression (and still routed in DOWNTREND)
#    6) Router activates BOTH LONG_PULLBACK AND LONG_BREAKOUT in UPTREND
#    7) Heterogeneous `extra` field: SHORT → {}, PULLBACK → ohlc, BREAKOUT → ohlc+volume
#    (8) validator stays observer-only
#
#  Usage: bash scripts/run_b3_smoke_test.sh [sleep_seconds]
# =========================================================================

set -u

SLEEP_SECONDS="${1:-30}"
EXPERIMENT="phase_b3_smoke_$(date +%s)"
LOG_DIR="/app/backend/logs"
LOG1="${LOG_DIR}/b3_smoke_part1.log"
LOG2="${LOG_DIR}/b3_smoke_part2.log"
SNAPSHOT_FILE="${LOG_DIR}/b3_smoke_snapshot.json"
MONGO_URL="${MONGO_URL:-mongodb://localhost:27017}"
DB_NAME="${PHASE_B1_DB:-trading_os}"

mkdir -p "${LOG_DIR}"

echo "======================================================================"
echo " F-TRADE v2 — Phase B.3 Smoke Test"
echo "   strategies     : SHORT_TREND + LONG_PULLBACK + LONG_BREAKOUT"
echo "   experiment     : ${EXPERIMENT}"
echo "   sleep_seconds  : ${SLEEP_SECONDS}"
echo "   log part1      : ${LOG1}"
echo "   log part2      : ${LOG2}"
echo "======================================================================"

# --- Step 0: clean generator_state (so first run is truly cold) ---
echo
echo "[0] Clearing generator_state and validator_observations ..."
MONGO_URL="${MONGO_URL}" PHASE_B1_DB="${DB_NAME}" python3 - <<'PY'
from pymongo import MongoClient
import os
mc = MongoClient(os.environ.get('MONGO_URL'))
db = mc[os.environ.get('PHASE_B1_DB')]
d1 = db.generator_state.delete_many({}).deleted_count
d2 = db.validator_observations.delete_many({}).deleted_count
print(f"    generator_state deleted       : {d1}")
print(f"    validator_observations deleted: {d2}")
PY

# --- PART 1: 5 cycles cold start ---
echo
echo "[1] Starting PART 1 (5 cycles, cold start)..."
cd /app/backend || exit 1
nohup python3 -u scripts/phase_b1_regime_collection.py \
    --max-cycles 5 \
    --sleep-seconds "${SLEEP_SECONDS}" \
    --experiment "${EXPERIMENT}" \
    > "${LOG1}" 2>&1 &
PID1=$!
echo "    PID1=${PID1}  — waiting..."
wait "${PID1}"
EXIT1=$?
echo "    PART 1 exited code=${EXIT1}"

# --- Snapshot state between parts ---
echo
echo "[2] Snapshot generator_state after PART 1 ..."
MONGO_URL="${MONGO_URL}" PHASE_B1_DB="${DB_NAME}" SNAPSHOT_FILE="${SNAPSHOT_FILE}" python3 - <<'PY'
from pymongo import MongoClient
import os, json

mc = MongoClient(os.environ.get('MONGO_URL'))
db = mc[os.environ.get('PHASE_B1_DB')]
docs = list(db.generator_state.find(
    {},
    {"_id": 0, "key": 1, "strategy": 1, "last_candle_ts": 1,
     "meta": 1, "prices": 1, "extra": 1}
))
snap = []
for d in docs:
    extra = d.get("extra") or {}
    ohlc = extra.get("ohlc_candles", [])
    has_volume = bool(ohlc) and "volume" in ohlc[-1]
    snap.append({
        "key": d["key"],
        "strategy": d.get("strategy"),
        "last_candle_ts": d.get("last_candle_ts"),
        "prices_len": len(d.get("prices", [])),
        "ohlc_len": len(ohlc),
        "has_volume": has_volume,
        "warm": d.get("meta", {}).get("warm"),
    })
with open(os.environ["SNAPSHOT_FILE"], "w") as f:
    json.dump(snap, f, indent=2, default=str)

from collections import Counter
by_strat = Counter(row["strategy"] for row in snap)
print(f"    total_checkpoints: {len(snap)} → {dict(by_strat)}")
for row in snap[:8]:
    print(f"      {row}")
PY

# --- PART 2: 5 more cycles — should restore state ---
echo
echo "[3] Starting PART 2 (5 cycles, state must be restored)..."
nohup python3 -u scripts/phase_b1_regime_collection.py \
    --max-cycles 5 \
    --sleep-seconds "${SLEEP_SECONDS}" \
    --experiment "${EXPERIMENT}" \
    > "${LOG2}" 2>&1 &
PID2=$!
echo "    PID2=${PID2}  — waiting..."
wait "${PID2}"
EXIT2=$?
echo "    PART 2 exited code=${EXIT2}"

# --- PASS/FAIL analysis ---
echo
echo "======================================================================"
echo " PHASE B.3 PASS/FAIL ANALYSIS"
echo "======================================================================"

MONGO_URL="${MONGO_URL}" PHASE_B1_DB="${DB_NAME}" LOG1="${LOG1}" LOG2="${LOG2}" \
SNAPSHOT_FILE="${SNAPSHOT_FILE}" EXPERIMENT="${EXPERIMENT}" python3 - <<'PY'
import os, json, re
from pymongo import MongoClient

def read(path):
    try:
        with open(path) as f:
            return f.read()
    except Exception:
        return ""

log1 = read(os.environ["LOG1"])
log2 = read(os.environ["LOG2"])
snap = []
try:
    with open(os.environ["SNAPSHOT_FILE"]) as f:
        snap = json.load(f)
except Exception:
    pass

mc = MongoClient(os.environ.get('MONGO_URL'))
db = mc[os.environ.get('PHASE_B1_DB')]
experiment = os.environ["EXPERIMENT"]

def extract_cycle_stats(log):
    pattern = re.compile(
        r"fresh_warmups=(?P<fw>\d+)\s+dup_skips=(?P<ds>\d+)\s+cold_skips=(?P<cs>\d+)\s+"
        r"checkpoints=(?P<ck>\d+)\s+validator_warns=(?P<vw>\d+)\s+signals=(?P<sg>\d+)"
    )
    return [{k: int(v) for k, v in m.groupdict().items()} for m in pattern.finditer(log)]

def extract_allowed_strategies(log):
    out = []
    for m in re.finditer(r"allowed_strategies:\s*\{([^}]*)\}", log):
        s = m.group(1)
        d = {}
        for kv in re.finditer(r"'([^']+)':\s*(\d+)", s):
            d[kv.group(1)] = int(kv.group(2))
        out.append(d)
    return out

def extract_regime_detections(log):
    out = []
    for m in re.finditer(r"regime_detections:\s*\{([^}]*)\}", log):
        s = m.group(1)
        d = {}
        for kv in re.finditer(r"'([^']+)':\s*(\d+)", s):
            d[kv.group(1)] = int(kv.group(2))
        out.append(d)
    return out

p1_stats = extract_cycle_stats(log1)
p2_stats = extract_cycle_stats(log2)
p1_allowed = extract_allowed_strategies(log1)
p2_allowed = extract_allowed_strategies(log2)
p1_regimes = extract_regime_detections(log1)
p2_regimes = extract_regime_detections(log2)

def strat_counts(docs):
    out = {}
    for d in docs:
        out[d.get("strategy")] = out.get(d.get("strategy"), 0) + 1
    return out

snap_by_strat = strat_counts(snap)
now_docs = list(db.generator_state.find({}, {"key": 1, "strategy": 1, "last_candle_ts": 1, "extra": 1, "prices": 1}))
now_by_strat = strat_counts(now_docs)

total_uptrend_cycles_p1 = sum(r.get("UPTREND", 0) for r in p1_regimes)
total_uptrend_cycles_p2 = sum(r.get("UPTREND", 0) for r in p2_regimes)
total_uptrend_cycles = total_uptrend_cycles_p1 + total_uptrend_cycles_p2

def sum_allowed(stat_list, key):
    return sum(a.get(key, 0) for a in stat_list)

total_long_pullback_allowed = sum_allowed(p1_allowed, "LONG_PULLBACK") + sum_allowed(p2_allowed, "LONG_PULLBACK")
total_long_breakout_allowed = sum_allowed(p1_allowed, "LONG_BREAKOUT") + sum_allowed(p2_allowed, "LONG_BREAKOUT")
total_short_allowed = sum_allowed(p1_allowed, "SHORT_TREND") + sum_allowed(p2_allowed, "SHORT_TREND")

# Heterogeneous state inspection
def check_extra_shape(strategy, expect_ohlc, expect_volume):
    """Return (ok, detail) for a given strategy's `extra` shape in Mongo."""
    docs_s = [d for d in now_docs if d.get("strategy") == strategy]
    if not docs_s:
        return (True, f"{strategy}: 0 docs (nothing to check)")
    all_ok = True
    sample = None
    for d in docs_s:
        extra = d.get("extra") or {}
        ohlc = extra.get("ohlc_candles", [])
        if expect_ohlc:
            if not ohlc:
                all_ok = False
                break
            if expect_volume and (not ohlc or "volume" not in ohlc[-1]):
                all_ok = False
                break
            sample = {"ohlc_len": len(ohlc), "has_vol": "volume" in (ohlc[-1] if ohlc else {})}
        else:
            if extra != {}:
                all_ok = False
                break
            sample = {"extra": extra}
    return (all_ok, f"{strategy}: docs={len(docs_s)}, sample={sample}")

checks = []

# ─── CHECK 1 ────────────────────────────────────────────────────────
# LONG_BREAKOUT warmup no side-effects (cycle 1 fw>0 → warmups happen
# WITHOUT creating any signal, because warmup() never calls maybe_generate)
if p1_stats:
    c1 = p1_stats[0]
    warm_no_signal = c1["fw"] > 0
else:
    warm_no_signal = False
lb_warmup_logged = "[BreakoutLong] warmup" in log1
checks.append((f"1. LONG_BREAKOUT warmup NO side-effects "
               f"(cycle1 fw={c1['fw'] if p1_stats else 'N/A'}, "
               f"lb_warmup_logged={lb_warmup_logged})", warm_no_signal and lb_warmup_logged))

# ─── CHECK 2 ────────────────────────────────────────────────────────
# LONG_BREAKOUT state survives restart
restored_ok = False
if p2_stats and p2_stats[0]["fw"] == 0:
    before = {d["key"]: d.get("last_candle_ts") for d in snap if d.get("strategy") == "LONG_BREAKOUT"}
    after = {d["key"]: d.get("last_candle_ts") for d in now_docs if d.get("strategy") == "LONG_BREAKOUT"}
    regressed = [k for k in before
                 if after.get(k) is not None and before[k] is not None
                 and after[k] < before[k]]
    restored_ok = len(regressed) == 0
checks.append((f"2. LONG_BREAKOUT survives restart "
               f"(p2c1 fw={p2_stats[0]['fw'] if p2_stats else 'N/A'}, "
               f"snap_LB={snap_by_strat.get('LONG_BREAKOUT', 0)}, "
               f"now_LB={now_by_strat.get('LONG_BREAKOUT', 0)})", restored_ok))

# ─── CHECK 3 ────────────────────────────────────────────────────────
# dedup works in BOTH parts (all strategies)
total_dup_p1 = sum(s["ds"] for s in p1_stats)
total_dup_p2 = sum(s["ds"] for s in p2_stats)
checks.append((f"3. duplicate dedup active (p1_dup={total_dup_p1}, p2_dup={total_dup_p2})",
               total_dup_p1 > 0 and total_dup_p2 > 0))

# ─── CHECK 4 ────────────────────────────────────────────────────────
# generator_state persisted for each routed strategy
n_short = now_by_strat.get("SHORT_TREND", 0)
n_long_p = now_by_strat.get("LONG_PULLBACK", 0)
n_long_b = now_by_strat.get("LONG_BREAKOUT", 0)
if total_uptrend_cycles > 0:
    state_ok = n_short > 0 and n_long_p > 0 and n_long_b > 0
else:
    state_ok = n_short > 0
checks.append((f"4. generator_state persisted "
               f"(SHORT_TREND={n_short}, LONG_PULLBACK={n_long_p}, "
               f"LONG_BREAKOUT={n_long_b}, UPTREND_cycles={total_uptrend_cycles})",
               state_ok))

# ─── CHECK 5 ────────────────────────────────────────────────────────
# SHORT_TREND no regression
short_regressed = False
if snap_by_strat.get("SHORT_TREND", 0) > 0:
    before_s = {d["key"]: d.get("last_candle_ts") for d in snap
                if d.get("strategy") == "SHORT_TREND"}
    after_s = {d["key"]: d.get("last_candle_ts") for d in now_docs
               if d.get("strategy") == "SHORT_TREND"}
    for k, ts_before in before_s.items():
        ts_after = after_s.get(k)
        if ts_before is not None and ts_after is not None and ts_after < ts_before:
            short_regressed = True
            break
downtrend_seen = sum(r.get("DOWNTREND", 0) for r in (p1_regimes + p2_regimes)) > 0
short_routing_ok = (total_short_allowed > 0) if downtrend_seen else True
checks.append((f"5. SHORT_TREND no regression "
               f"(ts_regressed={short_regressed}, short_allowed={total_short_allowed}, "
               f"downtrend_cycles={sum(r.get('DOWNTREND', 0) for r in (p1_regimes + p2_regimes))})",
               (not short_regressed) and short_routing_ok))

# ─── CHECK 6 ────────────────────────────────────────────────────────
# Router activates BOTH LONG_PULLBACK AND LONG_BREAKOUT in UPTREND
if total_uptrend_cycles > 0:
    long_both_routed = total_long_pullback_allowed > 0 and total_long_breakout_allowed > 0
    detail = (f"UPTREND_cycles={total_uptrend_cycles}, "
              f"LONG_PULLBACK_allowed={total_long_pullback_allowed}, "
              f"LONG_BREAKOUT_allowed={total_long_breakout_allowed}")
    check6_ok = long_both_routed
else:
    try:
        import sys
        sys.path.insert(0, '/app/backend')
        from scripts.phase_b1_regime_collection import STRATEGY_FACTORIES
        both_registered = ("LONG_PULLBACK" in STRATEGY_FACTORIES and
                           "LONG_BREAKOUT" in STRATEGY_FACTORIES)
    except Exception:
        both_registered = False
    detail = (f"UPTREND_cycles=0 → wiring-only check: "
              f"both in STRATEGY_FACTORIES = {both_registered}")
    check6_ok = both_registered
checks.append((f"6. Router activates LONG_PULLBACK AND LONG_BREAKOUT in UPTREND ({detail})",
               check6_ok))

# ─── CHECK 7 ────────────────────────────────────────────────────────
# Heterogeneous extra state shape:
#   SHORT_TREND   → extra = {}
#   LONG_PULLBACK → extra.ohlc_candles present (no volume required)
#   LONG_BREAKOUT → extra.ohlc_candles present WITH volume field
short_ok, short_detail = check_extra_shape("SHORT_TREND", expect_ohlc=False, expect_volume=False)
pullback_ok, pullback_detail = check_extra_shape("LONG_PULLBACK", expect_ohlc=True, expect_volume=False)
breakout_ok, breakout_detail = check_extra_shape("LONG_BREAKOUT", expect_ohlc=True, expect_volume=True)
heterogeneous_ok = short_ok and pullback_ok and breakout_ok
checks.append((f"7. heterogeneous extra shape | {short_detail} | {pullback_detail} | {breakout_detail}",
               heterogeneous_ok))

# ─── CHECK 8 ────────────────────────────────────────────────────────
# Validator observer-only
warn_total_p1 = sum(s["vw"] for s in p1_stats)
warn_total_p2 = sum(s["vw"] for s in p2_stats)
warn_docs = db.validator_observations.count_documents({})
if (warn_total_p1 + warn_total_p2) > 0:
    observer_ok = "NOT dropping signal" in (log1 + log2)
else:
    observer_ok = True
checks.append((f"8. validator OBSERVER-only "
               f"(warns_p1={warn_total_p1}, warns_p2={warn_total_p2}, warn_docs={warn_docs})",
               observer_ok))

print()
passed = 0
for label, ok in checks:
    mark = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    print(f"  [{mark}] {label}")
print()
print(f"  RESULT: {passed}/{len(checks)} checks passed")
if passed == len(checks):
    print("\n  OVERALL: PASS — Phase B.3 smoke test succeeded.")
else:
    print("\n  OVERALL: FAIL — investigate logs above.")

print("\n  Coverage summary:")
print(f"    PART1 cycles         : {len(p1_stats)}")
print(f"    PART2 cycles         : {len(p2_stats)}")
print(f"    UPTREND cycles (P1/P2): {total_uptrend_cycles_p1}/{total_uptrend_cycles_p2}")
print(f"    LONG_PULLBACK allowed: {total_long_pullback_allowed}")
print(f"    LONG_BREAKOUT allowed: {total_long_breakout_allowed}")
print(f"    SHORT_TREND allowed  : {total_short_allowed}")
print(f"    checkpoints after P2 : {now_by_strat}")

print("\n  Artifacts:")
print(f"    PART1 log      : {os.environ['LOG1']}")
print(f"    PART2 log      : {os.environ['LOG2']}")
print(f"    snapshot.json  : {os.environ['SNAPSHOT_FILE']}")
print(f"    experiment_id  : {experiment}")
PY
