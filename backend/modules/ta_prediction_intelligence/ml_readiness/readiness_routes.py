"""
Read-only HTTP surface for ML Readiness Layer.

    GET /api/ta-prediction-intelligence/ml-readiness
    GET /api/ta-prediction-intelligence/ml-readiness/details

No POST. No persistence. Always live-computed.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from .readiness_service import compute_readiness_report

router = APIRouter(
    prefix="/api/ta-prediction-intelligence/ml-readiness",
    tags=["ta-prediction-intelligence-ml-readiness"],
)


@router.get("")
def ml_readiness_summary() -> Dict[str, Any]:
    """Trim-down view: status / score / hard_gates / components / blocking / recommendation."""
    full = compute_readiness_report()
    full.pop("details", None)
    return full


@router.get("/details")
def ml_readiness_details() -> Dict[str, Any]:
    """Full view including the per-component evidence (samples, distributions, regimes)."""
    return compute_readiness_report()
