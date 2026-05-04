"""
Calibration Store (Step 7) — in-process cache of calibration stats loaded
from Mongo (collection: ta_prediction_calibration_stats).

Kept separate from the pure calibration_engine so the adjuster doesn't care
about I/O. Rebuild is explicit (via API or after worker evaluations). The
store is refreshed lazily with a short TTL so adjuster reads stay cheap.

No background rebuild loop — rebuild is explicit on /calibration/rebuild.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

_CACHE: Dict[str, Any] = {
    "at": 0.0,
    "stats_by_group": {},
}
_TTL_SECONDS = 30.0
_GROUPS = (
    "interaction_type",
    "dominant_engine",
    "symbol_tf",
    "symbol_tf_interaction",
)


def _load_from_mongo() -> Dict[str, List[Dict[str, Any]]]:
    try:
        from modules.ta_prediction_intelligence.repository import get_repository
        repo = get_repository()
        if not repo:
            return {g: [] for g in _GROUPS}
        out: Dict[str, List[Dict[str, Any]]] = {}
        for g in _GROUPS:
            rows = repo.get_calibration_stats(group_by=g)
            # repository.get_calibration_stats returns raw rows; each includes
            # bucket_key and metrics. Keep as-is.
            out[g] = rows or []
        return out
    except Exception:
        return {g: [] for g in _GROUPS}


def get_stats_by_group(force_refresh: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    now = time.time()
    if (
        force_refresh
        or not _CACHE["stats_by_group"]
        or (now - _CACHE["at"]) > _TTL_SECONDS
    ):
        _CACHE["stats_by_group"] = _load_from_mongo()
        _CACHE["at"] = now
    return _CACHE["stats_by_group"]


def invalidate() -> None:
    _CACHE["at"] = 0.0
    _CACHE["stats_by_group"] = {}


def rebuild_from_history() -> Dict[str, Any]:
    """
    Pull evaluated predictions from repo, run aggregate_calibration for every
    canonical group_by dimension, persist to the calibration collection, and
    refresh the cache. Returns a summary dict with counts.
    """
    from modules.ta_prediction_intelligence.repository import get_repository
    from modules.ta_prediction_intelligence.calibration.calibration_engine import (
        rebuild_all,
    )
    repo = get_repository()
    if not repo:
        return {"ok": False, "error": "repository_unavailable"}
    records = repo.get_evaluated_predictions(limit=5000)
    grouped = rebuild_all(records)
    summary = {"ok": True, "source_records": len(records), "buckets_per_group": {}}
    for group_by, buckets in grouped.items():
        written = repo.write_calibration_stats(group_by, buckets)
        summary["buckets_per_group"][group_by] = {
            "total": len(buckets),
            "written": written,
        }
    invalidate()
    # warm the cache
    get_stats_by_group(force_refresh=True)
    return summary
