"""
PHASE 8 - Liquidity Repository
=================================
MongoDB storage for liquidity intelligence data.

Collections:
- orderbook_depth_snapshots
- liquidity_zones
- stop_clusters
- liquidation_zones
- sweep_signals
- liquidity_imbalances
- liquidity_history
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient, DESCENDING

from .liquidity_types import (
    DepthProfile, LiquidityZone, StopCluster, LiquidationZone,
    SweepSignal, LiquidityImbalance, UnifiedLiquiditySnapshot
)


class LiquidityRepository:
    """
    MongoDB repository for liquidity intelligence data.
    """
    
    def __init__(self):
        self.mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        self.db_name = os.environ.get("DB_NAME", "ta_engine")
        self.client = None
        self.db = None
        
        # Collection names
        self.collections = {
            "depth": "orderbook_depth_snapshots",
            "zones": "liquidity_zones",
            "stops": "stop_clusters",
            "liquidations": "liquidation_zones",
            "sweeps": "sweep_signals",
            "imbalances": "liquidity_imbalances",
            "snapshots": "unified_liquidity_snapshots",
            "history": "liquidity_history"
        }
    
    def _get_db(self):
        """Get MongoDB database connection."""
        if self.db is None:
            self.client = MongoClient(self.mongo_url)
            self.db = self.client[self.db_name]
        return self.db
    
    def _serialize(self, data: Any) -> Any:
        """Convert data for MongoDB storage."""
        if hasattr(data, 'to_dict'):
            return data.to_dict()
        elif hasattr(data, 'value'):
            return data.value
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {k: self._serialize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize(item) for item in data]
        return data
    
    # ===== Depth Snapshots =====
    
    def save_depth_snapshot(
        self,
        depth: DepthProfile
    ) -> str:
        """Save orderbook depth snapshot."""
        db = self._get_db()
        
        doc = {
            "symbol": depth.symbol,
            "data": self._serialize(depth),
            "bid_depth": depth.bid_depth,
            "ask_depth": depth.ask_depth,
            "liquidity_quality": depth.liquidity_quality.value,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = db[self.collections["depth"]].insert_one(doc)
        return str(result.inserted_id)
    
    def get_latest_depth(
        self,
        symbol: str = "BTCUSDT"
    ) -> Optional[Dict]:
        """Get most recent depth snapshot."""
        db = self._get_db()
        
        doc = db[self.collections["depth"]].find_one(
            {"symbol": symbol},
            {"_id": 0},
            sort=[("created_at", DESCENDING)]
        )
        
        return doc
    
    def get_depth_history(
        self,
        symbol: str = "BTCUSDT",
        limit: int = 50
    ) -> List[Dict]:
        """Get depth snapshot history."""
        db = self._get_db()
        
        cursor = db[self.collections["depth"]].find(
            {"symbol": symbol},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ===== Liquidity Zones =====
    
    def save_liquidity_zones(
        self,
        zones: List[LiquidityZone],
        symbol: str = "BTCUSDT"
    ) -> int:
        """Save multiple liquidity zones."""
        if not zones:
            return 0
        
        db = self._get_db()
        
        docs = [{
            "symbol": symbol,
            "zone_type": z.zone_type.value,
            "mid_price": z.mid_price,
            "data": self._serialize(z),
            "created_at": datetime.now(timezone.utc).isoformat()
        } for z in zones]
        
        result = db[self.collections["zones"]].insert_many(docs)
        return len(result.inserted_ids)
    
    def get_liquidity_zones(
        self,
        symbol: str = "BTCUSDT",
        zone_type: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get recent liquidity zones."""
        db = self._get_db()
        
        query = {"symbol": symbol}
        if zone_type:
            query["zone_type"] = zone_type
        
        cursor = db[self.collections["zones"]].find(
            query,
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ===== Stop Clusters =====
    
    def save_stop_clusters(
        self,
        clusters: List[StopCluster],
        symbol: str = "BTCUSDT"
    ) -> int:
        """Save stop clusters."""
        if not clusters:
            return 0
        
        db = self._get_db()
        
        docs = [{
            "symbol": symbol,
            "side": c.side.value,
            "price_level": c.price_level,
            "cluster_strength": c.cluster_strength,
            "data": self._serialize(c),
            "created_at": datetime.now(timezone.utc).isoformat()
        } for c in clusters]
        
        result = db[self.collections["stops"]].insert_many(docs)
        return len(result.inserted_ids)
    
    def get_stop_clusters(
        self,
        symbol: str = "BTCUSDT",
        side: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get recent stop clusters."""
        db = self._get_db()
        
        query = {"symbol": symbol}
        if side:
            query["side"] = side
        
        cursor = db[self.collections["stops"]].find(
            query,
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ===== Liquidation Zones =====
    
    def save_liquidation_zones(
        self,
        zones: List[LiquidationZone],
        symbol: str = "BTCUSDT"
    ) -> int:
        """Save liquidation zones."""
        if not zones:
            return 0
        
        db = self._get_db()
        
        docs = [{
            "symbol": symbol,
            "position_type": z.position_type,
            "price_level": z.price_level,
            "cascade_risk": z.cascade_risk,
            "data": self._serialize(z),
            "created_at": datetime.now(timezone.utc).isoformat()
        } for z in zones]
        
        result = db[self.collections["liquidations"]].insert_many(docs)
        return len(result.inserted_ids)
    
    def get_liquidation_zones(
        self,
        symbol: str = "BTCUSDT",
        position_type: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get recent liquidation zones."""
        db = self._get_db()
        
        query = {"symbol": symbol}
        if position_type:
            query["position_type"] = position_type
        
        cursor = db[self.collections["liquidations"]].find(
            query,
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ===== Sweep Signals =====
    
    def save_sweep_signals(
        self,
        signals: List[SweepSignal],
        symbol: str = "BTCUSDT"
    ) -> int:
        """Save sweep signals."""
        if not signals:
            return 0
        
        db = self._get_db()
        
        docs = [{
            "symbol": symbol,
            "sweep_direction": s.sweep_direction.value,
            "sweep_probability": s.sweep_probability,
            "target_level": s.target_level,
            "data": self._serialize(s),
            "created_at": datetime.now(timezone.utc).isoformat()
        } for s in signals]
        
        result = db[self.collections["sweeps"]].insert_many(docs)
        return len(result.inserted_ids)
    
    def get_sweep_signals(
        self,
        symbol: str = "BTCUSDT",
        min_probability: float = 0.0,
        limit: int = 20
    ) -> List[Dict]:
        """Get recent sweep signals."""
        db = self._get_db()
        
        cursor = db[self.collections["sweeps"]].find(
            {
                "symbol": symbol,
                "sweep_probability": {"$gte": min_probability}
            },
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ===== Imbalances =====
    
    def save_imbalance(
        self,
        imbalance: LiquidityImbalance
    ) -> str:
        """Save liquidity imbalance."""
        db = self._get_db()
        
        doc = {
            "symbol": imbalance.symbol,
            "imbalance_score": imbalance.imbalance_score,
            "dominant_side": imbalance.dominant_side.value,
            "volatility_risk": imbalance.volatility_risk,
            "data": self._serialize(imbalance),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = db[self.collections["imbalances"]].insert_one(doc)
        return str(result.inserted_id)
    
    def get_imbalance_history(
        self,
        symbol: str = "BTCUSDT",
        limit: int = 50
    ) -> List[Dict]:
        """Get imbalance history."""
        db = self._get_db()
        
        cursor = db[self.collections["imbalances"]].find(
            {"symbol": symbol},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ===== Unified Snapshots =====
    
    def save_unified_snapshot(
        self,
        snapshot: UnifiedLiquiditySnapshot
    ) -> str:
        """Save unified liquidity snapshot."""
        db = self._get_db()
        
        doc = {
            "symbol": snapshot.symbol,
            "current_price": snapshot.current_price,
            "liquidity_quality": snapshot.liquidity_quality.value,
            "sweep_probability": snapshot.sweep_probability,
            "data": self._serialize(snapshot),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = db[self.collections["snapshots"]].insert_one(doc)
        return str(result.inserted_id)
    
    def get_latest_snapshot(
        self,
        symbol: str = "BTCUSDT"
    ) -> Optional[Dict]:
        """Get most recent unified snapshot."""
        db = self._get_db()
        
        doc = db[self.collections["snapshots"]].find_one(
            {"symbol": symbol},
            {"_id": 0},
            sort=[("created_at", DESCENDING)]
        )
        
        return doc
    
    def get_snapshot_history(
        self,
        symbol: str = "BTCUSDT",
        hours_back: int = 24,
        limit: int = 100
    ) -> List[Dict]:
        """Get snapshot history."""
        db = self._get_db()
        
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
        
        cursor = db[self.collections["snapshots"]].find(
            {
                "symbol": symbol,
                "created_at": {"$gte": cutoff}
            },
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ===== Cleanup =====
    
    def cleanup_old_data(
        self,
        hours_to_keep: int = 24
    ) -> Dict[str, int]:
        """Remove data older than specified hours."""
        db = self._get_db()
        
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_to_keep)).isoformat()
        
        deleted = {}
        for name, collection in self.collections.items():
            result = db[collection].delete_many({"created_at": {"$lt": cutoff}})
            deleted[name] = result.deleted_count
        
        return deleted
    
    def get_stats(self) -> Dict:
        """Get repository statistics."""
        db = self._get_db()
        
        stats = {}
        for name, collection in self.collections.items():
            count = db[collection].count_documents({})
            stats[name] = count
        
        return {
            "collections": stats,
            "total_documents": sum(stats.values())
        }
