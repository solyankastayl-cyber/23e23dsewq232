"""
Slippage Engine — PHASE 2.4

Models slippage as function of volatility.
Deterministic formula: slip = volatility * 0.1
"""


class SlippageEngine:

    def apply(self, order: dict, price: float, market_state: dict) -> float:
        volatility = market_state.get("volatility", 0.01)

        slip = volatility * 0.1

        if order["direction"] == "long":
            return price * (1 + slip)
        else:
            return price * (1 - slip)
