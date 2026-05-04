"""
Trend Model

Predicts continuation in strong directional markets.
Uses trend strength and momentum to size position.

FIX v2:
- Better momentum-based direction detection
- Conservative targets (3-10%)
- More accurate trend detection
"""

from typing import Dict, Any, Tuple


def predict_trend(inp: Dict[str, Any]) -> Tuple[str, float, float]:
    """
    Predict for trending market.
    
    Args:
        inp: Prediction input with price, structure, indicators
    
    Returns:
        (direction, target_price, confidence)
    """
    price = float(inp.get("price", 0))
    structure = inp.get("structure", {})
    indicators = inp.get("indicators", {})
    pattern = inp.get("pattern", {})
    
    # Key metrics
    trend = structure.get("trend", "flat")  # up, down, flat
    trend_strength = float(indicators.get("trend_strength", 0))
    momentum = float(indicators.get("momentum", 0))
    
    # Pattern can reinforce or counter trend
    pattern_dir = pattern.get("direction", "neutral")
    pattern_conf = float(pattern.get("confidence", 0))
    
    # === DIRECTION LOGIC (FIX v2: Use momentum as primary) ===
    direction = "neutral"
    direction_confidence = 0.0
    
    # 1. Strong momentum is primary signal
    if abs(momentum) > 0.02:
        if momentum > 0:
            direction = "bullish"
            direction_confidence = min(0.4, momentum * 5)
        else:
            direction = "bearish"
            direction_confidence = min(0.4, abs(momentum) * 5)
    
    # 2. Trend direction from structure
    elif trend == "up":
        direction = "bullish"
        direction_confidence = 0.35
    elif trend == "down":
        direction = "bearish"
        direction_confidence = 0.35
    
    # 3. Pattern as tiebreaker
    elif pattern_dir in ("bullish", "bearish") and pattern_conf > 0.5:
        direction = pattern_dir
        direction_confidence = pattern_conf * 0.3
    
    # 4. Trend strength as final fallback
    elif trend_strength > 0.02:
        direction = "bullish"
        direction_confidence = 0.25
    elif trend_strength < -0.02:
        direction = "bearish"
        direction_confidence = 0.25
    
    # === TARGET CALCULATION (FIX v2: Conservative 3-10%) ===
    abs_trend = abs(trend_strength)
    abs_momentum = abs(momentum)
    
    # Base move: 3-8% depending on strength
    base_move = 0.03 + abs_trend * 0.05
    
    # Momentum boost (capped)
    momentum_boost = min(abs_momentum * 1.5, 0.03)
    
    # Pattern confidence boost (small)
    if pattern_dir == direction and pattern_conf > 0.6:
        base_move += 0.01
    
    # Total move (capped at 10%)
    total_move = min(base_move + momentum_boost, 0.10)
    
    if direction == "bullish":
        target = price * (1 + total_move)
    elif direction == "bearish":
        target = price * (1 - total_move)
    else:
        target = price
    
    # === CONFIDENCE ===
    # Base: 50-80% depending on trend strength + momentum
    base_conf = 0.50 + direction_confidence
    
    # Momentum alignment boost
    if (direction == "bullish" and momentum > 0.01) or \
       (direction == "bearish" and momentum < -0.01):
        base_conf += min(abs_momentum * 0.5, 0.08)
    
    # Pattern alignment penalty
    if pattern_dir != "neutral" and pattern_dir != direction:
        base_conf -= pattern_conf * 0.1
    
    confidence = max(0.45, min(base_conf, 0.85))
    
    return direction, target, confidence
