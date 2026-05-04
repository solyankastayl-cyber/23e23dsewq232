"""
Signal Explanation Routes — PHASE 51
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone

from .explainer import get_signal_explainer
from ..research_analytics.chart_data import get_chart_data_service
from ..research_analytics.patterns import get_pattern_service
from ..research_analytics.hypothesis_viz import get_hypothesis_viz_service
from ..research_analytics.fractal_viz import get_fractal_viz_service


router = APIRouter(prefix="/signal", tags=["Signal Explanation"])


@router.get("/health")
async def health():
    """Signal Explanation API health."""
    return {
        "status": "ok",
        "phase": "51",
        "module": "signal_explanation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/explanation/{symbol}/{timeframe}")
async def get_signal_explanation(
    symbol: str,
    timeframe: str,
    limit: int = 500,
):
    """
    Get explanation for current signal.
    
    Explains WHY the system generated this signal.
    """
    symbol = symbol.upper()
    
    # Get chart data
    chart_service = get_chart_data_service()
    chart_data = await chart_service.get_chart_data(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )
    
    # Get hypothesis
    hypothesis_service = get_hypothesis_viz_service()
    hypothesis = hypothesis_service.build_hypothesis_visualization(
        chart_data.candles, symbol, timeframe
    )
    
    # Get patterns
    pattern_service = get_pattern_service()
    patterns = pattern_service.detect_patterns(
        chart_data.candles, symbol, timeframe
    )
    
    # Get fractal matches
    fractal_service = get_fractal_viz_service()
    fractal_result = fractal_service.find_fractal_matches(
        chart_data.candles, symbol, timeframe
    )
    
    # Build hypothesis dict
    hyp_dict = {
        "hypothesis_id": hypothesis.hypothesis_id,
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": hypothesis.direction,
        "confidence": hypothesis.confidence,
        "alpha_score": 0.6 if hypothesis.direction != "neutral" else 0.3,
        "regime_score": 0.5,
        "microstructure_score": 0.4,
        "capital_flow_score": 0.3,
        "fractal_similarity_score": fractal_result.matches[0].similarity if fractal_result.matches else 0,
        "alpha_sources": ["trend", "momentum", "structure"],
    }
    
    # Generate explanation
    explainer = get_signal_explainer()
    explanation = explainer.explain_hypothesis(
        hypothesis=hyp_dict,
        patterns=[p.model_dump() for p in patterns],
        fractal_matches=[m.model_dump() for m in fractal_result.matches],
    )
    
    return explanation.model_dump()


@router.get("/drivers/{symbol}/{timeframe}")
async def get_signal_drivers(
    symbol: str,
    timeframe: str,
):
    """Get simplified driver breakdown."""
    explanation = await get_signal_explanation(symbol, timeframe)
    
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "direction": explanation["direction"],
        "confidence": explanation["confidence"],
        "strength": explanation["strength"],
        "drivers": [
            {
                "name": d["name"],
                "contribution": round(d["contribution"], 3),
                "type": d["driver_type"],
            }
            for d in explanation["drivers"]
        ],
        "conflicts": [
            {
                "name": c["name"],
                "severity": c["severity"],
            }
            for c in explanation["conflicts"]
        ],
        "summary": explanation["summary"],
    }


# Export router
signal_explanation_router = router
