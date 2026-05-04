"""
Calibration Repository

Load and apply calibration to predictions.
"""

from typing import Dict, Any


def load_calibration(db) -> Dict[str, Any]:
    """
    Load current calibration from database.
    
    Returns empty/neutral calibration if none exists.
    """
    try:
        doc = db.prediction_calibration.find_one({"_id": "global"})
        if doc:
            return doc
    except Exception:
        pass
    
    # Return neutral calibration
    return {
        "regime_weights": {},
        "model_weights": {},
        "target_multipliers": {},
        "confidence_bias": {},
    }


def apply_calibration(
    pred: Dict[str, Any],
    calibration: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Apply calibration adjustments to prediction.
    
    Modifies:
    - confidence (regime_weight * model_weight + bias)
    - target_price (target_multiplier)
    
    Returns:
        Modified prediction dict
    """
    regime = pred.get("regime", "")
    model = pred.get("model", "")
    
    # Get calibration values with defaults
    regime_w = calibration.get("regime_weights", {}).get(regime, 1.0)
    model_w = calibration.get("model_weights", {}).get(model, 1.0)
    target_m = calibration.get("target_multipliers", {}).get(regime, 1.0)
    conf_bias = calibration.get("confidence_bias", {}).get(regime, 0.0)
    
    # Apply confidence correction
    conf = float(pred.get("confidence", {}).get("value", 0))
    conf = conf * regime_w * model_w
    conf = conf + conf_bias
    conf = max(0.0, min(conf, 0.90))
    
    # Apply target correction
    target = pred.get("target", {})
    start_price = float(target.get("start_price", 0))
    target_price = float(target.get("target_price", 0))
    
    if start_price > 0 and target_price > 0:
        delta = target_price - start_price
        target_price = start_price + delta * target_m
        expected_return = (target_price - start_price) / start_price
        
        pred["target"]["target_price"] = round(target_price, 2)
        pred["target"]["expected_return"] = round(expected_return, 4)
    
    pred["confidence"]["value"] = round(conf, 3)
    
    # Add calibration metadata
    pred["calibration_applied"] = {
        "regime_weight": regime_w,
        "model_weight": model_w,
        "target_multiplier": target_m,
        "confidence_bias": conf_bias,
    }
    
    return pred
