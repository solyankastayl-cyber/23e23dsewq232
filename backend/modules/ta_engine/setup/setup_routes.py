"""
Setup API Routes
=================
REST API endpoints for Setup Engine.

Endpoints:
- GET /api/ta/setup/{symbol}/{tf} — Full setup analysis
- GET /api/ta/confluence/{symbol}/{tf} — Confluence analysis
- GET /api/ta/patterns/{symbol}/{tf} — Detected patterns
- GET /api/ta/levels/{symbol}/{tf} — Key price levels
- GET /api/ta/structure/{symbol}/{tf} — Market structure
- GET /api/ta/indicators/{symbol}/{tf} — Indicator signals
"""

from fastapi import APIRouter, Query
from datetime import datetime, timezone
from typing import Optional

from modules.ta_engine.setup.setup_builder import get_setup_builder
from modules.ta_engine.setup.pattern_detector import get_pattern_detector
from modules.ta_engine.setup.indicator_engine import get_indicator_engine
from modules.ta_engine.setup.level_engine import get_level_engine
from modules.ta_engine.setup.structure_engine import get_structure_engine
from modules.ta_engine.setup.market_data_service import get_market_data_service
from modules.ta_engine.utils.time_utils import normalize_tf

router = APIRouter(prefix="/api/ta", tags=["ta-setup"])

# Get builder and engines
_builder = None
_pattern_detector = None
_indicator_engine = None
_level_engine = None
_structure_engine = None


def _get_builder():
    global _builder
    if _builder is None:
        _builder = get_setup_builder()
    return _builder


def _get_candles(symbol: str, timeframe: str, limit: int = 200):
    """Helper to get candles using MarketDataService."""
    service = get_market_data_service()
    return service.get_candles(symbol, timeframe, limit)


# ═══════════════════════════════════════════════════════════════
# MAIN SETUP ENDPOINT
# ═══════════════════════════════════════════════════════════════

@router.get("/setup/{symbol}/{tf}")
async def get_setup_analysis(
    symbol: str,
    tf: str = "1d",
):
    """
    Get full setup analysis for a symbol.
    
    Returns:
    - top_setup: The strongest detected setup with all details
    - alternative_setups: Other detected setups
    - technical_bias: Overall market direction (bullish/bearish/neutral)
    - bias_confidence: Confidence level (0-1)
    """
    tf = normalize_tf(tf)
    builder = _get_builder()
    result = builder.build(symbol.upper(), tf)
    
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": tf,
        **result.to_dict(),
    }


# ═══════════════════════════════════════════════════════════════
# CONFLUENCE ENDPOINT
# ═══════════════════════════════════════════════════════════════

