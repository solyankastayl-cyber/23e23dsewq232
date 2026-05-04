"""
Universe Registry — PHASE 2.8.1

Centralized tradable universe.
Scalable to 100+ assets. No DB dependency in V1.
"""


# Default universe: 50 crypto assets with metadata
DEFAULT_UNIVERSE = [
    # ─── Majors ───
    {"symbol": "BTCUSDT", "type": "major", "liquidity": "high", "cluster": "btc"},
    {"symbol": "ETHUSDT", "type": "major", "liquidity": "high", "cluster": "eth"},

    # ─── Large Cap Alt L1 ───
    {"symbol": "SOLUSDT", "type": "alt_l1", "liquidity": "high", "cluster": "alt_l1"},
    {"symbol": "AVAXUSDT", "type": "alt_l1", "liquidity": "high", "cluster": "alt_l1"},
    {"symbol": "DOTUSDT", "type": "alt_l1", "liquidity": "medium", "cluster": "alt_l1"},
    {"symbol": "ADAUSDT", "type": "alt_l1", "liquidity": "high", "cluster": "alt_l1"},
    {"symbol": "NEARUSDT", "type": "alt_l1", "liquidity": "medium", "cluster": "alt_l1"},
    {"symbol": "ATOMUSDT", "type": "alt_l1", "liquidity": "medium", "cluster": "alt_l1"},
    {"symbol": "APTUSDT", "type": "alt_l1", "liquidity": "medium", "cluster": "alt_l1"},
    {"symbol": "SUIUSDT", "type": "alt_l1", "liquidity": "medium", "cluster": "alt_l1"},

    # ─── L2 / Infra ───
    {"symbol": "MATICUSDT", "type": "l2", "liquidity": "high", "cluster": "infra"},
    {"symbol": "ARBUSDT", "type": "l2", "liquidity": "medium", "cluster": "infra"},
    {"symbol": "OPUSDT", "type": "l2", "liquidity": "medium", "cluster": "infra"},
    {"symbol": "STXUSDT", "type": "infra", "liquidity": "medium", "cluster": "infra"},

    # ─── DeFi ───
    {"symbol": "UNIUSDT", "type": "defi", "liquidity": "medium", "cluster": "defi"},
    {"symbol": "AAVEUSDT", "type": "defi", "liquidity": "medium", "cluster": "defi"},
    {"symbol": "LINKUSDT", "type": "defi", "liquidity": "high", "cluster": "defi"},
    {"symbol": "MKRUSDT", "type": "defi", "liquidity": "medium", "cluster": "defi"},
    {"symbol": "SNXUSDT", "type": "defi", "liquidity": "low", "cluster": "defi"},
    {"symbol": "CRVUSDT", "type": "defi", "liquidity": "medium", "cluster": "defi"},
    {"symbol": "LDOUSDT", "type": "defi", "liquidity": "medium", "cluster": "defi"},

    # ─── AI ───
    {"symbol": "FETUSDT", "type": "ai", "liquidity": "medium", "cluster": "ai"},
    {"symbol": "RENDERUSDT", "type": "ai", "liquidity": "medium", "cluster": "ai"},
    {"symbol": "TAOUSDT", "type": "ai", "liquidity": "medium", "cluster": "ai"},
    {"symbol": "WLDUSDT", "type": "ai", "liquidity": "medium", "cluster": "ai"},

    # ─── Memes ───
    {"symbol": "DOGEUSDT", "type": "meme", "liquidity": "high", "cluster": "meme"},
    {"symbol": "SHIBUSDT", "type": "meme", "liquidity": "high", "cluster": "meme"},
    {"symbol": "PEPEUSDT", "type": "meme", "liquidity": "medium", "cluster": "meme"},
    {"symbol": "WIFUSDT", "type": "meme", "liquidity": "medium", "cluster": "meme"},
    {"symbol": "BONKUSDT", "type": "meme", "liquidity": "medium", "cluster": "meme"},
    {"symbol": "FLOKIUSDT", "type": "meme", "liquidity": "low", "cluster": "meme"},

    # ─── Gaming / Metaverse ───
    {"symbol": "AXSUSDT", "type": "gaming", "liquidity": "medium", "cluster": "gaming"},
    {"symbol": "SANDUSDT", "type": "gaming", "liquidity": "medium", "cluster": "gaming"},
    {"symbol": "MANAUSDT", "type": "gaming", "liquidity": "medium", "cluster": "gaming"},
    {"symbol": "IMXUSDT", "type": "gaming", "liquidity": "low", "cluster": "gaming"},

    # ─── Exchange Tokens ───
    {"symbol": "BNBUSDT", "type": "exchange", "liquidity": "high", "cluster": "exchange"},
    {"symbol": "FTMUSDT", "type": "alt_l1", "liquidity": "medium", "cluster": "alt_l1"},

    # ─── Privacy / Store of Value ───
    {"symbol": "XMRUSDT", "type": "privacy", "liquidity": "medium", "cluster": "other"},
    {"symbol": "LTCUSDT", "type": "payment", "liquidity": "high", "cluster": "other"},

    # ─── Mid-cap Alts ───
    {"symbol": "INJUSDT", "type": "defi", "liquidity": "medium", "cluster": "defi"},
    {"symbol": "TIAUSDT", "type": "infra", "liquidity": "medium", "cluster": "infra"},
    {"symbol": "SEIUSDT", "type": "alt_l1", "liquidity": "medium", "cluster": "alt_l1"},
    {"symbol": "JUPUSDT", "type": "defi", "liquidity": "medium", "cluster": "defi"},
    {"symbol": "ENAUSDT", "type": "defi", "liquidity": "medium", "cluster": "defi"},
    {"symbol": "PENDLEUSDT", "type": "defi", "liquidity": "medium", "cluster": "defi"},
    {"symbol": "RNDRUSDT", "type": "ai", "liquidity": "medium", "cluster": "ai"},
    {"symbol": "ONDOUSDT", "type": "rwa", "liquidity": "medium", "cluster": "other"},
    {"symbol": "PYTHUSDT", "type": "infra", "liquidity": "medium", "cluster": "infra"},
    {"symbol": "JITOSOLUSDT", "type": "defi", "liquidity": "low", "cluster": "defi"},
    {"symbol": "ORDIUSDT", "type": "btc_eco", "liquidity": "medium", "cluster": "btc"},
    {"symbol": "STRKUSDT", "type": "l2", "liquidity": "medium", "cluster": "infra"},
]


class UniverseRegistry:

    def __init__(self):
        self.assets = []

    def load(self, custom_assets: list = None):
        """
        Load tradable universe.

        Args:
            custom_assets: override default universe (for testing)
        """
        if custom_assets is not None:
            self.assets = custom_assets
        else:
            self.assets = [a.copy() for a in DEFAULT_UNIVERSE]

    def get_assets(self) -> list:
        return self.assets

    def get_symbols(self) -> list:
        return [a["symbol"] for a in self.assets]

    def get_by_cluster(self, cluster: str) -> list:
        return [a for a in self.assets if a.get("cluster") == cluster]

    def get_by_liquidity(self, min_liquidity: str = "medium") -> list:
        levels = {"low": 0, "medium": 1, "high": 2}
        min_level = levels.get(min_liquidity, 1)
        return [a for a in self.assets if levels.get(a.get("liquidity", "low"), 0) >= min_level]

    def count(self) -> int:
        return len(self.assets)
