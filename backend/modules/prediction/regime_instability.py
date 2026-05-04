"""
Regime Instability Detector

Detects when regimes are unstable (predictions flip-flopping).
"""

from typing import Dict, Any, List


def compute_regime_instability(predictions: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Compute instability score for each regime.
    
    High instability = predictions in this regime keep changing direction.
    This suggests the regime detection may be unreliable.
    
    Returns:
        Dict mapping regime to instability score (0.0-1.0)
    """
    by_regime = {}
    
    for p in predictions:
        regime = p.get("regime") or p.get("prediction_payload", {}).get("regime")
        if not regime:
            continue
        by_regime.setdefault(regime, []).append(p)
    
    result = {}
    
    for regime, items in by_regime.items():
        ordered = sorted(items, key=lambda x: x.get("created_at", 0))
        
        if len(ordered) < 10:
            result[regime] = 0.0
            continue
        
        # Count direction changes
        direction_changes = 0
        prev_dir = None
        
        for p in ordered:
            payload = p.get("prediction_payload", {})
            cur_dir = payload.get("direction", {}).get("label")
            
            if prev_dir and cur_dir and cur_dir != prev_dir:
                direction_changes += 1
            prev_dir = cur_dir
        
        # Instability = ratio of changes to predictions
        instability = direction_changes / max(1, len(ordered) - 1)
        result[regime] = round(instability, 4)
    
    return result
