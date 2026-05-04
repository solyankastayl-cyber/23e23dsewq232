"""
PHASE 4.8 — Absorption Engine

Detects absorption: pressure exists but price holds,
indicating real demand/supply at current level.
"""


class AbsorptionEngine:
    """Detects absorption signals for entry confirmation."""

    def evaluate(self, data: dict) -> dict:
        flow = data.get("flow", {})
        side = data.get("side", "LONG")

        buy_pressure = flow.get("buy_pressure", 0.5)
        sell_pressure = flow.get("sell_pressure", 0.5)

        absorption_detected = False
        reason = "no_absorption"

        if side == "LONG" and buy_pressure > 0.65:
            absorption_detected = True
            reason = "buyers_absorbing_supply"

        if side == "SHORT" and sell_pressure > 0.65:
            absorption_detected = True
            reason = "sellers_absorbing_demand"

        return {
            "absorption_detected": absorption_detected,
            "absorption_reason": reason,
        }
