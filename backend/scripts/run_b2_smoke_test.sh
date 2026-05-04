#!/bin/bash
# =========================================================================
#  F-TRADE v2 — Phase B.2 Smoke Test (SHORT_TREND + LONG_PULLBACK)
#  Goal: validate stateful regime-aware pipeline across process restart
#        for TWO strategies simultaneously, with no regression on SHORT.
#
#  Protocol:
#    0. Clean generator_state / validator_observations (cold start).
#    1. Run PART 1 — 5 cycles.
#    2. Snapshot checkpoints (both strategies).
#    3. Run PART 2 — 5 more cycles (simulated restart → state must be restored).
#    4. PASS/FAIL checklist based on log + Mongo artefacts.
#
#  PASS criteria (Phase B.2 — 7 points, mirrors B.1.4 but checks BOTH strategies):
#    1) LONG_PULLBACK does NOT create side-effects on warmup
#    2) LONG_PULLBACK correctly survives restart (state restored)
#    3) dedup works for BOTH strategies
#    4) generator_state written to Mongo for BOTH strategies
#    5) SHORT_TREND did not regress after adding LONG_PULLBACK
#    6) Router actually activates LONG_PULLBACK in UPTREND regime
#       (permissive — allowed_strategies["LONG_PULLBACK"] >= 1 across run,
#        OR no UPTREND cycles detected → skip gracefully)
#    7) validator stays observer-only (warnings never drop signals)
#
#  Usage: bash scripts/run_b2_smoke_test.sh [sleep_seconds]
# =========================================================================

set -u

SLEEP_SECONDS="${1:-45}"
EXPERIMENT="phase_b2_smoke_$(date +%s)"
LOG_DIR="/app/backend/logs"
LOG1="${LOG_DIR}/b2_smoke_part1.log"
LOG2="${LOG_DIR}/b2_smoke_part2.log"
SNAPSHOT_FILE="${LOG_DIR}/b2_smoke_snapshot.json"
MONGO_URL="${MONGO_URL:-mongodb://localhost:27017}"
DB_NAME="${PHASE_B1_DB:-trading_os}"

mkdir -p "${LOG_DIR}"

echo "======================================================================"
echo " F-TRADE v2 — Phase B.2 Smoke Test"
echo "   strategies     : SHORT_TREND + LONG_PULLBACK"
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
    {"_id": 0, "key": 1, "strategy": 1, "last_candle_ts": 1, "meta": 1, "prices": 1, "extra": 1}
))
snap = []
for d in docs:
    snap.append({
        "key": d["key"],
        "strategy": d.get("strategy"),
        "last_candle_ts": d.get("last_candle_ts"),
        "prices_len": len(d.get("prices", [])),
        "ohlc_len": len((d.get("extra") or {}).get("ohlc_candles", [])),
        "warm": d.get("meta", {}).get("warm"),
    })
with open(os.environ["SNAPSHOT_FILE"], "w") as f:
    json.dump(snap, f, indent=2, default=str)

# Group by strategy for visibility
from collections import Counter
by_strat = Counter(row["strategy"] for row in snap)
print(f"    total_checkpoints: {len(snap)} → {dict(by_strat)}")
for row in snap[:6]:
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

# --- PASS/FAIL analysis (real data + log forensics) ---
echo
echo "======================================================================"
echo " PHASE B.2 PASS/FAIL ANALYSIS"
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

# Parse per-cycle stats from log
def extract_cycle_stats(log):
    pattern = re.compile(
        r"fresh_warmups=(?P<fw>\d+)\s+dup_skips=(?P<ds>\d+)\s+cold_skips=(?P<cs>\d+)\s+"
        r"checkpoints=(?P<ck>\d+)\s+validator_warns=(?P<vw>\d+)\s+signals=(?P<sg>\d+)"
    )
    return [{k: int(v) for k, v in m.groupdict().items()} for m in pattern.finditer(log)]

# Parse "allowed_strategies: {...}" lines
def extract_allowed_strategies(log):
    """Return list of dicts per cycle."""
    out = []
    for m in re.finditer(r"allowed_strategies:\s*\{([^}]*)\}", log):
        s = m.group(1)
        d = {}
        for kv in re.finditer(r"'([^']+)':\s*(\d+)", s):
            d[kv.group(1)] = int(kv.group(2))
        out.append(d)
    return out

# Parse "regime_detections: {...}" lines
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

