"""
Deterministic feature/schema hashing.

Rules (locked):
  * canonical JSON: sorted keys, no whitespace, dict-nested-aware
  * all floats rounded to 6 decimals BEFORE hashing (stable across platforms)
  * None is serialised as null and kept as-is (feature values never produce None
    in our pipeline — the builder writes 0.0/0 sentinels instead)
  * sha256 hex digest
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def _round_floats(obj: Any) -> Any:
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        # Avoid -0.0 vs 0.0 difference in hash.
        v = round(obj, 6)
        return 0.0 if v == 0 else v
    if isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round_floats(v) for v in obj]
    return obj


def canonical_json(data: Any) -> str:
    """
    Stable canonical serialization for hashing.

    * sorts keys at every depth
    * rounds floats to 6 decimals
    * no insignificant whitespace
    * ensure_ascii=True for byte-stable output across locales
    """
    return json.dumps(
        _round_floats(data),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def build_feature_hash(features: Dict[str, Any]) -> str:
    """sha256 of canonicalised feature dict (after float rounding)."""
    return sha256_hex(canonical_json(features))


def build_schema_hash(schema: Dict[str, Any]) -> str:
    """sha256 of canonicalised schema definition."""
    return sha256_hex(canonical_json(schema))
