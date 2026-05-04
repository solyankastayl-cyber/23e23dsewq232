"""
Chart Composer Routes — PHASE 50

Main endpoint: GET /api/v1/chart/full-analysis
Frontend only draws, no logic on UI.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime, timezone

from .composer import get_chart_composer
from .presets import get_preset_for_regime, REGIME_PRESETS, PresetType
from ..research_analytics.chart_data import get_chart_data_service
from ..research_analytics.indicators import get_indicator_service, IndicatorConfig
from ..research_analytics.patterns import get_pattern_service
from ..research_analytics.harmonics import get_harmonic_detector
from ..research_analytics.hypothesis_viz import get_hypothesis_viz_service
from ..research_analytics.fractal_viz import get_fractal_viz_service
from ..research_analytics.research_presets import get_presets_service


router = APIRouter(prefix="/chart", tags=["Chart Composer"])


@router.get("/health")
async def health():
    """Chart Composer health."""
    return {
        "status": "ok",
        "phase": "50",
        "module": "chart_composer",
        "presets_available": len(REGIME_PRESETS),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/presets")
async def get_presets():
    """Get all available chart presets."""
    composer = get_chart_composer()
    return {
        "presets": composer.get_available_presets(),
        "count": len(REGIME_PRESETS),
    }


@router.get("/preset/{preset_id}")
async def get_preset(preset_id: str):
    """Get specific preset configuration."""
    for preset in REGIME_PRESETS.values():
        if preset.preset_id == preset_id:
            return preset.model_dump()
    
    raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")


@router.get("/full-analysis/{symbol}/{timeframe}")
async def get_full_chart_analysis(
    symbol: str,
    timeframe: str,
    preset_id: Optional[str] = None,
    include_hypothesis: bool = True,
    include_fractals: bool = False,
    include_liquidations: bool = False,
    include_funding: bool = False,
    limit: int = Query(default=500, le=2000),
):
    """
    Get complete chart analysis with composed objects.
    
    This is the main endpoint for frontend rendering.
    Frontend only draws - no logic on UI.
    """
    symbol = symbol.upper()
    
    # Get chart data
    chart_service = get_chart_data_service()
    chart_data = await chart_service.get_chart_data(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        include_volume=True,
        include_liquidations=include_liquidations,
        include_funding=include_funding,
    )
    
    # Detect market regime
    presets_service = get_presets_service()
    suggestions = presets_service.get_suggestions(chart_data.candles, symbol)
    market_regime = suggestions.regime.value
    
    # Get or select preset
    if preset_id:
        preset = None
        for p in REGIME_PRESETS.values():
            if p.preset_id == preset_id:
                preset = p
                break
        if preset is None:
            preset = get_preset_for_regime(market_regime)
    else:
        preset = get_preset_for_regime(market_regime)
    
    # Get indicators based on preset
    indicator_service = get_indicator_service()
    configs = [
        IndicatorConfig(
            name=ind.get("name", ""),
            params=ind.get("params", {}),
            color=ind.get("color"),
        )
        for ind in preset.indicators
    ]
    indicators = indicator_service.calculate_batch(configs, chart_data.candles)
    indicators_data = [i.model_dump() for i in indicators]
    
    # Get patterns
    pattern_service = get_pattern_service()
    patterns = pattern_service.detect_patterns(
        chart_data.candles, symbol, timeframe
    )
    patterns_data = [p.model_dump() for p in patterns]
    
    # Get S/R levels
    sr_levels = pattern_service.detect_support_resistance(chart_data.candles)
    sr_data = [l.model_dump() for l in sr_levels]
    
    # Get liquidity zones
    liq_zones = pattern_service.detect_liquidity_zones(chart_data.candles)
    liq_data = [z.model_dump() for z in liq_zones]
    
    # Get harmonic patterns
    harmonic_detector = get_harmonic_detector()
    harmonic_results = harmonic_detector.detect(chart_data.candles, symbol, timeframe)
    patterns_data.extend(harmonic_results)
    
    # Get hypothesis
    hypothesis_data = None
    if include_hypothesis:
        hypothesis_service = get_hypothesis_viz_service()
        hypothesis = hypothesis_service.build_hypothesis_visualization(
            chart_data.candles, symbol, timeframe
        )
        hypothesis_data = hypothesis.model_dump()
    
    # Get fractal matches
    fractal_data = []
    if include_fractals:
        fractal_service = get_fractal_viz_service()
        fractal_result = fractal_service.find_fractal_matches(
            chart_data.candles, symbol, timeframe
        )
        fractal_data = [m.model_dump() for m in fractal_result.matches]
    
    # Compose final chart
    composer = get_chart_composer()
    composed = await composer.compose(
        symbol=symbol,
        timeframe=timeframe,
        candles=chart_data.candles,
        volume=chart_data.volume,
        patterns=patterns_data,
        support_resistance=sr_data,
        liquidity_zones=liq_data,
        indicators=indicators_data,
        hypothesis=hypothesis_data,
        fractal_matches=fractal_data,
        market_regime=market_regime,
        capital_flow_bias="neutral",  # TODO: Get from capital flow engine
        preset=preset,
    )
    
    return composed.model_dump()


# Export router
chart_composer_router = router
