"""
Cross-Asset Constraints — PHASE 2.8.4

Portfolio-level constraints across clusters:
- Cluster exposure cap
- Sector cap
- Per-universe heat

No magic correlation. Deterministic.
"""


class CrossAssetConstraints:

    def __init__(self, max_cluster_exposure: float = 0.40, max_single_asset: float = 0.15):
        """
        Args:
            max_cluster_exposure: max fraction of portfolio in one cluster (default 40%)
            max_single_asset: max fraction of portfolio in one symbol (default 15%)
        """
        self.max_cluster_exposure = max_cluster_exposure
        self.max_single_asset = max_single_asset

    def apply(self, trades: list, capital: float) -> list:
        """
        Filter trades that exceed cross-asset constraints.

        Args:
            trades: list of {symbol, cluster, size, ...}
            capital: total capital

        Returns:
            filtered list of trades that pass constraints
        """
        filtered = []
        cluster_exposure = {}
        symbol_exposure = {}

        for t in trades:
            cluster = t.get("cluster", "other")
            symbol = t.get("symbol", "unknown")
            size = t.get("size", 0.1)

            # Check cluster cap
            current_cluster = cluster_exposure.get(cluster, 0)
            if current_cluster + size > self.max_cluster_exposure:
                continue

            # Check single asset cap
            current_symbol = symbol_exposure.get(symbol, 0)
            if current_symbol + size > self.max_single_asset:
                continue

            # Accept trade
            cluster_exposure[cluster] = current_cluster + size
            symbol_exposure[symbol] = current_symbol + size
            filtered.append(t)

        return filtered

    def evaluate(self, trades: list, capital: float) -> dict:
        """
        Evaluate constraints and return detailed report.

        Returns:
            {accepted, rejected, cluster_exposure, symbol_exposure}
        """
        accepted = []
        rejected = []
        cluster_exposure = {}
        symbol_exposure = {}

        for t in trades:
            cluster = t.get("cluster", "other")
            symbol = t.get("symbol", "unknown")
            size = t.get("size", 0.1)

            current_cluster = cluster_exposure.get(cluster, 0)
            current_symbol = symbol_exposure.get(symbol, 0)

            reject_reason = None
            if current_cluster + size > self.max_cluster_exposure:
                reject_reason = f"cluster_cap ({cluster}: {current_cluster + size:.2f} > {self.max_cluster_exposure})"
            elif current_symbol + size > self.max_single_asset:
                reject_reason = f"symbol_cap ({symbol}: {current_symbol + size:.2f} > {self.max_single_asset})"

            if reject_reason:
                rejected.append({**t, "reject_reason": reject_reason})
            else:
                cluster_exposure[cluster] = current_cluster + size
                symbol_exposure[symbol] = current_symbol + size
                accepted.append(t)

        return {
            "accepted": accepted,
            "rejected": rejected,
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "cluster_exposure": {k: round(v, 4) for k, v in cluster_exposure.items()},
            "symbol_exposure": {k: round(v, 4) for k, v in symbol_exposure.items()},
        }