@router.get("/confluence/{symbol}/{tf}")
async def get_confluence_analysis(
    symbol: str,
    tf: str = "1d",
):
    """
    Get confluence analysis for a symbol.
    
    Returns:
    - technical_bias: Direction
    - confidence: Overall confidence
    - primary_confluence: Main confluence factors
    - secondary_confluence: Supporting factors
    - conflicts: Opposing signals
    """
    tf = normalize_tf(tf)
    builder = _get_builder()
    result = builder.build(symbol.upper(), tf)
    
    response = {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": tf,
        "technical_bias": result.technical_bias.value,
        "confidence": round(result.bias_confidence, 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    if result.top_setup:
        setup = result.top_setup
        response["primary_confluence"] = setup.primary_confluence.to_dict() if setup.primary_confluence else None
        response["secondary_confluence"] = [c.to_dict() for c in setup.secondary_confluence]
        response["conflicts"] = [c.to_dict() for c in setup.conflicts]
        response["patterns_detected"] = [p.pattern_type.value for p in setup.patterns]
        response["indicator_signals"] = [{"name": i.name, "direction": i.direction.value, "strength": i.strength} for i in setup.indicators]
        response["structure_state"] = setup.market_regime
        response["key_levels"] = [{"type": l.level_type.value, "price": l.price, "strength": l.strength} for l in setup.levels[:5]]
    else:
        response["primary_confluence"] = None
        response["secondary_confluence"] = []
        response["conflicts"] = []
        response["patterns_detected"] = []
        response["indicator_signals"] = []
        response["structure_state"] = "unknown"
        response["key_levels"] = []
    
    return response


# ═══════════════════════════════════════════════════════════════
# PATTERNS ENDPOINT
# ═══════════════════════════════════════════════════════════════

@router.get("/patterns/{symbol}/{tf}")
async def get_patterns(
    symbol: str,
    tf: str = "1d",
):
    """
    Get detected chart patterns.
    
    Returns list of patterns with:
    - type, direction, confidence
    - points (for drawing)
    - breakout_level, target, invalidation
    """
    tf = normalize_tf(tf)
    candles = _get_candles(symbol.upper(), tf)
    
    if len(candles) < 20:
        return {
            "ok": True,
            "symbol": symbol.upper(),
            "timeframe": tf,
            "patterns": [],
            "count": 0,
        }
    
    global _pattern_detector
    if _pattern_detector is None:
        _pattern_detector = get_pattern_detector()
    
    patterns = _pattern_detector.detect_all(candles)
    
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": tf,
        "patterns": [p.to_dict() for p in patterns],
        "count": len(patterns),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# LEVELS ENDPOINT
# ═══════════════════════════════════════════════════════════════

@router.get("/levels/{symbol}/{tf}")
async def get_levels(
    symbol: str,
    tf: str = "1d",
):
    """
    Get key price levels.
    
    Returns:
    - support levels
    - resistance levels
    - fibonacci levels
    - liquidity zones
    """
    tf = normalize_tf(tf)
    candles = _get_candles(symbol.upper(), tf)
    
    if len(candles) < 20:
        return {
            "ok": True,
            "symbol": symbol.upper(),
            "timeframe": tf,
            "levels": [],
            "count": 0,
        }
    
    global _level_engine
    if _level_engine is None:
        _level_engine = get_level_engine()
    
    levels = _level_engine.analyze_all(candles)
    
    # Group by type
    support = [l.to_dict() for l in levels if l.level_type.value == "support"]
    resistance = [l.to_dict() for l in levels if l.level_type.value == "resistance"]
    fib_levels = [l.to_dict() for l in levels if "fib" in l.level_type.value]
    liquidity = [l.to_dict() for l in levels if "liquidity" in l.level_type.value]
    
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": tf,
        "support": support,
        "resistance": resistance,
        "fib_levels": fib_levels,
        "liquidity_zones": liquidity,
        "all_levels": [l.to_dict() for l in levels],
        "count": len(levels),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# STRUCTURE ENDPOINT
# ═══════════════════════════════════════════════════════════════

@router.get("/structure/{symbol}/{tf}")
async def get_structure(
    symbol: str,
    tf: str = "1d",
):
    """
    Get market structure analysis.
    
    Returns:
    - structure_bias: Overall structure direction
    - structure_points: HH/HL/LH/LL points
    - bos_points: Break of structure events
    - choch_points: Change of character events
    """
    tf = normalize_tf(tf)
    candles = _get_candles(symbol.upper(), tf)
    
    if len(candles) < 20:
        return {
            "ok": True,
            "symbol": symbol.upper(),
            "timeframe": tf,
            "structure_bias": "neutral",
            "structure_points": [],
        }
    
    global _structure_engine
    if _structure_engine is None:
        _structure_engine = get_structure_engine()
    
    structure_points, bias, metadata = _structure_engine.analyze_all(candles)
    
    # Group by type
    hh_hl = [s.to_dict() for s in structure_points if s.structure_type.value in ["HH", "HL"]]
    lh_ll = [s.to_dict() for s in structure_points if s.structure_type.value in ["LH", "LL"]]
    bos = [s.to_dict() for s in structure_points if s.structure_type.value == "BOS"]
    choch = [s.to_dict() for s in structure_points if s.structure_type.value == "CHOCH"]
    
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": tf,
        "structure_bias": bias.value,
        "bullish_points": hh_hl,
        "bearish_points": lh_ll,
        "bos_events": bos,
        "choch_events": choch,
        "all_points": [s.to_dict() for s in structure_points],
        "metadata": metadata,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# INDICATORS ENDPOINT
# ═══════════════════════════════════════════════════════════════

@router.get("/indicators/{symbol}/{tf}")
async def get_indicators(
    symbol: str,
    tf: str = "1d",
):
    """
    Get indicator signals.
    
    Returns signals from:
    - EMA (20, 50, 200)
    - RSI
    - MACD
    - Bollinger Bands
    - Stochastic
    - ATR
    - OBV
    """
    tf = normalize_tf(tf)
    candles = _get_candles(symbol.upper(), tf)
    
    if len(candles) < 50:
        return {
            "ok": True,
            "symbol": symbol.upper(),
            "timeframe": tf,
            "signals": [],
            "count": 0,
        }
    
    global _indicator_engine
    if _indicator_engine is None:
        _indicator_engine = get_indicator_engine()
    
    signals = _indicator_engine.analyze_all(candles)
    
    # Group by direction
    bullish = [s.to_dict() for s in signals if s.direction.value == "bullish"]
    bearish = [s.to_dict() for s in signals if s.direction.value == "bearish"]
    neutral = [s.to_dict() for s in signals if s.direction.value == "neutral"]
    
    # Calculate overall indicator bias
    bullish_strength = sum(s.strength for s in signals if s.direction.value == "bullish")
    bearish_strength = sum(s.strength for s in signals if s.direction.value == "bearish")
    
    if bullish_strength > bearish_strength * 1.2:
        indicator_bias = "bullish"
    elif bearish_strength > bullish_strength * 1.2:
        indicator_bias = "bearish"
    else:
        indicator_bias = "neutral"
    
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": tf,
        "indicator_bias": indicator_bias,
        "bullish_signals": bullish,
        "bearish_signals": bearish,
        "neutral_signals": neutral,
        "all_signals": [s.to_dict() for s in signals],
        "count": len(signals),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════

@router.get("/status")
async def get_ta_status():
    """Health check for TA Setup Engine."""
    return {
        "ok": True,
        "module": "ta_setup_engine",
        "version": "1.0",
        "components": {
            "setup_builder": "active",
            "pattern_detector": "active",
            "indicator_engine": "active",
            "level_engine": "active",
            "structure_engine": "active",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# CANDLES ENDPOINT (for chart rendering)
# ═══════════════════════════════════════════════════════════════

@router.get("/candles/{symbol}")
async def get_candles_data(
    symbol: str,
    timeframe: str = Query("1d", description="Timeframe"),
    limit: int = Query(200, ge=10, le=500),
):
    """
    Get raw candle data for chart rendering.
    
    Returns OHLCV data that can be used directly by charting libraries.
    """
    candles = _get_candles(symbol.upper(), timeframe, limit)
    
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "candles": candles,
        "count": len(candles),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

