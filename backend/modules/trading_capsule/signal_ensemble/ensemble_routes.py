"""
Signal Ensemble API Routes
==========================

REST API endpoints для Signal Ensemble Engine.

Endpoints:
- POST /api/signal-ensemble/evaluate - evaluate ensemble signal
- GET /api/signal-ensemble/symbol/{symbol} - get ensemble for symbol
- GET /api/signal-ensemble/history - signal history
- GET /api/signal-ensemble/stats - engine statistics
- GET /api/signal-ensemble/weights - current weights
"""

import uuid
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .ensemble_types import (
    SignalDirection,
    SignalQuality,
    EnsembleSignal,
    EnsembleResult,
    EnsembleSnapshot,
    EnsembleHistoryQuery
)
from .ensemble_weights import EnsembleWeights, get_default_weights, get_weights_preset, WEIGHT_PRESETS
from .signal_scorer import SignalScorer
from .ensemble_repository import EnsembleRepository

# Import Alpha Engine for integration
try:
    from ..alpha_engine import AlphaSignalBuilder, get_alpha_registry
    ALPHA_ENGINE_AVAILABLE = True
except ImportError:
    ALPHA_ENGINE_AVAILABLE = False
    print("[SignalEnsemble] Alpha Engine not available - using mock data")


router = APIRouter(prefix="/api/signal-ensemble", tags=["Signal Ensemble"])

# Initialize components
scorer = SignalScorer()
repository = EnsembleRepository()


# ============================================
# Request/Response Models
# ============================================

class EnsembleEvaluateRequest(BaseModel):
    """Запрос на evaluate ensemble"""
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(default="1h", description="Timeframe")
    alpha_results: List[Dict[str, Any]] = Field(default_factory=list, description="Alpha results from Alpha Engine")
    regime: str = Field(default="UNKNOWN", description="Current market regime")
    market_context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    weights_preset: str = Field(default="default", description="Weights preset to use")
    current_price: float = Field(default=0.0, description="Current market price")


class EnsembleResponse(BaseModel):
    """Ответ с ensemble результатом"""
    symbol: str
    timeframe: str
    direction: str
    strength: float
    confidence: float
    quality: str
    long_score: float
    short_score: float
    action_score: float
    has_conflict: bool
    conflict_severity: float
    recommendation: str
    notes: List[str]
    warnings: List[str]
    computed_at: str


# ============================================
# Mock Data for Testing
# ============================================

def generate_mock_alpha_results(symbol: str = "BTCUSDT") -> List[Dict[str, Any]]:
    """Generate mock alpha results for testing"""
    alphas = [
        ("trend_strength_alpha", "Trend Strength"),
        ("trend_acceleration_alpha", "Trend Acceleration"),
        ("trend_exhaustion_alpha", "Trend Exhaustion"),
        ("breakout_pressure_alpha", "Breakout Pressure"),
        ("volatility_compression_alpha", "Volatility Compression"),
        ("volatility_expansion_alpha", "Volatility Expansion"),
        ("reversal_pressure_alpha", "Reversal Pressure"),
        ("volume_confirmation_alpha", "Volume Confirmation"),
        ("volume_anomaly_alpha", "Volume Anomaly"),
        ("liquidity_sweep_alpha", "Liquidity Sweep")
    ]
    
    results = []
    for alpha_id, alpha_name in alphas:
        direction = random.choice(["LONG", "SHORT", "NEUTRAL"])
        strength = random.uniform(0.2, 0.9)
        confidence = random.uniform(0.3, 0.85)
        
        results.append({
            "alpha_id": alpha_id,
            "alpha_name": alpha_name,
            "direction": direction,
            "strength": round(strength, 4),
            "confidence": round(confidence, 4),
            "regime_relevance": random.choice(["TRENDING", "RANGING", "ALL"])
        })
    
    return results


# ============================================
# API Endpoints
# ============================================

