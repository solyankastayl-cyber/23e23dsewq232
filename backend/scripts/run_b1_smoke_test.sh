#!/bin/bash
# =========================================================================
#  F-TRADE v2 — Phase B.1.4 Smoke Test
#  Goal: validate stateful regime-aware pipeline across process restart.
#
#  Protocol:
#    0. Clean generator_state / validator_observations.
#    1. Run 5 cycles.
#    2. Snapshot checkpoints.
#    3. Run 5 more cycles (simulated restart → state must be restored).
#    4. PASS/FAIL checklist based on log + Mongo artefacts.
#
#  Usage: bash scripts/run_b1_smoke_test.sh [sleep_seconds]
# =========================================================================

set -u

SLEEP_SECONDS="${1:-45}"
EXPERIMENT="phase_b1_smoke_$(date +%s)"
LOG_DIR="/app/backend/logs"
LOG1="${LOG_DIR}/b1_smoke_part1.log"
LOG2="${LOG_DIR}/b1_smoke_part2.log"
SNAPSHOT_FILE="${LOG_DIR}/b1_smoke_snapshot.json"
MONGO_URL="${MONGO_URL:-mongodb://localhost:27017}"
DB_NAME="${PHASE_B1_DB:-trading_os}"

mkdir -p "${LOG_DIR}"

echo "======================================================================"
echo " F-TRADE v2 — Phase B.1.4 Smoke Test"
echo "======================================================================"
echo " experiment     : ${EXPERIMENT}"
echo " sleep_seconds  : ${SLEEP_SECONDS}"
echo " log part1      : ${LOG1}"
echo " log part2      : ${LOG2}"
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
docs = list(db.generator_state.find({}, {"_id": 0, "key": 1, "last_candle_ts": 1, "meta": 1, "prices": 1}))
snap = []
for d in docs:
    snap.append({
        "key": d["key"],
        "last_candle_ts": d.get("last_candle_ts"),
        "prices_len": len(d.get("prices", [])),
        "warm": d.get("meta", {}).get("warm"),
    })
with open(os.environ["SNAPSHOT_FILE"], "w") as f:
    json.dump(snap, f, indent=2, default=str)
print(f"    checkpoints: {len(snap)}")
for row in snap[:5]:
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
echo " PASS/FAIL ANALYSIS"
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

# Extract cycle summary numbers (fresh_warmups / dup_skips / checkpoints) by parsing
def extract_cycle_stats(log):
    """Return list of dicts with cycle stats parsed from 'fresh_warmups=X' lines."""
    pattern = re.compile(
        r"fresh_warmups=(?P<fw>\d+)\s+dup_skips=(?P<ds>\d+)\s+cold_skips=(?P<cs>\d+)\s+"
        r"checkpoints=(?P<ck>\d+)\s+validator_warns=(?P<vw>\d+)\s+signals=(?P<sg>\d+)"
    )
    out = []
    for m in pattern.finditer(log):
        out.append({k: int(v) for k, v in m.groupdict().items()})
    return out

p1_stats = extract_cycle_stats(log1)
p2_stats = extract_cycle_stats(log2)

checks = []

# 1) warmup has no side-effects:
#    in PART 1 cycle 1 fresh_warmups>0 but signals==0  (warmup alone never triggers signals)
if p1_stats:
    c1 = p1_stats[0]
    warm_no_signal = c1["fw"] > 0 and c1["sg"] == 0
else:
    warm_no_signal = False
checks.append((f"1. warmup has NO side-effects (cycle1 fw>{0}, signals==0): {p1_stats[:1]}",
               warm_no_signal))

# 2) duplicate dedup works: cumulative dup_skips > 0 across cycles
total_dup_p1 = sum(s["ds"] for s in p1_stats)
total_dup_p2 = sum(s["ds"] for s in p2_stats)
checks.append((f"2. duplicate dedup active (p1_dup={total_dup_p1}, p2_dup={total_dup_p2})",
               total_dup_p1 > 0 and total_dup_p2 > 0))

# 3) generator_state persisted in Mongo
n_ckpt = db.generator_state.count_documents({})
checks.append((f"3. generator_state persisted (count={n_ckpt})", n_ckpt > 0 and len(snap) > 0))

# 4) after restart: state RESTORED (= PART 2 cycle 1 fresh_warmups == 0 AND last_candle_ts
#    in Mongo is >= pre-restart snapshot last_candle_ts)
restored = False
if p2_stats and p2_stats[0]["fw"] == 0:
    # Compare last_candle_ts: should not regress
    after = {d["key"]: d.get("last_candle_ts") for d in db.generator_state.find({}, {"key": 1, "last_candle_ts": 1})}
    before = {d["key"]: d.get("last_candle_ts") for d in snap}
    regressed = [k for k in before if after.get(k) is not None and before[k] is not None
                 and after[k] < before[k]]
    restored = len(regressed) == 0
checks.append((f"4. state RESTORED after restart (p2c1 fw={p2_stats[0]['fw'] if p2_stats else 'N/A'}, "
               f"no ts regression)", restored))

# 5) PART 2 ran >= 5 cycles
cycles_p2 = len(p2_stats)
checks.append((f"5. PART 2 executed 5 cycles (observed={cycles_p2})", cycles_p2 >= 5))

# 6) validator observer-only: warnings NEVER dropped signals; i.e. if warn_total > 0 we
#    still see signals generated that the router allowed. If warn_total == 0 → also OK.
warn_total_p1 = sum(s["vw"] for s in p1_stats)
warn_total_p2 = sum(s["vw"] for s in p2_stats)
warn_docs = db.validator_observations.count_documents({})
# Check that any warns still mention "NOT dropping signal"
if (warn_total_p1 + warn_total_p2) > 0:
    observer_ok = "NOT dropping signal" in (log1 + log2)
else:
    observer_ok = True
checks.append((f"6. validator OBSERVER-only (warns_p1={warn_total_p1}, warns_p2={warn_total_p2}, "
               f"warn_docs={warn_docs})", observer_ok))

# 7) warmup line present in logs (proves logging was active)
warmup_logged = "[MultiAsset] warmup" in log1 or "warmup" in log1.lower()
checks.append(("7. warmup events logged to stdout", warmup_logged))

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
    print("\n  OVERALL: PASS — Phase B.1.4 smoke test succeeded.")
else:
    print("\n  OVERALL: FAIL — investigate logs above.")

print("\n  Artifacts:")
print(f"    PART1 log      : {os.environ['LOG1']}")
print(f"    PART2 log      : {os.environ['LOG2']}")
print(f"    snapshot.json  : {os.environ['SNAPSHOT_FILE']}")
print(f"    experiment_id  : {os.environ['EXPERIMENT']}")
PY
