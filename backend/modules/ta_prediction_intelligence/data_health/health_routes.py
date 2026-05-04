"""
Read-only HTTP surface for the data health layer.

    GET /api/ta-prediction-intelligence/data-health
    GET /api/ta-prediction-intelligence/data-health/checks
    GET /api/ta-prediction-intelligence/data-health/drift
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from .health_service import compute_health_report
from .health_checks import (
    debug_health,
    feature_health,
    outcome_health,
    pipeline_health,
)
from .drift_checks import drift_checks
from .health_service import _default_db

router = APIRouter(
    prefix="/api/ta-prediction-intelligence/data-health",
    tags=["ta-prediction-intelligence-data-health"],
)


@router.get("")
def data_health_summary() -> Dict[str, Any]:
    return compute_health_report()


@router.get("/checks")
def data_health_checks() -> Dict[str, Any]:
    db = _default_db()
    return {
        "ok": True,
        "checks": {
            "pipeline": pipeline_health(db).to_dict(),
            "features": feature_health(db).to_dict(),
            "outcomes": outcome_health(db).to_dict(),
            "debug": debug_health(db).to_dict(),
        },
    }


@router.get("/drift")
def data_health_drift() -> Dict[str, Any]:
    db = _default_db()
    return {"ok": True, "drift": drift_checks(db).to_dict()}
