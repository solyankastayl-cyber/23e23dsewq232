"""
Capital Flow Routes

PHASE 42 — Capital Flow Engine
PHASE 42.4 — Capital Flow Integration

Endpoints:
- GET  /api/v1/capital-flow/snapshot    - Get current flow snapshot
- GET  /api/v1/capital-flow/rotation    - Get current rotation state
- GET  /api/v1/capital-flow/score       - Get current flow score
- POST /api/v1/capital-flow/recompute   - Recompute with custom data
- GET  /api/v1/capital-flow/history     - Get historical data
- GET  /api/v1/capital-flow/config      - Get configuration
- GET  /api/v1/capital-flow/health      - Health check
- GET  /api/v1/capital-flow/summary     - Full integration summary (PHASE 42.4)
- GET  /api/v1/capital-flow/hypothesis-modifier  - Hypothesis modifier (PHASE 42.4)
- GET  /api/v1/capital-flow/portfolio-adjustment - Portfolio adjustment (PHASE 42.4)
- GET  /api/v1/capital-flow/scenario-modifier    - Scenario ranking modifier (PHASE 42.4)
"""

from typing import Optional, Dict
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .flow_snapshot_engine import FlowSnapshotEngine
from .flow_rotation_engine import RotationDetectionEngine
from .flow_scoring_engine import FlowScoringEngine
from .flow_registry import get_flow_registry
from .flow_types import CapitalFlowConfig


router = APIRouter(prefix="/api/v1/capital-flow", tags=["Capital Flow Engine"])


# Shared engine instances
_config = CapitalFlowConfig()
_snapshot_engine = FlowSnapshotEngine(_config)
_rotation_engine = RotationDetectionEngine(_config)
_scoring_engine = FlowScoringEngine(_config)


# ══════════════════════════════════════════════════════════════
# Request Models
# ══════════════════════════════════════════════════════════════

class RecomputeRequest(BaseModel):
    """Custom market data for recompute."""
    btc_return: float = 0.0
    eth_return: float = 0.0
    alt_return: float = 0.0
    btc_oi_delta: float = 0.0
    eth_oi_delta: float = 0.0
    alt_oi_delta: float = 0.0
    btc_funding: float = 0.0
    eth_funding: float = 0.0
    alt_funding: float = 0.0
    btc_volume_delta: float = 0.0
    eth_volume_delta: float = 0.0
    alt_volume_delta: float = 0.0
    btc_dominance: float = 0.50
    eth_dominance: float = 0.18
    prev_btc_dominance: float = 0.50
    prev_eth_dominance: float = 0.18
    persist: bool = True


# ══════════════════════════════════════════════════════════════
# Snapshot
# ══════════════════════════════════════════════════════════════

