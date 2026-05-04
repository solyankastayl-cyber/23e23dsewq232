#!/bin/bash
# =========================================================================
#  F-TRADE v2 — Phase C stack wrapper (3 contours)
#    1. phase_c             → TRUTH lane (15m, 9 symbols, 3 tfs, shadow-only)
#    2. discovery_matrix    → EXPLORATORY lane (3m, 30 symbols, 1H+4H)
#    3. watchdog            → health-check + force-resolve + snapshot
#
#  Usage:
#    bash scripts/phase_c_launch.sh {start|stop|restart|status|report}
#    bash scripts/phase_c_launch.sh discovery:{start|stop|restart|status|report}
# =========================================================================

set -u

MONGO_URL="${MONGO_URL:-mongodb://localhost:27017}"
DB_NAME="${PHASE_B1_DB:-trading_os}"

# ------------ helper: render lifecycle summary for a program ----------
_lifecycle_summary() {
    local log="$1"
    local STARTS=$(grep -c "\[PROCESS\] STARTED" "$log" 2>/dev/null | head -1)
    local SIGTERMS=$(grep -cE "\[PROCESS\] SIG(TERM|HUP|INT) received" "$log" 2>/dev/null | head -1)
    local EXITS=$(grep -c "\[PROCESS\] EXIT" "$log" 2>/dev/null | head -1)
    STARTS="${STARTS:-0}"; SIGTERMS="${SIGTERMS:-0}"; EXITS="${EXITS:-0}"
    local SILENT=$(( STARTS - 1 - SIGTERMS ))
    [ "$SILENT" -lt 0 ] && SILENT=0
    echo "    started=$STARTS  sigterm=$SIGTERMS  clean_exit=$EXITS  silent_kills=$SILENT"
}

# ------------ status sections -----------------------------------------
_phase_c_status() {
    echo "======================================================================"
    echo " phase_c (TRUTH lane, experiment_id=phase_c_real_regime_run)"
    echo "======================================================================"
    sudo supervisorctl status phase_c 2>&1
    echo "  lifecycle:"
    _lifecycle_summary /app/backend/logs/phase_c_out.log
    echo
    echo "  last 5 [PHASE_C] cycle lines:"
    grep "\[PHASE_C\] cycle=" /app/backend/logs/phase_c_out.log 2>/dev/null | tail -5 | sed 's/^/    /'
    echo
    echo "  latest [PHASE_C_CUMULATIVE]:"
    grep "\[PHASE_C_CUMULATIVE\]" /app/backend/logs/phase_c_out.log 2>/dev/null | tail -1 | sed 's/^/    /'
}

_discovery_status() {
    echo "======================================================================"
    echo " discovery_matrix (EXPLORATORY lane, experiment_id=discovery_matrix_live)"
    echo "======================================================================"
    sudo supervisorctl status discovery_matrix 2>&1
    echo "  lifecycle:"
    _lifecycle_summary /app/backend/logs/discovery_out.log
    echo
    echo "  last 5 [DISCOVERY] cycle lines:"
    grep "\[DISCOVERY\] cycle=" /app/backend/logs/discovery_out.log 2>/dev/null | tail -5 | sed 's/^/    /'
    echo
    echo "  latest [DISCOVERY_CUMULATIVE]:"
    grep "\[DISCOVERY_CUMULATIVE\]" /app/backend/logs/discovery_out.log 2>/dev/null | tail -1 | sed 's/^/    /'
}

_watchdog_status() {
    echo "======================================================================"
    echo " watchdog (health + force-resolve + snapshot)"
    echo "======================================================================"
    sudo supervisorctl status watchdog 2>&1
    echo "  lifecycle:"
    _lifecycle_summary /app/backend/logs/watchdog_out.log
    echo
    echo "  last 3 [WATCHDOG] ticks:"
    grep "\[WATCHDOG\] tick=" /app/backend/logs/watchdog_out.log 2>/dev/null | tail -3 | sed 's/^/    /'
}

