"""
snapshot_db.py
==============

Dump selected MongoDB collections to JSONL files under
`/app/data_snapshots/latest/`.

Designed to pair with `restore_snapshot.py --mode base`. Running this
script is idempotent: the target directory is wiped of snapshot files
before writing. A `manifest.json` with counts + timestamp is produced
for integrity checks.

Collections that are runtime-only (heartbeats, sync logs, ephemeral
caches) are excluded by default to keep the snapshot tight and
committable to git.

Usage
-----
    python3 /app/scripts/snapshot_db.py
    python3 /app/scripts/snapshot_db.py --out /app/data_snapshots/my_tag
    python3 /app/scripts/snapshot_db.py --include worker_heartbeats
    python3 /app/scripts/snapshot_db.py --exclude candles
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Iterable, List, Set

from bson import json_util
from pymongo import MongoClient


# --- which collections are worth committing to git ---------------------
# These contain the accumulated trading history, config flags, audit
# trails, TA engine memory, and anything else needed to resume the live
# system in the same state.
DEFAULT_INCLUDE: List[str] = [
    # Historical ground truth
    "trading_cases",
    "ideas",
    "shadow_trades",
    # Live execution pipeline (payload carries LIVE-3d market_ctx)
    "execution_jobs",
    "execution_events",
    "execution_queue_audit",
    "execution_readiness_decisions",
    # Feature gates & their audit trail
    "regime_controls",
    "regime_alerts",
    "regime_decisions",
    "regime_guard_events",
    "regime_model_metrics",
    "vol_gate_events",
    "conf_gate_events",
    # Auto-runner state + audit
    "auto_runner_audit",
    "auto_safety_config",
    "auto_safety_state",
    # Signal & decision flow
    "pending_decisions",
    "position_exit_events",
    "generator_state",
    # TA engine memory
    "ta_prediction_history",
    "ta_prediction_temporal_buffer",
    "pattern_history",
    "pattern_outcomes",
    # Research / experiments / config
    "research_states",
    "experiments",
    "runtime_config",
    "exchange_balances",
    # Market data snapshots (needed for regime warmup)
    "candles",
]

# Collections we deliberately skip — runtime-only, churn every few seconds,
# and bloat the repo without carrying restart state.
DEFAULT_EXCLUDE_RUNTIME: Set[str] = {
    "worker_heartbeats",
    "exchange_sync_logs",
}


def get_db():
    url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "trading_os")
    return MongoClient(url, serverSelectionTimeoutMS=5000)[db_name]


def _wipe_old_jsonl(out_dir: str) -> None:
    if not os.path.isdir(out_dir):
        return
    for fn in os.listdir(out_dir):
        if fn.endswith(".jsonl") or fn == "manifest.json":
            try:
                os.remove(os.path.join(out_dir, fn))
            except OSError:
                pass


def _dump_collection(db, name: str, path: str) -> int:
    """Write every doc in collection `name` as one JSONL line.

    Returns number of docs written.
    """
    col = db[name]
    n = 0
    with open(path, "w") as f:
        # sort by _id for deterministic output → smaller git diffs on
        # repeat snapshots.
        for doc in col.find().sort("_id", 1):
            f.write(json_util.dumps(doc))
            f.write("\n")
            n += 1
    return n


def snapshot(
    out_dir: str,
    include: Iterable[str] | None = None,
    extra_include: Iterable[str] | None = None,
    extra_exclude: Iterable[str] | None = None,
) -> None:
    db = get_db()
    present = set(db.list_collection_names())

    include_set = set(include) if include is not None else set(DEFAULT_INCLUDE)
    if extra_include:
        include_set.update(extra_include)
    if extra_exclude:
        include_set.difference_update(set(extra_exclude))

    # Only export collections that actually exist — missing ones are
    # silently skipped so the script is safe on fresh DBs.
    targets = sorted(c for c in include_set if c in present)
    missing = sorted(c for c in include_set if c not in present)

    os.makedirs(out_dir, exist_ok=True)
    _wipe_old_jsonl(out_dir)

    manifest = {
        "snapshot_taken_at": datetime.now(timezone.utc).isoformat(),
        "db_name": db.name,
        "host": os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
        "collections": {},
        "skipped_runtime": sorted(DEFAULT_EXCLUDE_RUNTIME),
        "missing": missing,
    }

    total = 0
    for col_name in targets:
        path = os.path.join(out_dir, f"{col_name}.jsonl")
        count = _dump_collection(db, col_name, path)
        manifest["collections"][col_name] = count
        total += count
        print(f"  [+] {col_name}: {count} docs → {path}")

    manifest["total_docs"] = total
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    print(f"\n[snapshot-db] dumped {len(targets)} collections, "
          f"{total} docs total → {out_dir}")
    if missing:
        print(f"[snapshot-db] note: {len(missing)} collections in include "
              f"list were not present in DB: {missing}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Dump live MongoDB to JSONL snapshot for git.",
    )
    ap.add_argument(
        "--out",
        default="/app/data_snapshots/latest",
        help="Output directory (default: /app/data_snapshots/latest)",
    )
    ap.add_argument(
        "--include",
        action="append",
        default=[],
        help="Extra collection to include (repeatable)",
    )
    ap.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Collection from default list to exclude (repeatable)",
    )
    args = ap.parse_args()

    snapshot(
        out_dir=args.out,
        extra_include=args.include or None,
        extra_exclude=args.exclude or None,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
