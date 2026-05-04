"""
Direction Cap — PHASE 2.7

Limits maximum directional exposure (long vs short).
"""


class DirectionCap:

    def __init__(self, max_long_pct: float = 0.60, max_short_pct: float = 0.40):
        """
        Args:
            max_long_pct: max fraction of capital in long positions
            max_short_pct: max fraction of capital in short positions
        """
        self.max_long_pct = max_long_pct
        self.max_short_pct = max_short_pct

    def check(self, positions: list, new_trade: dict, capital: float) -> dict:
        """
        Check if adding new_trade exceeds direction cap.

        Args:
            positions: list of {direction, position_value}
            new_trade: {direction, position_value}
            capital: total capital

        Returns:
            {allowed, reason, long_exposure, short_exposure}
        """
        direction = new_trade.get("direction", "").lower()
        new_value = new_trade.get("position_value", 0)

        long_total = sum(
            p.get("position_value", 0)
            for p in positions
            if p.get("direction", "").lower() == "long"
        )
        short_total = sum(
            p.get("position_value", 0)
            for p in positions
            if p.get("direction", "").lower() == "short"
        )

        if direction == "long":
            new_long = long_total + new_value
            limit = capital * self.max_long_pct
            if new_long > limit:
                return {
                    "allowed": False,
                    "reason": f"Long cap exceeded: {new_long:.0f} > {limit:.0f}",
                    "long_exposure": round(long_total, 2),
                    "short_exposure": round(short_total, 2),
                }
        elif direction == "short":
            new_short = short_total + new_value
            limit = capital * self.max_short_pct
            if new_short > limit:
                return {
                    "allowed": False,
                    "reason": f"Short cap exceeded: {new_short:.0f} > {limit:.0f}",
                    "long_exposure": round(long_total, 2),
                    "short_exposure": round(short_total, 2),
                }

        return {
            "allowed": True,
            "reason": "Within direction cap",
            "long_exposure": round(long_total, 2),
            "short_exposure": round(short_total, 2),
        }
