"""
Asset Cap — PHASE 2.7

Limits maximum exposure to a single asset.
"""


class AssetCap:

    def __init__(self, max_pct: float = 0.20):
        """
        Args:
            max_pct: max fraction of capital in one asset (default 20%)
        """
        self.max_pct = max_pct

    def check(self, positions: list, new_trade: dict, capital: float) -> dict:
        """
        Check if adding new_trade exceeds asset cap.

        Args:
            positions: list of {symbol, position_value}
            new_trade: {symbol, position_value}
            capital: total capital

        Returns:
            {allowed, reason, current_exposure, limit}
        """
        symbol = new_trade.get("symbol", "")
        new_value = new_trade.get("position_value", 0)

        current_exposure = sum(
            p.get("position_value", 0)
            for p in positions
            if p.get("symbol") == symbol
        )

        total_exposure = current_exposure + new_value
        limit = capital * self.max_pct

        if total_exposure > limit:
            return {
                "allowed": False,
                "reason": f"Asset cap exceeded for {symbol}: {total_exposure:.0f} > {limit:.0f}",
                "current_exposure": round(current_exposure, 2),
                "limit": round(limit, 2),
            }

        return {
            "allowed": True,
            "reason": "Within asset cap",
            "current_exposure": round(current_exposure, 2),
            "limit": round(limit, 2),
        }
