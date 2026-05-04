"""
Failover Repository
===================

Хранение и получение данных failover.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING

from .failover_types import (
    FailoverEvent,
    FailoverEventType,
    ExchangeHealthMetrics,
    FailoverHistoryQuery
)


class FailoverRepository:
    """Repository для данных Failover Engine."""
    
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
        
        # Events collection
        db.failover_events.create_index([("timestamp", DESCENDING)])
        db.failover_events.create_index([("exchange", 1)])
        db.failover_events.create_index([("event_type", 1)])
        db.failover_events.create_index([("severity", 1)])
        
        # Health history collection
        db.exchange_health_history.create_index([("exchange", 1), ("timestamp", DESCENDING)])
        db.exchange_health_history.create_index([("timestamp", DESCENDING)])
        
        # Latency history collection
        db.latency_history.create_index([("exchange", 1), ("timestamp", DESCENDING)])
        
        # Rate limit breaches
        db.rate_limit_breaches.create_index([("exchange", 1), ("timestamp", DESCENDING)])
    
    def save_event(self, event: FailoverEvent) -> str:
        """Сохранить событие"""
        db = self._get_db()
        
        doc = {
            "id": event.id,
            "event_type": event.event_type.value,
            "exchange": event.exchange,
            "previous_status": event.previous_status.value if event.previous_status else None,
            "new_status": event.new_status.value if event.new_status else None,
            "action_triggered": event.action_triggered.value if event.action_triggered else None,
            "severity": event.severity,
            "details": event.details,
            "message": event.message,
            "timestamp": event.timestamp
        }
        
        db.failover_events.insert_one(doc)
        return event.id
    
    def save_health_snapshot(self, health: ExchangeHealthMetrics) -> None:
        """Сохранить снимок здоровья"""
        db = self._get_db()
        
        doc = {
            "exchange": health.exchange,
            "status": health.status.value,
            "health_score": health.health_score,
            "avg_latency_ms": health.avg_latency_ms,
            "p95_latency_ms": health.p95_latency_ms,
            "error_rate": health.error_rate,
            "error_count_1m": health.error_count_1m,
            "success_count_1m": health.success_count_1m,
            "api_available": health.api_available,
            "websocket_connected": health.websocket_connected,
            "timestamp": health.updated_at
        }
        
        db.exchange_health_history.insert_one(doc)
    
    def save_rate_limit_breach(
        self,
        exchange: str,
        limit_type: str,
        utilization_pct: float
    ) -> None:
        """Сохранить превышение rate limit"""
        db = self._get_db()
        
        doc = {
            "exchange": exchange,
            "limit_type": limit_type,
            "utilization_pct": utilization_pct,
            "timestamp": datetime.utcnow()
        }
        
        db.rate_limit_breaches.insert_one(doc)
    
    def get_events(self, query: FailoverHistoryQuery) -> List[Dict[str, Any]]:
        """Получить события по запросу"""
        db = self._get_db()
        
        filter_query = {}
        
        if query.exchange:
            filter_query["exchange"] = query.exchange
        if query.event_type:
            filter_query["event_type"] = query.event_type.value
        if query.severity:
            filter_query["severity"] = query.severity
        if query.start_date:
            filter_query["timestamp"] = {"$gte": query.start_date}
        if query.end_date:
            if "timestamp" in filter_query:
                filter_query["timestamp"]["$lte"] = query.end_date
            else:
                filter_query["timestamp"] = {"$lte": query.end_date}
        
        cursor = db.failover_events.find(
            filter_query,
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(query.limit)
        
        return list(cursor)
    
    def get_health_history(
        self,
        exchange: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Получить историю здоровья биржи"""
        db = self._get_db()
        
        cursor = db.exchange_health_history.find(
            {"exchange": exchange},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_rate_limit_breaches(
        self,
        exchange: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Получить историю превышений rate limit"""
        db = self._get_db()
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange
        
        cursor = db.rate_limit_breaches.find(
            filter_query,
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """Получить статистику за период"""
        db = self._get_db()
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Event counts by type
        event_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$event_type",
                "count": {"$sum": 1}
            }}
        ]
        event_counts = {
            r["_id"]: r["count"]
            for r in db.failover_events.aggregate(event_pipeline)
        }
        
        # Event counts by severity
        severity_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$severity",
                "count": {"$sum": 1}
            }}
        ]
        severity_counts = {
            r["_id"]: r["count"]
            for r in db.failover_events.aggregate(severity_pipeline)
        }
        
        # Health averages by exchange
        health_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$exchange",
                "avg_health_score": {"$avg": "$health_score"},
                "avg_latency_ms": {"$avg": "$avg_latency_ms"},
                "avg_error_rate": {"$avg": "$error_rate"},
                "snapshots": {"$sum": 1}
            }}
        ]
        health_by_exchange = {
            r["_id"]: {
                "avg_health_score": round(r["avg_health_score"], 4) if r["avg_health_score"] else 0,
                "avg_latency_ms": round(r["avg_latency_ms"], 2) if r["avg_latency_ms"] else 0,
                "avg_error_rate": round(r["avg_error_rate"], 4) if r["avg_error_rate"] else 0,
                "snapshots": r["snapshots"]
            }
            for r in db.exchange_health_history.aggregate(health_pipeline)
        }
        
        # Rate limit breaches count
        breach_count = db.rate_limit_breaches.count_documents(
            {"timestamp": {"$gte": cutoff}}
        )
        
        return {
            "period_days": days,
            "event_counts_by_type": event_counts,
            "event_counts_by_severity": severity_counts,
            "health_by_exchange": health_by_exchange,
            "rate_limit_breaches": breach_count,
            "total_events": sum(event_counts.values())
        }
    
    def get_exchange_comparison(self, days: int = 7) -> List[Dict[str, Any]]:
        """Сравнить биржи по метрикам"""
        db = self._get_db()
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$exchange",
                "avg_health": {"$avg": "$health_score"},
                "avg_latency": {"$avg": "$avg_latency_ms"},
                "avg_error_rate": {"$avg": "$error_rate"},
                "min_health": {"$min": "$health_score"},
                "max_latency": {"$max": "$avg_latency_ms"},
                "samples": {"$sum": 1}
            }},
            {"$sort": {"avg_health": -1}}
        ]
        
        results = list(db.exchange_health_history.aggregate(pipeline))
        
        return [
            {
                "exchange": r["_id"],
                "avg_health_score": round(r["avg_health"], 4) if r["avg_health"] else 0,
                "avg_latency_ms": round(r["avg_latency"], 2) if r["avg_latency"] else 0,
                "avg_error_rate": round(r["avg_error_rate"], 4) if r["avg_error_rate"] else 0,
                "min_health_score": round(r["min_health"], 4) if r["min_health"] else 0,
                "max_latency_ms": round(r["max_latency"], 2) if r["max_latency"] else 0,
                "samples": r["samples"]
            }
            for r in results
        ]
    
    def delete_old(self, days: int = 30) -> Dict[str, int]:
        """Удалить старые данные"""
        db = self._get_db()
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        events_deleted = db.failover_events.delete_many(
            {"timestamp": {"$lt": cutoff}}
        ).deleted_count
        
        health_deleted = db.exchange_health_history.delete_many(
            {"timestamp": {"$lt": cutoff}}
        ).deleted_count
        
        breaches_deleted = db.rate_limit_breaches.delete_many(
            {"timestamp": {"$lt": cutoff}}
        ).deleted_count
        
        return {
            "events_deleted": events_deleted,
            "health_deleted": health_deleted,
            "breaches_deleted": breaches_deleted
        }
