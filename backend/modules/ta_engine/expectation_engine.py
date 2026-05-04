"""
Expectation Engine
==================

Computes expected outcomes based on historical performance.

WHAT THIS DOES:
- Expected move percentage
- Expected resolution time
- Confidence level based on sample size
- Label with drift context

OUTPUT:
{
    "move_pct": 4.8,
    "resolution_h": 26.0,
    "confidence": "MEDIUM",  # LOW/MEDIUM/HIGH based on samples
    "label": "Expected move ~4.8% in ~26h (improving recently)"
}
"""

from typing import Dict, Optional


def compute_expectation(
    stats: Optional[Dict],
    drift: Optional[Dict] = None,
) -> Dict:
    """
    Compute expected outcome based on historical stats.
    
    Args:
        stats: Historical stats from compute_weighted_stats()
        drift: Drift analysis from detect_drift()
    
    Returns:
        Expectation object with move_pct, resolution_h, confidence, label
    """
    if not stats:
        return {
            "move_pct": None,
            "resolution_h": None,
            "confidence": "NONE",
            "label": "No historical data for expectation",
            "risk_adjusted_move": None,
        }
    
    move = stats.get("avg_move_pct", 0)
    time_h = stats.get("avg_resolution_h", 0)
    samples = stats.get("samples", 0)
    winrate = stats.get("winrate", 0.5)
    best_move = stats.get("best_move_pct", move)
    worst_move = stats.get("worst_move_pct", 0)
    
    # Confidence based on sample size
    if samples >= 30:
        confidence = "HIGH"
    elif samples >= 15:
        confidence = "MEDIUM"
    elif samples >= 10:
        confidence = "LOW"
    else:
        confidence = "VERY_LOW"
    
    # Risk-adjusted expected move (winrate × positive + (1-winrate) × negative)
    # This gives a more realistic expectation
    risk_adjusted = (winrate * abs(move)) + ((1 - winrate) * worst_move)
    
    # Build label
    label_parts = []
    
    if move > 0:
        label_parts.append(f"Expected move ~{move}%")
    else:
        label_parts.append(f"Expected move ~{abs(move)}%")
    
    if time_h > 0:
        if time_h < 24:
            label_parts.append(f"in ~{int(time_h)}h")
        else:
            days = round(time_h / 24, 1)
            label_parts.append(f"in ~{days}d")
    
    label = " ".join(label_parts)
    
    # Add drift context
    if drift and drift.get("label") not in ("INSUFFICIENT", None, "STABLE"):
        drift_label = drift.get("label")
        if drift_label == "STRONG_IMPROVING":
            label += " (strongly improving)"
        elif drift_label == "IMPROVING":
            label += " (improving recently)"
        elif drift_label == "STRONG_DEGRADING":
            label += " (strongly degrading)"
        elif drift_label == "DEGRADING":
            label += " (degrading recently)"
    
    return {
        "move_pct": round(move, 2),
        "resolution_h": round(time_h, 1),
        "confidence": confidence,
        "label": label,
        "risk_adjusted_move": round(risk_adjusted, 2),
        "best_case": round(best_move, 2),
        "worst_case": round(worst_move, 2),
    }


def get_expectation_multiplier(expectation: Dict) -> float:
    """
    Get confidence multiplier based on expectation quality.
    
    High expected moves with good confidence boost the score.
    Low expected moves or poor confidence reduce it.
    
    Args:
        expectation: Expectation from compute_expectation()
    
    Returns:
        Multiplier (0.95 to 1.08)
    """
    if not expectation or expectation.get("move_pct") is None:
        return 1.0
    
    move = expectation.get("move_pct", 0)
    confidence = expectation.get("confidence", "LOW")
    
    mult = 1.0
    
    # Move size adjustment
    if move >= 6:
        mult += 0.05
    elif move >= 4:
        mult += 0.03
    elif move >= 2:
        mult += 0.01
    elif move <= 1:
        mult -= 0.02
    
    # Confidence adjustment
    if confidence == "HIGH":
        mult += 0.03
    elif confidence == "MEDIUM":
        mult += 0.01
    elif confidence == "VERY_LOW":
        mult -= 0.03
    
    # Clamp
    return round(max(0.95, min(1.08, mult)), 4)


def format_expectation_for_ui(expectation: Dict) -> Dict:
    """
    Format expectation for frontend display.
    
    Returns simplified object for UI rendering.
    """
    if not expectation or expectation.get("confidence") == "NONE":
        return {
            "show": False,
            "text": "No expectation data",
            "move": None,
            "time": None,
        }
    
    move = expectation.get("move_pct", 0)
    time_h = expectation.get("resolution_h", 0)
    confidence = expectation.get("confidence", "LOW")
    
    # Format time
    if time_h < 24:
        time_str = f"{int(time_h)}h"
    else:
        days = round(time_h / 24, 1)
        time_str = f"{days}d"
    
    # Confidence indicator
    conf_emoji = {
        "HIGH": "●●●",
        "MEDIUM": "●●○",
        "LOW": "●○○",
        "VERY_LOW": "○○○",
    }
    
    return {
        "show": True,
        "text": expectation.get("label", ""),
        "move": f"{move}%",
        "time": time_str,
        "confidence": confidence,
        "confidence_indicator": conf_emoji.get(confidence, "○○○"),
        "risk_adjusted": f"{expectation.get('risk_adjusted_move', move)}%",
    }
