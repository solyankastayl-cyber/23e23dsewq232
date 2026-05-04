"""
Asset Registry

Manages the universe of assets to scan.
Controlled scaling: top 50 → 100 → 300 → 1000+
"""

import time
from typing import List, Optional, Dict
from .types import AssetRegistryItem, DEFAULT_ASSET_LIMIT


# Top 50 crypto by volume (seed data)
TOP_CRYPTO_SEED = [
    ("BTC", 1), ("ETH", 2), ("BNB", 3), ("XRP", 4), ("SOL", 5),
    ("ADA", 6), ("DOGE", 7), ("AVAX", 8), ("DOT", 9), ("LINK", 10),
    ("MATIC", 11), ("SHIB", 12), ("LTC", 13), ("TRX", 14), ("UNI", 15),
    ("ATOM", 16), ("XLM", 17), ("ETC", 18), ("BCH", 19), ("FIL", 20),
    ("APT", 21), ("NEAR", 22), ("ARB", 23), ("OP", 24), ("INJ", 25),
    ("SUI", 26), ("AAVE", 27), ("MKR", 28), ("GRT", 29), ("STX", 30),
    ("SAND", 31), ("MANA", 32), ("IMX", 33), ("AXS", 34), ("THETA", 35),
    ("FTM", 36), ("ALGO", 37), ("EGLD", 38), ("FLOW", 39), ("XTZ", 40),
    ("EOS", 41), ("RUNE", 42), ("SNX", 43), ("LDO", 44), ("CRV", 45),
    ("KAVA", 46), ("ROSE", 47), ("ZIL", 48), ("ENJ", 49), ("CHZ", 50),
]


class AssetRegistry:
    """
    Manages asset universe for scanning.
    
    Collections used:
    - asset_registry: stores active assets
    """
    
    def __init__(self, db=None):
        self.db = db
        self._ensure_db()
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            try:
                from core.database import get_database
                self.db = get_database()
            except Exception:
                self.db = None
    
    def get_active_assets(self, limit: int = DEFAULT_ASSET_LIMIT) -> List[AssetRegistryItem]:
        """
        Get active assets sorted by volume rank.
        
        Args:
            limit: Maximum number of assets to return
        
        Returns:
            List of active assets
        """
        if self.db is None:
            # Return seed data if no DB
            return [
                AssetRegistryItem(
                    symbol=symbol,
                    exchange="binance",
                    is_active=True,
                    volume_rank=rank,
                )
                for symbol, rank in TOP_CRYPTO_SEED[:limit]
            ]
        
        try:
            cursor = self.db.asset_registry.find(
                {"is_active": True}
            ).sort("volume_rank", 1).limit(limit)
            
            return [AssetRegistryItem.from_dict(doc) for doc in cursor]
        except Exception:
            return []
    
    def get_asset(self, symbol: str) -> Optional[AssetRegistryItem]:
        """Get single asset by symbol."""
        if self.db is None:
            for s, rank in TOP_CRYPTO_SEED:
                if s == symbol:
                    return AssetRegistryItem(
                        symbol=s, exchange="binance",
                        is_active=True, volume_rank=rank
                    )
            return None
        
        try:
            doc = self.db.asset_registry.find_one({"symbol": symbol})
            return AssetRegistryItem.from_dict(doc) if doc else None
        except Exception:
            return None
    
    def upsert_asset(self, asset: AssetRegistryItem) -> bool:
        """
        Insert or update an asset.
        
        Args:
            asset: Asset to upsert
        
        Returns:
            Success status
        """
        if self.db is None:
            return False
        
        try:
            self.db.asset_registry.update_one(
                {"symbol": asset.symbol, "exchange": asset.exchange},
                {"$set": asset.to_dict()},
                upsert=True
            )
            return True
        except Exception:
            return False
    
    def seed_default_assets(self) -> int:
        """
        Seed registry with default top crypto assets.
        
        Returns:
            Number of assets seeded
        """
        if self.db is None:
            return 0
        
        count = 0
        for symbol, rank in TOP_CRYPTO_SEED:
            asset = AssetRegistryItem(
                symbol=symbol,
                exchange="binance",
                is_active=True,
                volume_rank=rank,
            )
            if self.upsert_asset(asset):
                count += 1
        
        return count
    
    def set_asset_active(self, symbol: str, is_active: bool) -> bool:
        """Enable or disable an asset."""
        if self.db is None:
            return False
        
        try:
            self.db.asset_registry.update_one(
                {"symbol": symbol},
                {"$set": {"is_active": is_active, "updated_at": int(time.time())}}
            )
            return True
        except Exception:
            return False
    
    def get_stats(self) -> Dict:
        """Get registry statistics."""
        if self.db is None:
            return {"total": len(TOP_CRYPTO_SEED), "active": len(TOP_CRYPTO_SEED), "seeded": False}
        
        try:
            total = self.db.asset_registry.count_documents({})
            active = self.db.asset_registry.count_documents({"is_active": True})
            return {"total": total, "active": active, "seeded": total > 0}
        except Exception:
            return {"total": 0, "active": 0, "seeded": False}


# Singleton
_registry: Optional[AssetRegistry] = None


def get_asset_registry() -> AssetRegistry:
    """Get singleton asset registry."""
    global _registry
    if _registry is None:
        _registry = AssetRegistry()
    return _registry
