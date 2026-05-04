"""
Alpha Engine API Routes
=======================

REST API endpoints для Alpha Engine.

Endpoints:
- POST /api/alpha-engine/signals - получить alpha сигналы
- GET /api/alpha-engine/alpha/{alpha_id} - получить конкретный alpha
- GET /api/alpha-engine/summary - получить alpha summary
- GET /api/alpha-engine/symbol/{symbol} - alpha по символу
- GET /api/alpha-engine/history - история alpha
"""

import random
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .alpha_types import (
    AlphaDirection,
    AlphaRegimeRelevance,
    AlphaResult,
    AlphaSummary,
    AlphaSnapshot,
    AlphaHistoryQuery
)
from .alpha_registry import get_alpha_registry
from .alpha_scoring_engine import AlphaScoringEngine
from .alpha_signal_builder import AlphaSignalBuilder
from .alpha_repository import AlphaRepository


router = APIRouter(prefix="/api/alpha-engine", tags=["Alpha Engine"])

# Initialize components
scoring_engine = AlphaScoringEngine()
signal_builder = AlphaSignalBuilder()
repository = AlphaRepository()


# ============================================
# Request/Response Models
# ============================================

class AlphaSignalsRequest(BaseModel):
    """Запрос на расчёт alpha signals"""
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(default="1h", description="Timeframe")
    close: List[float] = Field(default_factory=list, description="Close prices")
    high: List[float] = Field(default_factory=list, description="High prices")
    low: List[float] = Field(default_factory=list, description="Low prices")
    volume: List[float] = Field(default_factory=list, description="Volumes")
    current_price: float = Field(default=0.0, description="Current price")
    regime: str = Field(default="UNKNOWN", description="Current market regime")


class AlphaSignalsResponse(BaseModel):
    """Ответ с alpha signals"""
    symbol: str
    timeframe: str
    summary: Dict[str, Any]
    decision_factors: Dict[str, Any]
    risk_adjustment: Dict[str, Any]
    strategy_hints: Dict[str, Any]
    computed_at: str


# ============================================
# Mock Data Generator
# ============================================

def generate_mock_market_data(symbol: str = "BTCUSDT") -> Dict[str, Any]:
    """Генерация mock market data для тестирования"""
    base_price = 45000 if "BTC" in symbol else 2500 if "ETH" in symbol else 100
    
    # Generate 100 candles
    close = []
    high = []
    low = []
    volume = []
    
    price = base_price
    for i in range(100):
        change = random.uniform(-0.02, 0.02)
        price = price * (1 + change)
        
        c = price
        h = price * (1 + random.uniform(0, 0.01))
        l = price * (1 - random.uniform(0, 0.01))
        v = random.uniform(1000, 5000) * base_price / 1000
        
        close.append(c)
        high.append(h)
        low.append(l)
        volume.append(v)
    
    return {
        "close": close,
        "high": high,
        "low": low,
        "volume": volume
    }


# ============================================
# API Endpoints - Static routes FIRST
# ============================================

@router.get("/registry")
async def get_alpha_registry_info():
    """
    Получение информации о реестре alpha-факторов.
    """
    registry = get_alpha_registry()
    return registry.get_registry_info()


@router.get("/stats")
async def get_alpha_stats():
    """
    Статистика Alpha Engine.
    """
    registry = get_alpha_registry()
    repo_stats = repository.get_stats()
    
    return {
        "engine_version": "phase_3.5.1",
        "registered_alphas": len(registry.get_ids()),
        "alpha_ids": registry.get_ids(),
        "repository": repo_stats
    }


@router.get("/health")
async def alpha_health():
    """
    Health check для Alpha Engine.
    """
    registry = get_alpha_registry()
    
    return {
        "status": "healthy",
        "version": "phase_3.5.1",
        "alphas_registered": len(registry.get_ids()),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/summary")
async def get_alpha_summary(
    symbol: str = Query(default="BTCUSDT"),
    timeframe: str = Query(default="1h")
):
    """
    Получение последнего alpha summary для символа.
    """
    # Try to get from repository
    snapshot = repository.get_snapshot(symbol, timeframe)
    
    if snapshot:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "summary": snapshot.summary.model_dump(),
            "market_price": snapshot.market_price,
            "regime": snapshot.regime,
            "created_at": snapshot.created_at.isoformat()
        }
    
    # Generate fresh if not found
    market_data = generate_mock_market_data(symbol)
    summary = signal_builder.build_signals(symbol, timeframe, market_data)
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "summary": summary.model_dump(),
        "market_price": market_data["close"][-1],
        "regime": "UNKNOWN",
        "created_at": datetime.utcnow().isoformat(),
        "note": "Generated fresh - no stored snapshot found"
    }


@router.get("/history")
async def get_alpha_history(
    symbol: str = Query(default="BTCUSDT"),
    timeframe: str = Query(default="1h"),
    alpha_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """
    Получение истории alpha.
    """
    query = AlphaHistoryQuery(
        symbol=symbol,
        timeframe=timeframe,
        alpha_id=alpha_id,
        limit=limit
    )
    
    history = repository.get_history(query)
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "alpha_id": alpha_id,
        "count": len(history),
        "history": history
    }


