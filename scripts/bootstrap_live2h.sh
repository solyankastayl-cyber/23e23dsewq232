#!/usr/bin/env bash
# =============================================================================
# bootstrap_live2h.sh
# -----------------------------------------------------------------------------
# Resume the trading terminal from the LIVE-2H baseline snapshot.
#
# This script is idempotent. Re-running it will reapply the LIVE-2H state
# (TP/SL ±0.30%, regime gates OFF, Phase tag LIVE2H_*_030) without overwriting
# already-captured live data.
#
# What it does:
#   1. Restore MongoDB collections from /app/data_snapshots/live2h/ if the
#      target collection is empty (or --force is given).
#   2. Apply the LIVE-2H regime_controls feature flags
#      (long_uptrend_only=False, short_downtrend_only=False, short_trading=True).
#   3. Restart backend so position_exit_manager picks up TP/SL=0.30% from code.
#   4. Start observer + watchdog v2 in background.
#
# Usage:
#   bash /app/scripts/bootstrap_live2h.sh             # normal resume
#   bash /app/scripts/bootstrap_live2h.sh --force     # force-restore snapshots
#   bash /app/scripts/bootstrap_live2h.sh --no-watch  # skip observer/watchdog
# =============================================================================
set -e

ROOT="${ROOT:-/app}"
SNAP="${ROOT}/data_snapshots"
LIVE2H_SNAP="${SNAP}/live2h"
BASE_SNAP="${SNAP}/latest"

FORCE="0"
NOWATCH="0"
for arg in "$@"; do
    case "$arg" in
        --force)    FORCE="1" ;;
        --no-watch) NOWATCH="1" ;;
        -h|--help)
            grep "^# " "$0" | head -25
            exit 0
            ;;
    esac
done

echo "=========================================="
echo "  LIVE-2H BASELINE BOOTSTRAP"
echo "=========================================="
echo "ROOT          = ${ROOT}"
echo "FORCE         = ${FORCE}"
echo "NOWATCH       = ${NOWATCH}"
echo "BASE_SNAP     = ${BASE_SNAP}"
echo "LIVE2H_SNAP   = ${LIVE2H_SNAP}"
echo

# ----------------------------------------------------------------------------
# Step 1. Restore base snapshot (only if Mongo is empty / --force).
# ----------------------------------------------------------------------------
echo "[1/4] checking MongoDB state"
python3 "${ROOT}/scripts/restore_snapshot.py" \
    --snapshot "${BASE_SNAP}" \
    --mode base \
    ${FORCE:+--force-empty-only}

# ----------------------------------------------------------------------------
# Step 2. Overlay LIVE-2H specific docs (regime_controls + recent cases).
# ----------------------------------------------------------------------------
echo "[2/4] overlaying LIVE-2H snapshot"
python3 "${ROOT}/scripts/restore_snapshot.py" \
    --snapshot "${LIVE2H_SNAP}" \
    --mode overlay

# ----------------------------------------------------------------------------
# Step 3. Restart backend (TP/SL is hardcoded → needs reload).
# ----------------------------------------------------------------------------
echo "[3/4] restarting backend (so position_exit_manager loads TP/SL=0.30%)"
sudo supervisorctl restart backend >/dev/null 2>&1 || true
sleep 5
sudo supervisorctl status backend || true

# ----------------------------------------------------------------------------
# Step 4. Start observer + watchdog (background).
# ----------------------------------------------------------------------------
if [ "${NOWATCH}" = "1" ]; then
    echo "[4/4] skipping observer/watchdog (--no-watch)"
else
    echo "[4/4] starting observer + watchdog (background)"
    pkill -f observe_live2h.py 2>/dev/null || true
    pkill -f watchdog_live2h 2>/dev/null || true
    cd "${ROOT}"
    nohup python3 scripts/observe_live2h.py --watch 240 60  > /tmp/observer.log 2>&1 &
    echo "  observer PID=$!"
    nohup python3 scripts/watchdog_live2h_v2.py            > /tmp/watchdog.log 2>&1 &
    echo "  watchdog PID=$!"
    sleep 2
    ps -eo pid,etime,cmd | grep -E "observe_live2h|watchdog_live2h" | grep -v grep || true
fi

echo
echo "=========================================="
echo "  LIVE-2H bootstrap complete"
echo "=========================================="
echo "Verify with:"
echo "  python3 ${ROOT}/scripts/observe_live2h.py     # one-shot status"
echo "  python3 ${ROOT}/scripts/forensic_v2_mfe_mae.py  # full forensic"
echo "  cat ${ROOT}/PHASE_STATE.md                    # current phase doc"
