"""
PHASE 4.8 — Orderbook Engine

Evaluates orderbook quality: depth imbalance and spread hostility.
"""


class OrderbookEngine:
    """Assesses orderbook conditions for entry."""

    def evaluate(self, data: dict) -> dict:
        ob = data.get("orderbook", {})

        bid_depth = ob.get("bid_depth", 0)
        ask_depth = ob.get("ask_depth", 0)
        spread_bps = ob.get("spread_bps", 0)

        imbalance_ratio = 0.0
        total = bid_depth + ask_depth
        if total > 0:
            imbalance_ratio = (bid_depth - ask_depth) / total

        hostile_spread = spread_bps > 8

        reasons = []
        if hostile_spread:
            reasons.append("hostile_spread")
        if abs(imbalance_ratio) > 0.3:
            reasons.append("strong_orderbook_imbalance")

        return {
            "imbalance_ratio": round(imbalance_ratio, 3),
            "hostile_spread": hostile_spread,
            "spread_bps": spread_bps,
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "reasons": reasons,
        }