# ============================================
# POST Endpoints
# ============================================

@router.post("/signals", response_model=AlphaSignalsResponse)
async def get_alpha_signals(request: AlphaSignalsRequest):
    """
    Расчёт alpha signals для символа.
    
    Принимает market data и возвращает полный alpha context.
    """
    # Validate market data
    if not request.close or len(request.close) < 30:
        # Use mock data if insufficient
        mock_data = generate_mock_market_data(request.symbol)
        market_data = mock_data
    else:
        market_data = {
            "close": request.close,
            "high": request.high or request.close,
            "low": request.low or request.close,
            "volume": request.volume or [1000] * len(request.close)
        }
    
    # Build signals context
    context = signal_builder.build_context(
        symbol=request.symbol,
        timeframe=request.timeframe,
        market_data=market_data,
        current_price=request.current_price or market_data["close"][-1],
        regime=request.regime
    )
    
    # Save snapshot
    summary = signal_builder.build_signals(request.symbol, request.timeframe, market_data)
    snapshot = signal_builder.create_snapshot(
        symbol=request.symbol,
        timeframe=request.timeframe,
        summary=summary,
        current_price=request.current_price or market_data["close"][-1],
        regime=request.regime
    )
    
    try:
        repository.save_snapshot(snapshot)
    except Exception as e:
        # Log but don't fail
        print(f"[Alpha] Failed to save snapshot: {e}")
    
    return AlphaSignalsResponse(
        symbol=request.symbol,
        timeframe=request.timeframe,
        summary=context["summary"],
        decision_factors=context["decision_factors"],
        risk_adjustment=context["risk_adjustment"],
        strategy_hints=context["strategy_hints"],
        computed_at=context["computed_at"]
    )


class BatchAlphaRequest(BaseModel):
    """Batch запрос для нескольких символов"""
    symbols: List[str] = Field(default=["BTCUSDT", "ETHUSDT"])
    timeframe: str = Field(default="1h")


@router.post("/batch")
async def get_batch_alpha(request: BatchAlphaRequest):
    """
    Получение alpha для нескольких символов одновременно.
    """
    results = []
    
    for symbol in request.symbols[:10]:  # Limit to 10
        market_data = generate_mock_market_data(symbol)
        summary = signal_builder.build_signals(symbol, request.timeframe, market_data)
        
        results.append({
            "symbol": symbol,
            "alpha_bias": summary.alpha_bias.value,
            "alpha_confidence": summary.alpha_confidence,
            "alpha_strength": summary.alpha_strength,
            "long_signals": summary.long_signals,
            "short_signals": summary.short_signals
        })
    
    return {
        "timeframe": request.timeframe,
        "count": len(results),
        "results": results,
        "computed_at": datetime.utcnow().isoformat()
    }


# ============================================
# Dynamic path endpoints LAST
# ============================================

@router.get("/alpha/{alpha_id}")
async def get_alpha_by_id(
    alpha_id: str,
    symbol: str = Query(default="BTCUSDT"),
    limit: int = Query(default=50, ge=1, le=500)
):
    """
    Получение истории конкретного alpha-фактора.
    """
    registry = get_alpha_registry()
    alpha = registry.get(alpha_id)
    
    if not alpha:
        raise HTTPException(status_code=404, detail=f"Alpha {alpha_id} not found")
    
    # Get history from repository
    history = repository.get_alpha_by_id(alpha_id, symbol, limit)
    
    return {
        "alpha_id": alpha_id,
        "alpha_name": alpha.alpha_name,
        "description": alpha.description,
        "regime_relevance": alpha.regime_relevance.value,
        "history_count": len(history),
        "history": history
    }


@router.get("/symbol/{symbol}")
async def get_alpha_for_symbol(
    symbol: str,
    timeframe: str = Query(default="1h"),
    fresh: bool = Query(default=False, description="Force fresh calculation")
):
    """
    Получение alpha для конкретного символа.
    """
    if not fresh:
        # Try cached
        snapshot = repository.get_snapshot(symbol, timeframe)
        if snapshot:
            # Check if recent (< 5 min)
            age = (datetime.utcnow() - snapshot.created_at).total_seconds()
            if age < 300:
                return {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "cached": True,
                    "age_seconds": int(age),
                    "summary": snapshot.summary.model_dump(),
                    "market_price": snapshot.market_price
                }
    
    # Generate fresh
    market_data = generate_mock_market_data(symbol)
    context = signal_builder.build_context(
        symbol=symbol,
        timeframe=timeframe,
        market_data=market_data,
        current_price=market_data["close"][-1]
    )
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "cached": False,
        "summary": context["summary"],
        "decision_factors": context["decision_factors"],
        "risk_adjustment": context["risk_adjustment"]
    }
