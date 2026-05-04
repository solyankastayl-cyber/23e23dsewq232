"""
Resolution Rules

Defines how predictions are evaluated against actual outcomes.
"""

from typing import Dict, Any


def compute_error_pct(actual_price: float, target_price: float) -> float:
    """Compute percentage error between actual and target."""
    if target_price == 0:
        return 1.0
    return abs(actual_price - target_price) / abs(target_price)


def evaluate_prediction_result(
    direction: str,
    start_price: float,
    target_price: float,
    actual_price: float
) -> Dict[str, Any]:
    """
    Evaluate prediction result based on actual price.
    
    Args:
        direction: "bullish", "bearish", or "neutral"
        start_price: Price when prediction was made
        target_price: Predicted target price
        actual_price: Actual price at resolution
    
    Returns:
        Resolution dict with result, resolution_type, error_pct, etc.
    """
    error_pct = compute_error_pct(actual_price, target_price)
    
    if direction == "bullish":
        direction_ok = actual_price >= start_price
        hit_target = actual_price >= target_price
        # Invalidation: price dropped more than 3% below start
        hit_invalidation = actual_price < start_price * 0.97
        
    elif direction == "bearish":
        direction_ok = actual_price <= start_price
        hit_target = actual_price <= target_price
        # Invalidation: price rose more than 3% above start
        hit_invalidation = actual_price > start_price * 1.03
        
    else:  # neutral
        direction_ok = False
        hit_target = False
        hit_invalidation = False
    
    # Determine result
    if hit_target:
        result = "correct"
        resolution_type = "target_hit"
    elif direction_ok and error_pct < 0.05:
        # Direction was right, close to target
        result = "partial"
        resolution_type = "horizon_expired"
    elif hit_invalidation:
        result = "wrong"
        resolution_type = "wrong_early"
    else:
        result = "wrong"
        resolution_type = "horizon_expired"
    
    return {
        "result": result,
        "resolution_type": resolution_type,
        "actual_price": round(actual_price, 2),
        "error_pct": round(error_pct, 4),
        "hit_target": hit_target,
        "hit_invalidation": hit_invalidation,
        "direction_ok": direction_ok,
    }