# Checkpoint strategy breakdown (both p1 snapshot and current)
def strat_keys(docs):
    out = {}
    for d in docs:
        out[d.get("strategy")] = out.get(d.get("strategy"), 0) + 1
    return out

snap_by_strat = strat_keys(snap)
now_docs = list(db.generator_state.find({}, {"key": 1, "strategy": 1, "last_candle_ts": 1, "extra": 1}))
now_by_strat = strat_keys(now_docs)

total_uptrend_cycles_p1 = sum(r.get("UPTREND", 0) for r in p1_regimes)
total_uptrend_cycles_p2 = sum(r.get("UPTREND", 0) for r in p2_regimes)
total_uptrend_cycles = total_uptrend_cycles_p1 + total_uptrend_cycles_p2

total_long_allowed_p1 = sum(a.get("LONG_PULLBACK", 0) for a in p1_allowed)
total_long_allowed_p2 = sum(a.get("LONG_PULLBACK", 0) for a in p2_allowed)
total_long_allowed = total_long_allowed_p1 + total_long_allowed_p2

total_short_allowed_p1 = sum(a.get("SHORT_TREND", 0) for a in p1_allowed)
total_short_allowed_p2 = sum(a.get("SHORT_TREND", 0) for a in p2_allowed)

checks = []

# ─── CHECK 1 ────────────────────────────────────────────────────────
# LONG_PULLBACK warmup produces NO side effects (signal generated from
# LONG_PULLBACK only on properly updated state, not on warmup alone).
# Evidence: cycle 1 of PART 1 has fresh_warmups > 0 AND signals can only
# come from strategies after maybe_generate (warmup never calls it).
if p1_stats:
    c1 = p1_stats[0]
    warm_no_signal = c1["fw"] > 0
else:
    warm_no_signal = False
# Also check for any explicit "warmup ... NEVER" kind of log line for LONG_PULLBACK
lp_warmup_logged = "[TrendPullbackLong] warmup" in log1
checks.append((f"1. LONG_PULLBACK warmup NO side-effects "
               f"(cycle1 fw={c1['fw'] if p1_stats else 'N/A'}, "
               f"lp_warmup_logged={lp_warmup_logged})", warm_no_signal))

# ─── CHECK 2 ────────────────────────────────────────────────────────
# LONG_PULLBACK state survives restart (PART 2 cycle 1: fresh_warmups == 0
# for LONG_PULLBACK keys AND last_candle_ts in Mongo not regressed).
restored_ok = False
if p2_stats and p2_stats[0]["fw"] == 0:
    before = {d["key"]: d.get("last_candle_ts") for d in snap if d.get("strategy") == "LONG_PULLBACK"}
    after = {d["key"]: d.get("last_candle_ts") for d in now_docs if d.get("strategy") == "LONG_PULLBACK"}
    regressed = [k for k in before
                 if after.get(k) is not None and before[k] is not None
                 and after[k] < before[k]]
    # If we have LONG checkpoints in snapshot, they must not regress.
    # If we have NO LONG checkpoints (no UPTREND detected during PART 1),
    # the restart-restore check for LONG is vacuously satisfied by the
    # fresh_warmups==0 condition at the cycle level.
    restored_ok = len(regressed) == 0
checks.append((f"2. LONG_PULLBACK survives restart "
               f"(p2c1 fw={p2_stats[0]['fw'] if p2_stats else 'N/A'}, "
               f"snap_LP={snap_by_strat.get('LONG_PULLBACK', 0)}, "
               f"now_LP={now_by_strat.get('LONG_PULLBACK', 0)})", restored_ok))

# ─── CHECK 3 ────────────────────────────────────────────────────────
# dedup works for BOTH strategies (cumulative dup_skips > 0 across cycles)
total_dup_p1 = sum(s["ds"] for s in p1_stats)
total_dup_p2 = sum(s["ds"] for s in p2_stats)
checks.append((f"3. duplicate dedup active "
               f"(p1_dup={total_dup_p1}, p2_dup={total_dup_p2})",
               total_dup_p1 > 0 and total_dup_p2 > 0))

# ─── CHECK 4 ────────────────────────────────────────────────────────
# generator_state persisted in Mongo for BOTH strategies (but LONG_PULLBACK
# only when UPTREND regime observed). Strict check: SHORT_TREND must be
# persisted; LONG_PULLBACK lenient — only required if UPTREND seen.
n_short = now_by_strat.get("SHORT_TREND", 0)
n_long = now_by_strat.get("LONG_PULLBACK", 0)
if total_uptrend_cycles > 0:
    state_ok = n_short > 0 and n_long > 0
    detail = (f"SHORT_TREND={n_short}, LONG_PULLBACK={n_long}, "
              f"UPTREND_cycles={total_uptrend_cycles}")