@router.get("/health")
async def ensemble_health():
    """Health check для Signal Ensemble Engine"""
    return {
        "status": "healthy",
        "version": "phase_3.5.2",
        "alpha_engine_available": ALPHA_ENGINE_AVAILABLE,
        "presets_available": list(WEIGHT_PRESETS.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stats")
async def ensemble_stats():
    """Статистика Signal Ensemble Engine"""
    repo_stats = repository.get_stats()
    
    return {
        "engine_version": "phase_3.5.2",
        "alpha_engine_available": ALPHA_ENGINE_AVAILABLE,
        "presets": list(WEIGHT_PRESETS.keys()),
        "repository": repo_stats
    }


@router.get("/weights")
async def get_weights(preset: str = Query(default="default")):
    """Получение текущих весов"""
    weights = get_weights_preset(preset)
    
    return {
        "preset": preset,
        "weights": weights.get_all_weights(),
        "available_presets": list(WEIGHT_PRESETS.keys())
    }


class WeightsPreviewRequest(BaseModel):
    """Запрос на preview весов"""
    preset: str = Field(default="default", description="Weight preset")
    regime: str = Field(default="UNKNOWN", description="Market regime")

@router.post("/weights/preview")
async def preview_weights_adjustment(request: WeightsPreviewRequest):
    """Preview весов после корректировки под режим"""
    base_weights = get_weights_preset(request.preset)
    adjusted = base_weights.adjust_for_regime(request.regime)
    
    return {
        "preset": request.preset,
        "regime": request.regime,
        "base_weights": base_weights.get_all_weights(),
        "adjusted_weights": adjusted.get_all_weights(),
        "changes": {
            k: round(adjusted.get_weight(k) - base_weights.get_weight(k), 4)
            for k in base_weights.get_all_weights().keys()
        }
    }


@router.post("/evaluate", response_model=EnsembleResponse)
async def evaluate_ensemble(request: EnsembleEvaluateRequest):
    """
    Evaluate ensemble signal.
    
    Объединяет alpha-сигналы в финальный торговый сигнал.
    """
    # Get alpha results
    if request.alpha_results:
        alpha_results = request.alpha_results
    elif ALPHA_ENGINE_AVAILABLE:
        # Use Alpha Engine to generate
        builder = AlphaSignalBuilder()
        # Generate mock market data for now
        mock_data = {
            "close": [45000 + random.uniform(-500, 500) for _ in range(100)],
            "high": [45200 + random.uniform(-500, 500) for _ in range(100)],
            "low": [44800 + random.uniform(-500, 500) for _ in range(100)],
            "volume": [random.uniform(1000, 5000) for _ in range(100)]
        }
        summary = builder.build_signals(request.symbol, request.timeframe, mock_data)
        alpha_results = [ar.model_dump() for ar in summary.alpha_results]
    else:
        # Use mock data
        alpha_results = generate_mock_alpha_results(request.symbol)
    
    # Set weights based on preset
    weights = get_weights_preset(request.weights_preset)
    scorer_instance = SignalScorer(weights=weights)
    
    # Score
    result = scorer_instance.score(
        symbol=request.symbol,
        timeframe=request.timeframe,
        alpha_results=alpha_results,
        regime=request.regime,
        market_context=request.market_context
    )
    
    # Save snapshot
    snapshot = EnsembleSnapshot(
        id=str(uuid.uuid4()),
        symbol=request.symbol,
        timeframe=request.timeframe,
        result=result,
        market_price=request.current_price,
        created_at=datetime.utcnow()
    )
    
    try:
        repository.save_snapshot(snapshot)
    except Exception as e:
        print(f"[Ensemble] Failed to save snapshot: {e}")
    
    return EnsembleResponse(
        symbol=result.symbol,
        timeframe=result.timeframe,
        direction=result.signal.direction.value,
        strength=result.signal.strength,
        confidence=result.signal.confidence,
        quality=result.signal.quality.value,
        long_score=result.signal.long_score,
        short_score=result.signal.short_score,
        action_score=result.action_score,
        has_conflict=result.conflict_report.has_conflict,
        conflict_severity=result.conflict_report.conflict_severity,
        recommendation=result.recommendation,
        notes=result.notes,
        warnings=result.warnings,
        computed_at=result.computed_at.isoformat()
    )


@router.get("/symbol/{symbol}")
async def get_ensemble_for_symbol(
    symbol: str,
    timeframe: str = Query(default="1h"),
    regime: str = Query(default="UNKNOWN"),
    fresh: bool = Query(default=False, description="Force fresh calculation")
):
    """Получение ensemble для конкретного символа"""
    
    if not fresh:
        # Try cached
        snapshot = repository.get_snapshot(symbol, timeframe)
        if snapshot:
            result = snapshot.get("result", {})
            signal = result.get("signal", {})
            
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "cached": True,
                "direction": signal.get("direction", "NEUTRAL"),
                "strength": signal.get("strength", 0),
                "confidence": signal.get("confidence", 0),
                "quality": signal.get("quality", "LOW"),
                "action_score": result.get("action_score", 0),
                "recommendation": result.get("recommendation", ""),
                "created_at": snapshot.get("created_at")
            }
    
    # Generate fresh
    alpha_results = generate_mock_alpha_results(symbol)
    
    result = scorer.score(
        symbol=symbol,
        timeframe=timeframe,
        alpha_results=alpha_results,
        regime=regime
    )
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "cached": False,
        "direction": result.signal.direction.value,
        "strength": result.signal.strength,
        "confidence": result.signal.confidence,
        "quality": result.signal.quality.value,
        "long_score": result.signal.long_score,
        "short_score": result.signal.short_score,
        "action_score": result.action_score,
        "has_conflict": result.conflict_report.has_conflict,
        "recommendation": result.recommendation,
        "notes": result.notes
    }