_mongo_live_counters() {
    echo
    echo "======================================================================"
    echo " Live Mongo counters (verdict-separated)"
    echo "======================================================================"
    MONGO_URL="${MONGO_URL}" PHASE_B1_DB="${DB_NAME}" python3 - <<'PY'
from pymongo import MongoClient
from collections import Counter
import os

mc = MongoClient(os.environ.get('MONGO_URL'))
db = mc[os.environ.get('PHASE_B1_DB')]

for label, exp in (("phase_c (TRUTH)", "phase_c_real_regime_run"),
                   ("discovery (EXPLORE)", "discovery_matrix_live")):
    total = db.shadow_trades.count_documents({"experiment_id": exp})
    resolved = db.shadow_trades.count_documents({"experiment_id": exp, "horizons.resolved": True})
    open_ = total - resolved
    by_strat = Counter()
    for d in db.shadow_trades.find({"experiment_id": exp}, {"features.strategy": 1}):
        by_strat[(d.get("features", {}) or {}).get("strategy")] += 1
    print(f"  {label}:")
    print(f"    total    : {total}")
    print(f"    resolved : {resolved}")
    print(f"    open     : {open_}")
    print(f"    by_strat : {dict(by_strat)}")
    print()

by_lane = Counter()
for d in db.generator_state.find({}, {"key": 1}):
    k = d["key"]
    if k.startswith("phase_c:"):
        by_lane["phase_c"] += 1
    elif k.startswith("discovery:"):
        by_lane["discovery"] += 1
    else:
        by_lane["legacy_no_lane"] += 1
print(f"  generator_state by lane: {dict(by_lane)}")
print(f"  validator_obs          : {db.validator_observations.count_documents({})}")
# Matured unresolved (what watchdog picks up)
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
matured = db.shadow_trades.count_documents({
    "horizons": {"$elemMatch": {"resolved": False, "resolve_at": {"$lte": now}}},
})
print(f"  matured_unresolved     : {matured}   (watchdog target)")
PY
}

# ------------ dispatch ------------------------------------------------
CMD="${1:-status}"

# Parse sub-command like "discovery:start" into program + verb
PROG="phase_c"
VERB="${CMD}"
if [[ "${CMD}" == *:* ]]; then
    PROG="${CMD%%:*}"
    VERB="${CMD##*:}"
fi

case "${VERB}" in
    start|stop|restart)
        if [ "${PROG}" = "phase_c" ] && [ "${CMD}" = "${VERB}" ]; then
            # Bare "start"/"stop"/"restart" = act on ALL 3 contours
            echo "Running '${VERB}' on all Phase C stack programs..."
            sudo supervisorctl ${VERB} phase_c discovery_matrix watchdog 2>&1
            sleep 2
            sudo supervisorctl status phase_c discovery_matrix watchdog 2>&1
        else
            sudo supervisorctl "${VERB}" "${PROG}" 2>&1
            sleep 2
            sudo supervisorctl status "${PROG}" 2>&1
        fi
        ;;

    status)
        if [ "${PROG}" = "phase_c" ] && [ "${CMD}" = "${VERB}" ]; then
            _phase_c_status
            echo
            _discovery_status
            echo
            _watchdog_status
            _mongo_live_counters
        elif [ "${PROG}" = "discovery" ]; then
            _discovery_status
        elif [ "${PROG}" = "watchdog" ]; then
            _watchdog_status
        else
            _phase_c_status
        fi
        ;;

    report)
        # --- Phase C truth report ---
        if [ "${PROG}" = "phase_c" ] && [ "${CMD}" = "${VERB}" ] || [ "${PROG}" = "phase_c" ]; then
            echo "======================================================================"
            echo " Phase C — TRUTH Report (experiment_id=phase_c_real_regime_run)"
            echo "======================================================================"
            MONGO_URL="${MONGO_URL}" PHASE_B1_DB="${DB_NAME}" \
            STDOUT_LOG=/app/backend/logs/phase_c_out.log \
            EXPERIMENT=phase_c_real_regime_run \
            TAG="PHASE_C" \
                python3 /app/backend/scripts/phase_c_report.py
        fi

        # --- Discovery exploratory report ---
        if [ "${PROG}" = "discovery" ] || [ "${CMD}" = "${VERB}" ]; then
            echo
            echo "======================================================================"
            echo " discovery_matrix_live — EXPLORATORY Report (verdict=exploratory_only)"
            echo "======================================================================"
            MONGO_URL="${MONGO_URL}" PHASE_B1_DB="${DB_NAME}" \
            STDOUT_LOG=/app/backend/logs/discovery_out.log \
            EXPERIMENT=discovery_matrix_live \
            TAG="DISCOVERY" \
                python3 /app/backend/scripts/phase_c_report.py
        fi
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status|report}"
        echo "       $0 {phase_c|discovery|watchdog}:{start|stop|restart|status|report}"
        echo
        echo "Bare commands act on the ENTIRE Phase C stack (phase_c + discovery + watchdog)."
        echo
        echo "First-time / fresh deploy? Run:"
        echo "    bash /app/backend/scripts/bootstrap_phase_c.sh"
        echo "It installs supervisor configs from /app/ops/supervisor/, restores the latest"
        echo "Mongo snapshot from /app/data_snapshots/latest, and starts all 3 contours."
        exit 1
        ;;
esac
