"""
Decision Adjustment Engine
===========================

Final layer that combines all factors into one decision score.

INPUTS:
- Base confidence from pattern detection
- Context fit score (Pattern × Context)
- Historical fit score (Pattern × Context × History)
- Drift analysis (improving/degrading)
- Expectation (expected move/time)

OUTPUT:
- Final probability score (0.05 - 0.95)
- Tradeable status
- Decision breakdown

MULTIPLIER CHAIN:
base × context × historical × drift × expectation = final
"""

from typing import Dict, Optional


def clamp(value: float, lo: float = 0.05, hi: float = 0.95) -> float:
    """Clamp value to range."""
    return max(lo, min(value, hi))


def apply_drift_multiplier(base_score: float, drift: Optional[Dict]) -> float:
    """
    Apply drift adjustment to score.
    
    IMPROVING: +5% boost (recent performance better)
    DEGRADING: -7% penalty (edge may be dying)
    STRONG variants: ±10%
    
    Args:
        base_score: Current score
        drift: Drift analysis from detect_drift()
    
    Returns:
        Adjusted score
    """
    if not drift or drift.get("label") in ("INSUFFICIENT", None):
        return base_score
    
    label = drift.get("label")
    
    # Multipliers based on drift direction
    multipliers = {
        "STRONG_IMPROVING": 1.10,
        "IMPROVING": 1.05,
        "STABLE": 1.0,
        "DEGRADING": 0.93,
        "STRONG_DEGRADING": 0.88,
    }
    
    mult = multipliers.get(label, 1.0)
    
    return round(base_score * mult, 4)


def apply_expectation_multiplier(base_score: float, expectation: Optional[Dict]) -> float:
    """
    Apply expectation adjustment to score.
    
    High expected moves with good confidence = boost
    Low expected moves or poor confidence = penalty
    
    Args:
        base_score: Current score
        expectation: Expectation from compute_expectation()
    
    Returns:
        Adjusted score
    """
    if not expectation or expectation.get("move_pct") is None:
        return base_score
    
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
    
    return round(base_score * mult, 4)


def finalize_probability_score(
    base_confidence: float,
    context_fit_score: Optional[float],
    historical_fit_score: Optional[float],
    drift: Optional[Dict],
    expectation: Optional[Dict],
) -> Dict:
    """
    Final probability calculation combining all factors.
    
    CHAIN:
    base × context × historical × drift × expectation = final
    
    Args:
        base_confidence: Base pattern confidence (0-1)
        context_fit_score: From context fit (0.3-1.5)
        historical_fit_score: From historical fit (0.85-1.15)
        drift: Drift analysis
        expectation: Expectation data
    
    Returns:
        Final decision with score, breakdown, and tradeable status
    """
    # Start with base
    score = float(base_confidence)
    
    # Track adjustments for breakdown
    breakdown = {
        "base": round(base_confidence, 4),
        "after_context": None,
        "after_historical": None,
        "after_drift": None,
        "after_expectation": None,
    }
    
    # Apply context fit
    ctx_mult = float(context_fit_score or 1.0)
    score *= ctx_mult
    breakdown["after_context"] = round(score, 4)
    breakdown["context_multiplier"] = round(ctx_mult, 4)
    
    # Apply historical fit
    hist_mult = float(historical_fit_score or 1.0)
    score *= hist_mult
    breakdown["after_historical"] = round(score, 4)
    breakdown["historical_multiplier"] = round(hist_mult, 4)
    
    # Apply drift
    score_pre_drift = score
    score = apply_drift_multiplier(score, drift)
    breakdown["after_drift"] = round(score, 4)
    breakdown["drift_multiplier"] = round(score / score_pre_drift, 4) if score_pre_drift > 0 else 1.0
    
    # Apply expectation
    score_pre_exp = score
    score = apply_expectation_multiplier(score, expectation)
    breakdown["after_expectation"] = round(score, 4)
    breakdown["expectation_multiplier"] = round(score / score_pre_exp, 4) if score_pre_exp > 0 else 1.0
    
    # Final clamp
    final_score = clamp(score)
    
    # Calculate total multiplier
    total_mult = final_score / base_confidence if base_confidence > 0 else 1.0
    
    return {
        "final_confidence": round(final_score, 4),
        "total_multiplier": round(total_mult, 4),
        "breakdown": breakdown,
    }


