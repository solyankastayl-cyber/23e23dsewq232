"""
Market Data Repository - PHASE 5.2
===================================

Persistence layer for market data.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING, ASCENDING

from .market_data_types import (
    MarketTick,
    MarketCandle,
    MarketOrderbook,
    MarketSnapshot
)


class MarketDataRepository:
    """Repository for market data persistence."""
    
    def __init__(self, mongo_uri: Optional[str] = None, db_name: str = "ta_engine"):
        self.mongo_uri = mongo_uri or os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        self.db_name = db_name
        self._client: Optional[MongoClient] = None
        self._db = None
    
    def _get_db(self):
        if self._db is None:
            self._client = MongoClient(self.mongo_uri)
            self._db = self._client[self.db_name]
            self._ensure_indexes()
        return self._db
    
    def _ensure_indexes(self):
        db = self._db
        
        # Candles collection
        db.market_candles.create_index([
            ("exchange", 1), ("symbol", 1), ("timeframe", 1), ("start_time", -1)
        ])
        db.market_candles.create_index([("start_time", -1)])
        
        # Ticks collection (with TTL for auto-cleanup)
        db.market_ticks.create_index([
            ("exchange", 1), ("symbol", 1), ("timestamp", -1)
        ])
        db.market_ticks.create_index(
            [("timestamp", 1)],
            expireAfterSeconds=86400  # 24 hour TTL
        )
        
        # Snapshots collection
        db.market_snapshots.create_index([("symbol", 1), ("timestamp", -1)])
        db.market_snapshots.create_index(
            [("timestamp", 1)],
            expireAfterSeconds=3600  # 1 hour TTL for snapshots
        )
        
        # Orderbook snapshots
        db.market_orderbooks.create_index([
            ("exchange", 1), ("symbol", 1), ("timestamp", -1)
        ])
        db.market_orderbooks.create_index(
            [("timestamp", 1)],
            expireAfterSeconds=300  # 5 minute TTL
        )
    
    # ============================================
    # Candles
    # ============================================
    
    def save_candle(self, candle: MarketCandle) -> str:
        """Save or update candle"""
        db = self._get_db()
        
        doc = {
            "exchange": candle.exchange,
            "symbol": candle.symbol,
            "timeframe": candle.timeframe,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
            "quote_volume": candle.quote_volume,
            "trades_count": candle.trades_count,
            "start_time": candle.start_time,
            "end_time": candle.end_time,
            "is_closed": candle.is_closed,
            "updated_at": datetime.utcnow()
        }
        
        # Upsert by exchange + symbol + timeframe + start_time
        db.market_candles.update_one(
            {
                "exchange": candle.exchange,
                "symbol": candle.symbol,
                "timeframe": candle.timeframe,
                "start_time": candle.start_time
            },
            {"$set": doc},
            upsert=True
        )
        
        return f"{candle.exchange}:{candle.symbol}:{candle.timeframe}:{candle.start_time}"
    
    def save_candles_batch(self, candles: List[MarketCandle]) -> int:
        """Save multiple candles"""
        count = 0
        for candle in candles:
            self.save_candle(candle)
            count += 1
        return count
    
    def get_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Get historical candles"""
        db = self._get_db()
        
        query = {
            "exchange": exchange.upper(),
            "symbol": symbol.upper(),
            "timeframe": timeframe
        }
        
        if start_time:
            query["start_time"] = {"$gte": start_time}
        if end_time:
            if "start_time" in query:
                query["start_time"]["$lte"] = end_time
            else:
                query["start_time"] = {"$lte": end_time}
        
        cursor = db.market_candles.find(
            query,
            {"_id": 0}
        ).sort("start_time", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_latest_candle(
        self,
        exchange: str,
        symbol: str,
        timeframe: str
    ) -> Optional[Dict[str, Any]]:
        """Get latest candle"""
        db = self._get_db()
        
        return db.market_candles.find_one(
            {
                "exchange": exchange.upper(),
                "symbol": symbol.upper(),
                "timeframe": timeframe
            },
            {"_id": 0},
            sort=[("start_time", DESCENDING)]
        )
    
    # ============================================
    # Ticks
    # ============================================
    
    def save_tick(self, tick: MarketTick) -> str:
        """Save market tick"""
        db = self._get_db()
        
        doc = {
            "exchange": tick.exchange,
            "symbol": tick.symbol,
            "price": tick.price,
            "bid": tick.bid,
            "ask": tick.ask,
            "spread": tick.spread,
            "volume": tick.volume,
            "side": tick.side,
            "trade_id": tick.trade_id,
            "timestamp": tick.timestamp
        }
        
        result = db.market_ticks.insert_one(doc)
        return str(result.inserted_id)
    
    def get_ticks(
        self,
        exchange: str,
        symbol: str,
        start_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get tick history"""
        db = self._get_db()
        
        query = {
            "exchange": exchange.upper(),
            "symbol": symbol.upper()
        }
        
        if start_time:
            query["timestamp"] = {"$gte": start_time}
        
        cursor = db.market_ticks.find(
            query,
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ============================================
    # Snapshots
    # ============================================
    
    def save_snapshot(self, snapshot: MarketSnapshot) -> str:
        """Save market snapshot"""
        db = self._get_db()
        
        doc = snapshot.dict()
        doc["saved_at"] = datetime.utcnow()
        
        result = db.market_snapshots.insert_one(doc)
        return str(result.inserted_id)
    
    def get_snapshots(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get snapshot history"""
        db = self._get_db()
        
        query = {"symbol": symbol.upper()}
        
        if start_time:
            query["timestamp"] = {"$gte": start_time}
        
        cursor = db.market_snapshots.find(
            query,
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_latest_snapshot(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest snapshot for symbol"""
        db = self._get_db()
        
        return db.market_snapshots.find_one(
            {"symbol": symbol.upper()},
            {"_id": 0},
            sort=[("timestamp", DESCENDING)]
        )
    
    # ============================================
    # Orderbooks
    # ============================================
    
    def save_orderbook(self, orderbook: MarketOrderbook) -> str:
        """Save orderbook snapshot"""
        db = self._get_db()
        
        doc = {
            "exchange": orderbook.exchange,
            "symbol": orderbook.symbol,
            "best_bid": orderbook.best_bid,
            "best_ask": orderbook.best_ask,
            "spread": orderbook.spread,
            "spread_bps": orderbook.spread_bps,
            "mid_price": orderbook.mid_price,
            "bid_depth": orderbook.bid_depth,
            "ask_depth": orderbook.ask_depth,
            "imbalance": orderbook.imbalance,
            "bids_count": len(orderbook.bids),
            "asks_count": len(orderbook.asks),
            "timestamp": orderbook.timestamp
        }
        
        result = db.market_orderbooks.insert_one(doc)
        return str(result.inserted_id)
    
    def get_orderbook_history(
        self,
        exchange: str,
        symbol: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get orderbook snapshot history"""
        db = self._get_db()
        
        cursor = db.market_orderbooks.find(
            {
                "exchange": exchange.upper(),
                "symbol": symbol.upper()
            },
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ============================================
    # Statistics
    # ============================================
    
    def get_candle_stats(self, symbol: str, timeframe: str = "1h", days: int = 7) -> Dict:
        """Get candle statistics"""
        db = self._get_db()
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {"$match": {
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "start_time": {"$gte": cutoff}
            }},
            {"$group": {
                "_id": "$exchange",
                "count": {"$sum": 1},
                "avg_volume": {"$avg": "$volume"},
                "total_volume": {"$sum": "$volume"},
                "high": {"$max": "$high"},
                "low": {"$min": "$low"}
            }}
        ]
        
        results = list(db.market_candles.aggregate(pipeline))
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "period_days": days,
            "by_exchange": {
                r["_id"]: {
                    "candle_count": r["count"],
                    "avg_volume": round(r["avg_volume"], 2),
                    "total_volume": round(r["total_volume"], 2),
                    "period_high": r["high"],
                    "period_low": r["low"]
                }
                for r in results
            }
        }
    
    def cleanup_old_data(self, days: int = 7) -> Dict[str, int]:
        """Cleanup old market data"""
        db = self._get_db()
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Note: TTL indexes handle most cleanup automatically
        # This is for manual cleanup of candles
        
        candles_deleted = db.market_candles.delete_many({
            "start_time": {"$lt": cutoff},
            "is_closed": True
        }).deleted_count
        
        return {
            "candles_deleted": candles_deleted
        }
