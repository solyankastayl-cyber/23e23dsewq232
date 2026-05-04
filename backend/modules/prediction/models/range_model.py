"""
Range Model

Predicts mean reversion within established bounds.
Buys near support, sells near resistance.
"""

from typing import Dict, Any, Tuple


def predict_range(inp: Dict[str, Any]) -> Tuple[str, float, float]:
    """
    Predict for range-bound market.
    
    Args:
        inp: Prediction input with price, pattern bounds, indicators
    
    Returns:
        (direction, target_price, confidence)
    """
    price = float(inp.get("price", 0))
    pattern = inp.get("pattern", {})
    indicators = inp.get("indicators", {})
    structure = inp.get("structure", {})
    
    # Get range bounds
    bounds = pattern.get("bounds", {})
    top = bounds.get("top") or bounds.get("resistance")
    bottom = bounds.get("bottom") or bounds.get("support")
    
    # Fallback: use structure levels if no pattern bounds
    if not top or not bottom:
        levels = structure.get("levels", {})
        top = levels.get("resistance") or price * 1.05
        bottom = levels.get("support") or price * 0.95
    
    # Ensure valid bounds
    top = float(top) if top else price * 1.05
    bottom = float(bottom) if bottom else price * 0.95
    
    if top <= bottom:
        # Invalid bounds, use defaults
        top = price * 1.05
        bottom = price * 0.95
    
    # Calculate position in range (0 = at bottom, 1 = at top)
    range_size = top - bottom
    if range_size > 0:
        position_in_range = (price - bottom) / range_size
    else:
        position_in_range = 0.5
    
    # Clamp to 0-1
    position_in_range = max(0, min(1, position_in_range))
    
    # === DIRECTION LOGIC ===
    # Near bottom (< 0.35) → bullish to top
    # Near top (> 0.65) → bearish to bottom
    # Middle → use pattern or momentum
    
    momentum = float(indicators.get("momentum", 0))
    pattern_dir = pattern.get("direction", "neutral")
    pattern_conf = float(pattern.get("confidence", 0.5))
    
    if position_in_range < 0.35:
        direction = "bullish"
        target = top * 0.98  # Slightly below resistance
    elif position_in_range > 0.65:
        direction = "bearish"
        target = bottom * 1.02  # Slightly above support
    else:
        # Middle zone - use pattern first, then momentum
        if pattern_dir in ("bullish", "bearish") and pattern_conf > 0.5:
            direction = pattern_dir
            # Target based on pattern direction
            if direction == "bullish":
                target = top * 0.95
            else:
                target = bottom * 1.05
        elif momentum > 0.3:
            direction = "bullish"
            target = top * 0.95
        elif momentum < -0.3:
            direction = "bearish"
            target = bottom * 1.05
        else:
            # Truly neutral - small move toward center
            direction = "neutral"
            mid = (top + bottom) / 2
            # Target 50% move toward mid
            target = price + (mid - price) * 0.5
    
    # === CONFIDENCE ===
    # Higher confidence at extremes
    distance_from_center = abs(position_in_range - 0.5) * 2  # 0-1
    
    # Base confidence: 50-70%
    base_conf = 0.50 + distance_from_center * 0.20
    
    # Range age/validity boost (if pattern is clear)
    pattern_conf = float(pattern.get("confidence", 0.5))
    base_conf += pattern_conf * 0.1
    
    confidence = max(0.40, min(base_conf, 0.75))
    
    return direction, target, confidence
