"""
Read-only HTTP surface for Root-Cause Aggregator.

    GET /api/ta-prediction-intelligence/root-causes
    GET /api/ta-prediction-intelligence/root-causes/by/{axis}
    GET /api/ta-prediction-intelligence/root-causes/weaknesses

Invalid axis returns ok=false + allowed list (per spec).
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .aggregator_service import compute_root_cause_report
from .types import AXES

router = APIRouter(
    prefix="/api/ta-prediction-intelligence/root-causes",
    tags=["ta-prediction-intelligence-root-causes"],
)


@router.get("")
def root_causes_full() -> Dict[str, Any]:
    return compute_root_cause_report()


@router.get("/by/{axis}")
def root_causes_by_axis(axis: str) -> Any:
    if axis not in AXES:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "invalid_axis", "allowed": AXES},
        )
    full = compute_root_cause_report()
    return {
        "ok": True,
        "aggregator_version": full["aggregator_version"],
        "computed_at": full["computed_at"],
        "axis": axis,
        "cohorts": full["by_axis"].get(axis, {}),
    }


@router.get("/weaknesses")
def root_causes_weaknesses() -> Dict[str, Any]:
    full = compute_root_cause_report()
    return {
        "ok": True,
        "aggregator_version": full["aggregator_version"],
        "computed_at": full["computed_at"],
        "actionable_weaknesses": full["actionable_weaknesses"],
        "summary": full["summary"],
    }
