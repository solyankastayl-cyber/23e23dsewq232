"""
Resolution Engine

Handles prediction lifecycle: pending → resolved/expired.
"""

import time
from typing import Dict, Any, Optional

from .resolution_rules import evaluate_prediction_result


def should_resolve_by_horizon(pred: Dict[str, Any], now_ts: int) -> bool:
    """Check if prediction has passed its horizon."""
    payload = pred.get("prediction_payload", {})
    horizon_days = int(payload.get("horizon_days", 5))
    created_at = int(pred.get("created_at", now_ts))
    
    return now_ts - created_at >= horizon_days * 86400


def try_early_resolution(
    pred: Dict[str, Any],
    current_price: float
) -> Optional[Dict[str, Any]]:
    """
    Check if prediction can be resolved early.
    
    Early resolution happens when:
    - Target is hit (correct_early)
    - Price moves strongly against prediction (wrong_early)
    
    Returns:
        Resolution dict if early resolution applies, None otherwise.
    """
    payload = pred.get("prediction_payload", {})
    direction = payload.get("direction", {}).get("label", "neutral")
    target = payload.get("target", {})
    
    start_price = float(target.get("start_price", 0))
    target_price = float(target.get("target_price", 0))
    
    if start_price == 0 or target_price == 0:
        return None
    
    resolution = evaluate_prediction_result(
        direction, start_price, target_price, current_price
    )
    
    # Only return early resolution for definitive outcomes
    if resolution["resolution_type"] in ("target_hit", "wrong_early"):
        resolution["resolution_type"] = (
            "correct_early" if resolution["result"] == "correct" 
            else "wrong_early"
        )
        return resolution
    
    return None


def resolve_at_horizon(
    pred: Dict[str, Any],
    current_price: float
) -> Dict[str, Any]:
    """
    Resolve prediction at horizon expiry.
    
    Returns full resolution dict.
    """
    payload = pred.get("prediction_payload", {})
    direction = payload.get("direction", {}).get("label", "neutral")
    target = payload.get("target", {})
    
    start_price = float(target.get("start_price", 0))
    target_price = float(target.get("target_price", 0))
    
    return evaluate_prediction_result(
        direction, start_price, target_price, current_price
    )
