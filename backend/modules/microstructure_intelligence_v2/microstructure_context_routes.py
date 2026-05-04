"""
Microstructure Context Integration — Routes

PHASE 28.5 — API endpoints for unified microstructure context.

Endpoints:
- GET /api/v1/microstructure/context/{symbol}
- GET /api/v1/microstructure/context/summary/{symbol}
- GET /api/v1/microstructure/context/drivers/{symbol}
- POST /api/v1/microstructure/context/recompute/{symbol}
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone

from .microstructure_context_engine import (
    MicrostructureContextEngine,
    get_microstructure_context_engine,
)


router = APIRouter(prefix="/api/v1/microstructure/context", tags=["microstructure-context"])


@router.get("/{symbol}", response_model=Dict[str, Any])
async def get_microstructure_context(symbol: str):
    """
    Get unified microstructure context for symbol.
    
    Aggregates all 4 microstructure layers into execution-critical context.
    """
    engine = get_microstructure_context_engine()
    
    # Build context
    context = engine.build_context_simulated(symbol.upper())
    
    return {
        "symbol": context.symbol,
        "liquidity_state": context.liquidity_state,
        "pressure_bias": context.pressure_bias,
        "vacuum_direction": context.vacuum_direction,
        "cascade_direction": context.cascade_direction,
        "vacuum_probability": context.vacuum_probability,
        "sweep_probability": context.sweep_probability,
        "cascade_probability": context.cascade_probability,
        "microstructure_state": context.microstructure_state,
        "confidence_modifier": context.confidence_modifier,
        "capital_modifier": context.capital_modifier,
        "dominant_driver": context.dominant_driver,
        "reason": context.reason,
        "computed_at": context.computed_at.isoformat(),
    }


@router.get("/summary/{symbol}", response_model=Dict[str, Any])
async def get_context_summary(symbol: str):
    """
    Get microstructure context summary statistics for symbol.
    """
    engine = get_microstructure_context_engine()
    
    # Build first if not exists
    if not engine.get_context(symbol.upper()):
        engine.build_context_simulated(symbol.upper())
    
    summary = engine.get_summary(symbol.upper())
    
    return {
        "symbol": summary.symbol,
        "states": {
            "supportive": summary.supportive_count,
            "neutral": summary.neutral_count,
            "fragile": summary.fragile_count,
            "stressed": summary.stressed_count,
        },
        "drivers": {
            "liquidity": summary.liquidity_dominant_count,
            "pressure": summary.pressure_dominant_count,
            "vacuum": summary.vacuum_dominant_count,
            "cascade": summary.cascade_dominant_count,
            "mixed": summary.mixed_dominant_count,
        },
        "averages": {
            "confidence_modifier": summary.average_confidence_modifier,
            "capital_modifier": summary.average_capital_modifier,
            "vacuum_probability": summary.average_vacuum_probability,
            "cascade_probability": summary.average_cascade_probability,
        },
        "current": {
            "state": summary.current_state,
            "driver": summary.current_driver,
        },
    }


@router.get("/drivers/{symbol}", response_model=Dict[str, Any])
async def get_context_drivers(symbol: str):
    """
    Get microstructure drivers breakdown for symbol.
    
    Shows impact of each driver on microstructure state.
    """
    engine = get_microstructure_context_engine()
    
    # Build first if not exists
    if not engine.get_context(symbol.upper()):
        engine.build_context_simulated(symbol.upper())
    
    drivers = engine.get_drivers(symbol.upper())
    
    if not drivers:
        raise HTTPException(status_code=404, detail=f"Drivers not found for {symbol}")
    
    return {
        "symbol": drivers.symbol,
        "impacts": {
            "liquidity": drivers.liquidity_impact,
            "pressure": drivers.pressure_impact,
            "vacuum": drivers.vacuum_impact,
            "cascade": drivers.cascade_impact,
        },
        "dominant": drivers.dominant,
        "direction_consistency": drivers.direction_consistency,
        "consistency_score": drivers.consistency_score,
    }


@router.post("/recompute/{symbol}", response_model=Dict[str, Any])
async def recompute_context(symbol: str):
    """
    Force recompute of microstructure context.
    
    Rebuilds context from all 4 layers.
    """
    try:
        engine = get_microstructure_context_engine()
        
        # Recompute
        context = engine.build_context_simulated(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": context.symbol,
            "liquidity_state": context.liquidity_state,
            "pressure_bias": context.pressure_bias,
            "vacuum_direction": context.vacuum_direction,
            "cascade_direction": context.cascade_direction,
            "vacuum_probability": context.vacuum_probability,
            "sweep_probability": context.sweep_probability,
            "cascade_probability": context.cascade_probability,
            "microstructure_state": context.microstructure_state,
            "confidence_modifier": context.confidence_modifier,
            "capital_modifier": context.capital_modifier,
            "dominant_driver": context.dominant_driver,
            "reason": context.reason,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recompute failed: {str(e)}"
        )
