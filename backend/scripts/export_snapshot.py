#!/usr/bin/env python3
"""Dump all non-empty Mongo collections from `trading_os` to JSONL.
Usage: python3 scripts/export_snapshot.py [output_dir]
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

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

out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/app/data_snapshots/latest')
out_dir.mkdir(parents=True, exist_ok=True)

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

manifest = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "db_name": DB_NAME,
    "collections": {},
}

for col in sorted(db.list_collection_names()):
    n = db[col].count_documents({})
    if n == 0:
        continue
    path = out_dir / f"{col}.jsonl"
    written = 0
    with open(path, 'w') as f:
        for doc in db[col].find({}):
            f.write(json_util.dumps(doc) + '\n')
            written += 1
    manifest["collections"][col] = {"count": written, "file": f"{col}.jsonl"}
    print(f"  {col:40s} {written:>8} docs -> {path.name}")

with open(out_dir / "manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)

print(f"\nDone. Snapshot at: {out_dir}")
print(f"Total collections: {len(manifest['collections'])}")
