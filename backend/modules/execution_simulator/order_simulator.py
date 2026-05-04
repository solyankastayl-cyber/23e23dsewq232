"""
Order Simulator — PHASE 2.4

Creates order from trade setup.
Deterministic. No magic.
"""


class OrderSimulator:

    def create_order(self, trade_setup: dict) -> dict:
        return {
            "type": trade_setup.get("order_type", "limit"),
            "entry": trade_setup["entry"],
            "direction": trade_setup["direction"],
            "size": trade_setup.get("position_size", 1.0),
        }