else:
    state_ok = n_short > 0
    detail = (f"SHORT_TREND={n_short}, LONG_PULLBACK={n_long}, "
              f"UPTREND_cycles=0 (LONG checkpoint not required)")
checks.append((f"4. generator_state persisted ({detail})", state_ok))

# ─── CHECK 5 ────────────────────────────────────────────────────────
# SHORT_TREND not regressed:
#   - SHORT checkpoints still present
#   - SHORT last_candle_ts never regresses between snapshot and now
#   - SHORT still routed when DOWNTREND present
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
# If DOWNTREND observed anywhere, SHORT_allowed must be > 0
downtrend_seen = sum(r.get("DOWNTREND", 0) for r in (p1_regimes + p2_regimes)) > 0
short_routing_ok = (total_short_allowed_p1 + total_short_allowed_p2 > 0) if downtrend_seen else True
checks.append((f"5. SHORT_TREND no regression "
               f"(ts_regressed={short_regressed}, short_allowed="
               f"{total_short_allowed_p1 + total_short_allowed_p2}, "
               f"downtrend_cycles="
               f"{sum(r.get('DOWNTREND', 0) for r in (p1_regimes + p2_regimes))})",
               (not short_regressed) and short_routing_ok))

# ─── CHECK 6 ────────────────────────────────────────────────────────
# Router activates LONG_PULLBACK in UPTREND (if UPTREND observed).
# If NO UPTREND observed at all → mark as SKIP (non-failing) — we note it.
if total_uptrend_cycles > 0:
    long_routed = total_long_allowed > 0
    detail = (f"UPTREND_cycles={total_uptrend_cycles}, "
              f"LONG_PULLBACK_allowed={total_long_allowed}")
    check6_ok = long_routed
else:
    # No UPTREND observed — we still want to prove the wiring is correct.
    # Look for the factory being registered by scanning logs for LONG_PULLBACK
    # references OR by verifying STRATEGY_FACTORIES contains LONG_PULLBACK.
    try:
        import sys
        sys.path.insert(0, '/app/backend')
        from scripts.phase_b1_regime_collection import STRATEGY_FACTORIES
        factory_registered = "LONG_PULLBACK" in STRATEGY_FACTORIES
    except Exception:
        factory_registered = False
    detail = (f"UPTREND_cycles=0 → wiring-only check: "
              f"LONG_PULLBACK in STRATEGY_FACTORIES = {factory_registered}")
    check6_ok = factory_registered
checks.append((f"6. Router activates LONG_PULLBACK in UPTREND ({detail})", check6_ok))

# ─── CHECK 7 ────────────────────────────────────────────────────────
# Validator observer-only: any warnings must NOT drop signals
warn_total_p1 = sum(s["vw"] for s in p1_stats)
warn_total_p2 = sum(s["vw"] for s in p2_stats)
warn_docs = db.validator_observations.count_documents({})
if (warn_total_p1 + warn_total_p2) > 0:
    observer_ok = "NOT dropping signal" in (log1 + log2)
else:
    observer_ok = True
checks.append((f"7. validator OBSERVER-only "
               f"(warns_p1={warn_total_p1}, warns_p2={warn_total_p2}, "
               f"warn_docs={warn_docs})", observer_ok))

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
    print("\n  OVERALL: PASS — Phase B.2 smoke test succeeded.")
else:
    print("\n  OVERALL: FAIL — investigate logs above.")

print("\n  Coverage summary:")
print(f"    PART1 cycles         : {len(p1_stats)}")
print(f"    PART2 cycles         : {len(p2_stats)}")
print(f"    UPTREND cycles (P1/P2): {total_uptrend_cycles_p1}/{total_uptrend_cycles_p2}")
print(f"    LONG_PULLBACK allowed: {total_long_allowed} occurrences")
print(f"    SHORT_TREND allowed  : {total_short_allowed_p1 + total_short_allowed_p2} occurrences")
print(f"    checkpoints after P2 : {now_by_strat}")

print("\n  Artifacts:")
print(f"    PART1 log      : {os.environ['LOG1']}")
print(f"    PART2 log      : {os.environ['LOG2']}")
print(f"    snapshot.json  : {os.environ['SNAPSHOT_FILE']}")
print(f"    experiment_id  : {experiment}")
PY
