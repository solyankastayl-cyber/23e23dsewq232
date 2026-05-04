"""
Prediction Finalizer

Applies full P2 pipeline:
1. Stability score
2. Regime calibration
3. Anti-overconfidence
4. Filter validation
5. Ranking score
"""

from typing import Dict, Any

from .stability import compute_stability_score, stability_label
from .regime_calibration import apply_regime_weight
from .anti_overconfidence import apply_anti_overconfidence
from .filter import is_prediction_valid, get_rejection_reason
from .ranking_v2 import compute_score


def finalize_prediction(
    inp: Dict[str, Any],
    base_pred: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Apply full Decision Engine pipeline to prediction.
    
    Pipeline:
    1. Compute stability score
    2. Apply regime weight to confidence
    3. Apply anti-overconfidence adjustments
    4. Check if prediction passes filter
    5. Compute ranking score
    
    Args:
        inp: Original prediction input (TA data)
        base_pred: Base prediction from model
    
    Returns:
        Finalized prediction with stability, valid, score fields
    """
    regime = base_pred.get("regime", "range")
    
    # 1. Stability score
    stability = compute_stability_score(inp)
    base_pred["stability"] = stability
    base_pred["stability_label"] = stability_label(stability)
    
    # 2. Confidence pipeline
    conf = float(base_pred.get("confidence", {}).get("value", 0))
    
    # 2a. Regime weight
    conf = apply_regime_weight(conf, regime)
    
    # 2b. Anti-overconfidence
    conf = apply_anti_overconfidence(conf, stability, regime)
    
    # Update confidence
    base_pred["confidence"]["value"] = round(conf, 3)
    base_pred["confidence"]["label"] = _confidence_label(conf)
    
    # 3. Validation
    base_pred["valid"] = is_prediction_valid(base_pred)
    if not base_pred["valid"]:
        base_pred["rejection_reason"] = get_rejection_reason(base_pred)
    
    # 4. Ranking score
    base_pred["score"] = compute_score(base_pred)
    
    return base_pred


def _confidence_label(conf: float) -> str:
    """Map confidence to label."""
    if conf >= 0.75:
        return "HIGH"
    elif conf >= 0.55:
        return "MEDIUM"
    else:
        return "LOW"
