"""
Strategy Regime Mapping — Routes

API endpoints for strategy-regime mapping.

Endpoints:
- GET /api/v1/regime/strategies
- GET /api/v1/regime/strategies/{strategy}
- GET /api/v1/regime/strategies/summary
- POST /api/v1/regime/strategies/recompute
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from datetime import datetime, timezone

from .strategy_regime_mapping_engine import (
    StrategyRegimeMappingEngine,
    get_strategy_regime_mapping_engine,
)
from .strategy_regime_registry import (
    StrategyRegimeRegistry,
    get_strategy_regime_registry,
)
from .strategy_regime_types import STRATEGY_LIST
from .regime_detection_engine import get_regime_detection_engine


router = APIRouter(prefix="/api/v1/regime/strategies", tags=["strategy-regime"])


@router.get("", response_model=Dict[str, Any])
async def get_all_strategy_mappings(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Get strategy mappings for all strategies in current regime.
    
    Returns list of mappings with suitability scores and states.
    """
    engine = get_strategy_regime_mapping_engine()
    registry = get_strategy_regime_registry()
    
    # Compute mappings
    mappings = await engine.compute_mappings(symbol, timeframe)
    
    # Store in history
    await registry.store_mappings_bulk(mappings)
    
    # Get summary
    regime = engine.current_regime
    summary = engine.get_summary(regime)
    
    return {
        "regime_type": regime.regime_type,
        "regime_confidence": regime.regime_confidence,
        "mappings": [
            {
                "strategy": m.strategy,
                "suitability": m.suitability,
                "state": m.state,
                "confidence_modifier": m.confidence_modifier,
                "capital_modifier": m.capital_modifier,
                "reason": m.reason,
            }
            for m in mappings
        ],
        "summary": {
            "favored": summary.favored_strategies,
            "neutral": summary.neutral_strategies,
            "disfavored": summary.disfavored_strategies,
        },
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/summary", response_model=Dict[str, Any])
async def get_strategy_summary(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Get summary of strategy suitability for current regime.
    
    Groups strategies by FAVORED, NEUTRAL, DISFAVORED.
    """
    engine = get_strategy_regime_mapping_engine()
    regime_engine = get_regime_detection_engine()
    
    # Get current regime
    regime = regime_engine.detect_regime_simulated(symbol, timeframe)
    
    # Get summary
    summary = engine.get_summary(regime)
    
    return {
        "regime_type": summary.regime_type,
        "regime_confidence": summary.regime_confidence,
        "favored_strategies": summary.favored_strategies,
        "neutral_strategies": summary.neutral_strategies,
        "disfavored_strategies": summary.disfavored_strategies,
        "total_strategies": summary.total_strategies,
        "symbol": symbol,
        "timeframe": timeframe,
    }


@router.get("/{strategy}", response_model=Dict[str, Any])
async def get_single_strategy_mapping(
    strategy: str,
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Get mapping for a specific strategy.
    """
    if strategy not in STRATEGY_LIST:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy}' not found. Valid strategies: {STRATEGY_LIST}"
        )
    
    engine = get_strategy_regime_mapping_engine()
    regime_engine = get_regime_detection_engine()
    
    # Get current regime
    regime = regime_engine.detect_regime_simulated(symbol, timeframe)
    
    # Map single strategy
    mapping = engine.map_strategy(strategy, regime)
    
    return {
        "strategy": mapping.strategy,
        "regime_type": mapping.regime_type,
        "suitability": mapping.suitability,
        "confidence_modifier": mapping.confidence_modifier,
        "capital_modifier": mapping.capital_modifier,
        "state": mapping.state,
        "reason": mapping.reason,
        "regime_confidence": mapping.regime_confidence,
        "computed_at": mapping.computed_at.isoformat(),
    }


@router.post("/recompute", response_model=Dict[str, Any])
async def recompute_strategy_mappings(
    symbol: str = Query("BTCUSDT", description="Trading pair symbol"),
    timeframe: str = Query("1H", description="Timeframe"),
):
    """
    Force recompute of all strategy mappings.
    
    Stores results in history.
    """
    try:
        engine = get_strategy_regime_mapping_engine()
        registry = get_strategy_regime_registry()
        
        # Recompute
        mappings = await engine.compute_mappings(symbol, timeframe)
        
        # Store in history
        await registry.store_mappings_bulk(mappings)
        
        # Get regime and summary
        regime = engine.current_regime
        summary = engine.get_summary(regime)
        
        return {
            "status": "ok",
            "recomputed": len(mappings),
            "regime_type": regime.regime_type,
            "regime_confidence": regime.regime_confidence,
            "summary": {
                "favored": summary.favored_strategies,
                "neutral": summary.neutral_strategies,
                "disfavored": summary.disfavored_strategies,
            },
            "symbol": symbol,
            "timeframe": timeframe,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recompute failed: {str(e)}"
        )


@router.get("/history/{strategy}", response_model=Dict[str, Any])
async def get_strategy_mapping_history(
    strategy: str,
    limit: int = Query(50, ge=1, le=500, description="Max records"),
):
    """
    Get mapping history for a specific strategy.
    """
    if strategy not in STRATEGY_LIST:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy}' not found"
        )
    
    registry = get_strategy_regime_registry()
    history = await registry.get_strategy_history(strategy, limit)
    
    return {
        "strategy": strategy,
        "history": [
            {
                "regime_type": h.regime_type,
                "suitability": h.suitability,
                "state": h.state,
                "confidence_modifier": h.confidence_modifier,
                "capital_modifier": h.capital_modifier,
                "timestamp": h.timestamp.isoformat(),
            }
            for h in history
        ],
        "count": len(history),
    }
