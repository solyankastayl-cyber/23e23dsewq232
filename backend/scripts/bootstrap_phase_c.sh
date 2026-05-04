#!/bin/bash
# =========================================================================
#  F-TRADE v2 — Phase C + C.3 + R.1 Bootstrap
#  One-shot installer to recreate the FULL stack from a fresh clone / fresh
#  container, restoring the LAST captured state including:
#    * 4 supervisor programs (phase_c / discovery_matrix / watchdog /
#      regime_decision)
#    * Mongo snapshot with ALL collections including the Phase C.3 decision
#      layer (regime_model_metrics, regime_decisions, regime_alerts,
#      research_states, regime_controls, regime_guard_events)
#    * Backend restart to pick up /api/regime/* router
#
#  Usage:
#    bash /app/backend/scripts/bootstrap_phase_c.sh              # full bootstrap
#    bash /app/backend/scripts/bootstrap_phase_c.sh --no-restore # configs + start only
#    bash /app/backend/scripts/bootstrap_phase_c.sh --drop       # restore with --drop
# =========================================================================

set -euo pipefail

RESTORE=1
DROP_FLAG=""
for arg in "$@"; do
    case "$arg" in
        --no-restore) RESTORE=0 ;;
        --drop)       DROP_FLAG="--drop" ;;
        *) echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

REPO_SUPERVISOR_DIR="/app/ops/supervisor"
SYS_SUPERVISOR_DIR="/etc/supervisor/conf.d"
PYTHON="/root/.venv/bin/python3"
SNAPSHOT_DIR="/app/data_snapshots/latest"

echo "======================================================================"
echo " F-TRADE v2 — Phase C + C.3 + R.1 bootstrap"
echo "======================================================================"

# ---------- 1) install supervisor configs -----------------------------
echo "[1/6] Installing supervisor configs -> ${SYS_SUPERVISOR_DIR}"
mkdir -p "${SYS_SUPERVISOR_DIR}"
for f in phase_c.conf discovery_matrix.conf watchdog.conf regime_decision.conf; do
    src="${REPO_SUPERVISOR_DIR}/${f}"
    dst="${SYS_SUPERVISOR_DIR}/${f}"
    if [ ! -f "$src" ]; then
        echo "  ERROR: missing $src — check repo checkout."
        exit 1
    fi
    cp -f "$src" "$dst"
    echo "    installed: ${f}"
done

# ---------- 2) ensure log dir exists ----------------------------------
mkdir -p /app/backend/logs

# ---------- 3) optional: restore latest snapshot ----------------------
if [ "$RESTORE" = "1" ]; then
    if [ -d "${SNAPSHOT_DIR}" ] && [ -f "${SNAPSHOT_DIR}/manifest.json" ]; then
        echo "[2/6] Restoring Mongo snapshot from ${SNAPSHOT_DIR} ${DROP_FLAG}"
        "${PYTHON}" /app/backend/scripts/restore_snapshot.py "${SNAPSHOT_DIR}" ${DROP_FLAG}
    else
        echo "[2/6] No snapshot at ${SNAPSHOT_DIR} — skipping restore."
    fi
else
    echo "[2/6] --no-restore passed — skipping Mongo restore."
fi

# ---------- 4) reload supervisor and start 3-tier + decision stack ---
echo "[3/6] supervisorctl reread && update"
sudo supervisorctl reread
sudo supervisorctl update

echo "[4/6] Starting Phase C stack (phase_c + discovery_matrix + watchdog + regime_decision)"
sudo supervisorctl start phase_c discovery_matrix watchdog regime_decision 2>&1 || true
sleep 3

# ---------- 5) restart backend so /api/regime/* router is live -------
echo "[5/6] Restarting backend so /api/regime/* router is registered"
sudo supervisorctl restart backend 2>&1 || true
sleep 6

# ---------- 6) verify routes + DB state ------------------------------
echo "[6/6] Verifying regime API + DB state"
BACKEND_URL="http://localhost:8001"
for ep in \
    "/api/health" \
    "/api/regime/accuracy" \
    "/api/regime/decision" \
    "/api/regime/state" \
    "/api/regime/alerts" \
    "/api/regime/guard-events" \
    "/api/regime/controls/short-v2-guard" \
    "/api/regime/post-guard-report"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}${ep}" || echo "ERR")
    echo "    ${code}  ${ep}"
done

echo
echo "======================================================================"
echo " Guard state:"
curl -s "${BACKEND_URL}/api/regime/controls/short-v2-guard" 2>/dev/null || echo "  (unavailable)"
echo
echo "======================================================================"
echo " Supervisor status:"
sudo supervisorctl status | grep -E "phase_c|discovery_matrix|watchdog|regime_decision|backend|mongodb" || true
echo
echo "======================================================================"
echo " Bootstrap complete. Live status:"
echo "======================================================================"
bash /app/backend/scripts/phase_c_launch.sh status | head -60
