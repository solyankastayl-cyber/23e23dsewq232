"""
Symbol Ranker — PHASE 2.8.5

Ranks assets by performance.
Can rank by: pnl, expectancy, profit_factor, win_rate.
"""


class SymbolRanker:

    def rank(self, diagnostics: dict, by: str = "pnl") -> list:
        """
        Rank symbols by a given metric.

        Args:
            diagnostics: output of SymbolDiagnostics.compute()
            by: metric to rank by (pnl, expectancy, profit_factor, win_rate)

        Returns:
            sorted list of (symbol, stats) tuples, best first
        """
        def sort_key(item):
            val = item[1].get(by, 0)
            if val == "inf":
                return float("inf")
            return val

        return sorted(
            diagnostics.items(),
            key=sort_key,
            reverse=True,
        )

    def top_n(self, diagnostics: dict, n: int = 10, by: str = "pnl") -> list:
        """Top N performing symbols."""
        ranked = self.rank(diagnostics, by=by)
        return ranked[:n]

    def bottom_n(self, diagnostics: dict, n: int = 10, by: str = "pnl") -> list:
        """Bottom N performing symbols (worst first)."""
        ranked = self.rank(diagnostics, by=by)
        return list(reversed(ranked[-n:]))

    def has_edge(self, diagnostics: dict, min_expectancy: float = 0) -> list:
        """Return symbols with positive expectancy."""
        return [
            (s, d) for s, d in diagnostics.items()
            if d.get("expectancy", 0) > min_expectancy
        ]

    def no_edge(self, diagnostics: dict) -> list:
        """Return symbols with zero or negative expectancy."""
        return [
            (s, d) for s, d in diagnostics.items()
            if d.get("expectancy", 0) <= 0
        ]
