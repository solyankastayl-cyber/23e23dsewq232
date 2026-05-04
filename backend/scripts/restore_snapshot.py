#!/usr/bin/env python3
"""Restore Mongo collections from JSONL snapshot.
Usage: python3 scripts/restore_snapshot.py [input_dir] [--drop]
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, '/app/backend')
try:
    from dotenv import load_dotenv
    load_dotenv('/app/backend/.env')
except Exception:
    pass

from pymongo import MongoClient
from bson import json_util

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('PHASE_B1_DB', 'trading_os')

args = [a for a in sys.argv[1:] if not a.startswith('--')]
drop_flag = '--drop' in sys.argv

in_dir = Path(args[0]) if args else Path('/app/data_snapshots/latest')
if not in_dir.exists():
    print(f"ERROR: snapshot directory not found: {in_dir}")
    sys.exit(1)

manifest_path = in_dir / "manifest.json"
if not manifest_path.exists():
    print(f"ERROR: manifest.json not found in {in_dir}")
    sys.exit(1)

with open(manifest_path) as f:
    manifest = json.load(f)

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

print(f"Restoring snapshot created at {manifest.get('created_at')}")
print(f"Target DB: {DB_NAME} @ {MONGO_URL}")
print(f"Drop existing: {drop_flag}")
print("-" * 60)

for col, info in manifest["collections"].items():
    path = in_dir / info["file"]
    if not path.exists():
        print(f"  SKIP {col} (missing file {info['file']})")
        continue
    if drop_flag:
        db[col].drop()
    docs = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            docs.append(json_util.loads(line))
    if not docs:
        continue
    # Batch insert; ignore duplicate _id on re-imports (unless dropped)
    inserted = 0
    skipped = 0
    for doc in docs:
        try:
            db[col].insert_one(doc)
            inserted += 1
        except Exception:
            skipped += 1
    print(f"  {col:40s} inserted={inserted:>6}  skipped_dup={skipped}")

print("\nRestore complete.")
