"""
Ranking 2.0

Score formula that considers stability, not just confidence.
"""

from typing import Dict, Any


def compute_score(prediction: Dict[str, Any]) -> float:
    """
    Compute prediction score for ranking.
    
    Formula:
        score = confidence * 0.4 + |return| * 2.0 + stability * 0.6
    
    This balances:
    - Confidence (40%): Model's certainty
    - Return (amplified): Reward bigger moves
    - Stability (60% weight relative to conf): Setup quality
    
    Returns:
        Score value (higher = better prediction)
    """
    confidence = float(prediction.get("confidence", {}).get("value", 0))
    expected_return = abs(float(
        prediction.get("target", {}).get("expected_return", 0)
    ))
    stability = float(prediction.get("stability", 0))
    
    score = (
        confidence * 0.4 +
        expected_return * 2.0 +
        stability * 0.6
    )
    
    return round(score, 4)


def compute_score_breakdown(prediction: Dict[str, Any]) -> Dict[str, float]:
    """Get score with component breakdown."""
    confidence = float(prediction.get("confidence", {}).get("value", 0))
    expected_return = abs(float(
        prediction.get("target", {}).get("expected_return", 0)
    ))
    stability = float(prediction.get("stability", 0))
    
    conf_contrib = confidence * 0.4
    ret_contrib = expected_return * 2.0
    stab_contrib = stability * 0.6
    
    return {
        "total": round(conf_contrib + ret_contrib + stab_contrib, 4),
        "confidence_contrib": round(conf_contrib, 4),
        "return_contrib": round(ret_contrib, 4),
        "stability_contrib": round(stab_contrib, 4),
    }
