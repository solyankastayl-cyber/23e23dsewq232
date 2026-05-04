"""
Watchdog v2 for LIVE-2H baseline observation — read-only.

Per architect directive (post first 9-trade snapshot):

  * Excludes "frozen" trades (sandbox pause artefacts).  A trade is frozen
    when exit_rule == TIME_EXIT but duration > 31 minutes — the
    position_exit_manager loops at 10s, so any TIME_EXIT longer than
    ~30.5min indicates the daemon was paused.
  * Hardcoded exclusion list for known frozen cases (8, 9 from previous run).
  * Targets clean N >= 10.

Early-alarm patterns (architect rules):
  1. SL_CLUSTER     : ≥3 STOP_LOSS in a row (any duration) — entry weak
  2. TP_CLUSTER     : ≥3 TAKE_PROFIT in a row              — strong signal
  3. SANDBOX_PAUSE  : detected gap >120s in mark_updated_at across active
                      cases — alert immediately so we can re-tag

Otherwise — quiet. Stops automatically when CLEAN n >= 10.

Output:
  /tmp/live2h_alarm.json    one alarm at a time, overwritten
  /tmp/watchdog.log         heartbeat / activity log

Run:
  nohup python /app/scripts/watchdog_live2h_v2.py > /tmp/watchdog.log 2>&1 &
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

from pymongo import MongoClient


ALARM_FILE = "/tmp/live2h_alarm.json"
TARGET_N = 10
POLL_INTERVAL_SEC = 60
MAX_RUN_MIN = 240  # 4 hours hard stop

# Hardcoded frozen-from-pause cases (sandbox suspended 15:52 → 20:09 UTC).
EXCLUDED_CASE_IDS = {
    "case-3cbabe9b6d08",  # SHORT, dur 257m, opened 15:52 closed 20:09
    "case-e9c8f0d50298",  # SHORT, dur 252m, opened 15:57 closed 20:09
}

# A trade with exit_rule=TIME_EXIT and duration > 31min is presumed
# pause-tainted (the production daemon ticks every 10s, so a clean TIME
# trade closes between 30.0 and 30.2 minutes).
PAUSE_DURATION_THRESHOLD_MIN = 31.0


def load_closes(db):
    return list(
        db.trading_cases.find(
            {"close_reason": {"$regex": "^LIVE2H_"}},
            {
                "case_id": 1, "side": 1, "exit_rule": 1,
                "close_reason": 1, "opened_at": 1, "closed_at": 1,
                "realized_pnl_pct": 1,
            },
        ).sort("closed_at", 1)
    )


def duration_min(c):
    op, cl = c.get("opened_at"), c.get("closed_at")
    if not (op and cl):
        return None
    if op.tzinfo is None:
        op = op.replace(tzinfo=timezone.utc)
    if cl.tzinfo is None:
        cl = cl.replace(tzinfo=timezone.utc)
    return (cl - op).total_seconds() / 60.0


def is_clean(c):
    """Return True if trade qualifies for baseline subset."""
    if c["case_id"] in EXCLUDED_CASE_IDS:
        return False
    if c.get("exit_rule") == "TIME_EXIT":
        d = duration_min(c)
        if d is not None and d > PAUSE_DURATION_THRESHOLD_MIN:
            return False
    return True


def detect_alarms(clean_closes, db):
    alarms = []

    # 1. SL_CLUSTER — ≥3 SL in a row (any duration)
    last3 = clean_closes[-3:] if len(clean_closes) >= 3 else []
    if (
        len(last3) == 3
        and all(c.get("exit_rule") == "STOP_LOSS" for c in last3)
    ):
        alarms.append({
            "pattern": "SL_CLUSTER",
            "severity": "high",
            "message": "≥3 STOP_LOSS in a row — entry weakness signal",
            "case_ids": [c["case_id"] for c in last3],
        })

    # 2. TP_CLUSTER — ≥3 TP in a row
    if (
        len(last3) == 3
        and all(c.get("exit_rule") == "TAKE_PROFIT" for c in last3)
    ):
        alarms.append({
            "pattern": "TP_CLUSTER",
            "severity": "info",
            "message": "≥3 TAKE_PROFIT in a row — system catches market impulse",
            "case_ids": [c["case_id"] for c in last3],
        })

    # 3. SANDBOX_PAUSE — check for ANY mark_updated_at lag >120s on active
    actives = list(db.trading_cases.find(
        {"status": "ACTIVE"},
        {"case_id": 1, "mark_updated_at": 1, "opened_at": 1},
    ))
    now = datetime.now(timezone.utc)
    for a in actives:
        m = a.get("mark_updated_at")
        if m is None:
            continue
        if m.tzinfo is None:
            m = m.replace(tzinfo=timezone.utc)
        lag_s = (now - m).total_seconds()
        if lag_s > 120:
            alarms.append({
                "pattern": "SANDBOX_PAUSE",
                "severity": "critical",
                "message": (
                    f"Mark price stale {lag_s:.0f}s on case "
                    f"{a['case_id']} — daemon may be paused"
                ),
                "case_ids": [a["case_id"]],
                "lag_seconds": round(lag_s, 1),
            })
            break  # one is enough

    return alarms


def main():
    db = MongoClient(
        os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
        serverSelectionTimeoutMS=5000,
    )["trading_os"]

    started = time.time()
    seen_alarms = set()
    print(
        f"[watchdog-v2] started; target CLEAN n={TARGET_N}, "
        f"max_run={MAX_RUN_MIN}m, "
        f"hard-excluded={len(EXCLUDED_CASE_IDS)}",
        flush=True,
    )

    while True:
        elapsed_min = (time.time() - started) / 60.0
        if elapsed_min > MAX_RUN_MIN:
            print(f"[watchdog-v2] max runtime reached, exiting", flush=True)
            break

        try:
            all_closes = load_closes(db)
            clean = [c for c in all_closes if is_clean(c)]
            excluded = len(all_closes) - len(clean)
            now = datetime.now(timezone.utc)

            if len(clean) >= TARGET_N:
                print(
                    f"[watchdog-v2] CLEAN_TARGET_REACHED "
                    f"clean={len(clean)} excluded={excluded} "
                    f"at T+{elapsed_min:.1f}m",
                    flush=True,
                )
                with open(ALARM_FILE, "w") as f:
                    json.dump({
                        "ts": now.isoformat(),
                        "trigger": "CLEAN_TARGET_REACHED",
                        "n_clean": len(clean),
                        "n_excluded": excluded,
                        "elapsed_min": round(elapsed_min, 1),
                    }, f, indent=2, default=str)
                break

            # detect early alarms
            for a in detect_alarms(clean, db):
                key = a["pattern"] + ":" + ",".join(a.get("case_ids", []))
                if key in seen_alarms:
                    continue
                seen_alarms.add(key)
                a["ts"] = now.isoformat()
                a["n_clean"] = len(clean)
                a["n_excluded"] = excluded
                a["elapsed_min"] = round(elapsed_min, 1)
                print(
                    f"[watchdog-v2] ALARM {a['pattern']}: {a['message']}",
                    flush=True,
                )
                with open(ALARM_FILE, "w") as f:
                    json.dump(a, f, indent=2, default=str)

            print(
                f"[watchdog-v2] T+{elapsed_min:5.1f}m  "
                f"clean={len(clean)} excluded={excluded}",
                flush=True,
            )
        except Exception as e:
            print(f"[watchdog-v2] error: {e}", flush=True)

        time.sleep(POLL_INTERVAL_SEC)

    print("[watchdog-v2] done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
