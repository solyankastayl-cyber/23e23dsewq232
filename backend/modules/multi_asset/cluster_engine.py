"""
Cluster Engine — PHASE 2.8.2

Groups assets by cluster for portfolio-level analysis.
"""


class ClusterEngine:

    def group(self, assets: list) -> dict:
        """
        Group assets by cluster.

        Args:
            assets: list of {symbol, cluster, ...}

        Returns:
            {cluster_name: [assets]}
        """
        clusters = {}

        for asset in assets:
            c = asset.get("cluster", "other")
            clusters.setdefault(c, []).append(asset)

        return clusters

    def summary(self, assets: list) -> dict:
        """
        Cluster summary with counts.

        Returns:
            {cluster_name: count}
        """
        groups = self.group(assets)
        return {k: len(v) for k, v in groups.items()}
