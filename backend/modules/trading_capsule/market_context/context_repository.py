"""
Context Repository
==================

Хранение и получение Market Context данных.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING

from .context_types import MarketContextSnapshot, ContextHistoryQuery


class ContextRepository:
    """Repository для Market Context данных."""
    
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
        db.context_snapshots.create_index([("symbol", 1), ("timeframe", 1)])
        db.context_snapshots.create_index([("created_at", DESCENDING)])
        db.context_history.create_index([("symbol", 1), ("timeframe", 1), ("created_at", DESCENDING)])
    
    def save_snapshot(self, snapshot: MarketContextSnapshot) -> str:
        db = self._get_db()
        
        doc = {
            "id": str(snapshot.computed_at.timestamp()),
            "symbol": snapshot.symbol,
            "timeframe": snapshot.timeframe,
            "context_score": snapshot.context_score,
            "long_bias_score": snapshot.long_bias_score,
            "short_bias_score": snapshot.short_bias_score,
            "primary_bias": snapshot.primary_bias,
            "context_quality": snapshot.context_quality,
            "funding_state": snapshot.funding.funding_state.value,
            "funding_extreme": snapshot.funding.funding_extreme,
            "oi_state": snapshot.oi.oi_state.value,
            "volatility_regime": snapshot.volatility.volatility_regime.value,
            "macro_regime": snapshot.macro.macro_regime.value,
            "risk_environment": snapshot.macro.risk_environment.value,
            "volume_profile_bias": snapshot.volume_profile.volume_profile_bias.value,
            "breakout_confidence_adj": snapshot.breakout_confidence_adj,
            "mean_reversion_confidence_adj": snapshot.mean_reversion_confidence_adj,
            "trend_confidence_adj": snapshot.trend_confidence_adj,
            "risk_multiplier": snapshot.risk_multiplier,
            "warnings": snapshot.warnings,
            "notes": snapshot.notes,
            "created_at": snapshot.computed_at
        }
        
        db.context_snapshots.update_one(
            {"symbol": snapshot.symbol, "timeframe": snapshot.timeframe},
            {"$set": doc},
            upsert=True
        )
        
        # Save to history
        db.context_history.insert_one(doc.copy())
        
        return doc["id"]
    
    def get_snapshot(self, symbol: str, timeframe: str = "1h") -> Optional[Dict[str, Any]]:
        db = self._get_db()
        return db.context_snapshots.find_one(
            {"symbol": symbol, "timeframe": timeframe},
            {"_id": 0}
        )
    
    def get_history(self, query: ContextHistoryQuery) -> List[Dict[str, Any]]:
        db = self._get_db()
        
        filter_query = {
            "symbol": query.symbol,
            "timeframe": query.timeframe
        }
        
        if query.start_date:
            filter_query["created_at"] = {"$gte": query.start_date}
        if query.end_date:
            if "created_at" in filter_query:
                filter_query["created_at"]["$lte"] = query.end_date
            else:
                filter_query["created_at"] = {"$lte": query.end_date}
        
        cursor = db.context_history.find(
            filter_query, {"_id": 0}
        ).sort("created_at", DESCENDING).limit(query.limit)
        
        return list(cursor)
    
    def get_stats(self) -> Dict[str, Any]:
        db = self._get_db()
        
        return {
            "snapshots_count": db.context_snapshots.count_documents({}),
            "history_count": db.context_history.count_documents({}),
            "symbols": db.context_snapshots.distinct("symbol")
        }
    
    def delete_old_history(self, days: int = 30) -> int:
        db = self._get_db()
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = db.context_history.delete_many({"created_at": {"$lt": cutoff}})
        return result.deleted_count
