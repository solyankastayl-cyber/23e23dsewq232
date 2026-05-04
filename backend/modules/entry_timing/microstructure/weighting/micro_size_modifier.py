"""
PHASE 4.8.3 — Micro Size Modifier

Computes position size multiplier based on microstructure quality.
Range: 0.0 (blocked) to 1.15 (max boost).
"""


class MicroSizeModifier:
    """Position size multiplier from microstructure."""

    def compute(self, micro: dict) -> float:
        if not micro.get("entry_permission", False):
            return 0.0

        score = micro.get("microstructure_score", 0.5)
        sweep_risk = micro.get("sweep_risk", 0.5)
        liquidity_risk = micro.get("liquidity_risk", 0.5)

        if score >= 0.8 and sweep_risk < 0.3 and liquidity_risk < 0.35:
            return 1.15

        if score >= 0.65 and sweep_risk < 0.45:
            return 1.0

        if score >= 0.5:
            return 0.8

        return 0.6
