"""
Direction Calculator

Determines prediction direction based on TA signals.
Pure TA-based, no external dependencies.
"""

from typing import List
from .types import (
    PredictionInput,
    Direction,
    DIRECTION_WEIGHTS,
    DIRECTION_THRESHOLDS,
)


def build_direction(input: PredictionInput) -> Direction:
    """
    Calculate direction from TA input.
    
    Formula:
        score = pattern_weight * pattern_direction
              + structure_weight * trend_direction
              + momentum_weight * momentum
    
    Returns:
        Direction with label (bullish/bearish/neutral) and score (-1 to 1)
    """
    score = 0.0
    reasoning = []
    
    # ─────────────────────────────────────────────────────────
    # 1. Pattern contribution (40%)
    # ─────────────────────────────────────────────────────────
    pattern_score = 0.0
    
    if input.pattern.direction == "bullish":
        pattern_score = input.pattern.confidence
        reasoning.append(f"Bullish {input.pattern.type} pattern ({input.pattern.confidence:.0%})")
    elif input.pattern.direction == "bearish":
        pattern_score = -input.pattern.confidence
        reasoning.append(f"Bearish {input.pattern.type} pattern ({input.pattern.confidence:.0%})")
    else:
        reasoning.append(f"Neutral pattern ({input.pattern.type})")
    
    score += DIRECTION_WEIGHTS["pattern"] * pattern_score
    
    # ─────────────────────────────────────────────────────────
    # 2. Structure contribution (30%)
    # ─────────────────────────────────────────────────────────
    structure_score = 0.0
    
    if input.structure.trend == "up":
        structure_score = input.structure.trend_strength
        reasoning.append(f"Uptrend structure ({input.structure.trend_strength:.0%} strength)")
    elif input.structure.trend == "down":
        structure_score = -input.structure.trend_strength
        reasoning.append(f"Downtrend structure ({input.structure.trend_strength:.0%} strength)")
    else:
        # Flat/ranging
        if input.structure.state == "compression":
            reasoning.append("Compression (breakout expected)")
        else:
            reasoning.append(f"Ranging market ({input.structure.state})")
    
    score += DIRECTION_WEIGHTS["structure"] * structure_score
    
    # ─────────────────────────────────────────────────────────
    # 3. Momentum contribution (30%)
    # ─────────────────────────────────────────────────────────
    momentum = input.indicators.momentum
    
    if momentum > 0.1:
        reasoning.append(f"Bullish momentum ({momentum:+.0%})")
    elif momentum < -0.1:
        reasoning.append(f"Bearish momentum ({momentum:+.0%})")
    else:
        reasoning.append("Neutral momentum")
    
    score += DIRECTION_WEIGHTS["momentum"] * momentum
    
    # ─────────────────────────────────────────────────────────
    # 4. Classify label
    # ─────────────────────────────────────────────────────────
    if score > DIRECTION_THRESHOLDS["bullish"]:
        label = "bullish"
    elif score < DIRECTION_THRESHOLDS["bearish"]:
        label = "bearish"
    else:
        label = "neutral"
    
    # Clamp score to [-1, 1]
    score = max(-1.0, min(1.0, score))
    
    return Direction(
        label=label,
        score=score,
        reasoning=reasoning,
    )


def calculate_direction_agreement(input: PredictionInput, direction: Direction) -> float:
    """
    Calculate how well different signals agree with direction.
    Used for confidence calculation.
    
    Returns: agreement score 0-1 (1 = full agreement)
    """
    agreements = []
    
    # Pattern agreement
    if direction.label == "bullish":
        if input.pattern.direction == "bullish":
            agreements.append(1.0)
        elif input.pattern.direction == "neutral":
            agreements.append(0.5)
        else:
            agreements.append(0.0)
    elif direction.label == "bearish":
        if input.pattern.direction == "bearish":
            agreements.append(1.0)
        elif input.pattern.direction == "neutral":
            agreements.append(0.5)
        else:
            agreements.append(0.0)
    else:
        agreements.append(0.5)  # Neutral direction
    
    # Momentum agreement
    if direction.label == "bullish" and input.indicators.momentum > 0:
        agreements.append(1.0)
    elif direction.label == "bearish" and input.indicators.momentum < 0:
        agreements.append(1.0)
    elif direction.label == "neutral":
        agreements.append(0.5 + (1 - abs(input.indicators.momentum)) * 0.5)
    else:
        # Momentum disagrees with direction
        agreements.append(0.2)
    
    # Structure agreement
    if direction.label == "bullish" and input.structure.trend == "up":
        agreements.append(1.0)
    elif direction.label == "bearish" and input.structure.trend == "down":
        agreements.append(1.0)
    elif input.structure.trend == "flat":
        agreements.append(0.5)
    else:
        agreements.append(0.3)
    
    return sum(agreements) / len(agreements) if agreements else 0.5
