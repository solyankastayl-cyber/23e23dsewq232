"""
Market Context API Routes
=========================

REST API для Advanced Market Context Pack.

Endpoints:
- POST /api/market-context/analyze - полный анализ контекста
- GET /api/market-context/symbol/{symbol} - контекст по символу
- GET /api/market-context/funding/{symbol} - funding контекст
- GET /api/market-context/oi/{symbol} - OI контекст
- GET /api/market-context/volatility/{symbol} - volatility контекст
- GET /api/market-context/macro - macro контекст
- GET /api/market-context/volume-profile/{symbol} - volume profile
- GET /api/market-context/history - история
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from .context_types import (
    FundingContext,
    OIContext,
    VolatilityContext,
    MacroContext,
    VolumeProfileContext,
    MarketContextSnapshot,
    ContextHistoryQuery
)
from .funding_context_engine import FundingContextEngine
from .oi_context_engine import OIContextEngine
from .volatility_context_engine import VolatilityContextEngine
from .macro_context_engine import MacroContextEngine
from .volume_profile_engine import VolumeProfileEngine
from .context_aggregator import ContextAggregator
from .context_repository import ContextRepository


router = APIRouter(prefix="/api/market-context", tags=["Market Context"])

# Initialize
aggregator = ContextAggregator()
funding_engine = FundingContextEngine()
oi_engine = OIContextEngine()
volatility_engine = VolatilityContextEngine()
macro_engine = MacroContextEngine()
volume_profile_engine = VolumeProfileEngine()
repository = ContextRepository()


# ============================================
# Request Models
# ============================================

class ContextAnalyzeRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    funding_rates: List[float] = Field(default_factory=list)
    oi_values: List[float] = Field(default_factory=list)
    highs: List[float] = Field(default_factory=list)
    lows: List[float] = Field(default_factory=list)
    closes: List[float] = Field(default_factory=list)
    volumes: List[float] = Field(default_factory=list)
    current_price: float = 0.0


class ContextResponse(BaseModel):
    symbol: str
    timeframe: str
    context_score: float
    primary_bias: str
    context_quality: str
    long_bias_score: float
    short_bias_score: float
    funding_state: str
    oi_state: str
    volatility_regime: str
    macro_regime: str
    volume_profile_bias: str
    breakout_confidence_adj: float
    mean_reversion_confidence_adj: float
    trend_confidence_adj: float
    risk_multiplier: float
    warnings: List[str]
    notes: List[str]
    computed_at: str


# ============================================
# API Endpoints
# ============================================

@router.get("/health")
async def context_health():
    return {
        "status": "healthy",
        "version": "phase_3.5.4",
        "engines": ["funding", "oi", "volatility", "macro", "volume_profile"],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stats")
async def context_stats():
    repo_stats = repository.get_stats()
    return {
        "engine_version": "phase_3.5.4",
        "repository": repo_stats
    }


@router.post("/analyze", response_model=ContextResponse)
async def analyze_context(request: ContextAnalyzeRequest):
    """Полный анализ рыночного контекста"""
    
    snapshot = aggregator.aggregate(
        symbol=request.symbol,
        timeframe=request.timeframe,
        funding_rates=request.funding_rates if request.funding_rates else None,
        oi_values=request.oi_values if request.oi_values else None,
        highs=request.highs if request.highs else None,
        lows=request.lows if request.lows else None,
        closes=request.closes if request.closes else None,
        volumes=request.volumes if request.volumes else None,
        current_price=request.current_price
    )
    
    # Save
    try:
        repository.save_snapshot(snapshot)
    except Exception as e:
        print(f"[Context] Failed to save: {e}")
    
    return ContextResponse(
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        context_score=snapshot.context_score,
        primary_bias=snapshot.primary_bias,
        context_quality=snapshot.context_quality,
        long_bias_score=snapshot.long_bias_score,
        short_bias_score=snapshot.short_bias_score,
        funding_state=snapshot.funding.funding_state.value,
        oi_state=snapshot.oi.oi_state.value,
        volatility_regime=snapshot.volatility.volatility_regime.value,
        macro_regime=snapshot.macro.macro_regime.value,
        volume_profile_bias=snapshot.volume_profile.volume_profile_bias.value,
        breakout_confidence_adj=snapshot.breakout_confidence_adj,
        mean_reversion_confidence_adj=snapshot.mean_reversion_confidence_adj,
        trend_confidence_adj=snapshot.trend_confidence_adj,
        risk_multiplier=snapshot.risk_multiplier,
        warnings=snapshot.warnings,
        notes=snapshot.notes,
        computed_at=snapshot.computed_at.isoformat()
    )


@router.get("/symbol/{symbol}")
async def get_context_for_symbol(
    symbol: str,
    timeframe: str = Query(default="1h"),
    fresh: bool = Query(default=False)
):
    """Контекст для символа"""
    
    if not fresh:
        cached = repository.get_snapshot(symbol, timeframe)
        if cached:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "cached": True,
                **{k: v for k, v in cached.items() if k not in ["_id"]}
            }
    
    # Fresh analysis
    snapshot = aggregator.aggregate(symbol=symbol, timeframe=timeframe)
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "cached": False,
        "context_score": snapshot.context_score,
        "primary_bias": snapshot.primary_bias,
        "context_quality": snapshot.context_quality,
        "funding_state": snapshot.funding.funding_state.value,
        "oi_state": snapshot.oi.oi_state.value,
        "volatility_regime": snapshot.volatility.volatility_regime.value,
        "macro_regime": snapshot.macro.macro_regime.value,
        "risk_multiplier": snapshot.risk_multiplier,
        "warnings": snapshot.warnings
    }


@router.get("/funding/{symbol}")
async def get_funding_context(symbol: str):
    """Funding контекст"""
    funding_rates = funding_engine.generate_mock_data()
    ctx = funding_engine.analyze(funding_rates)
    
    return {
        "symbol": symbol,
        "funding_state": ctx.funding_state.value,
        "funding_rate": ctx.funding_rate,
        "funding_pressure": ctx.funding_pressure,
        "funding_extreme": ctx.funding_extreme,
        "directional_bias": ctx.directional_bias,
        "long_overcrowded": ctx.long_overcrowded,
        "short_overcrowded": ctx.short_overcrowded,
        "confidence_adjustment": ctx.confidence_adjustment,
        "notes": ctx.notes
    }


@router.get("/oi/{symbol}")
async def get_oi_context(symbol: str):
    """Open Interest контекст"""
    oi_values, prices = oi_engine.generate_mock_data()
    ctx = oi_engine.analyze(oi_values, prices)
    
    return {
        "symbol": symbol,
        "oi_state": ctx.oi_state.value,
        "oi_change_pct": ctx.oi_change_pct,
        "oi_pressure": ctx.oi_pressure,
        "squeeze_probability": ctx.squeeze_probability,
        "participation_quality": ctx.participation_quality,
        "price_oi_alignment": ctx.price_oi_alignment,
        "short_covering_detected": ctx.short_covering_detected,
        "long_liquidation_detected": ctx.long_liquidation_detected,
        "confidence_adjustment": ctx.confidence_adjustment,
        "notes": ctx.notes
    }


@router.get("/volatility/{symbol}")
async def get_volatility_context(symbol: str):
    """Volatility контекст"""
    highs, lows, closes = volatility_engine.generate_mock_data()
    ctx = volatility_engine.analyze(highs, lows, closes)
    
    return {
        "symbol": symbol,
        "volatility_regime": ctx.volatility_regime.value,
        "volatility_percentile": ctx.volatility_percentile,
        "volatility_pressure": ctx.volatility_pressure,
        "volatility_quality": ctx.volatility_quality,
        "expansion_probability": ctx.expansion_probability,
        "breakout_favorable": ctx.breakout_favorable,
        "mean_reversion_favorable": ctx.mean_reversion_favorable,
        "risk_multiplier": ctx.risk_multiplier,
        "notes": ctx.notes
    }


@router.get("/macro")
async def get_macro_context():
    """Macro контекст (global)"""
    ctx = macro_engine.analyze()
    
    return {
        "macro_regime": ctx.macro_regime.value,
        "macro_bias": ctx.macro_bias,
        "risk_environment": ctx.risk_environment.value,
        "spx_context": ctx.spx_context,
        "dxy_context": ctx.dxy_context,
        "cross_market_alignment": ctx.cross_market_alignment,
        "crypto_long_confidence_adj": ctx.crypto_long_confidence_adj,
        "crypto_short_confidence_adj": ctx.crypto_short_confidence_adj,
        "notes": ctx.notes
    }


@router.get("/volume-profile/{symbol}")
async def get_volume_profile_context(symbol: str):
    """Volume Profile контекст"""
    highs, lows, closes, volumes = volume_profile_engine.generate_mock_data()
    current_price = closes[-1]
    ctx = volume_profile_engine.analyze(highs, lows, closes, volumes, current_price)
    
    return {
        "symbol": symbol,
        "volume_profile_bias": ctx.volume_profile_bias.value,
        "poc_price": ctx.poc_price,
        "value_area_high": ctx.value_area_high,
        "value_area_low": ctx.value_area_low,
        "node_proximity": ctx.node_proximity,
        "price_acceptance": ctx.price_acceptance,
        "breakout_validation": ctx.breakout_validation,
        "mean_reversion_quality": ctx.mean_reversion_quality,
        "sr_refinement": ctx.sr_refinement,
        "notes": ctx.notes
    }


@router.get("/history")
async def get_context_history(
    symbol: str = Query(default="BTCUSDT"),
    timeframe: str = Query(default="1h"),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """История контекста"""
    query = ContextHistoryQuery(symbol=symbol, timeframe=timeframe, limit=limit)
    history = repository.get_history(query)
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(history),
        "history": history
    }


# ============================================
# Batch
# ============================================

class BatchContextRequest(BaseModel):
    symbols: List[str] = ["BTCUSDT", "ETHUSDT"]
    timeframe: str = "1h"


@router.post("/batch")
async def batch_context(request: BatchContextRequest):
    """Batch анализ контекста"""
    results = []
    
    for symbol in request.symbols[:10]:
        snapshot = aggregator.aggregate(symbol=symbol, timeframe=request.timeframe)
        results.append({
            "symbol": symbol,
            "context_score": snapshot.context_score,
            "primary_bias": snapshot.primary_bias,
            "context_quality": snapshot.context_quality,
            "risk_multiplier": snapshot.risk_multiplier,
            "warnings_count": len(snapshot.warnings)
        })
    
    return {
        "timeframe": request.timeframe,
        "count": len(results),
        "results": results,
        "computed_at": datetime.utcnow().isoformat()
    }
