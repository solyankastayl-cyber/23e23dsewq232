"""
Prediction Filter

Removes weak signals that shouldn't be published.
"""

from typing import Dict, Any


# Minimum thresholds
MIN_CONFIDENCE = 0.55
MIN_RETURN = 0.02  # 2%
MIN_STABILITY = 0.5


def is_prediction_valid(prediction: Dict[str, Any]) -> bool:
    """
    Check if prediction meets quality thresholds.
    
    Filters out:
    - Low confidence predictions
    - Tiny expected returns
    - Unstable setups
    
    Returns:
        True if prediction is publishable
    """
    confidence = float(prediction.get("confidence", {}).get("value", 0))
    expected_return = abs(float(
        prediction.get("target", {}).get("expected_return", 0)
    ))
    stability = float(prediction.get("stability", 0))
    
    # Must pass ALL thresholds
    if confidence < MIN_CONFIDENCE:
        return False
    
    if expected_return < MIN_RETURN:
        return False
    
    if stability < MIN_STABILITY:
        return False
    
    return True


def get_rejection_reason(prediction: Dict[str, Any]) -> str:
    """Get reason why prediction was rejected."""
    confidence = float(prediction.get("confidence", {}).get("value", 0))
    expected_return = abs(float(
        prediction.get("target", {}).get("expected_return", 0)
    ))
    stability = float(prediction.get("stability", 0))
    
    reasons = []
    
    if confidence < MIN_CONFIDENCE:
        reasons.append(f"low_confidence ({confidence:.0%} < {MIN_CONFIDENCE:.0%})")
    
    if expected_return < MIN_RETURN:
        reasons.append(f"low_return ({expected_return:.1%} < {MIN_RETURN:.0%})")
    
    if stability < MIN_STABILITY:
        reasons.append(f"low_stability ({stability:.2f} < {MIN_STABILITY})")
    
    return "; ".join(reasons) if reasons else "valid"
