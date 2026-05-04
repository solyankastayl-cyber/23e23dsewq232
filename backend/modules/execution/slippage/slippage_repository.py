"""
Slippage Repository
===================

Хранение и получение данных об исполнении.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING

from .slippage_types import (
    ExecutionSnapshot,
    ExecutionAnalysis,
    ExecutionHistoryQuery,
    ExecutionGrade
)


class SlippageRepository:
    """Repository для данных Slippage Engine."""
    
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
        db.execution_snapshots.create_index([("order_id", 1)], unique=True)
        db.execution_snapshots.create_index([("symbol", 1)])
        db.execution_snapshots.create_index([("exchange", 1)])
        db.execution_snapshots.create_index([("created_at", DESCENDING)])
        db.execution_snapshots.create_index([("execution_grade", 1)])
    
    def save(self, snapshot: ExecutionSnapshot) -> str:
        db = self._get_db()
        
        doc = {
            "id": snapshot.id,
            "order_id": snapshot.order_id,
            "symbol": snapshot.symbol,
            "exchange": snapshot.exchange,
            "side": snapshot.analysis.side,
            "execution_score": snapshot.analysis.execution_score,
            "execution_grade": snapshot.analysis.execution_grade.value,
            "slippage_bps": snapshot.analysis.slippage.slippage_bps,
            "slippage_percent": snapshot.analysis.slippage.slippage_percent,
            "slippage_direction": snapshot.analysis.slippage.direction.value,
            "total_latency_ms": snapshot.analysis.latency.total_latency_ms,
            "latency_grade": snapshot.analysis.latency.latency_grade,
            "fill_quality": snapshot.analysis.fill_analysis.fill_quality.value,
            "fill_rate": snapshot.analysis.fill_analysis.fill_rate,
            "liquidity_impact": snapshot.analysis.liquidity_impact.impact_level.value,
            "liquidity_score": snapshot.analysis.liquidity_impact.liquidity_score,
            "market_conditions": snapshot.analysis.market_conditions,
            "order_type": snapshot.analysis.order_type,
            "recommendations": snapshot.analysis.recommendations,
            "warnings": snapshot.analysis.warnings,
            "created_at": snapshot.created_at
        }
        
        # Upsert by order_id
        db.execution_snapshots.update_one(
            {"order_id": snapshot.order_id},
            {"$set": doc},
            upsert=True
        )
        
        return snapshot.order_id
    
    def get_by_order_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        db = self._get_db()
        return db.execution_snapshots.find_one(
            {"order_id": order_id},
            {"_id": 0}
        )
    
    def get_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        db = self._get_db()
        cursor = db.execution_snapshots.find(
            {"symbol": symbol},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        return list(cursor)
    
    def get_by_exchange(self, exchange: str, limit: int = 50) -> List[Dict[str, Any]]:
        db = self._get_db()
        cursor = db.execution_snapshots.find(
            {"exchange": exchange},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        return list(cursor)
    
    def get_history(self, query: ExecutionHistoryQuery) -> List[Dict[str, Any]]:
        db = self._get_db()
        
        filter_query = {}
        
        if query.symbol:
            filter_query["symbol"] = query.symbol
        if query.exchange:
            filter_query["exchange"] = query.exchange
        if query.min_grade:
            grade_order = ["A+", "A", "B", "C", "D", "F"]
            min_idx = grade_order.index(query.min_grade.value)
            filter_query["execution_grade"] = {"$in": grade_order[:min_idx+1]}
        if query.start_date:
            filter_query["created_at"] = {"$gte": query.start_date}
        if query.end_date:
            if "created_at" in filter_query:
                filter_query["created_at"]["$lte"] = query.end_date
            else:
                filter_query["created_at"] = {"$lte": query.end_date}
        
        cursor = db.execution_snapshots.find(
            filter_query,
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(query.limit)
        
        return list(cursor)
    
    def get_stats(self, symbol: Optional[str] = None, exchange: Optional[str] = None) -> Dict[str, Any]:
        db = self._get_db()
        
        match_stage = {}
        if symbol:
            match_stage["symbol"] = symbol
        if exchange:
            match_stage["exchange"] = exchange
        
        pipeline = [
            {"$match": match_stage} if match_stage else {"$match": {}},
            {"$group": {
                "_id": None,
                "count": {"$sum": 1},
                "avg_slippage_bps": {"$avg": "$slippage_bps"},
                "avg_latency_ms": {"$avg": "$total_latency_ms"},
                "avg_score": {"$avg": "$execution_score"},
                "avg_fill_rate": {"$avg": "$fill_rate"}
            }}
        ]
        
        result = list(db.execution_snapshots.aggregate(pipeline))
        
        if result:
            stats = result[0]
            del stats["_id"]
        else:
            stats = {
                "count": 0,
                "avg_slippage_bps": 0,
                "avg_latency_ms": 0,
                "avg_score": 0,
                "avg_fill_rate": 0
            }
        
        # Grade distribution
        grade_pipeline = [
            {"$match": match_stage} if match_stage else {"$match": {}},
            {"$group": {
                "_id": "$execution_grade",
                "count": {"$sum": 1}
            }}
        ]
        
        grade_dist = list(db.execution_snapshots.aggregate(grade_pipeline))
        stats["grade_distribution"] = {g["_id"]: g["count"] for g in grade_dist}
        
        return stats
    
    def get_exchange_comparison(self) -> List[Dict[str, Any]]:
        db = self._get_db()
        
        pipeline = [
            {"$group": {
                "_id": "$exchange",
                "count": {"$sum": 1},
                "avg_slippage_bps": {"$avg": "$slippage_bps"},
                "avg_latency_ms": {"$avg": "$total_latency_ms"},
                "avg_score": {"$avg": "$execution_score"}
            }},
            {"$sort": {"avg_score": -1}}
        ]
        
        return list(db.execution_snapshots.aggregate(pipeline))
    
    def delete_old(self, days: int = 30) -> int:
        db = self._get_db()
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = db.execution_snapshots.delete_many({"created_at": {"$lt": cutoff}})
        return result.deleted_count
