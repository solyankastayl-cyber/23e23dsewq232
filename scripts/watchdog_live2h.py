"""
Watchdog for LIVE-2H baseline observation — read-only.

Polls trading_cases every 60s. Triggers an alarm file when one of three
architect-defined early patterns is detected:

  1. SL_CLUSTER     : ≥3 STOP_LOSS in a row, each duration < 20 min
  2. TIME_KILL_OPEN : first 3 closes are all TIME_EXIT
  3. TP_BURST       : ≥2 TAKE_PROFIT in a row, each duration < 15 min

Otherwise — quiet. Stops automatically when ≥10 LIVE-2H closes are seen.
Writes alarms to /tmp/live2h_alarm.json so the main agent can pick them up.

Usage (background):
  nohup python /app/scripts/watchdog_live2h.py > /tmp/watchdog.log 2>&1 &
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
MAX_RUN_MIN = 120


def load_closes(db):
    return list(
        db.trading_cases.find(
            {"close_reason": {"$regex": "^LIVE2H_"}},
            {
                "case_id": 1, "side": 1, "exit_rule": 1,
                "close_reason": 1, "opened_at": 1, "closed_at": 1,
                "realized_pnl_pct": 1, "regime_at_entry": 1,
            },
        ).sort("closed_at", 1)
    )


def duration_min(c):
    op = c.get("opened_at")
    cl = c.get("closed_at")
    if not (op and cl):
        return None
    if op.tzinfo is None:
        op = op.replace(tzinfo=timezone.utc)
    if cl.tzinfo is None:
        cl = cl.replace(tzinfo=timezone.utc)
    return (cl - op).total_seconds() / 60.0


def detect_alarms(closes):
    alarms = []
    if len(closes) < 2:
        return alarms

    # 1. SL_CLUSTER — last 3 SL in a row, each <20 min
    last3 = closes[-3:] if len(closes) >= 3 else []
    if (
        len(last3) == 3
        and all(c.get("exit_rule") == "STOP_LOSS" for c in last3)
        and all((duration_min(c) or 999) < 20 for c in last3)
    ):
        alarms.append({
            "pattern": "SL_CLUSTER",
            "severity": "high",
            "message": "≥3 STOP_LOSS in a row, all <20 min — entry catches impulse noise",
            "case_ids": [c["case_id"] for c in last3],
        })

    # 2. TIME_KILL_OPEN — first 3 closes all TIME_EXIT
    first3 = closes[:3]
    if (
        len(first3) == 3
        and all(c.get("exit_rule") == "TIME_EXIT" for c in first3)
    ):
        alarms.append({
            "pattern": "TIME_KILL_OPEN",
            "severity": "info",
            "message": "First 3 LIVE-2H closes are all TIME_EXIT — FLAT_NO_MOVE environment continues",
            "case_ids": [c["case_id"] for c in first3],
        })

    # 3. TP_BURST — last 2 TP in a row, each <15 min
    last2 = closes[-2:] if len(closes) >= 2 else []
    if (
        len(last2) == 2
        and all(c.get("exit_rule") == "TAKE_PROFIT" for c in last2)
        and all((duration_min(c) or 999) < 15 for c in last2)
    ):
        alarms.append({
            "pattern": "TP_BURST",
            "severity": "info",
            "message": "≥2 TAKE_PROFIT in a row, both <15 min — market gave impulse, system caught it",
            "case_ids": [c["case_id"] for c in last2],
        })

    return alarms


def main():
    db = MongoClient(
        os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
        serverSelectionTimeoutMS=5000,
    )["trading_os"]

    started = time.time()
    seen_alarms = set()
    print(f"[watchdog] started; target N={TARGET_N}, max_run={MAX_RUN_MIN}m", flush=True)

    while True:
        elapsed_min = (time.time() - started) / 60.0
        if elapsed_min > MAX_RUN_MIN:
            print(f"[watchdog] max runtime reached ({MAX_RUN_MIN}m), exiting", flush=True)
            break

        try:
            closes = load_closes(db)
            n = len(closes)
            now = datetime.now(timezone.utc)

            # Check terminal condition
            if n >= TARGET_N:
                print(f"[watchdog] TARGET_REACHED n={n} at T+{elapsed_min:.1f}m", flush=True)
                with open(ALARM_FILE, "w") as f:
                    json.dump({
                        "ts": now.isoformat(),
                        "trigger": "TARGET_REACHED",
                        "n_closed": n,
                        "elapsed_min": round(elapsed_min, 1),
                    }, f, indent=2)
                break

            # Detect early-pattern alarms
            for a in detect_alarms(closes):
                key = a["pattern"] + ":" + ",".join(a.get("case_ids", []))
                if key in seen_alarms:
                    continue
                seen_alarms.add(key)
                a["ts"] = now.isoformat()
                a["n_closed"] = n
                a["elapsed_min"] = round(elapsed_min, 1)
                print(f"[watchdog] ALARM {a['pattern']}: {a['message']}", flush=True)
                with open(ALARM_FILE, "w") as f:
                    json.dump(a, f, indent=2, default=str)

            print(f"[watchdog] T+{elapsed_min:5.1f}m  n={n}", flush=True)
        except Exception as e:
            print(f"[watchdog] error: {e}", flush=True)

        time.sleep(POLL_INTERVAL_SEC)

    print("[watchdog] done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
