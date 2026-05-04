"""
Fill Engine — PHASE 2.4

CRITICAL: No magic fills.
- LIMIT: fills only if price passes through entry
- MARKET: fills at given price
- BREAKOUT: fills only when breakout level is breached
"""


class FillEngine:

    def execute(self, order: dict, price: float, candle: dict) -> dict:
        high = candle["high"]
        low = candle["low"]

        if order["type"] == "limit":
            if low <= order["entry"] <= high:
                return {"filled": True, "price": order["entry"]}

        if order["type"] == "market":
            return {"filled": True, "price": price}

        if order["type"] == "breakout":
            if order["direction"] == "long" and high >= order["entry"]:
                return {"filled": True, "price": order["entry"]}
            if order["direction"] == "short" and low <= order["entry"]:
                return {"filled": True, "price": order["entry"]}

        return {"filled": False}
