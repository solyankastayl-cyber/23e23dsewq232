"""
Strategy Regime Engine Routes
=============================

API endpoints for market regime classification.
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .regime_service import regime_service
from .regime_types import MarketRegimeType


router = APIRouter(prefix="/api/strategy-regime", tags=["strategy-regime"])


# ===========================================
# Request/Response Models
# ===========================================

class AnalyzeRequest(BaseModel):
    """Request to analyze regime"""
    symbol: str = Field(..., description="Trading symbol (e.g., BTC, BTCUSDT)")
    timeframe: str = Field("4H", description="Timeframe (1H, 4H, 1D)")


class BatchAnalyzeRequest(BaseModel):
    """Request to analyze multiple symbols"""
    symbols: List[str] = Field(..., description="List of symbols")
    timeframe: str = Field("4H", description="Timeframe")


class UpdateConfigRequest(BaseModel):
    """Request to update configuration"""
    trendingThreshold: Optional[float] = None
    rangeThreshold: Optional[float] = None
    highVolThreshold: Optional[float] = None
    lowVolThreshold: Optional[float] = None
    compressionThreshold: Optional[float] = None


class CompatibilityRequest(BaseModel):
    """Request to check regime compatibility"""
    symbol: str
    timeframe: str = "4H"
    compatibleRegimes: List[str] = Field(default_factory=list)
    hostileRegimes: List[str] = Field(default_factory=list)


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for regime engine"""
    return regime_service.get_health()


# ===========================================
# Configuration (MUST be before /{symbol})
# ===========================================

@router.get("/config")
async def get_config():
    """Get regime engine configuration"""
    return regime_service.get_config()


@router.post("/config")
async def update_config(request: UpdateConfigRequest):
    """Update regime engine configuration"""
    updates = request.dict(exclude_none=True)
    regime_service.update_config(updates)
    return {
        "success": True,
        "updatedFields": list(updates.keys()),
        "currentConfig": regime_service.get_config()
    }


# ===========================================
# Registry & Metadata (MUST be before /{symbol})
# ===========================================

@router.get("/registry")
async def get_registry():
    """Get regime type registry"""
    return {
        "regimeTypes": [
            {
                "id": r.value,
                "name": r.value.replace("_", " ").title(),
                "description": _get_regime_description(r)
            }
            for r in MarketRegimeType
        ],
        "version": "1.0.0"
    }


@router.get("/snapshot")
async def get_snapshot():
    """Get snapshot of all current regime states"""
    return regime_service.get_snapshot()


# ===========================================
# Main Classification Endpoints
# ===========================================

@router.post("/analyze")
async def analyze_regime(request: AnalyzeRequest):
    """
    Analyze and classify market regime for a symbol.
    
    Returns regime classification with confidence metrics.
    """
    state = regime_service.classify_regime(request.symbol, request.timeframe)
    return state.to_dict()


@router.get("/{symbol}")
async def get_regime(
    symbol: str,
    timeframe: str = Query("4H", description="Timeframe")
):
    """
    Get current regime state for symbol.
    
    If no cached state, performs fresh analysis.
    """
    state = regime_service.get_current_state(symbol, timeframe)
    
    if not state:
        # Perform fresh analysis
        state = regime_service.classify_regime(symbol, timeframe)
    
    return state.to_dict()


@router.get("/{symbol}/features")
async def get_features(
    symbol: str,
    timeframe: str = Query("4H", description="Timeframe")
):
    """Get current regime features for symbol"""
    features = regime_service.get_features(symbol, timeframe)
    
    if not features:
        # Compute fresh
        state = regime_service.classify_regime(symbol, timeframe)
        features = state.features
    
    if not features:
        raise HTTPException(status_code=404, detail="No features available")
    
    return features.to_dict()


@router.get("/{symbol}/history")
async def get_history(
    symbol: str,
    timeframe: str = Query("4H", description="Timeframe"),
    limit: int = Query(50, description="Maximum records")
):
    """Get regime state history for symbol"""
    history = regime_service.get_regime_history(symbol, timeframe, limit)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "history": history,
        "count": len(history)
    }


@router.get("/{symbol}/transitions")
async def get_transitions(
    symbol: str,
    timeframe: str = Query("4H", description="Timeframe"),
    limit: int = Query(20, description="Maximum records")
):
    """Get regime transition events for symbol"""
    transitions = regime_service.get_transitions(symbol, timeframe, limit)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "transitions": transitions,
        "count": len(transitions)
    }


# ===========================================
# Multi-Symbol Operations
# ===========================================

@router.post("/batch/analyze")
async def batch_analyze(request: BatchAnalyzeRequest):
    """
    Analyze regimes for multiple symbols.
    
    Returns regime states for all requested symbols.
    """
    results = []
    
    for symbol in request.symbols:
        try:
            state = regime_service.classify_regime(symbol, request.timeframe)
            results.append({
                "symbol": symbol,
                "status": "success",
                "state": state.to_dict()
            })
        except Exception as e:
            results.append({
                "symbol": symbol,
                "status": "error",
                "error": str(e)
            })
    
    return {
        "timeframe": request.timeframe,
        "results": results,
        "successCount": sum(1 for r in results if r["status"] == "success"),
        "errorCount": sum(1 for r in results if r["status"] == "error")
    }


# ===========================================
# Integration Endpoints (for STG2/STG5)
# ===========================================

@router.post("/compatibility")
async def check_compatibility(request: CompatibilityRequest):
    """
    Check if current regime is compatible with strategy.
    
    Used by STG2 Logic Engine for regime-based filtering.
    """
    result = regime_service.is_regime_compatible(
        request.symbol,
        request.compatibleRegimes,
        request.hostileRegimes,
        request.timeframe
    )
    return result


@router.get("/{symbol}/modifiers")
async def get_modifiers(
    symbol: str,
    timeframe: str = Query("4H", description="Timeframe")
):
    """
    Get regime-based modifiers for sizing/risk.
    
    Used by STG5 Selection for regime-aware scoring.
    """
    modifiers = regime_service.get_regime_modifier(symbol, timeframe)
    
    state = regime_service.get_current_state(symbol, timeframe)
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "regime": state.regime.value if state else None,
        "confidence": state.confidence if state else 0,
        "modifiers": modifiers
    }


# ===========================================
# Helper Functions
# ===========================================

def _get_registry_data():
    """Get registry data (internal helper)"""
    return {
        "regimeTypes": [
            {
                "id": r.value,
                "name": r.value.replace("_", " ").title(),
                "description": _get_regime_description(r)
            }
            for r in MarketRegimeType
        ],
        "version": "1.0.0"
    }


def _get_regime_description(regime: MarketRegimeType) -> str:
    """Get description for regime type"""
    descriptions = {
        MarketRegimeType.TRENDING: "Directional market with clear HH/HL or LH/LL structure. Best for trend-following strategies.",
        MarketRegimeType.RANGE: "Sideways consolidation. Mean reversion environment with defined support/resistance.",
        MarketRegimeType.HIGH_VOLATILITY: "Large price swings, breakout environment. Requires wider stops and smaller position sizes.",
        MarketRegimeType.LOW_VOLATILITY: "Compressed range, low ATR. Often precedes significant moves. Watch for breakouts.",
        MarketRegimeType.TRANSITION: "Unclear/dirty market structure. Conflicting signals. Requires caution and reduced exposure."
    }
    return descriptions.get(regime, "")