@router.get("/history")
async def get_ensemble_history(
    symbol: str = Query(default="BTCUSDT"),
    timeframe: str = Query(default="1h"),
    direction: Optional[str] = Query(default=None),
    min_quality: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Получение истории ensemble сигналов"""
    
    query = EnsembleHistoryQuery(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit
    )
    
    if direction:
        try:
            query.direction = SignalDirection(direction)
        except ValueError:
            pass
    
    if min_quality:
        try:
            query.min_quality = SignalQuality(min_quality)
        except ValueError:
            pass
    
    history = repository.get_history(query)
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "filters": {
            "direction": direction,
            "min_quality": min_quality
        },
        "count": len(history),
        "history": history
    }


@router.get("/quality/{quality}")
async def get_signals_by_quality(
    quality: str,
    limit: int = Query(default=50, ge=1, le=200)
):
    """Получение сигналов по качеству"""
    try:
        q = SignalQuality(quality)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid quality: {quality}")
    
    signals = repository.get_signals_by_quality(q, limit)
    
    return {
        "quality": quality,
        "count": len(signals),
        "signals": signals
    }


# ============================================
# Batch Operations
# ============================================

class BatchEnsembleRequest(BaseModel):
    """Batch запрос для нескольких символов"""
    symbols: List[str] = Field(default=["BTCUSDT", "ETHUSDT"])
    timeframe: str = Field(default="1h")
    regime: str = Field(default="UNKNOWN")


@router.post("/batch")
async def batch_evaluate(request: BatchEnsembleRequest):
    """Batch evaluation для нескольких символов"""
    results = []
    
    for symbol in request.symbols[:10]:  # Limit to 10
        alpha_results = generate_mock_alpha_results(symbol)
        
        result = scorer.score(
            symbol=symbol,
            timeframe=request.timeframe,
            alpha_results=alpha_results,
            regime=request.regime
        )
        
        results.append({
            "symbol": symbol,
            "direction": result.signal.direction.value,
            "strength": result.signal.strength,
            "confidence": result.signal.confidence,
            "quality": result.signal.quality.value,
            "action_score": result.action_score,
            "has_conflict": result.conflict_report.has_conflict,
            "recommendation": result.recommendation
        })
    
    return {
        "timeframe": request.timeframe,
        "regime": request.regime,
        "count": len(results),
        "results": results,
        "computed_at": datetime.utcnow().isoformat()
    }


@router.get("/conflict-analysis/{symbol}")
async def analyze_conflicts(
    symbol: str,
    timeframe: str = Query(default="1h")
):
    """Детальный анализ конфликтов для символа"""
    alpha_results = generate_mock_alpha_results(symbol)
    
    result = scorer.score(
        symbol=symbol,
        timeframe=timeframe,
        alpha_results=alpha_results
    )
    
    conflict = result.conflict_report
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "has_conflict": conflict.has_conflict,
        "conflict_severity": conflict.conflict_severity,
        "conflicting_alphas": conflict.conflicting_alphas,
        "resolution_action": conflict.resolution_action,
        "confidence_penalty": conflict.confidence_penalty,
        "notes": conflict.notes,
        "alpha_breakdown": [
            {
                "alpha_id": c.alpha_id,
                "direction": c.direction,
                "weighted_score": c.weighted_score,
                "in_conflict": c.in_conflict
            }
            for c in result.alpha_contributions
        ]
    }
