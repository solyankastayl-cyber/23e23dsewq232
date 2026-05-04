"""
Asset Classifier — PHASE 2.8.2

Classifies assets by cluster, type, and risk tier.
Deterministic. Extensible.
"""


# Cluster rules (symbol substring → cluster)
CLUSTER_RULES = {
    "BTC": "btc",
    "ETH": "eth",
    "SOL": "alt_l1",
    "AVAX": "alt_l1",
    "DOT": "alt_l1",
    "ADA": "alt_l1",
    "NEAR": "alt_l1",
    "ATOM": "alt_l1",
    "APT": "alt_l1",
    "SUI": "alt_l1",
    "SEI": "alt_l1",
    "FTM": "alt_l1",
    "MATIC": "infra",
    "ARB": "infra",
    "OP": "infra",
    "STX": "infra",
    "TIA": "infra",
    "PYTH": "infra",
    "STRK": "infra",
    "UNI": "defi",
    "AAVE": "defi",
    "LINK": "defi",
    "MKR": "defi",
    "SNX": "defi",
    "CRV": "defi",
    "LDO": "defi",
    "INJ": "defi",
    "JUP": "defi",
    "ENA": "defi",
    "PENDLE": "defi",
    "JITOSOL": "defi",
    "FET": "ai",
    "RENDER": "ai",
    "RNDR": "ai",
    "TAO": "ai",
    "WLD": "ai",
    "DOGE": "meme",
    "SHIB": "meme",
    "PEPE": "meme",
    "WIF": "meme",
    "BONK": "meme",
    "FLOKI": "meme",
    "AXS": "gaming",
    "SAND": "gaming",
    "MANA": "gaming",
    "IMX": "gaming",
    "BNB": "exchange",
    "ORDI": "btc",
    "ONDO": "other",
    "XMR": "other",
    "LTC": "other",
}


class AssetClassifier:

    def classify(self, symbol: str) -> dict:
        """
        Classify asset by symbol.

        Returns:
            {cluster, risk_tier}
        """
        symbol_clean = symbol.upper().replace("USDT", "").replace("USD", "")

        cluster = "other"
        for key, value in CLUSTER_RULES.items():
            if symbol_clean == key or symbol_clean.startswith(key):
                cluster = value
                break

        risk_tier = self._risk_tier(cluster)

        return {
            "cluster": cluster,
            "risk_tier": risk_tier,
        }

    def _risk_tier(self, cluster: str) -> str:
        """Assign risk tier based on cluster."""
        tiers = {
            "btc": "low",
            "eth": "low",
            "alt_l1": "medium",
            "infra": "medium",
            "defi": "medium",
            "exchange": "low",
            "ai": "high",
            "meme": "high",
            "gaming": "high",
            "other": "medium",
        }
        return tiers.get(cluster, "medium")
