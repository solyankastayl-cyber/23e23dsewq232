"""
Take a fresh LIVE-2H state snapshot.

Captures collections required to resume the trading terminal at the current
phase (regime_controls + LIVE-2H trading_cases + audit events). The base
snapshot in `data_snapshots/latest/` is NOT touched — this is an *overlay*
on top of it.

Usage:
  python /app/scripts/snapshot_live2h.py
  python /app/scripts/snapshot_live2h.py --out /app/data_snapshots/live2h
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from bson import json_util
from pymongo import MongoClient


def get_db():
    return MongoClient(
        os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
        serverSelectionTimeoutMS=5000,
    )["trading_os"]


# Collection → mongo query
def collections_to_dump() -> Dict[str, Any]:
    return {
        "regime_controls":      {},
        "trading_cases":        {"close_reason": {"$regex": "^LIVE2H_"}},
        "regime_guard_events":  {
            "timestamp": {
                "$gte": datetime(2026, 4, 25, 14, 40, tzinfo=timezone.utc)
            }
        },
        "position_exit_events": {"phase": "LIVE-2"},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/data_snapshots/live2h",
                    help="Output directory (will be created)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    db = get_db()

    manifest = {
        "taken_at": datetime.now(timezone.utc).isoformat(),
        "phase": "LIVE-2H",
        "collections": {},
    }

    for col_name, query in collections_to_dump().items():
        docs = list(db[col_name].find(query))
        out_path = os.path.join(args.out, f"{col_name}.jsonl")
        with open(out_path, "w") as f:
            for d in docs:
                f.write(json_util.dumps(d) + "\n")
        manifest["collections"][col_name] = {
            "count": len(docs),
            "query": str(query),
        }
        print(f"  {col_name}: {len(docs)} docs → {out_path}")

    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nmanifest → {args.out}/manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
