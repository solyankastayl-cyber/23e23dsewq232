"""
Ensemble Repository
===================

Хранение и получение ensemble данных.
MongoDB storage для snapshots и history.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING

from .ensemble_types import (
    EnsembleSnapshot,
    EnsembleResult,
    EnsembleHistoryQuery,
    SignalDirection,
    SignalQuality
)


class EnsembleRepository:
    """
    Repository для хранения ensemble данных.
    
    Collections:
    - ensemble_snapshots: текущие снимки ensemble
    - ensemble_history: история ensemble сигналов
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
        db.ensemble_snapshots.create_index([("symbol", 1), ("timeframe", 1)])
        db.ensemble_snapshots.create_index([("created_at", DESCENDING)])
        
        # History indexes
        db.ensemble_history.create_index([("symbol", 1), ("timeframe", 1), ("created_at", DESCENDING)])
        db.ensemble_history.create_index([("signal_direction", 1)])
        db.ensemble_history.create_index([("signal_quality", 1)])
    
    def save_snapshot(self, snapshot: EnsembleSnapshot) -> str:
        """
        Сохранение snapshot.
        Обновляет существующий или создаёт новый.
        """
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
        
        # Upsert по symbol + timeframe
        db.ensemble_snapshots.update_one(
            {"symbol": snapshot.symbol, "timeframe": snapshot.timeframe},
            {"$set": doc},
            upsert=True
        )
        
        # Also save to history
        self._save_to_history(snapshot)
        
        return snapshot.id
    
    def _serialize_result(self, result: EnsembleResult) -> Dict[str, Any]:
        """Сериализация EnsembleResult в dict"""
        return {
            "symbol": result.symbol,
            "timeframe": result.timeframe,
            "signal": {
                "direction": result.signal.direction.value,
                "strength": result.signal.strength,
                "confidence": result.signal.confidence,
                "quality": result.signal.quality.value,
                "long_score": result.signal.long_score,
                "short_score": result.signal.short_score,
                "neutral_score": result.signal.neutral_score,
                "dominant_alpha": result.signal.dominant_alpha,
                "supporting_alphas": result.signal.supporting_alphas,
                "opposing_alphas": result.signal.opposing_alphas
            },
            "alpha_contributions": [
                {
                    "alpha_id": c.alpha_id,
                    "alpha_name": c.alpha_name,
                    "direction": c.direction,
                    "raw_strength": c.raw_strength,
                    "raw_confidence": c.raw_confidence,
                    "weight": c.weight,
                    "weighted_score": c.weighted_score,
                    "contribution_pct": c.contribution_pct,
                    "in_conflict": c.in_conflict
                }
                for c in result.alpha_contributions
            ],
            "conflict_report": {
                "has_conflict": result.conflict_report.has_conflict,
                "conflict_severity": result.conflict_report.conflict_severity,
                "conflicting_alphas": result.conflict_report.conflicting_alphas,
                "resolution_action": result.conflict_report.resolution_action,
                "confidence_penalty": result.conflict_report.confidence_penalty,
                "notes": result.conflict_report.notes
            },
            "regime": result.regime,
            "recommendation": result.recommendation,
            "action_score": result.action_score,
            "total_alphas": result.total_alphas,
            "aligned_alphas": result.aligned_alphas,
            "opposing_alphas": result.opposing_alphas,
            "neutral_alphas": result.neutral_alphas,
            "notes": result.notes,
            "warnings": result.warnings,
            "computed_at": result.computed_at.isoformat()
        }
    
    def _save_to_history(self, snapshot: EnsembleSnapshot):
        """Сохранение в историю"""
        db = self._get_db()
        
        result = snapshot.result
        
        doc = {
            "symbol": snapshot.symbol,
            "timeframe": snapshot.timeframe,
            "signal_direction": result.signal.direction.value,
            "signal_strength": result.signal.strength,
            "signal_confidence": result.signal.confidence,
            "signal_quality": result.signal.quality.value,
            "long_score": result.signal.long_score,
            "short_score": result.signal.short_score,
            "action_score": result.action_score,
            "has_conflict": result.conflict_report.has_conflict,
            "conflict_severity": result.conflict_report.conflict_severity,
            "regime": result.regime,
            "total_alphas": result.total_alphas,
            "aligned_alphas": result.aligned_alphas,
            "opposing_alphas": result.opposing_alphas,
            "recommendation": result.recommendation,
            "dominant_alpha": result.signal.dominant_alpha,
            "market_price": snapshot.market_price,
            "created_at": snapshot.created_at
        }
        
        db.ensemble_history.insert_one(doc)
    
    def get_snapshot(self, symbol: str, timeframe: str = "1h") -> Optional[Dict[str, Any]]:
        """Получение последнего snapshot"""
        db = self._get_db()
        
        doc = db.ensemble_snapshots.find_one(
            {"symbol": symbol, "timeframe": timeframe},
            {"_id": 0}
        )
        
        return doc
    
    def get_history(self, query: EnsembleHistoryQuery) -> List[Dict[str, Any]]:
        """Получение истории ensemble"""
        db = self._get_db()
        
        filter_query = {
            "symbol": query.symbol,
            "timeframe": query.timeframe
        }
        
        if query.direction:
            filter_query["signal_direction"] = query.direction.value
        
        if query.min_quality:
            quality_order = ["LOW", "MEDIUM", "HIGH", "PREMIUM"]
            min_idx = quality_order.index(query.min_quality.value)
            filter_query["signal_quality"] = {"$in": quality_order[min_idx:]}
        
        if query.start_date:
            filter_query["created_at"] = {"$gte": query.start_date}
        
        if query.end_date:
            if "created_at" in filter_query:
                filter_query["created_at"]["$lte"] = query.end_date
            else:
                filter_query["created_at"] = {"$lte": query.end_date}
        
        cursor = db.ensemble_history.find(
            filter_query,
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(query.limit)
        
        return list(cursor)
    
    def get_latest_by_symbol(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение последних записей по символу"""
        db = self._get_db()
        
        cursor = db.ensemble_history.find(
            {"symbol": symbol},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_signals_by_quality(
        self,
        quality: SignalQuality,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Получение сигналов по качеству"""
        db = self._get_db()
        
        cursor = db.ensemble_history.find(
            {"signal_quality": quality.value},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_all_snapshots(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение всех последних snapshots"""
        db = self._get_db()
        
        cursor = db.ensemble_snapshots.find(
            {},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def delete_old_history(self, days: int = 30) -> int:
        """Удаление старой истории"""
        db = self._get_db()
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = db.ensemble_history.delete_many({
            "created_at": {"$lt": cutoff}
        })
        
        return result.deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика repository"""
        db = self._get_db()
        
        # Aggregate stats
        pipeline = [
            {"$group": {
                "_id": "$signal_direction",
                "count": {"$sum": 1},
                "avg_strength": {"$avg": "$signal_strength"},
                "avg_confidence": {"$avg": "$signal_confidence"}
            }}
        ]
        
        direction_stats = list(db.ensemble_history.aggregate(pipeline))
        
        return {
            "snapshots_count": db.ensemble_snapshots.count_documents({}),
            "history_count": db.ensemble_history.count_documents({}),
            "symbols": db.ensemble_snapshots.distinct("symbol"),
            "timeframes": db.ensemble_snapshots.distinct("timeframe"),
            "direction_stats": direction_stats
        }
