"""
PHASE 4.8 — Microstructure Routes

API endpoints for Microstructure Entry Layer.
"""

from fastapi import APIRouter, Query
from typing import Optional, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel

from .microstructure_decision_engine import get_microstructure_engine, MOCK_SCENARIOS


router = APIRouter(prefix="/api/entry-timing/microstructure", tags=["microstructure-entry"])


# === Request Models ===

class OrderbookInput(BaseModel):
    bid_depth: float = 0
    ask_depth: float = 0
    best_bid: float = 0
    best_ask: float = 0
    spread_bps: float = 3.0


class LiquidityInput(BaseModel):
    above_liquidity: float = 0.5
    below_liquidity: float = 0.5
    local_cluster_nearby: bool = False
    cluster_distance_bps: float = 30.0


class FlowInput(BaseModel):
    buy_pressure: float = 0.5
    sell_pressure: float = 0.5
    recent_sweep_up: bool = False
    recent_sweep_down: bool = False


class ExecutionContextInput(BaseModel):
    entry_type: str = "pullback"
    expected_slippage_bps: float = 5.0
    volatility_state: str = "normal"


class MicrostructureEvalInput(BaseModel):
    symbol: str = "BTCUSDT"
    side: str = "LONG"
    price: float = 0
    orderbook: OrderbookInput
    liquidity: LiquidityInput
    flow: FlowInput
    execution_context: ExecutionContextInput


# === Endpoints ===

@router.get("/health")
async def microstructure_health():
    """Health check for Microstructure layer."""
    engine = get_microstructure_engine()
    return engine.health_check()


@router.post("/evaluate")
async def evaluate_microstructure(data: MicrostructureEvalInput):
    """
    Full microstructure evaluation.

    Combines liquidity, orderbook, imbalance, absorption, and sweep
    into a single entry permission decision.
    """
    engine = get_microstructure_engine()
    input_dict = data.dict()
    result = engine.evaluate(input_dict)

    return {"ok": True, **result}


@router.post("/evaluate/mock/{scenario}")
async def evaluate_mock(scenario: str):
    """
    Run microstructure evaluation with mock data.

    Scenarios: supportive, hostile_spread, sweep_risk, liquidity_cluster
    """
    engine = get_microstructure_engine()
    result = engine.evaluate_mock(scenario)

    if "error" in result:
        return {"ok": False, **result}

    return {"ok": True, "scenario": scenario, **result}


@router.get("/scenarios")
async def list_scenarios():
    """List available mock scenarios."""
    return {
        "ok": True,
        "scenarios": [
            {"name": "supportive", "description": "All microstructure conditions supportive for LONG entry"},
            {"name": "hostile_spread", "description": "Wide spread, selling pressure, hostile orderbook"},
            {"name": "sweep_risk", "description": "High downside liquidity, sweep not yet completed"},
            {"name": "liquidity_cluster", "description": "Liquidity cluster very close to entry point"},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/simulate/all")
async def simulate_all():
    """Run all mock scenarios."""
    engine = get_microstructure_engine()

    results = {}
    for scenario in MOCK_SCENARIOS:
        results[scenario] = engine.evaluate_mock(scenario)

    return {
        "ok": True,
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/stats")
async def get_stats():
    """Get microstructure decision statistics."""
    engine = get_microstructure_engine()
    stats = engine.get_stats()

    return {"ok": True, **stats, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=200)):
    """Get recent microstructure decision history."""
    engine = get_microstructure_engine()
    history = engine.get_history(limit)

    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
