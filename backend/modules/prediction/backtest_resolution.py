"""
Backtest Resolution V2

Resolves predictions against future candles (NO LEAKAGE).

CRITICAL RULE:
- Prediction sees ONLY candles BEFORE anchor_time
- Resolution uses ONLY candles AFTER anchor_time

PHASE 2.1 FIX:
- Regime-specific invalidation thresholds:
  - trend: 5%
  - range: 3.5%
  - compression: 6%
  - high_volatility: 8%
"""

from typing import Dict, Any, List


# Regime-specific invalidation thresholds
INVALIDATION_THRESHOLDS = {
    "trend": 0.05,      # 5% - trends can have pullbacks
    "range": 0.035,     # 3.5% - range should stay in bounds
    "compression": 0.06, # 6% - compression breakouts can be volatile
    "high_volatility": 0.08,  # 8% - high vol needs more room
    "default": 0.05,    # 5% default
}


def resolve_on_future(
    pred: Dict[str, Any],
    future_candles: List[Dict[str, Any]],
    regime: str = None
) -> Dict[str, Any]:
    """
    Resolve prediction using only future candles.
    
    Args:
        pred: Prediction payload with direction, target
        future_candles: Candles AFTER anchor_time (no leakage!)
        regime: Market regime for invalidation threshold (optional)
    
    Returns:
        Resolution dict with result, resolution_type, actual_price, error_pct
    """
    if not future_candles:
        return {
            "result": "wrong",
            "resolution_type": "no_future_data",
            "actual_price": 0,
            "error_pct": 1.0
        }
    
    direction = pred.get("direction", {}).get("label", "neutral")
    target_info = pred.get("target", {})
    start = float(target_info.get("start_price", 0))
    target = float(target_info.get("target_price", 0))
    
    if start == 0 or target == 0:
        return {
            "result": "wrong",
            "resolution_type": "invalid_prediction",
            "actual_price": 0,
            "error_pct": 1.0
        }
    
    # Get regime-specific invalidation threshold
    if regime is None:
        regime = pred.get("regime", "default")
    invalidation_threshold = INVALIDATION_THRESHOLDS.get(regime, INVALIDATION_THRESHOLDS["default"])
    
    hit_target = False
    hit_invalidation = False
    final_price = float(future_candles[-1].get("close", start))
    best_price = start  # Track best price achieved in direction
    
    # Normalize direction (V2 uses long/short, V3 uses bullish/bearish)
    direction_normalized = direction.lower()
    if direction_normalized in ["long", "bullish"]:
        is_bullish = True
    elif direction_normalized in ["short", "bearish"]:
        is_bullish = False
    else:
        is_bullish = None
    
    # Walk through future candles
    for candle in future_candles:
        high = float(candle.get("high", 0))
        low = float(candle.get("low", 0))
        
        if is_bullish:
            # Track best price (highest high)
            if high > best_price:
                best_price = high
            
            # Check target hit (price went up to target)
            if high >= target:
                hit_target = True
                final_price = target
                break
            
            # Check invalidation with regime-specific threshold
            invalidation_level = start * (1 - invalidation_threshold)
            if low < invalidation_level:
                hit_invalidation = True
                final_price = low
                break
        
        elif not is_bullish:
            # Track best price (lowest low)
            if low < best_price or best_price == start:
                best_price = low
            
            # Check target hit (price went down to target)
            if low <= target:
                hit_target = True
                final_price = target
                break
            
            # Check invalidation with regime-specific threshold
            invalidation_level = start * (1 + invalidation_threshold)
            if high > invalidation_level:
                hit_invalidation = True
                final_price = high
                break
    
    # Calculate error
    error_pct = abs(final_price - target) / target if target else 1.0
    
    # Determine result
    if hit_target:
        return {
            "result": "correct",
            "resolution_type": "target_hit",
            "actual_price": round(final_price, 2),
            "error_pct": round(error_pct, 4),
            "best_price": round(best_price, 2),
        }
    
    if hit_invalidation:
        return {
            "result": "wrong",
            "resolution_type": "wrong_early",
            "actual_price": round(final_price, 2),
            "error_pct": round(error_pct, 4),
            "invalidation_threshold": invalidation_threshold,
            "best_price": round(best_price, 2),
        }
    
    # Horizon expired - check if direction was right
    if is_bullish:
        direction_ok = final_price >= start
        # Calculate how much of the expected move was achieved
        expected_move = target - start
        actual_move = final_price - start
        best_move = best_price - start
        move_pct = actual_move / expected_move if expected_move != 0 else 0
        best_move_pct = best_move / expected_move if expected_move != 0 else 0
    elif is_bullish == False:  # Explicitly check False (not None)
        direction_ok = final_price <= start
        expected_move = start - target
        actual_move = start - final_price
        best_move = start - best_price
        move_pct = actual_move / expected_move if expected_move != 0 else 0
        best_move_pct = best_move / expected_move if expected_move != 0 else 0
    else:
        direction_ok = False
        move_pct = 0
        best_move_pct = 0
    
    # Partial: direction was right AND achieved at least 30% of expected move
    # OR best price achieved at least 50% of expected move
    if direction_ok and (move_pct >= 0.3 or best_move_pct >= 0.5):
        result = "partial"
    elif direction_ok and move_pct >= 0.1:
        # Direction was right but move was minimal
        result = "partial"
    else:
        result = "wrong"
    
    return {
        "result": result,
        "resolution_type": "horizon_expired",
        "actual_price": round(final_price, 2),
        "error_pct": round(error_pct, 4),
        "move_achieved_pct": round(move_pct, 3),
        "best_move_pct": round(best_move_pct, 3),
        "best_price": round(best_price, 2),
    }
