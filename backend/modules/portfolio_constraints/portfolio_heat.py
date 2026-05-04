"""
Portfolio Heat — PHASE 2.7

Total risk exposure limit.
Heat = sum of all position risk amounts / capital
"""


class PortfolioHeat:

    def __init__(self, max_heat: float = 0.06):
        """
        Args:
            max_heat: max total risk as fraction of capital (default 6%)
        """
        self.max_heat = max_heat

    def check(self, positions: list, new_trade: dict, capital: float) -> dict:
        """
        Check if adding new_trade exceeds portfolio heat limit.

        Args:
            positions: list of {risk_amount}
            new_trade: {risk_amount}
            capital: total capital

        Returns:
            {allowed, reason, current_heat, new_heat, limit}
        """
        current_risk = sum(p.get("risk_amount", 0) for p in positions)
        new_risk = new_trade.get("risk_amount", 0)
        total_risk = current_risk + new_risk

        current_heat = current_risk / capital if capital > 0 else 0
        new_heat = total_risk / capital if capital > 0 else 0

        if new_heat > self.max_heat:
            return {
                "allowed": False,
                "reason": f"Portfolio heat exceeded: {new_heat:.2%} > {self.max_heat:.2%}",
                "current_heat": round(current_heat, 6),
                "new_heat": round(new_heat, 6),
                "limit": self.max_heat,
            }

        return {
            "allowed": True,
            "reason": "Within portfolio heat limit",
            "current_heat": round(current_heat, 6),
            "new_heat": round(new_heat, 6),
            "limit": self.max_heat,
        }

    def compute_adjusted_size(self, positions: list, new_trade: dict, capital: float) -> float:
        """
        Compute adjusted position size to stay within heat limit.

        Returns:
            adjusted risk_amount (may be reduced)
        """
        current_risk = sum(p.get("risk_amount", 0) for p in positions)
        max_allowed = capital * self.max_heat - current_risk

        if max_allowed <= 0:
            return 0.0

        original_risk = new_trade.get("risk_amount", 0)
        return round(min(original_risk, max_allowed), 2)
