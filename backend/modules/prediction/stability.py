"""
Stability Score

Measures how "clean" the setup is.
High stability = strong pattern + clear trend + low noise.
"""

from typing import Dict, Any


def compute_stability_score(inp: Dict[str, Any]) -> float:
    """
    Compute stability score for prediction quality assessment.
    
    Components:
    - Pattern confidence (40%): Strong pattern = reliable signal
    - Trend strength (30%): Clear trend = easier to predict
    - Low volatility (30%): Less noise = more stable prediction
    
    Returns:
        Score 0.0-1.0 (higher = more stable setup)
    """
    pattern = inp.get("pattern", {})
    indicators = inp.get("indicators", {})
    
    pattern_conf = float(pattern.get("confidence", 0))
    trend_strength = float(indicators.get("trend_strength", 0))
    volatility = float(indicators.get("volatility_score", indicators.get("volatility", 0)))
    
    # Stability = strong pattern + trend - noise
    score = (
        pattern_conf * 0.4 +
        trend_strength * 0.3 +
        (1 - volatility) * 0.3
    )
    
    return round(max(0.0, min(score, 1.0)), 3)


def stability_label(score: float) -> str:
    """Map stability score to label."""
    if score >= 0.7:
        return "HIGH"
    elif score >= 0.5:
        return "MEDIUM"
    else:
        return "LOW"
