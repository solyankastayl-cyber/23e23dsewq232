"""
Compression Model

Predicts breakout direction from compression patterns.
Triangles, wedges, pennants → anticipate breakout.

FIX v2: 
- Reduced target multiplier (0.85x) - was 12-15%, now 5-10%
- Better direction detection using market context
- Balanced bullish/bearish bias
"""

from typing import Dict, Any, Tuple


def predict_compression(inp: Dict[str, Any]) -> Tuple[str, float, float]:
    """
    Predict for compression/consolidation market.
    
    Args:
        inp: Prediction input with price, pattern, indicators
    
    Returns:
        (direction, target_price, confidence)
    """
    price = float(inp.get("price", 0))
    pattern = inp.get("pattern", {})
    indicators = inp.get("indicators", {})
    structure = inp.get("structure", {})
    
    # Pattern signals
    pattern_type = pattern.get("type", "none")
    pattern_dir = pattern.get("direction", "neutral")
    pattern_conf = float(pattern.get("confidence", 0.5))
    
    # Momentum (often breaks in momentum direction)
    momentum = float(indicators.get("momentum", 0))
    
    # Prior trend (continuation bias)
    prior_trend = structure.get("trend", "flat")
    
    # Trend strength from structure
    trend_strength = float(indicators.get("trend_strength", 0.5))
    
    # === DIRECTION LOGIC (FIX v2: Better balance) ===
    direction = "neutral"
    direction_confidence = 0.0
    
    # 1. STRONG momentum signal (primary)
    if abs(momentum) > 0.03:  # 3% move in recent candles
        if momentum > 0:
            direction = "bullish"
            direction_confidence = min(0.3, momentum * 5)
        else:
            direction = "bearish"
            direction_confidence = min(0.3, abs(momentum) * 5)
    
    # 2. Pattern direction (secondary)
    if pattern_dir in ("bullish", "bearish") and pattern_conf > 0.4:
        if direction == "neutral":
            direction = pattern_dir
            direction_confidence = pattern_conf * 0.3
        elif direction == pattern_dir:
            direction_confidence += pattern_conf * 0.15
        # Conflicting signals - reduce confidence
    
    # 3. Pattern type signals
    if pattern_type in ("ascending_triangle", "rising_wedge", "inv_head_shoulders"):
        if direction == "neutral":
            direction = "bullish"
            direction_confidence = 0.25
        elif direction == "bullish":
            direction_confidence += 0.1
    elif pattern_type in ("descending_triangle", "falling_wedge", "head_shoulders"):
        if direction == "neutral":
            direction = "bearish"
            direction_confidence = 0.25
        elif direction == "bearish":
            direction_confidence += 0.1
    
    # 4. Prior trend continuation (weak signal)
    if direction == "neutral":
        if prior_trend == "up" and trend_strength > 0.02:
            direction = "bullish"
            direction_confidence = 0.15
        elif prior_trend == "down" and trend_strength < -0.02:
            direction = "bearish"
            direction_confidence = 0.15
        else:
            # No clear direction - stay neutral
            direction = "neutral"
    
    # === TARGET CALCULATION (FIX v2: Reduced multiplier 0.85x) ===
    # Conservative targets: 3-8% (was 4-15%)
    base_move = 0.03 + pattern_conf * 0.05  # 3-8% range
    
    # Apply 0.85x multiplier for compression regime
    base_move *= 0.85
    
    # Slight boost for very tight compression
    volatility = float(indicators.get("volatility_score", 0.5))
    if volatility < 0.3:
        base_move *= 1.15  # Max ~9% for tight compression
    
    # Cap at 10%
    total_move = min(base_move, 0.10)
    
    if direction == "bullish":
        target = price * (1 + total_move)
    elif direction == "bearish":
        target = price * (1 - total_move)
    else:
        target = price
    
    # === CONFIDENCE (FIX v2: More conservative) ===
    base_conf = 0.40 + direction_confidence
    
    # Momentum alignment boost
    if (direction == "bullish" and momentum > 0.01) or \
       (direction == "bearish" and momentum < -0.01):
        base_conf += 0.05
    
    # Clear pattern type boost
    if pattern_type in ("ascending_triangle", "descending_triangle", 
                        "symmetrical_triangle", "pennant", "wedge",
                        "head_shoulders", "inv_head_shoulders"):
        base_conf += 0.05
    
    # Cap confidence lower for compression (uncertain regime)
    confidence = max(0.35, min(base_conf, 0.70))
    
    return direction, target, confidence
