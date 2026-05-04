"""
High Volatility Model

Predicts in extreme volatility conditions.
Momentum-driven, wider targets, careful confidence.
"""

from typing import Dict, Any, Tuple


def predict_high_vol(inp: Dict[str, Any]) -> Tuple[str, float, float]:
    """
    Predict for high volatility market.
    
    Args:
        inp: Prediction input with price, indicators
    
    Returns:
        (direction, target_price, confidence)
    """
    price = float(inp.get("price", 0))
    indicators = inp.get("indicators", {})
    structure = inp.get("structure", {})
    pattern = inp.get("pattern", {})
    
    # Key metrics
    momentum = float(indicators.get("momentum", 0))
    volatility = float(indicators.get("volatility_score", 0.7))
    trend_strength = float(indicators.get("trend_strength", 0))
    
    # Recent price action
    trend = structure.get("trend", "flat")
    pattern_dir = pattern.get("direction", "neutral")
    
    # === DIRECTION LOGIC ===
    # In high vol, momentum is king
    
    if abs(momentum) > 0.5:
        # Strong momentum → follow it
        direction = "bullish" if momentum > 0 else "bearish"
    elif trend in ("up", "down"):
        # Trend direction as fallback
        direction = "bullish" if trend == "up" else "bearish"
    elif pattern_dir != "neutral":
        # Pattern as last resort
        direction = pattern_dir
    else:
        direction = "neutral"
    
    # === TARGET CALCULATION ===
    # High vol = bigger moves: 5-20%
    base_move = 0.05 + abs(momentum) * 0.12
    
    # Volatility multiplier
    vol_mult = 0.8 + volatility * 0.4  # 0.8-1.2x
    
    total_move = base_move * vol_mult
    
    # Cap at 20% (high vol can move fast)
    total_move = min(total_move, 0.20)
    
    if direction == "bullish":
        target = price * (1 + total_move)
    elif direction == "bearish":
        target = price * (1 - total_move)
    else:
        target = price
    
    # === CONFIDENCE ===
    # High vol = lower base confidence (unpredictable)
    # But strong momentum increases it
    
    base_conf = 0.45
    
    # Momentum conviction
    base_conf += min(abs(momentum) * 0.35, 0.25)
    
    # Trend alignment
    if (direction == "bullish" and trend == "up") or \
       (direction == "bearish" and trend == "down"):
        base_conf += 0.05
    
    # High vol penalty (uncertainty)
    base_conf -= volatility * 0.1
    
    confidence = max(0.35, min(base_conf, 0.80))
    
    return direction, target, confidence
