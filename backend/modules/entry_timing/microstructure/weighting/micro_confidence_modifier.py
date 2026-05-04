"""
PHASE 4.8.3 — Micro Confidence Modifier

Adjusts prediction confidence based on microstructure signals.
Boosts on strong micro, penalizes on weak.
"""


class MicroConfidenceModifier:
    """Confidence modifier from microstructure."""

    def compute(self, prediction_confidence: float, micro: dict) -> dict:
        score = micro.get("microstructure_score", 0.5)
        absorption = micro.get("absorption_detected", False)
        imbalance = micro.get("imbalance", "neutral")
        supportive = micro.get("imbalance_supportive", False)

        multiplier = 1.0
        reasons = []

        if score >= 0.8:
            multiplier += 0.08
            reasons.append("high_micro_score")
        elif score >= 0.65:
            multiplier += 0.03
            reasons.append("decent_micro_score")
        elif score < 0.5:
            multiplier -= 0.12
            reasons.append("weak_micro_score")

        if absorption:
            multiplier += 0.03
            reasons.append("absorption_supportive")

        if supportive:
            multiplier += 0.02
            reasons.append("directional_imbalance_aligned")
        elif imbalance != "neutral":
            multiplier -= 0.04
            reasons.append("directional_imbalance_against")

        final_conf = max(0.0, min(prediction_confidence * multiplier, 1.0))

        return {
            "confidence_multiplier": round(multiplier, 3),
            "final_execution_confidence": round(final_conf, 4),
            "original_confidence": round(prediction_confidence, 4),
            "reasons": reasons,
        }
