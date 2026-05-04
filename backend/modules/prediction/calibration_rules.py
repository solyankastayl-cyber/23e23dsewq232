"""
Calibration Rules

Converts statistics into calibration weights and adjustments.
"""

from typing import Dict, Any


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value to range [lo, hi]."""
    return max(lo, min(value, hi))


def stats_to_weight(stats: Dict[str, Any]) -> float:
    """
    Convert stats to regime/model weight.
    
    Higher accuracy → higher weight
    Lower error → higher weight
    
    Returns weight in range [0.8, 1.15]
    """
    count = stats.get("count", 0)
    if count < 20:
        # Not enough data, use neutral weight
        return 1.0
    
    acc = stats.get("accuracy", 0)
    err = stats.get("avg_error", 0.1)
    
    weight = 1.0
    
    # Accuracy impact
    if acc >= 0.62:
        weight += 0.08
    elif acc <= 0.45:
        weight -= 0.08
    elif acc <= 0.52:
        weight -= 0.04
    
    # Error impact
    if err <= 0.03:
        weight += 0.04
    elif err >= 0.08:
        weight -= 0.04
    elif err >= 0.06:
        weight -= 0.02
    
    return round(clamp(weight, 0.8, 1.15), 3)


def stats_to_target_multiplier(stats: Dict[str, Any]) -> float:
    """
    Convert stats to target price multiplier.
    
    High error → reduce target (too aggressive)
    Low error → can be slightly more aggressive
    
    Returns multiplier in range [0.85, 1.05]
    """
    count = stats.get("count", 0)
    if count < 20:
        return 1.0
    
    err = stats.get("avg_error", 0.05)
    
    if err >= 0.10:
        return 0.85  # Very aggressive targets, cut significantly
    if err >= 0.06:
        return 0.92  # Somewhat aggressive
    if err <= 0.03:
        return 1.03  # Conservative, can push slightly
    
    return 1.0


def stats_to_confidence_bias(stats: Dict[str, Any]) -> float:
    """
    Convert stats to confidence bias adjustment.
    
    If confidence >> accuracy → reduce confidence (overconfident)
    If confidence << accuracy → increase confidence (underconfident)
    
    Returns bias in range [-0.08, +0.08]
    """
    count = stats.get("count", 0)
    if count < 20:
        return 0.0
    
    acc = stats.get("accuracy", 0)
    conf = stats.get("avg_confidence", 0)
    
    # Delta: positive means accuracy > confidence (underconfident)
    delta = acc - conf
    
    # Apply 25% of delta as bias
    bias = delta * 0.25
    
    return round(clamp(bias, -0.08, 0.08), 3)
