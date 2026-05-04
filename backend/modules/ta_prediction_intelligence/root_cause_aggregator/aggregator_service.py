"""
Orchestrator — read joined data, build cohorts, score them, collect
actionable weaknesses, assemble the locked output contract.

Live-only. No persistence. No mutations.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .cohort_builder import build_cohorts, build_global, load_joined_records
from .types import (
    AGGREGATOR_BUILDER_VERSION,
    AGGREGATOR_VERSION,
    AXES,
    MIN_COHORT,
)
from .weakness_detector import collect_actionable


def _default_db():
    try:
        from core.database import get_database
        return get_database()
    except Exception:
        try:
            from pymongo import MongoClient
            return MongoClient(
                os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
                serverSelectionTimeoutMS=3000,
            )["trading_os"]
        except Exception:
            return None


def compute_root_cause_report(db: Any = None) -> Dict[str, Any]:
    db = db if db is not None else _default_db()
    joined = load_joined_records(db)
    by_axis = build_cohorts(joined)
    actionable = collect_actionable(by_axis)
    glob = build_global(joined)

    return {
        "ok": True,
        "aggregator_version": AGGREGATOR_VERSION,
        "builder_version": AGGREGATOR_BUILDER_VERSION,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "axes": AXES,
        "by_axis": by_axis,
        "actionable_weaknesses": actionable,
        "summary": {
            "total_debug_records": glob["total_debug_records"],
            "total_error_records": glob["total_error_records"],
            "actionable_count": len(actionable),
            "concentration_global": glob["concentration_global"],
            "global_distribution_top10": glob["global_distribution_top10"],
            "min_cohort_size": MIN_COHORT,
        },
    }
