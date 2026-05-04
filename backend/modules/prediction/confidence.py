"""
Confidence Calculator

Calculates prediction confidence based on TA signal agreement.
"""

from .types import (
    PredictionInput,
    Direction,
    Confidence,
    CONFIDENCE_WEIGHTS,
    CONFIDENCE_THRESHOLDS,
)
from .direction import calculate_direction_agreement


def build_confidence(input: PredictionInput, direction: Direction) -> Confidence:
    """
    Calculate confidence from TA input and direction.
    
    Formula:
        confidence = pattern_weight * pattern_confidence
                   + trend_weight * trend_strength
                   + agreement_weight * signal_agreement
    
    With conflict penalty if signals disagree.
    
    Returns:
        Confidence with value (0-1), label, and factor breakdown
    """
    factors = {}
    
    # ─────────────────────────────────────────────────────────
    # 1. Pattern confidence contribution (40%)
    # ─────────────────────────────────────────────────────────
    pattern_conf = input.pattern.confidence
    factors["pattern"] = pattern_conf
    
    # ─────────────────────────────────────────────────────────
    # 2. Trend strength contribution (30%)
    # ─────────────────────────────────────────────────────────
    trend_strength = input.indicators.trend_strength
    factors["trend_strength"] = trend_strength
    
    # ─────────────────────────────────────────────────────────
    # 3. Signal agreement contribution (30%)
    # ─────────────────────────────────────────────────────────
    agreement = calculate_direction_agreement(input, direction)
    factors["agreement"] = agreement
    
    # ─────────────────────────────────────────────────────────
    # 4. Calculate weighted confidence
    # ─────────────────────────────────────────────────────────
    confidence = (
        CONFIDENCE_WEIGHTS["pattern"] * pattern_conf
        + CONFIDENCE_WEIGHTS["trend_strength"] * trend_strength
        + CONFIDENCE_WEIGHTS["momentum_agreement"] * agreement
    )
    
    # ─────────────────────────────────────────────────────────
    # 5. Apply conflict penalty
    # ─────────────────────────────────────────────────────────
    if _has_signal_conflict(input, direction):
        confidence *= 0.7
        factors["conflict_penalty"] = 0.7
    
    # ─────────────────────────────────────────────────────────
    # 6. Apply volatility adjustment
    # ─────────────────────────────────────────────────────────
    # High volatility slightly reduces confidence (harder to predict)
    volatility_factor = 1 - (input.indicators.volatility * 0.15)
    confidence *= volatility_factor
    factors["volatility_adj"] = volatility_factor
    
    # ─────────────────────────────────────────────────────────
    # 7. Classify label
    # ─────────────────────────────────────────────────────────
    confidence = max(0.0, min(1.0, confidence))
    
    if confidence >= CONFIDENCE_THRESHOLDS["HIGH"]:
        label = "HIGH"
    elif confidence >= CONFIDENCE_THRESHOLDS["MEDIUM"]:
        label = "MEDIUM"
    else:
        label = "LOW"
    
    return Confidence(
        value=confidence,
        label=label,
        factors=factors,
    )


def _has_signal_conflict(input: PredictionInput, direction: Direction) -> bool:
    """
    Check if momentum conflicts with predicted direction.
    """
    if direction.label == "bullish" and input.indicators.momentum < -0.2:
        return True
    if direction.label == "bearish" and input.indicators.momentum > 0.2:
        return True
    return False
