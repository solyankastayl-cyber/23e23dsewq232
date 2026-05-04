"""
Alpha Repository
================

Хранение и получение alpha данных.
MongoDB storage для snapshots и history.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING

from .alpha_types import (
    AlphaSnapshot,
    AlphaSummary,
    AlphaHistoryQuery,
    AlphaResult
)


class AlphaRepository:
    """
    Repository для хранения alpha данных.
    
    Collections:
    - alpha_snapshots: текущие снимки alpha
    - alpha_history: история alpha по символам
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
        
        # Snapshots indexes
        db.alpha_snapshots.create_index([("symbol", 1), ("timeframe", 1)])
        db.alpha_snapshots.create_index([("created_at", DESCENDING)])
        
        # History indexes
        db.alpha_history.create_index([("symbol", 1), ("timeframe", 1), ("created_at", DESCENDING)])
        db.alpha_history.create_index([("alpha_id", 1), ("created_at", DESCENDING)])
    
    def save_snapshot(self, snapshot: AlphaSnapshot) -> str:
        """
        Сохранение snapshot.
        Обновляет существующий или создаёт новый.
        """
        db = self._get_db()
        
        doc = {
            "id": snapshot.id,
            "symbol": snapshot.symbol,
            "timeframe": snapshot.timeframe,
            "summary": snapshot.summary.model_dump(),
            "market_price": snapshot.market_price,
            "regime": snapshot.regime,
            "created_at": snapshot.created_at
        }
        
        # Upsert по symbol + timeframe
        result = db.alpha_snapshots.update_one(
            {"symbol": snapshot.symbol, "timeframe": snapshot.timeframe},
            {"$set": doc},
            upsert=True
        )
        
        # Also save to history
        self._save_to_history(snapshot)
        
        return snapshot.id
    
    def _save_to_history(self, snapshot: AlphaSnapshot):
        """Сохранение в историю"""
        db = self._get_db()
        
        # Save individual alpha results to history
        for alpha_result in snapshot.summary.alpha_results:
            doc = {
                "symbol": snapshot.symbol,
                "timeframe": snapshot.timeframe,
                "alpha_id": alpha_result.alpha_id,
                "alpha_name": alpha_result.alpha_name,
                "direction": alpha_result.direction.value,
                "strength": alpha_result.strength,
                "confidence": alpha_result.confidence,
                "regime_relevance": alpha_result.regime_relevance.value,
                "raw_value": alpha_result.raw_value,
                "normalized_value": alpha_result.normalized_value,
                "market_price": snapshot.market_price,
                "regime": snapshot.regime,
                "created_at": snapshot.created_at
            }
            db.alpha_history.insert_one(doc)
    
    def get_snapshot(self, symbol: str, timeframe: str = "1h") -> Optional[AlphaSnapshot]:
        """Получение последнего snapshot"""
        db = self._get_db()
        
        doc = db.alpha_snapshots.find_one(
            {"symbol": symbol, "timeframe": timeframe},
            {"_id": 0}
        )
        
        if not doc:
            return None
        
        # Reconstruct AlphaSummary
        summary_data = doc.get("summary", {})
        
        # Reconstruct alpha_results
        alpha_results = []
        for ar_data in summary_data.get("alpha_results", []):
            alpha_results.append(AlphaResult(
                alpha_id=ar_data.get("alpha_id", ""),
                alpha_name=ar_data.get("alpha_name", ""),
                direction=ar_data.get("direction", "NEUTRAL"),
                strength=ar_data.get("strength", 0),
                confidence=ar_data.get("confidence", 0),
                regime_relevance=ar_data.get("regime_relevance", "ALL"),
                raw_value=ar_data.get("raw_value", 0),
                normalized_value=ar_data.get("normalized_value", 0),
                metadata=ar_data.get("metadata", {})
            ))
        
        summary = AlphaSummary(
            symbol=summary_data.get("symbol", symbol),
            timeframe=summary_data.get("timeframe", timeframe),
            alpha_bias=summary_data.get("alpha_bias", "NEUTRAL"),
            alpha_confidence=summary_data.get("alpha_confidence", 0),
            alpha_strength=summary_data.get("alpha_strength", 0),
            trend_strength=summary_data.get("trend_strength", 0),
            trend_acceleration=summary_data.get("trend_acceleration", 0),
            trend_exhaustion=summary_data.get("trend_exhaustion", 0),
            breakout_pressure=summary_data.get("breakout_pressure", 0),
            volatility_compression=summary_data.get("volatility_compression", 0),
            volatility_expansion=summary_data.get("volatility_expansion", 0),
            reversal_pressure=summary_data.get("reversal_pressure", 0),
            volume_confirmation=summary_data.get("volume_confirmation", 0),
            volume_anomaly=summary_data.get("volume_anomaly", 0),
            liquidity_sweep=summary_data.get("liquidity_sweep", 0),
            alphas_count=summary_data.get("alphas_count", 0),
            long_signals=summary_data.get("long_signals", 0),
            short_signals=summary_data.get("short_signals", 0),
            neutral_signals=summary_data.get("neutral_signals", 0),
            alpha_results=alpha_results,
            notes=summary_data.get("notes", [])
        )
        
        return AlphaSnapshot(
            id=doc.get("id", ""),
            symbol=doc.get("symbol", symbol),
            timeframe=doc.get("timeframe", timeframe),
            summary=summary,
            market_price=doc.get("market_price", 0),
            regime=doc.get("regime", "UNKNOWN"),
            created_at=doc.get("created_at", datetime.utcnow())
        )
    
    def get_history(self, query: AlphaHistoryQuery) -> List[Dict[str, Any]]:
        """Получение истории alpha"""
        db = self._get_db()
        
        filter_query = {
            "symbol": query.symbol,
            "timeframe": query.timeframe
        }
        
        if query.alpha_id:
            filter_query["alpha_id"] = query.alpha_id
        
        if query.start_date:
            filter_query["created_at"] = {"$gte": query.start_date}
        
        if query.end_date:
            if "created_at" in filter_query:
                filter_query["created_at"]["$lte"] = query.end_date
            else:
                filter_query["created_at"] = {"$lte": query.end_date}
        
        cursor = db.alpha_history.find(
            filter_query,
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(query.limit)
        
        return list(cursor)
    
    def get_latest_by_symbol(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение последних записей по символу"""
        db = self._get_db()
        
        cursor = db.alpha_snapshots.find(
            {"symbol": symbol},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_alpha_by_id(self, alpha_id: str, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Получение истории конкретного alpha"""
        db = self._get_db()
        
        cursor = db.alpha_history.find(
            {"alpha_id": alpha_id, "symbol": symbol},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_all_snapshots(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение всех последних snapshots"""
        db = self._get_db()
        
        cursor = db.alpha_snapshots.find(
            {},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def delete_old_history(self, days: int = 30) -> int:
        """Удаление старой истории"""
        db = self._get_db()
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = db.alpha_history.delete_many({
            "created_at": {"$lt": cutoff}
        })
        
        return result.deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика repository"""
        db = self._get_db()
        
        return {
            "snapshots_count": db.alpha_snapshots.count_documents({}),
            "history_count": db.alpha_history.count_documents({}),
            "symbols": db.alpha_snapshots.distinct("symbol"),
            "timeframes": db.alpha_snapshots.distinct("timeframe")
        }
