"""
Market Simulation API Routes

PHASE 32.3 — API endpoints for Market Simulation Engine.

Endpoints:
- GET  /api/v1/simulation/health              - Health check
- GET  /api/v1/simulation/{symbol}            - Get current simulation
- GET  /api/v1/simulation/top/{symbol}        - Get top scenarios
- GET  /api/v1/simulation/history/{symbol}    - Get simulation history
- POST /api/v1/simulation/recompute/{symbol}  - Force recomputation
- GET  /api/v1/simulation/modifier/{symbol}   - Get allocation modifier
- GET  /api/v1/simulation/summary/{symbol}    - Get simulation summary
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException

from .simulation_engine import get_simulation_engine
from .simulation_registry import get_simulation_registry
from .simulation_types import (
    SimulationResult,
    MarketScenario,
    ScenarioModifier,
    SimulationSummary,
    SIMULATION_HORIZONS,
)


router = APIRouter(
    prefix="/api/v1/simulation",
    tags=["Market Simulation Engine"],
)


# ══════════════════════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def simulation_health() -> dict:
    """Health check for simulation engine."""
    return {
        "status": "ok",
        "module": "market_simulation",
        "phase": "32.3",
        "version": "1.0.0",
        "horizons": SIMULATION_HORIZONS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/simulation/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/{symbol}")
async def get_simulation(
    symbol: str,
    horizon: int = Query(default=60, description="Horizon in minutes"),
) -> dict:
    """
    Get current market simulation for symbol.
    
    Returns scenarios with probabilities, directions, and expected moves.
    """
    engine = get_simulation_engine()
    
    result = engine.get_current_simulation(symbol)
    
    if result is None or result.horizon_minutes != horizon:
        result = engine.simulate(symbol, horizon)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "horizon_minutes": result.horizon_minutes,
        "dominant_direction": result.dominant_direction,
        "direction_confidence": result.direction_confidence,
        "expected_volatility": result.expected_volatility,
        "scenarios_count": result.scenarios_generated,
        "top_scenario": {
            "type": result.top_scenario.scenario_type,
            "probability": result.top_scenario.probability,
            "direction": result.top_scenario.expected_direction,
            "expected_move": result.top_scenario.expected_move_percent,
            "confidence": result.top_scenario.confidence,
            "reasoning": result.top_scenario.reasoning,
        } if result.top_scenario else None,
        "all_scenarios": [
            {
                "scenario_id": s.scenario_id,
                "type": s.scenario_type,
                "probability": s.probability,
                "direction": s.expected_direction,
                "expected_move": s.expected_move_percent,
                "confidence": s.confidence,
                "scores": {
                    "hypothesis": s.hypothesis_score,
                    "regime": s.regime_score,
                    "microstructure": s.microstructure_score,
                    "fractal_similarity": s.fractal_similarity_score,
                    "meta_alpha": s.meta_alpha_score,
                },
            }
            for s in result.scenarios
        ],
        "created_at": result.created_at.isoformat(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/simulation/top/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/top/{symbol}")
async def get_top_scenarios(
    symbol: str,
    limit: int = Query(default=3, ge=1, le=5),
) -> dict:
    """
    Get top scenarios from current simulation.
    """
    engine = get_simulation_engine()
    
    scenarios = engine.get_top_scenarios(symbol, limit)
    
    if not scenarios:
        result = engine.simulate(symbol)
        scenarios = result.scenarios[:limit]
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "count": len(scenarios),
        "scenarios": [
            {
                "scenario_id": s.scenario_id,
                "type": s.scenario_type,
                "probability": s.probability,
                "direction": s.expected_direction,
                "expected_move_percent": s.expected_move_percent,
                "confidence": s.confidence,
                "horizon_minutes": s.horizon_minutes,
                "reasoning": s.reasoning,
            }
            for s in scenarios
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/simulation/history/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/history/{symbol}")
async def get_simulation_history(
    symbol: str,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """
    Get simulation history for symbol.
    """
    engine = get_simulation_engine()
    
    history = engine.get_history(symbol, limit)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "count": len(history),
        "history": [
            {
                "top_scenario": r.top_scenario.scenario_type if r.top_scenario else "UNKNOWN",
                "top_probability": r.top_scenario.probability if r.top_scenario else 0.0,
                "dominant_direction": r.dominant_direction,
                "direction_confidence": r.direction_confidence,
                "expected_volatility": r.expected_volatility,
                "horizon_minutes": r.horizon_minutes,
                "created_at": r.created_at.isoformat(),
            }
            for r in history
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# POST /api/v1/simulation/recompute/{symbol}
# ══════════════════════════════════════════════════════════════

@router.post("/recompute/{symbol}")
async def recompute_simulation(
    symbol: str,
    horizon: int = Query(default=60, description="Horizon in minutes"),
) -> dict:
    """
    Force recomputation of simulation.
    """
    engine = get_simulation_engine()
    
    result = engine.simulate(symbol, horizon)
    
    # Save to database
    try:
        registry = get_simulation_registry()
        registry.save_result(result)
    except Exception:
        pass
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "horizon_minutes": result.horizon_minutes,
        "dominant_direction": result.dominant_direction,
        "direction_confidence": result.direction_confidence,
        "expected_volatility": result.expected_volatility,
        "top_scenario": {
            "type": result.top_scenario.scenario_type,
            "probability": result.top_scenario.probability,
            "direction": result.top_scenario.expected_direction,
            "expected_move": result.top_scenario.expected_move_percent,
        } if result.top_scenario else None,
        "recomputed_at": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/simulation/modifier/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/modifier/{symbol}")
async def get_allocation_modifier(
    symbol: str,
) -> dict:
    """
    Get allocation modifier based on scenario analysis.
    
    Returns modifier value for capital allocation:
    - >1.0: Increase allocation (favorable scenarios)
    - <1.0: Decrease allocation (risky scenarios)
    - 1.0: No change
    """
    engine = get_simulation_engine()
    
    modifier = engine.get_allocation_modifier(symbol)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "modifier": {
            "allocation_modifier": modifier.allocation_modifier,
            "top_scenario_type": modifier.top_scenario_type,
            "top_scenario_probability": modifier.top_scenario_probability,
            "risk_level": modifier.risk_level,
            "liquidation_risk": modifier.liquidation_risk,
            "reason": modifier.reason,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/simulation/summary/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/summary/{symbol}")
async def get_simulation_summary(
    symbol: str,
) -> dict:
    """
    Get simulation summary for symbol.
    """
    engine = get_simulation_engine()
    
    # Ensure simulation exists
    if not engine.get_current_simulation(symbol):
        engine.simulate(symbol)
    
    summary = engine.get_summary(symbol)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "summary": {
            "current_top_scenario": summary.current_top_scenario,
            "current_probability": summary.current_probability,
            "current_direction": summary.current_direction,
            "total_simulations": summary.total_simulations,
            "avg_top_probability": summary.avg_top_probability,
            "scenario_distribution": summary.scenario_distribution,
            "last_updated": summary.last_updated.isoformat() if summary.last_updated else None,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/simulation/multi-horizon/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/multi-horizon/{symbol}")
async def get_multi_horizon_simulation(
    symbol: str,
) -> dict:
    """
    Get simulations for all standard horizons (15m, 60m, 240m).
    """
    engine = get_simulation_engine()
    
    results = {}
    for horizon in SIMULATION_HORIZONS:
        result = engine.simulate(symbol, horizon)
        results[f"{horizon}m"] = {
            "top_scenario": result.top_scenario.scenario_type if result.top_scenario else "UNKNOWN",
            "probability": result.top_scenario.probability if result.top_scenario else 0.0,
            "direction": result.dominant_direction,
            "expected_move": result.top_scenario.expected_move_percent if result.top_scenario else 0.0,
            "expected_volatility": result.expected_volatility,
        }
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "horizons": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
