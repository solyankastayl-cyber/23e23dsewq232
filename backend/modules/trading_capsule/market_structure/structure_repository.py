"""
Structure Repository
====================

Хранение и получение данных Market Structure.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING

from .structure_types import (
    StructureSnapshot,
    MarketStructureResult,
    StructureHistoryQuery,
    TrendStructure
)


class StructureRepository:
    """
    Repository для хранения Market Structure данных.
    
    Collections:
    - structure_snapshots: текущие снимки структуры
    - structure_history: история структуры
    """
    
    def __init__(self, mongo_uri: Optional[str] = None, db_name: str = "ta_engine"):
        self.mongo_uri = mongo_uri or os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        self.db_name = db_name
        self._client: Optional[MongoClient] = None
        self._db = None
    
    def _get_db(self):
        """Lazy connection to MongoDB"""
        if self._db is None:
            self._client = MongoClient(self.mongo_uri)
            self._db = self._client[self.db_name]
            self._ensure_indexes()
        return self._db
    
    def _ensure_indexes(self):
        """Создание индексов"""
        db = self._db
        
        db.structure_snapshots.create_index([("symbol", 1), ("timeframe", 1)])
        db.structure_snapshots.create_index([("created_at", DESCENDING)])
        
        db.structure_history.create_index([("symbol", 1), ("timeframe", 1), ("created_at", DESCENDING)])
        db.structure_history.create_index([("trend_structure", 1)])
    
    def save_snapshot(self, snapshot: StructureSnapshot) -> str:
        """Сохранение snapshot"""
        db = self._get_db()
        
        # Serialize result
        result_dict = self._serialize_result(snapshot.result)
        
        doc = {
            "id": snapshot.id,
            "symbol": snapshot.symbol,
            "timeframe": snapshot.timeframe,
            "result": result_dict,
            "market_price": snapshot.market_price,
            "created_at": snapshot.created_at
        }
        
        # Upsert
        db.structure_snapshots.update_one(
            {"symbol": snapshot.symbol, "timeframe": snapshot.timeframe},
            {"$set": doc},
            upsert=True
        )
        
        # Save to history
        self._save_to_history(snapshot)
        
        return snapshot.id
    
    def _serialize_result(self, result: MarketStructureResult) -> Dict[str, Any]:
        """Сериализация результата"""
        return {
            "symbol": result.symbol,
            "timeframe": result.timeframe,
            "trend_structure": result.trend_structure.value,
            "structure_confidence": result.structure_confidence,
            "bos_count": result.bos_count,
            "choch_count": result.choch_count,
            "active_liquidity_zones": result.active_liquidity_zones,
            "active_imbalances": result.active_imbalances,
            "current_price": result.current_price,
            "nearest_support": result.nearest_support,
            "nearest_resistance": result.nearest_resistance,
            "structure_bias": result.structure_bias,
            "key_levels": result.key_levels,
            "notes": result.notes,
            "warnings": result.warnings,
            "bos_events": [
                {
                    "event_type": e.event_type.value,
                    "price": e.price,
                    "strength": e.strength,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in result.bos_events[-5:]  # Last 5
            ],
            "choch_events": [
                {
                    "event_type": e.event_type.value,
                    "price": e.price,
                    "strength": e.strength,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in result.choch_events[-3:]  # Last 3
            ],
            "liquidity_zones": [
                {
                    "zone_type": z.zone_type.value,
                    "price_level": z.price_level,
                    "strength": z.strength,
                    "swept": z.swept
                }
                for z in result.liquidity_zones[:5]  # Top 5
            ],
            "support_clusters": [
                {
                    "price_center": c.price_center,
                    "strength": c.strength,
                    "sources": c.sources
                }
                for c in result.support_clusters[:3]
            ],
            "resistance_clusters": [
                {
                    "price_center": c.price_center,
                    "strength": c.strength,
                    "sources": c.sources
                }
                for c in result.resistance_clusters[:3]
            ],
            "computed_at": result.computed_at.isoformat()
        }
    
    def _save_to_history(self, snapshot: StructureSnapshot):
        """Сохранение в историю"""
        db = self._get_db()
        
        result = snapshot.result
        
        doc = {
            "symbol": snapshot.symbol,
            "timeframe": snapshot.timeframe,
            "trend_structure": result.trend_structure.value,
            "structure_confidence": result.structure_confidence,
            "bos_count": result.bos_count,
            "choch_count": result.choch_count,
            "active_liquidity_zones": result.active_liquidity_zones,
            "active_imbalances": result.active_imbalances,
            "structure_bias": result.structure_bias,
            "nearest_support": result.nearest_support,
            "nearest_resistance": result.nearest_resistance,
            "market_price": snapshot.market_price,
            "created_at": snapshot.created_at
        }
        
        db.structure_history.insert_one(doc)
    
    def get_snapshot(self, symbol: str, timeframe: str = "1h") -> Optional[Dict[str, Any]]:
        """Получение snapshot"""
        db = self._get_db()
        
        doc = db.structure_snapshots.find_one(
            {"symbol": symbol, "timeframe": timeframe},
            {"_id": 0}
        )
        
        return doc
    
    def get_history(self, query: StructureHistoryQuery) -> List[Dict[str, Any]]:
        """Получение истории"""
        db = self._get_db()
        
        filter_query = {
            "symbol": query.symbol,
            "timeframe": query.timeframe
        }
        
        if query.structure_type:
            filter_query["trend_structure"] = query.structure_type.value
        
        if query.start_date:
            filter_query["created_at"] = {"$gte": query.start_date}
        
        if query.end_date:
            if "created_at" in filter_query:
                filter_query["created_at"]["$lte"] = query.end_date
            else:
                filter_query["created_at"] = {"$lte": query.end_date}
        
        cursor = db.structure_history.find(
            filter_query,
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(query.limit)
        
        return list(cursor)
    
    def get_all_snapshots(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение всех snapshots"""
        db = self._get_db()
        
        cursor = db.structure_snapshots.find(
            {},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика"""
        db = self._get_db()
        
        pipeline = [
            {"$group": {
                "_id": "$trend_structure",
                "count": {"$sum": 1}
            }}
        ]
        
        structure_stats = list(db.structure_history.aggregate(pipeline))
        
        return {
            "snapshots_count": db.structure_snapshots.count_documents({}),
            "history_count": db.structure_history.count_documents({}),
            "symbols": db.structure_snapshots.distinct("symbol"),
            "structure_distribution": structure_stats
        }
    
    def delete_old_history(self, days: int = 30) -> int:
        """Удаление старой истории"""
        db = self._get_db()
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = db.structure_history.delete_many({
            "created_at": {"$lt": cutoff}
        })
        
        return result.deleted_count
