"""
Debug Layer routes — read-only surface for inspection.

    GET  /api/ta-prediction-intelligence/debug/preview?symbol=&tf=&limit=
    GET  /api/ta-prediction-intelligence/debug/stats?symbol=&tf=&limit=
    GET  /api/ta-prediction-intelligence/debug/case/{prediction_id}
    POST /api/ta-prediction-intelligence/debug/rebuild?symbol=&tf=&limit=

The rebuild endpoint scans recent evaluated predictions and upserts a debug
record per prediction. It does NOT re-evaluate outcomes (that's the outcome
worker's job) and does NOT mutate prediction history.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from .debug import (
    analyze_record,
    build_debug_record,
    compute_metrics,
    get_debug_repository,
)
from .debug.service import analyze_many
from .repository import get_repository

router = APIRouter(
    prefix="/api/ta-prediction-intelligence/debug",
    tags=["ta-prediction-intelligence-debug"],
)


def _repo_or_503():
    repo = get_debug_repository()
    if repo is None:
        raise HTTPException(status_code=503, detail="debug_repository_unavailable")
    return repo


def _history_or_503():
    repo = get_repository()
    if repo is None:
        raise HTTPException(status_code=503, detail="history_repository_unavailable")
    return repo


@router.get("/preview")
def debug_preview(
    symbol: Optional[str] = Query(None),
    tf: Optional[str] = Query(None),
    error_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> Dict[str, Any]:
    """Recent debug records (read from ta_prediction_debug). Read-only."""
    repo = _repo_or_503()
    items = repo.list_recent(
        symbol=symbol, tf=tf, error_type=error_type, limit=limit
    )
    return {
        "ok": True,
        "count": len(items),
        "items": items,
    }


@router.get("/stats")
def debug_stats(
    symbol: Optional[str] = Query(None),
    tf: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=50000),
) -> Dict[str, Any]:
    """Tier 1 / 2 / 3 metrics aggregated from ta_prediction_debug."""
    repo = _repo_or_503()
    items = repo.list_for_metrics(symbol=symbol, tf=tf, limit=limit)
    metrics = compute_metrics(items)
    return {
        "ok": True,
        "filters": {"symbol": symbol, "tf": tf, "limit": limit},
        "sample_size": metrics["sample_size"],
        "tier1": metrics["tier1"],
        "tier2": metrics["tier2"],
        "tier3": metrics["tier3"],
    }


@router.get("/case/{prediction_id}")
def debug_case(prediction_id: str) -> Dict[str, Any]:
    """Single debug record by prediction_id.

    If a debug record doesn't exist yet, build it on the fly from history
    (without persisting) so the caller sees the analysis even before the
    next rebuild — useful for instrumenting one specific case.
    """
    repo = _repo_or_503()
    rec = repo.get(prediction_id)
    if rec:
        return {"ok": True, "source": "persisted", "record": rec}
    history = _history_or_503()
    history_rec = history.get_prediction(prediction_id) if hasattr(
        history, "get_prediction"
    ) else None
    if not history_rec:
        raise HTTPException(status_code=404, detail="prediction_not_found")
    built = build_debug_record(history_rec)
    if built is None:
        return {
            "ok": True,
            "source": "history",
            "record": None,
            "reason": "prediction_not_evaluated",
        }
    return {"ok": True, "source": "derived_on_the_fly", "record": built}


@router.post("/rebuild")
def debug_rebuild(
    symbol: Optional[str] = Query(None),
    tf: Optional[str] = Query(None),
    limit: int = Query(2000, ge=1, le=20000),
) -> Dict[str, Any]:
    """Re-scan recent evaluated predictions and upsert their debug records.

    Idempotent: the debug repo upserts by prediction_id.
    """
    history = _history_or_503()
    if hasattr(history, "get_evaluated_predictions"):
        records: List[Dict[str, Any]] = history.get_evaluated_predictions(
            symbol=symbol, timeframe=tf, limit=limit
        )
    else:
        records = []
    counts = analyze_many(records)
    return {
        "ok": True,
        "records_scanned": len(records),
        "analyzed": counts["analyzed"],
        "skipped": counts["skipped"],
    }
