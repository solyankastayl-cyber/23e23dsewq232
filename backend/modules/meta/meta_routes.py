"""
Meta Layer Routes (Pass 4 + Pass 4.3 + Pass 5)

Endpoints:
    GET /api/meta/health
    GET /api/meta/score                       — ad-hoc score (manual source)
    GET /api/meta/policies                    — registry snapshot
    GET /api/meta/shadow/recent               — recent decisions
    GET /api/meta/shadow/stats                — buckets / totals
    GET /api/meta/shadow/performance          — Pass 5: WR / PF / DD / Sharpe-like
    GET /api/meta/scheduler/status            — Pass 5: forward-test loop health
    GET /api/meta/outcome_evaluator/status    — Pass 5: evaluator loop health

NEVER places an order. Decision math lives in meta_scoring_engine, the
policy overlay in policy_registry, the recording in shadow_logger.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

from modules.meta.meta_pipeline import (
    build_snapshot,
    compute_decision,
    extract_current_price,
)
from modules.meta.policy_registry import list_policies
from modules.meta.shadow_logger import (
    aggregate_performance,
    get_recent_signals,
    get_stats,
    record_shadow_signal,
)
from modules.meta.shadow_outcome_evaluator import get_outcome_evaluator
from modules.meta.shadow_scheduler import get_shadow_scheduler

router = APIRouter(prefix="/api/meta", tags=["meta-decision-layer"])


# ────────────────────────────────────────────────────────────────────────────
# Health
# ────────────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    return {
        "ok": True,
        "module": "meta_scoring_engine",
        "layer": "DECISION_MATH",
        "trading": False,
        "shadow_mode": True,
        "note": "Produces strategy_score & allocation; logs decisions only. No order execution.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ────────────────────────────────────────────────────────────────────────────
# Score endpoint (manual / ad-hoc)
# ────────────────────────────────────────────────────────────────────────────

@router.get("/score")
async def score(
    symbol: str = Query("BTCUSDT", description="Trading pair, e.g. BTCUSDT"),
    tf: str = Query("4H", description="Canonical timeframe: 1H, 4H, 1D"),
    log_shadow: bool = Query(
        True,
        description="If True (default) — append decision to meta_shadow_signals (source=manual).",
    ),
):
    """
    Final meta decision via shared meta_pipeline.compute_decision().

    Honest behaviour:
      * No combined_analysis → score=0, allocation=0
      * quality=LOW          → SKIP
      * regime=balanced      → SKIP
      * CRITICAL risk        → allocation forced to 0
      * sample<30 hypothesis → demoted (base_score *= 0.5)
    """
    decision, analysis, policy = await compute_decision(symbol, tf)

    if log_shadow:
        current_price = extract_current_price(analysis)
        snapshot = build_snapshot(analysis, decision, current_price=current_price)
        shadow_id = record_shadow_signal(
            symbol=symbol,
            timeframe=tf,
            policy_name=policy.name,
            regime=decision.get("regime"),
            decision=decision,
            snapshot=snapshot,
            entry_price=current_price,
            source="manual",
            # Phase 6 / P0 — propagate market regime + explicit score regime.
            market_regime=decision.get("market_regime"),
            score_regime=decision.get("score_regime") or decision.get("regime"),
        )
        decision["shadow_id"] = shadow_id

    return decision


# ────────────────────────────────────────────────────────────────────────────
# Registry snapshot
# ────────────────────────────────────────────────────────────────────────────

@router.get("/policies")
async def policies():
    return {
        "ok": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **list_policies(),
    }


# ────────────────────────────────────────────────────────────────────────────
# Shadow log views
# ────────────────────────────────────────────────────────────────────────────

@router.get("/shadow/recent")
async def shadow_recent(
    symbol: Optional[str] = Query(None),
    tf: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    items = get_recent_signals(symbol=symbol, timeframe=tf, limit=limit)
    return {
        "ok": True,
        "count": len(items),
        "items": items,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/shadow/stats")
async def shadow_stats(
    symbol: Optional[str] = Query(None),
    tf: Optional[str] = Query(None),
):
    return {
        "ok": True,
        "filter": {"symbol": symbol, "timeframe": tf},
        "stats": get_stats(symbol=symbol, timeframe=tf),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ────────────────────────────────────────────────────────────────────────────
# Performance (Pass 5)
# ────────────────────────────────────────────────────────────────────────────

@router.get("/shadow/performance")
async def shadow_performance(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    tf: Optional[str] = Query(None, description="Filter by timeframe"),
    policy: Optional[str] = Query(None, description="Filter by policy name"),
    regime: Optional[str] = Query(None, description="(legacy) score_regime: uncertain | balanced | overheated"),
    score_regime: Optional[str] = Query(None, description="uncertain | balanced | overheated"),
    market_regime: Optional[str] = Query(None, description="trend | range | compression | high_volatility"),
    source: Optional[str] = Query(None, description="scheduler | manual"),
):
    """
    Live-shadow performance per horizon (h1 / h3 / h6).
    Aggregates only EVALUATED records and only those where should_trade==True.

    Phase 6 / P0 — added independent filters:
      * `score_regime`  (universal toxic-band classifier)
      * `market_regime` (independent regime_detector label)
    `regime` is kept as alias of `score_regime` for back-compat.
    """
    perf = aggregate_performance(
        symbol=symbol, timeframe=tf, policy=policy,
        regime=regime, score_regime=score_regime,
        market_regime=market_regime,
        source=source,
    )
    return {
        "ok": True,
        "filter": {
            "symbol": symbol, "timeframe": tf, "policy": policy,
            "regime": regime, "score_regime": score_regime,
            "market_regime": market_regime, "source": source,
        },
        "performance": perf,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ────────────────────────────────────────────────────────────────────────────
# Background tasks status (Pass 5)
# ────────────────────────────────────────────────────────────────────────────

@router.get("/scheduler/status")
async def scheduler_status() -> Dict[str, Any]:
    return {
        "ok": True,
        "scheduler": get_shadow_scheduler().status(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/outcome_evaluator/status")
async def outcome_evaluator_status() -> Dict[str, Any]:
    return {
        "ok": True,
        "evaluator": get_outcome_evaluator().status(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
