"""
LIVE-2H baseline observer — read-only.

Polls trading_cases every 30s and prints a compact status line so we can
watch the baseline observation in real-time without spamming logs.

Usage:
  python /app/scripts/observe_live2h.py                     # one-shot snapshot
  python /app/scripts/observe_live2h.py --watch 90 30      # 90 min, 30s tick
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from collections import Counter

from pymongo import MongoClient


def snapshot(db) -> dict:
    """Compose a single observation snapshot."""
    now = datetime.now(timezone.utc)
    active = list(db.trading_cases.find({"status": "ACTIVE"}))
    closed_2h = list(
        db.trading_cases.find({
            "status": "CLOSED",
            "exit_rule": {"$in": ["TIME_EXIT", "TAKE_PROFIT", "STOP_LOSS"]},
            "close_reason": {"$regex": "^LIVE2H_"},
        }).sort("closed_at", 1)
    )
    skipped_recent = db.regime_guard_events.count_documents({
        "timestamp": {"$gte": datetime(2026, 4, 25, 14, 41, tzinfo=timezone.utc)}
    })
    rules = Counter(c.get("exit_rule") for c in closed_2h)
    sides = Counter(c.get("side") for c in closed_2h)
    pnls = [float(c.get("realized_pnl_pct") or 0) for c in closed_2h]
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    wr = wins / len(pnls) * 100 if pnls else 0
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0
    return {
        "ts": now.isoformat(),
        "active": len(active),
        "active_detail": [
            {
                "case": (a.get("case_id") or "")[:14],
                "side": a.get("side"),
                "entry": a.get("entry_price"),
                "mark": a.get("mark_price"),
                "pnl_pct": a.get("unrealized_pnl_pct"),
                "age_min": (
                    round(
                        (now - a["opened_at"].replace(tzinfo=timezone.utc)
                         ).total_seconds() / 60, 1
                    )
                    if a.get("opened_at") else None
                ),
            }
            for a in active
        ],
        "closed_live2h_total": len(closed_2h),
        "closed_live2h_by_rule": dict(rules),
        "closed_live2h_by_side": dict(sides),
        "wins": wins,
        "losses": losses,
        "wr_pct": round(wr, 2),
        "avg_pnl_pct": round(avg_pnl, 4),
        "regime_skips_since_baseline": skipped_recent,
    }


def render_line(s: dict) -> str:
    """Render a single status line."""
    head = (
        f"{s['ts'][:19]}  active={s['active']}  "
        f"closed_2H={s['closed_live2h_total']} "
        f"(W={s['wins']}/L={s['losses']} WR={s['wr_pct']:.1f}% "
        f"avg={s['avg_pnl_pct']:+.4f}%)"
    )
    rules = ",".join(f"{k}={v}" for k, v in s['closed_live2h_by_rule'].items())
    sides = ",".join(f"{k}={v}" for k, v in s['closed_live2h_by_side'].items())
    parts = [head]
    if rules:
        parts.append(f"  rules: {rules}")
    if sides:
        parts.append(f"  sides: {sides}")
    if s['active_detail']:
        a = s['active_detail'][0]
        parts.append(
            f"  active[0]: {a['case']} {a['side']} "
            f"entry={a['entry']} mark={a['mark']} "
            f"pnl={a['pnl_pct']}% age={a['age_min']}m"
        )
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", nargs=2, type=int, default=None,
                    metavar=("MINUTES", "INTERVAL_SEC"),
                    help="Watch mode: total minutes + tick interval (sec)")
    ap.add_argument("--out", type=str,
                    default="/tmp/live2h_observer.jsonl",
                    help="Append snapshots to this JSONL file")
    args = ap.parse_args()

    db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
                     serverSelectionTimeoutMS=5000)["trading_os"]

    if args.watch is None:
        s = snapshot(db)
        print(render_line(s))
        return 0

    minutes, interval = args.watch
    end = time.time() + minutes * 60
    print(f"[observer] watching for {minutes}m @ {interval}s tick. "
          f"writing → {args.out}")
    with open(args.out, "a") as f:
        while time.time() < end:
            s = snapshot(db)
            f.write(json.dumps(s, default=str) + "\n")
            f.flush()
            print(render_line(s))
            print("-" * 70)
            time.sleep(interval)
    print("[observer] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
