"""
Regime Router

Routes prediction to appropriate model based on detected regime.
"""

from typing import Dict, Any, Tuple

from .models.trend_model import predict_trend
from .models.range_model import predict_range
from .models.compression_model import predict_compression
from .models.high_vol_model import predict_high_vol


def route_prediction(inp: Dict[str, Any], regime: str) -> Tuple[str, float, float]:
    """
    Route to appropriate model based on regime.
    
    Args:
        inp: Prediction input dict
        regime: Detected regime
    
    Returns:
        (direction, target_price, confidence)
    """
    if regime == "trend":
        return predict_trend(inp)
    elif regime == "range":
        return predict_range(inp)
    elif regime == "compression":
        return predict_compression(inp)
    elif regime == "high_volatility":
        return predict_high_vol(inp)
    else:
        # Fallback to range (safest default)
        return predict_range(inp)


def apply_bias_fixes(
    direction: str,
    target: float, 
    confidence: float,
    inp: Dict[str, Any]
) -> Tuple[str, float, float]:
    """
    Apply anti-bias corrections after model prediction.
    
    Fixes:
    1. Strong pattern override
    2. Strong momentum override
    3. Confidence clamp
    """
    pattern = inp.get("pattern", {})
    indicators = inp.get("indicators", {})
    
    pattern_dir = pattern.get("direction", "neutral")
    pattern_conf = float(pattern.get("confidence", 0))
    momentum = float(indicators.get("momentum", 0))
    
    # FIX 1: Strong pattern override
    # If pattern has clear direction with high confidence, trust it
    if pattern_dir in ("bullish", "bearish") and pattern_conf > 0.7:
        if direction == "neutral":
            direction = pattern_dir
            confidence = max(confidence, 0.55)
    
    # FIX 2: Strong momentum override
    # Very strong momentum (>0.7) should align direction
    if abs(momentum) > 0.7:
        momentum_dir = "bullish" if momentum > 0 else "bearish"
        if direction == "neutral":
            direction = momentum_dir
        elif direction != momentum_dir:
            # Conflicting - reduce confidence
            confidence *= 0.85
    
    # FIX 3: Confidence boost for aligned signals
    if pattern_dir == direction and pattern_conf > 0.6:
        confidence = min(confidence + 0.08, 0.90)
    
    if (direction == "bullish" and momentum > 0.3) or \
       (direction == "bearish" and momentum < -0.3):
        confidence = min(confidence + 0.05, 0.90)
    
    return direction, target, confidence
