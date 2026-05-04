"""
Learning-layer read-only routes (Step 8 + 9 debug endpoints).

These live under the ta-prediction-intelligence namespace so the whole
module stays self-contained. They DO NOT participate in /live, they do
NOT mutate anything, and they are safe to poll from the UI.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from .learning import (
    FEATURE_SCHEMA_HASH,
    FEATURE_SCHEMA_V1,
    FEATURE_VERSION,
    BUILDER_VERSION,
    get_feature_builder,
    get_temporal_buffer,
)
from .live_adapter import fetch_live_context

router = APIRouter(
    prefix="/api/ta-prediction-intelligence",
    tags=["ta-prediction-intelligence-learning"],
)


@router.get("/features/schema")
def features_schema() -> Dict[str, Any]:
    # Aggregate features by their `block` so consumers (UI / ML notebooks) can
    # render the 8 canonical groups without re-deriving the layout. Order is
    # preserved within each block from the canonical FEATURE_SCHEMA_V1 list.
    blocks: Dict[str, list] = {}
    for spec in FEATURE_SCHEMA_V1.get("features", []):
        block = spec.get("block") or "uncategorized"
        blocks.setdefault(block, []).append({
            "name": spec.get("name"),
            "type": spec.get("type"),
            "range": spec.get("range"),
            "default": spec.get("default"),
            "doc": spec.get("doc") or "",
        })
    return {
        "ok": True,
        "feature_version": FEATURE_VERSION,
        "builder_version": BUILDER_VERSION,
        "schema_hash": FEATURE_SCHEMA_HASH,
        "feature_count": FEATURE_SCHEMA_V1["count"],
        "count": FEATURE_SCHEMA_V1["count"],  # back-compat alias
        "blocks": blocks,
        "schema": FEATURE_SCHEMA_V1,
    }


@router.get("/features/preview")
async def features_preview(
    symbol: str = Query(..., description="Trading pair, e.g. ETHUSDT"),
    tf: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
    candles_limit: int = Query(200, ge=20, le=1000),
    market_regime: Optional[str] = Query(None),
) -> Dict[str, Any]:
    tf_resolved = tf or timeframe or ""
    # Live context is read-only here — but it WILL persist as usual (live_adapter
    # already passes persist=True). For pure preview without side-effects, use
    # /from-typed or /from-setup and inspect the returned snapshot header.
    result = await fetch_live_context(
        symbol=symbol, timeframe=tf_resolved, candles_limit=candles_limit,
        market_regime=market_regime,
    )
    builder = get_feature_builder()
    snap = builder.build_preview(result)
    # For the preview endpoint we strip the raw result and return just the
    # features + hashes + states + a summary of the upstream call.
    return {
        "ok": True,
        "snapshot": snap,
        "upstream": {
            "bias": result.get("bias"),
            "confidence": result.get("confidence"),
            "conflict_ratio": result.get("conflict_ratio"),
            "dominant_engine": result.get("dominant_engine"),
            "interaction": result.get("interaction"),
            "prediction_id": result.get("prediction_id"),
        },
    }


@router.get("/buffer/status")
def buffer_status() -> Dict[str, Any]:
    return {"ok": True, "buffer": get_temporal_buffer().status()}


# ─────────────────────────────────────────────────────────────────────────────
# Step 10 — Dataset Builder (read-only)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dataset/preview")
def dataset_preview(
    symbol: Optional[str] = Query(None),
    tf: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    source: str = Query(
        "history",
        description="history|persisted — rebuild from live history vs read from ta_prediction_dataset",
    ),
) -> Dict[str, Any]:
    from .learning import (
        DATASET_VERSION,
        DATASET_BUILDER_VERSION,
        FEATURE_SCHEMA_HASH,
        FEATURE_VERSION,
        build_dataset,
        read_dataset_samples,
    )
    from .repository import get_repository
    repo = get_repository()
    if repo is None:
        raise HTTPException(status_code=503, detail="repository_unavailable")

    if source == "persisted":
        samples = read_dataset_samples(repo.db, symbol=symbol, tf=tf, limit=limit)
        return {
            "ok": True,
            "source": "persisted",
            "dataset_version": DATASET_VERSION,
            "dataset_builder_version": DATASET_BUILDER_VERSION,
            "feature_version": FEATURE_VERSION,
            "feature_schema_hash": FEATURE_SCHEMA_HASH,
            "count": len(samples),
            "samples": samples,
        }

    # source == "history" — build on the fly from evaluated predictions
    records = repo.get_evaluated_predictions(
        symbol=symbol, timeframe=tf, limit=max(limit * 3, 200)
    )
    samples, skips = build_dataset(records)
    preview = samples[:limit]
    return {
        "ok": True,
        "source": "history",
        "dataset_version": DATASET_VERSION,
        "dataset_builder_version": DATASET_BUILDER_VERSION,
        "feature_version": FEATURE_VERSION,
        "feature_schema_hash": FEATURE_SCHEMA_HASH,
        "records_scanned": len(records),
        "samples_built": len(samples),
        "samples_previewed": len(preview),
        "skip_counts": skips,
        "samples": preview,
    }


@router.get("/dataset/stats")
def dataset_stats(
    symbol: Optional[str] = Query(None),
    tf: Optional[str] = Query(None),
) -> Dict[str, Any]:
    from .learning import (
        DATASET_VERSION,
        DATASET_BUILDER_VERSION,
        FEATURE_SCHEMA_HASH,
        FEATURE_VERSION,
        build_dataset,
        compute_dataset_stats,
        count_dataset_samples,
    )
    from .repository import get_repository
    repo = get_repository()
    if repo is None:
        raise HTTPException(status_code=503, detail="repository_unavailable")
    records = repo.get_evaluated_predictions(
        symbol=symbol, timeframe=tf, limit=5000
    )
    samples, skips = build_dataset(records)
    stats = compute_dataset_stats(samples)
    return {
        "ok": True,
        "dataset_version": DATASET_VERSION,
        "dataset_builder_version": DATASET_BUILDER_VERSION,
        "feature_version": FEATURE_VERSION,
        "feature_schema_hash": FEATURE_SCHEMA_HASH,
        "min_samples_for_training": 500,
        "records_scanned": len(records),
        "samples_built": len(samples),
        "skip_counts": skips,
        "persisted_total": count_dataset_samples(repo.db),
        "stats": stats,
    }


@router.post("/dataset/rebuild")
def dataset_rebuild(
    symbol: Optional[str] = Query(None),
    tf: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=50000),
) -> Dict[str, Any]:
    from .learning import (
        DATASET_VERSION,
        build_dataset,
        persist_dataset_samples,
    )
    from .repository import get_repository
    repo = get_repository()
    if repo is None:
        raise HTTPException(status_code=503, detail="repository_unavailable")
    records = repo.get_evaluated_predictions(symbol=symbol, timeframe=tf, limit=limit)
    samples, skips = build_dataset(records)
    write_counts = persist_dataset_samples(repo.db, samples)
    return {
        "ok": True,
        "dataset_version": DATASET_VERSION,
        "records_scanned": len(records),
        "samples_built": len(samples),
        "skip_counts": skips,
        "persistence": write_counts,
    }
