"""
PHASE 4.8 — Sweep Detector

Detects risk of liquidity sweep before intended move.
If sweep already happened — safer to enter.
If sweep risk is open — delay entry.
"""


class SweepDetector:
    """Assesses sweep risk for entry timing."""

    def evaluate(self, data: dict) -> dict:
        side = data.get("side", "LONG")
        flow = data.get("flow", {})
        liquidity = data.get("liquidity", {})

        recent_sweep_up = flow.get("recent_sweep_up", False)
        recent_sweep_down = flow.get("recent_sweep_down", False)

        above_liquidity = liquidity.get("above_liquidity", 0.5)
        below_liquidity = liquidity.get("below_liquidity", 0.5)

        sweep_risk = 0.2
        reason = "low_sweep_risk"

        if side == "LONG":
            if recent_sweep_down:
                sweep_risk = 0.15
                reason = "downside_liquidity_already_taken"
            elif below_liquidity > 0.7:
                sweep_risk = 0.75
                reason = "downside_liquidity_still_open"
            elif below_liquidity > 0.5:
                sweep_risk = 0.45
                reason = "moderate_downside_liquidity"

        elif side == "SHORT":
            if recent_sweep_up:
                sweep_risk = 0.15
                reason = "upside_liquidity_already_taken"
            elif above_liquidity > 0.7:
                sweep_risk = 0.75
                reason = "upside_liquidity_still_open"
            elif above_liquidity > 0.5:
                sweep_risk = 0.45
                reason = "moderate_upside_liquidity"

        return {
            "sweep_risk": round(sweep_risk, 3),
            "sweep_reason": reason,
        }
