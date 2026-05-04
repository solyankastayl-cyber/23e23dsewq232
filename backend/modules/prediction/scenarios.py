"""
Scenario Builder

Builds bull/base/bear scenarios with probability distribution.
"""

from typing import Dict
from .types import (
    PredictionInput,
    Direction,
    Scenario,
)


def build_scenarios(
    input: PredictionInput,
    direction: Direction,
) -> Dict[str, Scenario]:
    """
    Build three scenarios: bull, base, bear.
    
    Each scenario has:
    - probability (sums to 1.0)
    - target_price
    - expected_return
    
    Path and bands are added later by path_builder.
    """
    # ─────────────────────────────────────────────────────────
    # 1. Calculate base move from pattern + indicators
    # ─────────────────────────────────────────────────────────
    base_move = _calculate_base_move(input)
    
    # ─────────────────────────────────────────────────────────
    # 2. Calculate scenario-specific moves
    # ─────────────────────────────────────────────────────────
    # Bull scenario: 1.5x base move (upside)
    bull_move = base_move * 1.5
    
    # Base scenario: expected move based on direction
    if direction.label == "bullish":
        base_scenario_move = base_move
    elif direction.label == "bearish":
        base_scenario_move = -base_move
    else:
        base_scenario_move = base_move * 0.3  # Small move for neutral
    
    # Bear scenario: 1.2x base move (downside)
    bear_move = base_move * 1.2
    
    # ─────────────────────────────────────────────────────────
    # 3. Calculate target prices
    # ─────────────────────────────────────────────────────────
    price = input.price
    
    # Use pattern target if available
    pattern_target = input.pattern.target_price
    
    if pattern_target and input.pattern.confidence > 0.6:
        # Pattern has strong target - use it for base scenario
        if input.pattern.direction == "bullish":
            base_target = pattern_target
            bull_target = price * (1 + bull_move)
            bear_target = price * (1 - bear_move * 0.5)
        elif input.pattern.direction == "bearish":
            base_target = pattern_target
            bull_target = price * (1 + bull_move * 0.5)
            bear_target = pattern_target
        else:
            base_target = price * (1 + base_scenario_move)
            bull_target = price * (1 + bull_move)
            bear_target = price * (1 - bear_move)
    else:
        # No strong pattern target - use calculated moves
        base_target = price * (1 + base_scenario_move)
        bull_target = price * (1 + bull_move)
        bear_target = price * (1 - bear_move)
    
    # ─────────────────────────────────────────────────────────
    # 4. Assign probabilities
    # ─────────────────────────────────────────────────────────
    probs = _assign_probabilities(direction.score, input)
    
    # ─────────────────────────────────────────────────────────
    # 5. Build scenarios
    # ─────────────────────────────────────────────────────────
    return {
        "bull": Scenario(
            name="bull",
            probability=probs["bull"],
            target_price=bull_target,
            expected_return=(bull_target - price) / price,
        ),
        "base": Scenario(
            name="base",
            probability=probs["base"],
            target_price=base_target,
            expected_return=(base_target - price) / price,
        ),
        "bear": Scenario(
            name="bear",
            probability=probs["bear"],
            target_price=bear_target,
            expected_return=(bear_target - price) / price,
        ),
    }


def _calculate_base_move(input: PredictionInput) -> float:
    """
    Calculate base expected move from TA signals.
    
    Base move = pattern_confidence * 0.04 (4% base)
              × volatility_boost
              × trend_strength_boost
    """
    # Start with pattern confidence (max 4% base move)
    base = input.pattern.confidence * 0.04
    
    # If no strong pattern, use structure
    if input.pattern.confidence < 0.3:
        if input.structure.state == "compression":
            base = 0.05  # Compression often leads to big moves
        elif input.structure.state == "expansion":
            base = 0.04
        else:
            base = 0.025  # Default small move
    
    # Volatility boost (high vol = bigger moves)
    volatility_boost = 1 + input.indicators.volatility * 0.5
    
    # Trend strength boost (strong trend = bigger continuation)
    trend_boost = 1 + input.indicators.trend_strength * 0.3
    
    move = base * volatility_boost * trend_boost
    
    # Clamp to reasonable range (1% to 15%)
    return max(0.01, min(0.15, move))


def _assign_probabilities(
    direction_score: float,
    input: PredictionInput,
) -> Dict[str, float]:
    """
    Assign probabilities to scenarios based on direction score.
    
    Bullish direction → higher bull probability
    Bearish direction → higher bear probability
    Neutral → even distribution
    """
    # Strong bullish (score > 0.3)
    if direction_score > 0.3:
        return {
            "bull": 0.55,
            "base": 0.30,
            "bear": 0.15,
        }
    
    # Moderate bullish (score 0.1 to 0.3)
    if direction_score > 0.1:
        return {
            "bull": 0.45,
            "base": 0.35,
            "bear": 0.20,
        }
    
    # Strong bearish (score < -0.3)
    if direction_score < -0.3:
        return {
            "bull": 0.15,
            "base": 0.30,
            "bear": 0.55,
        }
    
    # Moderate bearish (score -0.3 to -0.1)
    if direction_score < -0.1:
        return {
            "bull": 0.20,
            "base": 0.35,
            "bear": 0.45,
        }
    
    # Neutral (score -0.1 to 0.1)
    # Slightly favor current structure
    if input.structure.state == "compression":
        # Compression = breakout coming, slightly favor current direction
        if input.indicators.momentum > 0:
            return {"bull": 0.40, "base": 0.35, "bear": 0.25}
        else:
            return {"bull": 0.25, "base": 0.35, "bear": 0.40}
    
    # Default even distribution
    return {
        "bull": 0.33,
        "base": 0.34,
        "bear": 0.33,
    }
