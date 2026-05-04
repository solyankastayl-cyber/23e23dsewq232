"""
Correlation Cap — PHASE 2.7

Limits number of correlated positions.
V1: Uses a static correlation map (no live calculation).
"""


# Static correlation groups for crypto
DEFAULT_CORRELATION_GROUPS = {
    "major_crypto": {"BTC", "ETH"},
    "alt_l1": {"SOL", "AVAX", "DOT", "ADA"},
    "defi": {"UNI", "AAVE", "LINK", "MKR"},
    "meme": {"DOGE", "SHIB", "PEPE"},
}


class CorrelationCap:

    def __init__(self, max_per_group: int = 2, groups: dict = None):
        """
        Args:
            max_per_group: max positions in one correlation group
            groups: dict of {group_name: set(symbols)}
        """
        self.max_per_group = max_per_group
        self.groups = groups or DEFAULT_CORRELATION_GROUPS

    def check(self, positions: list, new_trade: dict) -> dict:
        """
        Check if adding new_trade exceeds correlation cap.

        Args:
            positions: list of {symbol}
            new_trade: {symbol}

        Returns:
            {allowed, reason, group, count}
        """
        new_symbol = new_trade.get("symbol", "").upper()

        # Find which group the new symbol belongs to
        target_group = None
        for group_name, symbols in self.groups.items():
            if new_symbol in symbols:
                target_group = group_name
                break

        if target_group is None:
            return {
                "allowed": True,
                "reason": "Symbol not in any correlation group",
                "group": None,
                "count": 0,
            }

        # Count existing positions in the same group
        group_symbols = self.groups[target_group]
        count = sum(
            1 for p in positions
            if p.get("symbol", "").upper() in group_symbols
        )

        if count >= self.max_per_group:
            return {
                "allowed": False,
                "reason": f"Correlation cap for '{target_group}': {count} >= {self.max_per_group}",
                "group": target_group,
                "count": count,
            }

        return {
            "allowed": True,
            "reason": "Within correlation cap",
            "group": target_group,
            "count": count,
        }
