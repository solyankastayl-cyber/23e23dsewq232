"""
PHASE 4.8.3 — Micro Execution Modifier

Determines execution style based on microstructure conditions.
Aggressive when micro is strong, passive/limit when micro is weak.
"""


class MicroExecutionModifier:
    """Execution style modifier from microstructure."""

    def compute(self, micro: dict) -> dict:
        if not micro.get("entry_permission", False):
            decision = micro.get("decision", "WAIT_MICRO_CONFIRMATION")
            if decision in ["WAIT_SWEEP", "WAIT_LIQUIDITY_CLEAR", "WAIT_MICRO_CONFIRMATION"]:
                return {
                    "execution_modifier": "WAIT",
                    "weighted_decision": "WAIT_MICROSTRUCTURE",
                }
            return {
                "execution_modifier": "SKIP",
                "weighted_decision": "SKIP",
            }

        score = micro.get("microstructure_score", 0.5)
        sweep_risk = micro.get("sweep_risk", 0.5)
        liquidity_risk = micro.get("liquidity_risk", 0.5)

        if score >= 0.8 and sweep_risk < 0.25 and liquidity_risk < 0.3:
            return {
                "execution_modifier": "AGGRESSIVE",
                "weighted_decision": "GO_FULL",
            }

        if score >= 0.65 and sweep_risk < 0.45:
            return {
                "execution_modifier": "NORMAL",
                "weighted_decision": "GO_REDUCED",
            }

        if score >= 0.5:
            return {
                "execution_modifier": "PASSIVE_LIMIT",
                "weighted_decision": "GO_REDUCED",
            }

        return {
            "execution_modifier": "PASSIVE_LIMIT",
            "weighted_decision": "GO_REDUCED",
        }
