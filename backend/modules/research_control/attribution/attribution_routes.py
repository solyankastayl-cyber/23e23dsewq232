"""
PHASE 17.4 — Attribution Routes
================================
API endpoints for Attribution / Failure Forensics Engine.

Endpoints:
- GET /api/v1/research-control/attribution/health
- GET /api/v1/research-control/attribution/trades/list
- POST /api/v1/research-control/attribution/batch
- GET /api/v1/research-control/attribution/summary/{trade_id}
- GET /api/v1/research-control/attribution/{trade_id}
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from modules.research_control.attribution.attribution_engine import (
    get_attribution_engine,
)
from modules.research_control.attribution.attribution_types import (
    TradeOutcome,
    FailureClassification,
    FailureSource,
    SystemLayer,
    DEFAULT_LAYER_WEIGHTS,
)

router = APIRouter(
    prefix="/api/v1/research-control/attribution",
    tags=["Attribution"]
)


# ══════════════════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════════════════

class AttributionBatchRequest(BaseModel):
    trade_ids: List[str]


# ══════════════════════════════════════════════════════════════
# STATIC ROUTES (must be before dynamic routes)
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def attribution_health():
    """Attribution Engine health check."""
    try:
        engine = get_attribution_engine()
        
        # Quick test analysis
        test_result = engine.analyze_trade("BTC_2026_03_13_01")
        
        return {
            "status": "healthy",
            "phase": "17.4",
            "module": "Attribution / Failure Forensics Engine",
            "description": "Final layer of Research Control Fabric - Explainable Trading System",
            "capabilities": [
                "Trade Attribution",
                "Layer Contribution Analysis",
                "Failure Forensics",
                "Human-readable Explanations",
            ],
            "layer_weights": {k.value: v for k, v in DEFAULT_LAYER_WEIGHTS.items()},
            "failure_classifications": [f.value for f in FailureClassification],
            "failure_sources": [f.value for f in FailureSource],
            "test_result": {
                "trade_id": test_result.trade_id,
                "outcome": test_result.trade_outcome.value,
                "primary_driver": test_result.primary_driver,
                "failure_reason": test_result.failure_reason.value if test_result.failure_reason else None,
                "responsible_layer": test_result.responsible_layer.value if test_result.responsible_layer else None,
            },
            "known_trades_count": len(engine.get_all_known_trades()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/trades/list")
async def list_trades():
    """List all known trades for attribution."""
    try:
        engine = get_attribution_engine()
        trades = engine.get_all_known_trades()
        
        return {
            "status": "ok",
            "trades": trades,
            "count": len(trades),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# BATCH ENDPOINT
# ══════════════════════════════════════════════════════════════

@router.post("/batch")
async def batch_analyze(request: AttributionBatchRequest):
    """Batch trade attribution analysis."""
    try:
        engine = get_attribution_engine()
        results = {}
        
        summary = {
            "total": len(request.trade_ids),
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "failure_classifications": {},
        }
        
        for trade_id in request.trade_ids:
            try:
                result = engine.analyze_trade(trade_id)
                results[trade_id] = result.to_summary()
                
                # Update summary
                outcome = result.trade_outcome.value.lower()
                if outcome == "win":
                    summary["wins"] += 1
                elif outcome == "loss":
                    summary["losses"] += 1
                else:
                    summary["breakeven"] += 1
                
                # Track failure classifications
                if result.failure_classification.value != "NONE":
                    fc = result.failure_classification.value
                    summary["failure_classifications"][fc] = \
                        summary["failure_classifications"].get(fc, 0) + 1
                        
            except Exception as e:
                results[trade_id] = {"error": str(e)}
        
        return {
            "status": "ok",
            "results": results,
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# DYNAMIC ROUTES (must be after static routes)
# ══════════════════════════════════════════════════════════════

@router.get("/summary/{trade_id}")
async def trade_summary(trade_id: str):
    """Compact attribution summary for a trade."""
    try:
        engine = get_attribution_engine()
        result = engine.analyze_trade(trade_id)
        
        return {
            "status": "ok",
            **result.to_summary(),
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trade_id}")
async def analyze_trade(trade_id: str):
    """
    Full attribution analysis for a trade.
    
    Returns:
    - trade_direction, trade_outcome
    - primary_driver, secondary_driver
    - layer_contributions (TA, Exchange, MarketState, Ecology, Interaction, Governance)
    - failure_reason, failure_classification, responsible_layer
    - confidence_breakdown, risk_breakdown
    - human-readable explanation
    """
    try:
        engine = get_attribution_engine()
        result = engine.analyze_trade(trade_id)
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
