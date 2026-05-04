"""
TA Interpreter

Reads TA Engine output and converts to PredictionInput.
Bridge between TA Engine and Prediction Engine.
"""

from typing import Dict, Optional, Any
from datetime import datetime

from .types import (
    PredictionInput,
    PatternInput,
    StructureInput,
    IndicatorsInput,
)


def interpret_ta_output(
    ta_output: Dict[str, Any],
    symbol: str,
    timeframe: str,
) -> PredictionInput:
    """
    Convert TA Engine output to PredictionInput.
    
    Handles various TA output formats from:
    - Pattern detectors
    - Structure analyzers
    - Indicator calculators
    """
    # Extract price
    price = _extract_price(ta_output)
    
    # Extract pattern
    pattern = _extract_pattern(ta_output)
    
    # Extract structure
    structure = _extract_structure(ta_output)
    
    # Extract indicators
    indicators = _extract_indicators(ta_output)
    
    return PredictionInput(
        symbol=symbol,
        timeframe=timeframe,
        price=price,
        pattern=pattern,
        structure=structure,
        indicators=indicators,
        timestamp=datetime.utcnow(),
    )


def _extract_price(ta_output: Dict) -> float:
    """Extract current price from TA output."""
    # Try various possible locations
    if "price" in ta_output:
        return float(ta_output["price"])
    if "current_price" in ta_output:
        return float(ta_output["current_price"])
    if "candles" in ta_output and ta_output["candles"]:
        return float(ta_output["candles"][-1].get("close", 0))
    if "close" in ta_output:
        return float(ta_output["close"])
    
    return 0.0


def _extract_pattern(ta_output: Dict) -> PatternInput:
    """Extract pattern information from TA output."""
    pattern_data = ta_output.get("pattern", {})
    
    # Handle nested pattern structure
    if isinstance(pattern_data, dict):
        pattern_type = pattern_data.get("type", pattern_data.get("name", "none"))
        direction = pattern_data.get("direction", "neutral")
        confidence = pattern_data.get("confidence", pattern_data.get("score", 0.0))
        
        # Normalize direction
        direction = _normalize_direction(direction)
        
        # Normalize confidence to 0-1
        if confidence > 1:
            confidence = confidence / 100
        
        return PatternInput(
            type=pattern_type.lower() if pattern_type else "none",
            direction=direction,
            confidence=float(confidence),
            breakout_level=pattern_data.get("breakout_level"),
            target_price=pattern_data.get("target_price", pattern_data.get("target")),
            bounds_top=pattern_data.get("bounds_top", pattern_data.get("resistance")),
            bounds_bottom=pattern_data.get("bounds_bottom", pattern_data.get("support")),
        )
    
    # No pattern data
    return PatternInput(
        type="none",
        direction="neutral",
        confidence=0.0,
    )


def _extract_structure(ta_output: Dict) -> StructureInput:
    """Extract market structure from TA output."""
    structure_data = ta_output.get("structure", {})
    
    if isinstance(structure_data, dict):
        state = structure_data.get("state", structure_data.get("phase", "range"))
        trend = structure_data.get("trend", structure_data.get("direction", "flat"))
        strength = structure_data.get("strength", structure_data.get("trend_strength", 0.5))
        
        # Normalize state
        state = _normalize_state(state)
        
        # Normalize trend
        trend = _normalize_trend(trend)
        
        # Normalize strength to 0-1
        if strength > 1:
            strength = strength / 100
        
        return StructureInput(
            state=state,
            trend=trend,
            trend_strength=float(strength),
        )
    
    # No structure data - default to range
    return StructureInput(
        state="range",
        trend="flat",
        trend_strength=0.5,
    )