def determine_tradeable(
    final_confidence: float,
    context_fit_label: Optional[str],
    historical_fit_label: Optional[str],
    drift: Optional[Dict],
) -> Dict:
    """
    Determine if setup is tradeable based on all factors.
    
    NOT TRADEABLE when:
    - Context fit is LOW
    - Historical fit is POOR
    - Strong degrading drift + low confidence
    - Final confidence < 0.35
    
    Args:
        final_confidence: Final computed confidence
        context_fit_label: Context fit label (HIGH/MEDIUM/LOW)
        historical_fit_label: Historical fit label (STRONG/GOOD/NEUTRAL/WEAK/POOR)
        drift: Drift analysis
    
    Returns:
        Tradeable decision with reason
    """
    reasons = []
    tradeable = True
    
    # Check context fit
    if context_fit_label == "LOW":
        tradeable = False
        reasons.append("Context mismatch (pattern not suited for current regime)")
    
    # Check historical fit
    if historical_fit_label == "POOR":
        tradeable = False
        reasons.append("Poor historical performance in this context")
    
    # Check drift + confidence combo
    if drift and drift.get("label") in ("DEGRADING", "STRONG_DEGRADING"):
        if final_confidence < 0.55:
            tradeable = False
            reasons.append(f"Degrading edge with low confidence ({int(final_confidence*100)}%)")
    
    # Check minimum confidence
    if final_confidence < 0.35:
        tradeable = False
        reasons.append(f"Confidence too low ({int(final_confidence*100)}%)")
    
    # Build status
    if tradeable:
        if final_confidence >= 0.70:
            status = "STRONG_ENTRY"
            message = "High confidence setup - consider entry"
        elif final_confidence >= 0.55:
            status = "MODERATE_ENTRY"
            message = "Moderate setup - wait for confirmation"
        else:
            status = "WEAK_ENTRY"
            message = "Low confidence - extra caution advised"
    else:
        status = "NO_TRADE"
        message = "; ".join(reasons) if reasons else "Setup not recommended"
    
    return {
        "tradeable": tradeable,
        "status": status,
        "message": message,
        "reasons": reasons,
    }


def build_decision_summary(
    final_confidence: float,
    tradeable_result: Dict,
    drift: Optional[Dict],
    expectation: Optional[Dict],
) -> str:
    """
    Build human-readable decision summary.
    """
    parts = []
    
    # Confidence
    conf_pct = int(final_confidence * 100)
    parts.append(f"Confidence: {conf_pct}%")
    
    # Tradeable status
    if tradeable_result.get("tradeable"):
        parts.append(f"Status: {tradeable_result.get('status', 'OK')}")
    else:
        parts.append("Status: NO TRADE")
    
    # Drift
    if drift and drift.get("label") not in ("INSUFFICIENT", "STABLE", None):
        drift_label = drift.get("label", "")
        if "IMPROVING" in drift_label:
            parts.append("Trend: ↑ Improving")
        elif "DEGRADING" in drift_label:
            parts.append("Trend: ↓ Degrading")
    
    # Expectation
    if expectation and expectation.get("move_pct"):
        move = expectation.get("move_pct", 0)
        time_h = expectation.get("resolution_h", 0)
        if time_h < 24:
            parts.append(f"Expected: ~{move}% in ~{int(time_h)}h")
        else:
            days = round(time_h / 24, 1)
            parts.append(f"Expected: ~{move}% in ~{days}d")
    
    return " | ".join(parts)
