"""
Orchestrator — calls 5 components, applies 3 hard gates, derives status &
recommendation, assembles the locked output contract.

Live-only (no persistence in v1).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .types import (
    BlockingFactor,
    DATA_HEALTH_BROKEN,
    FEATURE_INTEGRITY_GATE,
    MIN_TOTAL_SAMPLES,
    ML_READINESS_BUILDER_VERSION,
    ML_READINESS_VERSION,
    Status,
    TARGET_TOTAL_SAMPLES,
)
from .readiness_metrics import (
    compute_class_balance,
    compute_error_stability,
    compute_feature_integrity,
    compute_regime_coverage,
    compute_sample_quality,
)
from .readiness_score import (
    compute_final_score,
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
            return MongoClient(
                os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
                serverSelectionTimeoutMS=3000,
            )["trading_os"]
        except Exception:
            return None


def _data_health_report() -> Optional[Dict[str, Any]]:
    try:
        from modules.ta_prediction_intelligence.data_health.health_service import (
            compute_health_report,
        )
        return compute_health_report()
    except Exception:
        return None


def compute_readiness_report(
    db: Any = None,
    data_health_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    db = db if db is not None else _default_db()
    if data_health_report is None:
        data_health_report = _data_health_report()

    sample_quality, sq_block, sq_details = compute_sample_quality(db)
    class_balance, cb_block, cb_details = compute_class_balance(db)
    error_stability, es_block, es_details = compute_error_stability(db)
    feature_integrity, fi_block, fi_details = compute_feature_integrity(
        data_health_report
    )
    regime_coverage, rc_block, rc_details = compute_regime_coverage(db)

    components = {
        "sample_quality": sample_quality,
        "feature_integrity": feature_integrity,
        "class_balance": class_balance,
        "error_stability": error_stability,
        "regime_coverage": regime_coverage,
    }
    blocking: List[str] = []
    blocking.extend(sq_block)
    blocking.extend(cb_block)
    blocking.extend(es_block)
    blocking.extend(fi_block)
    blocking.extend(rc_block)

    # ── Hard gates ─────────────────────────────────────────────────────────────
    total_samples = int(sq_details.get("total") or 0)
    data_health_status = (data_health_report or {}).get("status") if data_health_report else None

    data_health_ok = data_health_status not in (DATA_HEALTH_BROKEN,)
    total_samples_ok = total_samples >= MIN_TOTAL_SAMPLES
    feature_integrity_ok = feature_integrity >= FEATURE_INTEGRITY_GATE

    if not data_health_ok:
        blocking.append(BlockingFactor.DATA_HEALTH_BROKEN.value)
    if not total_samples_ok:
        blocking.append(BlockingFactor.LOW_TOTAL_SAMPLES.value)
    if not feature_integrity_ok:
        blocking.append(BlockingFactor.FEATURE_INTEGRITY_LOW.value)

    # Dedup while preserving order
    seen = set()
    blocking_clean: List[str] = []
    for b in blocking:
        if b in seen:
            continue
        seen.add(b)
        blocking_clean.append(b)

    hard_gate_triggered = not (
        data_health_ok and total_samples_ok and feature_integrity_ok
    )

    score = compute_final_score(components)
    status = derive_status(score, hard_gate_triggered)
    recommendation = derive_recommendation(status, blocking_clean)

    return {
        "ok": True,
        "ml_readiness_version": ML_READINESS_VERSION,
        "builder_version": ML_READINESS_BUILDER_VERSION,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "status": status.value,
        "readiness_score": score,
        "min_samples_for_training": TARGET_TOTAL_SAMPLES,
        "hard_gates": {
            "data_health_ok": bool(data_health_ok),
            "total_samples_ok": bool(total_samples_ok),
            "feature_integrity_ok": bool(feature_integrity_ok),
        },
        "components": {k: round(float(v), 4) for k, v in components.items()},
        "blocking_factors": blocking_clean,
        "recommendation": recommendation.value,
        "details": {
            "samples": sq_details,
            "class_balance": cb_details,
            "error_stability": es_details,
            "feature_integrity": fi_details,
            "regime_coverage": rc_details,
            "data_health_status": data_health_status,
        },
    }
