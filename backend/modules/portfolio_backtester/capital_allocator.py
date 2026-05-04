"""
Capital Allocator — PHASE 2.5

Determines position size based on available capital and risk budget.
Deterministic. No ML.
"""


class CapitalAllocator:

    def __init__(self, risk_per_trade: float = 0.01):
        """
        Args:
            risk_per_trade: fraction of capital risked per trade (default 1%)
        """
        self.risk_per_trade = risk_per_trade

    def allocate(self, capital: float, entry: float, stop: float) -> dict:
        """
        Compute position size from capital, entry, and stop.

        Returns:
            {risk_amount, position_size, position_value}
        """
        risk_amount = capital * self.risk_per_trade
        risk_per_unit = abs(entry - stop)

        if risk_per_unit == 0 or entry == 0:
            return {
                "risk_amount": 0,
                "position_size": 0,
                "position_value": 0,
            }

        position_size = risk_amount / risk_per_unit
        position_value = position_size * entry

        return {
            "risk_amount": round(risk_amount, 2),
            "position_size": round(position_size, 6),
            "position_value": round(position_value, 2),
        }