@router.get("/snapshot")
async def get_snapshot():
    """Get current capital flow snapshot."""
    try:
        snapshot = _snapshot_engine.build_snapshot()
        registry = get_flow_registry()
        registry.save_snapshot(snapshot)

        return {
            "status": "ok",
            "phase": "42",
            "snapshot": {
                "snapshot_id": snapshot.snapshot_id,
                "btc_flow_score": snapshot.btc_flow_score,
                "eth_flow_score": snapshot.eth_flow_score,
                "alt_flow_score": snapshot.alt_flow_score,
                "cash_flow_score": snapshot.cash_flow_score,
                "btc_dominance_shift": snapshot.btc_dominance_shift,
                "eth_dominance_shift": snapshot.eth_dominance_shift,
                "oi_shift": snapshot.oi_shift,
                "funding_shift": snapshot.funding_shift,
                "volume_shift": snapshot.volume_shift,
                "flow_state": snapshot.flow_state.value,
                "timestamp": snapshot.timestamp.isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Rotation
# ══════════════════════════════════════════════════════════════

@router.get("/rotation")
async def get_rotation():
    """Get current capital rotation state."""
    try:
        snapshot = _snapshot_engine.build_snapshot()
        rotation = _rotation_engine.detect_rotation(snapshot)
        registry = get_flow_registry()
        registry.save_rotation(rotation)

        return {
            "status": "ok",
            "phase": "42",
            "rotation": {
                "rotation_id": rotation.rotation_id,
                "rotation_type": rotation.rotation_type.value,
                "from_bucket": rotation.from_bucket.value,
                "to_bucket": rotation.to_bucket.value,
                "rotation_strength": rotation.rotation_strength,
                "confidence": rotation.confidence,
                "timestamp": rotation.timestamp.isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Score
# ══════════════════════════════════════════════════════════════

@router.get("/score")
async def get_score():
    """Get current flow score."""
    try:
        snapshot = _snapshot_engine.build_snapshot()
        rotation = _rotation_engine.detect_rotation(snapshot)
        score = _scoring_engine.compute_score(snapshot, rotation)
        registry = get_flow_registry()
        registry.save_score(score)

        return {
            "status": "ok",
            "phase": "42",
            "score": {
                "score_id": score.score_id,
                "flow_bias": score.flow_bias.value,
                "flow_strength": score.flow_strength,
                "flow_confidence": score.flow_confidence,
                "dominant_rotation": score.dominant_rotation.value,
                "timestamp": score.timestamp.isoformat(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Recompute with Custom Data
# ══════════════════════════════════════════════════════════════

@router.post("/recompute")
async def recompute(request: RecomputeRequest):
    """Recompute capital flow with custom market data."""
    try:
        market_data = request.model_dump(exclude={"persist"})

        snapshot = _snapshot_engine.build_snapshot(market_data)
        rotation = _rotation_engine.detect_rotation(snapshot)
        score = _scoring_engine.compute_score(snapshot, rotation)

        if request.persist:
            registry = get_flow_registry()
            registry.save_snapshot(snapshot)
            registry.save_rotation(rotation)
            registry.save_score(score)

        return {
            "status": "ok",
            "phase": "42",
            "snapshot": {
                "btc_flow_score": snapshot.btc_flow_score,
                "eth_flow_score": snapshot.eth_flow_score,
                "alt_flow_score": snapshot.alt_flow_score,
                "cash_flow_score": snapshot.cash_flow_score,
                "btc_dominance_shift": snapshot.btc_dominance_shift,
                "eth_dominance_shift": snapshot.eth_dominance_shift,
                "oi_shift": snapshot.oi_shift,
                "funding_shift": snapshot.funding_shift,
                "volume_shift": snapshot.volume_shift,
                "flow_state": snapshot.flow_state.value,
            },
            "rotation": {
                "rotation_type": rotation.rotation_type.value,
                "from_bucket": rotation.from_bucket.value,
                "to_bucket": rotation.to_bucket.value,
                "rotation_strength": rotation.rotation_strength,
                "confidence": rotation.confidence,
            },
            "score": {
                "flow_bias": score.flow_bias.value,
                "flow_strength": score.flow_strength,
                "flow_confidence": score.flow_confidence,
                "dominant_rotation": score.dominant_rotation.value,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# History
# ══════════════════════════════════════════════════════════════

@router.get("/history")
async def get_history(
    data_type: str = Query(default="scores", description="snapshots, rotations, or scores"),
    limit: int = Query(default=50, ge=1, le=500),
):
    """Get historical capital flow data."""
    try:
        registry = get_flow_registry()

        if data_type == "snapshots":
            data = registry.get_latest_snapshots(limit)
        elif data_type == "rotations":
            data = registry.get_latest_rotations(limit)
        else:
            data = registry.get_latest_scores(limit)

        return {
            "status": "ok",
            "phase": "42",
            "data_type": data_type,
            "count": len(data),
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Config & Health
# ══════════════════════════════════════════════════════════════

@router.get("/config")
async def get_config():
    """Get capital flow configuration."""
    return {"status": "ok", "phase": "42", "config": _config.model_dump()}


@router.get("/health")
async def capital_flow_health():
    """Capital flow health check."""
    try:
        snapshot = _snapshot_engine.build_snapshot()
        rotation = _rotation_engine.detect_rotation(snapshot)
        score = _scoring_engine.compute_score(snapshot, rotation)

        return {
            "status": "ok",
            "phase": "42.4",
            "module": "Capital Flow Engine",
            "current_state": {
                "flow_state": snapshot.flow_state.value,
                "rotation_type": rotation.rotation_type.value,
                "flow_bias": score.flow_bias.value,
            },
            "buckets": ["BTC", "ETH", "ALTS", "CASH"],
            "endpoints": [
                "GET  /api/v1/capital-flow/snapshot",
                "GET  /api/v1/capital-flow/rotation",
                "GET  /api/v1/capital-flow/score",
                "POST /api/v1/capital-flow/recompute",
                "GET  /api/v1/capital-flow/history",
                "GET  /api/v1/capital-flow/config",
                "GET  /api/v1/capital-flow/summary",
                "GET  /api/v1/capital-flow/hypothesis-modifier",
                "GET  /api/v1/capital-flow/portfolio-adjustment",
                "GET  /api/v1/capital-flow/scenario-modifier",
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# PHASE 42.4 — Integration Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/summary")
async def get_integration_summary():
    """
    Get full capital flow integration summary.
    
    PHASE 42.4: Shows integration with Hypothesis/Portfolio/Simulation.
    """
    try:
        from .flow_integration import get_capital_flow_integration
        
        engine = get_capital_flow_integration()
        summary = engine.get_integration_summary()
        
        return {
            "status": "ok",
            **summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hypothesis-modifier")
async def get_hypothesis_modifier(
    symbol: str = Query(default="BTCUSDT", description="Symbol to analyze"),
    direction: str = Query(default="LONG", description="LONG or SHORT"),
):
    """
    Get capital flow modifier for hypothesis engine.
    
    PHASE 42.4: Integration with Hypothesis Engine.
    
    Returns modifier based on flow_bias alignment:
    - aligned: 1.08
    - conflict: 0.92
    - neutral: 1.0
    """
    try:
        from .flow_integration import get_capital_flow_integration
        
        engine = get_capital_flow_integration()
        result = engine.get_hypothesis_modifier(symbol, direction)
        
        return {
            "status": "ok",
            "phase": "42.4",
            "integration": "hypothesis_engine",
            **result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio-adjustment")
async def get_portfolio_adjustment(
    symbol: str = Query(default="BTCUSDT", description="Symbol"),
    direction: str = Query(default="LONG", description="LONG or SHORT"),
    base_weight: float = Query(default=0.10, description="Base portfolio weight"),
):
    """
    Get capital flow adjustment for portfolio weight.
    
    PHASE 42.4: Integration with Portfolio Manager.
    
    Returns adjusted weight based on flow_bias:
    - aligned: weight × 1.05
    - conflict: weight × 0.95
    """
    try:
        from .flow_integration import get_capital_flow_integration
        
        engine = get_capital_flow_integration()
        result = engine.get_portfolio_weight_adjustment(symbol, direction, base_weight)
        
        return {
            "status": "ok",
            "phase": "42.4",
            "integration": "portfolio_manager",
            **result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio-rotation-signals")
async def get_portfolio_rotation_signals():
    """
    Get portfolio rotation signals from capital flow.
    
    PHASE 42.4: Integration with Portfolio Manager.
    """
    try:
        from .flow_integration import get_capital_flow_integration
        
        engine = get_capital_flow_integration()
        signals = engine.get_portfolio_rotation_signals()
        
        return {
            "status": "ok",
            "phase": "42.4",
            "integration": "portfolio_manager",
            **signals,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scenario-modifier")
async def get_scenario_modifier(
    scenario_type: str = Query(default="FLASH_CRASH", description="Scenario type"),
):
    """
    Get capital flow modifier for simulation scenario ranking.
    
    PHASE 42.4: Integration with Simulation Engine.
    
    Returns ranking modifier based on flow alignment:
    - aligned: 1.06
    - conflict: 0.94
    """
    try:
        from .flow_integration import get_capital_flow_integration
        
        engine = get_capital_flow_integration()
        result = engine.get_scenario_ranking_modifier(scenario_type)
        
        return {
            "status": "ok",
            "phase": "42.4",
            "integration": "simulation_engine",
            **result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
