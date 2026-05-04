"""
Research Analytics API Routes — PHASE 48

Unified API for chart visualization data.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import datetime, timezone

from .chart_data import get_chart_data_service
from .indicators import get_indicator_service, IndicatorConfig
from .patterns import get_pattern_service
from .hypothesis_viz import get_hypothesis_viz_service
from .fractal_viz import get_fractal_viz_service
from .research_presets import get_presets_service


router = APIRouter(prefix="/research-analytics", tags=["Research Analytics"])


# ═══════════════════════════════════════════════════════════════
# Health & Info
# ═══════════════════════════════════════════════════════════════

@router.get("/health")
async def health():
    """Research Analytics API health check."""
    return {
        "status": "ok",
        "phase": "48",
        "module": "research_analytics",
        "components": {
            "chart_data": "ready",
            "indicators": "ready",
            "patterns": "ready",
            "hypothesis_viz": "ready",
            "fractal_viz": "ready",
            "presets": "ready",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/available-indicators")
async def get_available_indicators():
    """Get list of available indicators."""
    service = get_presets_service()
    return {
        "indicators": service.get_available_indicators(),
        "count": len(service.get_available_indicators()),
    }


@router.get("/available-overlays")
async def get_available_overlays():
    """Get list of available overlays."""
    service = get_presets_service()
    return {
        "overlays": service.get_available_overlays(),
        "count": len(service.get_available_overlays()),
    }


# ═══════════════════════════════════════════════════════════════
# Chart Data API (48.1)
# ═══════════════════════════════════════════════════════════════

@router.get("/chart-data/{symbol}/{timeframe}")
async def get_chart_data(
    symbol: str,
    timeframe: str,
    limit: int = Query(default=500, le=2000),
    include_volume: bool = True,
    include_oi: bool = False,
    include_funding: bool = False,
    include_liquidations: bool = False,
    include_dominance: bool = False,
):
    """Get chart data for a symbol."""
    service = get_chart_data_service()
    
    data = await service.get_chart_data(
        symbol=symbol.upper(),
        timeframe=timeframe,
        limit=limit,
        include_volume=include_volume,
        include_oi=include_oi,
        include_funding=include_funding,
        include_liquidations=include_liquidations,
        include_dominance=include_dominance,
    )
    
    return data.model_dump()


# ═══════════════════════════════════════════════════════════════
# Indicator API (48.2)
# ═══════════════════════════════════════════════════════════════

@router.post("/indicators/{symbol}/{timeframe}")
async def calculate_indicators(
    symbol: str,
    timeframe: str,
    indicators: List[dict],
    limit: int = Query(default=500, le=2000),
):
    """Calculate indicators for chart data."""
    # Get candle data
    chart_service = get_chart_data_service()
    chart_data = await chart_service.get_chart_data(
        symbol=symbol.upper(),
        timeframe=timeframe,
        limit=limit,
    )
    
    # Calculate indicators
    indicator_service = get_indicator_service()
    
    configs = [
        IndicatorConfig(
            name=ind.get("name", ""),
            params=ind.get("params", {}),
            color=ind.get("color"),
        )
        for ind in indicators
    ]
    
    results = indicator_service.calculate_batch(configs, chart_data.candles)
    
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "indicators": [r.model_dump() for r in results],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/indicator/{indicator_name}/{symbol}/{timeframe}")
async def calculate_single_indicator(
    indicator_name: str,
    symbol: str,
    timeframe: str,
    period: int = Query(default=14),
    limit: int = Query(default=500, le=2000),
):
    """Calculate a single indicator."""
    # Get candle data
    chart_service = get_chart_data_service()
    chart_data = await chart_service.get_chart_data(
        symbol=symbol.upper(),
        timeframe=timeframe,
        limit=limit,
    )
    
    # Calculate indicator
    indicator_service = get_indicator_service()
    result = indicator_service.calculate_indicator(
        indicator_name,
        chart_data.candles,
        period=period,
    )
    
    return result.model_dump()


# ═══════════════════════════════════════════════════════════════
# Pattern Detection API (48.3)
# ═══════════════════════════════════════════════════════════════

@router.get("/patterns/{symbol}/{timeframe}")
async def detect_patterns(
    symbol: str,
    timeframe: str,
    pattern_types: Optional[str] = None,
    limit: int = Query(default=500, le=2000),
):
    """Detect chart patterns."""
    # Get candle data
    chart_service = get_chart_data_service()
    chart_data = await chart_service.get_chart_data(
        symbol=symbol.upper(),
        timeframe=timeframe,
        limit=limit,
    )
    
    # Detect patterns
    pattern_service = get_pattern_service()
    types_list = pattern_types.split(",") if pattern_types else None
    
    patterns = pattern_service.detect_patterns(
        chart_data.candles,
        symbol.upper(),
        timeframe,
        pattern_types=types_list,
    )
    
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "patterns": [p.model_dump() for p in patterns],
        "count": len(patterns),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/support-resistance/{symbol}/{timeframe}")
async def get_support_resistance(
    symbol: str,
    timeframe: str,
    sensitivity: float = Query(default=0.02, ge=0.005, le=0.1),
    limit: int = Query(default=500, le=2000),
):
    """Get support and resistance levels."""
    # Get candle data
    chart_service = get_chart_data_service()
    chart_data = await chart_service.get_chart_data(
        symbol=symbol.upper(),
        timeframe=timeframe,
        limit=limit,
    )
    
    # Detect levels
    pattern_service = get_pattern_service()
    levels = pattern_service.detect_support_resistance(
        chart_data.candles,
        sensitivity=sensitivity,
    )
    
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "levels": [l.model_dump() for l in levels],
        "count": len(levels),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/liquidity-zones/{symbol}/{timeframe}")
async def get_liquidity_zones(
    symbol: str,
    timeframe: str,
    limit: int = Query(default=500, le=2000),
):
    """Get liquidity zones."""
    # Get candle data
    chart_service = get_chart_data_service()
    chart_data = await chart_service.get_chart_data(
        symbol=symbol.upper(),
        timeframe=timeframe,
        limit=limit,
    )
    
    # Detect zones
    pattern_service = get_pattern_service()
    zones = pattern_service.detect_liquidity_zones(chart_data.candles)
    
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "zones": [z.model_dump() for z in zones],
        "count": len(zones),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# Hypothesis Visualization API (48.4)
# ═══════════════════════════════════════════════════════════════

@router.get("/hypothesis/{symbol}/{timeframe}")
async def get_hypothesis_visualization(
    symbol: str,
    timeframe: str,
    limit: int = Query(default=500, le=2000),
):
    """Get hypothesis visualization data."""
    # Get candle data
    chart_service = get_chart_data_service()
    chart_data = await chart_service.get_chart_data(
        symbol=symbol.upper(),
        timeframe=timeframe,
        limit=limit,
    )
    
    # Build hypothesis visualization
    hypothesis_service = get_hypothesis_viz_service()
    viz = hypothesis_service.build_hypothesis_visualization(
        chart_data.candles,
        symbol.upper(),
        timeframe,
    )
    
    return viz.model_dump()


# ═══════════════════════════════════════════════════════════════
# Fractal Visualization API (48.5)
# ═══════════════════════════════════════════════════════════════

@router.get("/fractal-matches/{symbol}/{timeframe}")
async def get_fractal_matches(
    symbol: str,
    timeframe: str,
    min_similarity: float = Query(default=0.70, ge=0.5, le=0.99),
    limit: int = Query(default=3, ge=1, le=10),
    candle_limit: int = Query(default=500, le=2000),
):
    """Get fractal pattern matches."""
    # Get candle data
    chart_service = get_chart_data_service()
    chart_data = await chart_service.get_chart_data(
        symbol=symbol.upper(),
        timeframe=timeframe,
        limit=candle_limit,
    )
    
    # Find matches
    fractal_service = get_fractal_viz_service()
    result = fractal_service.find_fractal_matches(
        chart_data.candles,
        symbol.upper(),
        timeframe,
        min_similarity=min_similarity,
        limit=limit,
    )
    
    return result.model_dump()


# ═══════════════════════════════════════════════════════════════
# Research Presets API (48.6)
# ═══════════════════════════════════════════════════════════════

@router.get("/presets")
async def get_all_presets():
    """Get all research presets."""
    service = get_presets_service()
    presets = service.get_all_presets()
    
    return {
        "presets": [p.model_dump() for p in presets],
        "count": len(presets),
    }


@router.get("/preset/{preset_id}")
async def get_preset(preset_id: str):
    """Get a specific preset."""
    service = get_presets_service()
    preset = service.get_preset(preset_id)
    
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")
    
    return preset.model_dump()


@router.get("/suggestions/{symbol}/{timeframe}")
async def get_suggestions(
    symbol: str,
    timeframe: str,
    limit: int = Query(default=500, le=2000),
):
    """Get system suggestions for chart configuration."""
    # Get candle data
    chart_service = get_chart_data_service()
    chart_data = await chart_service.get_chart_data(
        symbol=symbol.upper(),
        timeframe=timeframe,
        limit=limit,
    )
    
    # Get suggestions
    presets_service = get_presets_service()
    suggestions = presets_service.get_suggestions(
        chart_data.candles,
        symbol.upper(),
    )
    
    return suggestions.model_dump()


# ═══════════════════════════════════════════════════════════════
# Combined Chart Payload
# ═══════════════════════════════════════════════════════════════

@router.get("/full-payload/{symbol}/{timeframe}")
async def get_full_chart_payload(
    symbol: str,
    timeframe: str,
    include_indicators: bool = True,
    include_patterns: bool = True,
    include_hypothesis: bool = True,
    include_fractals: bool = False,
    limit: int = Query(default=500, le=2000),
):
    """Get complete chart payload with all analytics."""
    symbol = symbol.upper()
    
    # Get base chart data
    chart_service = get_chart_data_service()
    chart_data = await chart_service.get_chart_data(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        include_volume=True,
    )
    
    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "candles": chart_data.candles,
        "volume": chart_data.volume,
    }
    
    # Get suggestions for indicators
    presets_service = get_presets_service()
    suggestions = presets_service.get_suggestions(chart_data.candles, symbol)
    result["regime"] = suggestions.regime.value
    result["suggested_indicators"] = suggestions.suggested_indicators
    result["suggested_overlays"] = suggestions.suggested_overlays
    
    # Add indicators if requested
    if include_indicators and suggestions.suggested_indicators:
        indicator_service = get_indicator_service()
        configs = [
            IndicatorConfig(
                name=ind.get("name", ""),
                params=ind.get("params", {}),
                color=ind.get("color"),
            )
            for ind in suggestions.suggested_indicators[:5]  # Limit to 5
        ]
        indicators = indicator_service.calculate_batch(configs, chart_data.candles)
        result["indicators"] = [i.model_dump() for i in indicators]
    
    # Add patterns if requested
    if include_patterns:
        pattern_service = get_pattern_service()
        patterns = pattern_service.detect_patterns(
            chart_data.candles, symbol, timeframe
        )
        sr_levels = pattern_service.detect_support_resistance(chart_data.candles)
        
        result["patterns"] = [p.model_dump() for p in patterns[:10]]
        result["support_resistance"] = [l.model_dump() for l in sr_levels[:10]]
    
    # Add hypothesis if requested
    if include_hypothesis:
        hypothesis_service = get_hypothesis_viz_service()
        hypothesis = hypothesis_service.build_hypothesis_visualization(
            chart_data.candles, symbol, timeframe
        )
        result["hypothesis"] = hypothesis.model_dump()
    
    # Add fractals if requested
    if include_fractals:
        fractal_service = get_fractal_viz_service()
        fractal_result = fractal_service.find_fractal_matches(
            chart_data.candles, symbol, timeframe
        )
        result["fractal_matches"] = [m.model_dump() for m in fractal_result.matches]
    
    return result


# Export router
research_analytics_router = router
