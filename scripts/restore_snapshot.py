"""
Restore MongoDB collections from a JSONL snapshot directory.

Two modes:

  base    — restore the canonical large-collection snapshot
            (data_snapshots/latest). Only restores collections that are
            currently empty in Mongo, unless --force-empty-only is unset.
            Skips collections already containing data.

  overlay — apply a small targeted overlay snapshot on top of an existing DB
            (data_snapshots/live2h). Each document is upserted by a key
            chosen per-collection (case_id, control, etc.). Existing docs
            are NOT deleted; the overlay only inserts/updates the rows in
            the snapshot.

This script is read-friendly and idempotent. Safe to re-run.

Usage:
  python /app/scripts/restore_snapshot.py --snapshot /app/data_snapshots/latest --mode base
  python /app/scripts/restore_snapshot.py --snapshot /app/data_snapshots/live2h --mode overlay
"""
import argparse
import os
import sys
from typing import Any, Dict

from bson import json_util
from pymongo import MongoClient


# Per-collection upsert key for overlay mode.
OVERLAY_KEYS: Dict[str, str] = {
    "trading_cases":         "case_id",
    "regime_controls":       "control",
    "regime_guard_events":   "_id",
    "position_exit_events":  "_id",
}


def get_db():
    url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    return MongoClient(url, serverSelectionTimeoutMS=5000)["trading_os"]


def iter_jsonl(path: str):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json_util.loads(line)


def restore_base(snapshot_dir: str, force_empty_only: bool = True) -> None:
    """Restore canonical large-collection snapshot.

    Skips collections that are already non-empty unless force_empty_only=False.
    """
    db = get_db()
    files = sorted(
        f for f in os.listdir(snapshot_dir) if f.endswith(".jsonl")
    )
    print(f"[restore-base] found {len(files)} jsonl files in {snapshot_dir}")
    for fn in files:
        col_name = fn[:-len(".jsonl")]
        col = db[col_name]
        existing = col.estimated_document_count()
        if force_empty_only and existing > 0:
            print(f"  skip {col_name}: already {existing} docs (force_empty_only=True)")
            continue
        n = 0
        bulk = []
        for doc in iter_jsonl(os.path.join(snapshot_dir, fn)):
            bulk.append(doc)
            if len(bulk) >= 500:
                col.insert_many(bulk, ordered=False)
                n += len(bulk)
                bulk = []
        if bulk:
            col.insert_many(bulk, ordered=False)
            n += len(bulk)
        print(f"  restored {col_name}: {n} docs")


def restore_overlay(snapshot_dir: str) -> None:
    """Overlay small targeted snapshot via upserts (does not delete)."""
    db = get_db()
    if not os.path.isdir(snapshot_dir):
        print(f"[restore-overlay] {snapshot_dir} not found, skip")
        return
    files = sorted(
        f for f in os.listdir(snapshot_dir) if f.endswith(".jsonl")
    )
    print(f"[restore-overlay] found {len(files)} files in {snapshot_dir}")
    for fn in files:
        col_name = fn[:-len(".jsonl")]
        col = db[col_name]
        key = OVERLAY_KEYS.get(col_name, "_id")
        n = 0
        upd = 0
        for doc in iter_jsonl(os.path.join(snapshot_dir, fn)):
            kval = doc.get(key)
            if kval is None:
                continue
            try:
                res = col.replace_one({key: kval}, doc, upsert=True)
                if res.modified_count or res.upserted_id:
                    upd += 1
            except Exception as e:
                print(f"    upsert failed {col_name}.{kval}: {e}")
                continue
            n += 1
        print(f"  overlay {col_name} (key={key}): {n} docs processed, "
              f"{upd} written")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True,
                    help="Snapshot directory containing *.jsonl")
    ap.add_argument("--mode", choices=["base", "overlay"], required=True)
    ap.add_argument("--force-empty-only", action="store_true",
                    help="(base mode) only insert into empty collections "
                         "(default behaviour)")
    args = ap.parse_args()

    if not os.path.isdir(args.snapshot):
        print(f"[restore] snapshot dir not found: {args.snapshot}",
              file=sys.stderr)
        return 1

    if args.mode == "base":
        restore_base(args.snapshot, force_empty_only=True)
    else:
        restore_overlay(args.snapshot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
