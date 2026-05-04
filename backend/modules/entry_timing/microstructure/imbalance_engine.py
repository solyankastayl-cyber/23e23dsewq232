"""
PHASE 4.8 — Imbalance Engine

Normalizes orderbook + flow into directional imbalance state.
Determines if imbalance is supportive of the intended trade direction.
"""


class ImbalanceEngine:
    """Determines directional imbalance from orderbook and flow data."""

    def evaluate(self, data: dict, orderbook_ctx: dict) -> dict:
        side = data.get("side", "LONG")
        flow = data.get("flow", {})

        buy_pressure = flow.get("buy_pressure", 0.5)
        sell_pressure = flow.get("sell_pressure", 0.5)
        imbalance_ratio = orderbook_ctx.get("imbalance_ratio", 0.0)

        if buy_pressure > sell_pressure and imbalance_ratio > 0.05:
            imbalance = "buying"
            score = min(0.5 + buy_pressure * 0.4 + imbalance_ratio * 0.3, 1.0)
        elif sell_pressure > buy_pressure and imbalance_ratio < -0.05:
            imbalance = "selling"
            score = min(0.5 + sell_pressure * 0.4 + abs(imbalance_ratio) * 0.3, 1.0)
        else:
            imbalance = "neutral"
            score = 0.5

        supportive = (
            (side == "LONG" and imbalance == "buying")
            or (side == "SHORT" and imbalance == "selling")
        )

        reasons = []
        if supportive:
            reasons.append(f"{imbalance}_imbalance_supportive")
        elif imbalance != "neutral":
            reasons.append(f"{imbalance}_imbalance_against_side")

        return {
            "imbalance": imbalance,
            "imbalance_score": round(score, 3),
            "supportive": supportive,
            "reasons": reasons,
        }
