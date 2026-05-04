"""
ScenarioBuilder
===============
Builds bull/base/bear scenarios with normalised probabilities and target /
invalidation prices for the given bias and expected_move_pct.
"""

from typing import List, Optional

from modules.ta_prediction_intelligence.types import (
    PredictionBias,
    PredictionScenario,
)


class ScenarioBuilder:
    def build(
        self,
        bias: PredictionBias,
        confidence: float,
        expected_move_pct: float,
        current_price: Optional[float],
        drivers: List[str],
    ) -> List[PredictionScenario]:
        if not current_price:
            return []

        base_prob = max(0.0, min(1.0, float(confidence)))
        neutral_prob = max(0.10, 1.0 - base_prob)
        directional_prob = 1.0 - neutral_prob

        if bias == PredictionBias.BULLISH:
            bull_prob = directional_prob
            bear_prob = max(0.05, neutral_prob * 0.35)
        elif bias == PredictionBias.BEARISH:
            bear_prob = directional_prob
            bull_prob = max(0.05, neutral_prob * 0.35)
        else:
            bull_prob = 0.25
            bear_prob = 0.25
            neutral_prob = 0.50

        total = bull_prob + bear_prob + neutral_prob
        bull_prob /= total
        bear_prob /= total
        neutral_prob /= total

        magnitude = abs(float(expected_move_pct))
        up_target = current_price * (1.0 + magnitude)
        down_target = current_price * (1.0 - magnitude)

        return [
            PredictionScenario(
                name="bull",
                bias=PredictionBias.BULLISH,
                probability=round(bull_prob, 4),
                target_price=round(up_target, 4),
                invalidation_price=round(down_target, 4),
                expected_move_pct=round(magnitude, 6),
                drivers=drivers,
            ),
            PredictionScenario(
                name="base",
                bias=PredictionBias.NEUTRAL,
                probability=round(neutral_prob, 4),
                target_price=round(current_price, 4),
                invalidation_price=None,
                expected_move_pct=0.0,
                drivers=["base_case"],
            ),
            PredictionScenario(
                name="bear",
                bias=PredictionBias.BEARISH,
                probability=round(bear_prob, 4),
                target_price=round(down_target, 4),
                invalidation_price=round(up_target, 4),
                expected_move_pct=round(-magnitude, 6),
                drivers=drivers,
            ),
        ]
