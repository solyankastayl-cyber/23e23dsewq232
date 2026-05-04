"""
Orchestrator — calls each block, mixes scores, derives status & recommendation.

Pure for everything that's not Mongo IO. The single side-effect is the
actual `find/count_documents` calls inside the block functions — all reads.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .types import (
    DATA_HEALTH_BUILDER_VERSION,
    DATA_HEALTH_VERSION,
    HealthIssue,
    Severity,
)
from .health_checks import (
    debug_health,
    feature_health,
    outcome_health,
    pipeline_health,
)
from .drift_checks import drift_checks
from .trust_score import (
    compute_trust_score,
    derive_recommendation,
    derive_status,
)


def _default_db():
    try:
        from core.database import get_database
        return get_database()
    except Exception:
        try:
            from pymongo import MongoClient
            url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            return MongoClient(url, serverSelectionTimeoutMS=3000)["trading_os"]
        except Exception:
            return None


def compute_health_report(db: Any = None) -> Dict[str, Any]:
    """
    Run all 5 checks (pipeline, features, outcomes, debug, drift),
    aggregate trust score, derive status + recommendation.

    Read-only on every collection. Returns the canonical contract dict.
    """
    if db is None:
        db = _default_db()

    pipeline = pipeline_health(db)
    features = feature_health(db)
    outcomes = outcome_health(db)
    debug = debug_health(db)
    drift = drift_checks(db)

    block_scores = {
        pipeline.block: pipeline.score,
        features.block: features.score,
        outcomes.block: outcomes.score,
        debug.block: debug.score,
        drift.block: drift.score,
    }
    trust_score = compute_trust_score(block_scores)

    all_issues = []
    for cr in (pipeline, features, outcomes, debug, drift):
        all_issues.extend(cr.issues)

    status = derive_status(trust_score, all_issues)
    evaluated_count = int(pipeline.metrics.get("evaluated_count") or 0)
    recommendation = derive_recommendation(status, evaluated_count)

    return {
        "ok": True,
        "data_health_version": DATA_HEALTH_VERSION,
        "builder_version": DATA_HEALTH_BUILDER_VERSION,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "status": status.value,
        "trust_score": trust_score,
        "recommendation": recommendation.value,
        "block_scores": {k: round(v, 4) for k, v in block_scores.items()},
        "issues": [i.to_dict() for i in all_issues],
        "checks": {
            "pipeline": pipeline.to_dict(),
            "features": features.to_dict(),
            "outcomes": outcomes.to_dict(),
            "debug": debug.to_dict(),
            "drift": drift.to_dict(),
        },
    }