def _extract_indicators(ta_output: Dict) -> IndicatorsInput:
    """Extract indicator signals from TA output."""
    indicators_data = ta_output.get("indicators", {})
    
    # Try to find momentum
    momentum = 0.0
    if "momentum" in indicators_data:
        momentum = float(indicators_data["momentum"])
    elif "macd" in indicators_data:
        macd = indicators_data["macd"]
        if isinstance(macd, dict):
            momentum = macd.get("histogram", 0) / 100  # Normalize
        else:
            momentum = 0.1 if macd == "bullish" else (-0.1 if macd == "bearish" else 0)
    
    # Clamp momentum to [-1, 1]
    momentum = max(-1.0, min(1.0, momentum))
    
    # Try to find trend strength
    trend_strength = indicators_data.get("trend_strength", 0.5)
    if isinstance(trend_strength, str):
        trend_strength = {"strong": 0.8, "moderate": 0.5, "weak": 0.3}.get(trend_strength.lower(), 0.5)
    trend_strength = max(0.0, min(1.0, float(trend_strength)))
    
    # Try to find volatility
    volatility = indicators_data.get("volatility", 0.3)
    if isinstance(volatility, str):
        volatility = {"high": 0.8, "medium": 0.5, "low": 0.2}.get(volatility.lower(), 0.3)
    volatility = max(0.0, min(1.0, float(volatility)))
    
    # RSI
    rsi = indicators_data.get("rsi")
    if rsi is not None:
        rsi = float(rsi)
    
    # MACD signal
    macd_signal = None
    if "macd" in indicators_data:
        macd = indicators_data["macd"]
        if isinstance(macd, dict):
            if macd.get("histogram", 0) > 0:
                macd_signal = "bullish"
            elif macd.get("histogram", 0) < 0:
                macd_signal = "bearish"
            else:
                macd_signal = "neutral"
        elif isinstance(macd, str):
            macd_signal = macd.lower()
    
    return IndicatorsInput(
        momentum=momentum,
        trend_strength=trend_strength,
        volatility=volatility,
        rsi=rsi,
        macd_signal=macd_signal,
    )


def _normalize_direction(direction: str) -> str:
    """Normalize direction to bullish/bearish/neutral."""
    if not direction:
        return "neutral"
    
    direction = str(direction).lower()
    
    if direction in ("bullish", "up", "long", "buy", "1"):
        return "bullish"
    if direction in ("bearish", "down", "short", "sell", "-1"):
        return "bearish"
    
    return "neutral"


def _normalize_state(state: str) -> str:
    """Normalize market state."""
    if not state:
        return "range"
    
    state = str(state).lower()
    
    if state in ("trend", "trending", "impulse"):
        return "trend"
    if state in ("range", "ranging", "consolidation", "sideways"):
        return "range"
    if state in ("compression", "squeeze", "contracting"):
        return "compression"
    if state in ("expansion", "expanding", "breakout"):
        return "expansion"
    
    return "range"


def _normalize_trend(trend: str) -> str:
    """Normalize trend to up/down/flat."""
    if not trend:
        return "flat"
    
    trend = str(trend).lower()
    
    if trend in ("up", "bullish", "uptrend", "rising"):
        return "up"
    if trend in ("down", "bearish", "downtrend", "falling"):
        return "down"
    
    return "flat"


def build_input_from_raw(
    symbol: str,
    timeframe: str,
    price: float,
    pattern_type: str = "none",
    pattern_direction: str = "neutral",
    pattern_confidence: float = 0.0,
    pattern_target: Optional[float] = None,
    structure_state: str = "range",
    structure_trend: str = "flat",
    trend_strength: float = 0.5,
    momentum: float = 0.0,
    volatility: float = 0.3,
) -> PredictionInput:
    """
    Build PredictionInput from raw values.
    
    Useful for API endpoints or testing.
    """
    return PredictionInput(
        symbol=symbol,
        timeframe=timeframe,
        price=price,
        pattern=PatternInput(
            type=pattern_type,
            direction=_normalize_direction(pattern_direction),
            confidence=pattern_confidence,
            target_price=pattern_target,
        ),
        structure=StructureInput(
            state=_normalize_state(structure_state),
            trend=_normalize_trend(structure_trend),
            trend_strength=trend_strength,
        ),
        indicators=IndicatorsInput(
            momentum=momentum,
            trend_strength=trend_strength,
            volatility=volatility,
        ),
        timestamp=datetime.utcnow(),
    )
