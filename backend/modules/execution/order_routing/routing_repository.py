"""
Routing Repository - PHASE 5.3
==============================

Persistence layer for routing data.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING

from .routing_types import (
    RoutingDecision,
    ExecutionPlan,
    RoutingEvent
)


class RoutingRepository:
    """Repository for routing data persistence."""
    
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
        
        # Routing decisions
        db.routing_decisions.create_index([("request_id", 1)], unique=True)
        db.routing_decisions.create_index([("symbol", 1), ("timestamp", -1)])
        db.routing_decisions.create_index([("selected_exchange", 1)])
        db.routing_decisions.create_index([("timestamp", -1)])
        
        # Execution plans
        db.execution_plans.create_index([("plan_id", 1)], unique=True)
        db.execution_plans.create_index([("symbol", 1), ("created_at", -1)])
        db.execution_plans.create_index([("status", 1)])
        
        # Routing events
        db.routing_events.create_index([("request_id", 1)])
        db.routing_events.create_index([("event_type", 1), ("timestamp", -1)])
        db.routing_events.create_index([("timestamp", -1)])
        
        # Venue statistics
        db.venue_stats.create_index([("exchange", 1), ("symbol", 1)])
    
    # ============================================
    # Routing Decisions
    # ============================================
    
    def save_decision(self, decision: RoutingDecision) -> str:
        """Save routing decision"""
        db = self._get_db()
        
        doc = decision.dict()
        doc["venue_scores"] = [s.dict() for s in decision.venue_scores]
        doc["saved_at"] = datetime.utcnow()
        
        db.routing_decisions.update_one(
            {"request_id": decision.request_id},
            {"$set": doc},
            upsert=True
        )
        
        return decision.request_id
    
    def get_decision(self, request_id: str) -> Optional[Dict]:
        """Get decision by request ID"""
        db = self._get_db()
        return db.routing_decisions.find_one(
            {"request_id": request_id},
            {"_id": 0}
        )
    
    def get_decisions(
        self,
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get routing decisions"""
        db = self._get_db()
        
        query = {}
        if symbol:
            query["symbol"] = symbol.upper()
        if exchange:
            query["selected_exchange"] = exchange.upper()
        
        cursor = db.routing_decisions.find(
            query,
            {"_id": 0, "venue_scores": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ============================================
    # Execution Plans
    # ============================================
    
    def save_plan(self, plan: ExecutionPlan) -> str:
        """Save execution plan"""
        db = self._get_db()
        
        doc = plan.dict()
        doc["legs"] = [leg.dict() for leg in plan.legs]
        doc["saved_at"] = datetime.utcnow()
        
        db.execution_plans.update_one(
            {"plan_id": plan.plan_id},
            {"$set": doc},
            upsert=True
        )
        
        return plan.plan_id
    
    def get_plan(self, plan_id: str) -> Optional[Dict]:
        """Get plan by ID"""
        db = self._get_db()
        return db.execution_plans.find_one(
            {"plan_id": plan_id},
            {"_id": 0}
        )
    
    def update_plan_status(self, plan_id: str, status: str) -> bool:
        """Update plan status"""
        db = self._get_db()
        result = db.execution_plans.update_one(
            {"plan_id": plan_id},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    def get_plans(
        self,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get execution plans"""
        db = self._get_db()
        
        query = {}
        if symbol:
            query["symbol"] = symbol.upper()
        if status:
            query["status"] = status
        
        cursor = db.execution_plans.find(
            query,
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ============================================
    # Routing Events
    # ============================================
    
    def save_event(self, event: RoutingEvent) -> str:
        """Save routing event"""
        db = self._get_db()
        
        doc = event.dict()
        result = db.routing_events.insert_one(doc)
        
        return str(result.inserted_id)
    
    def save_events_batch(self, events: List[RoutingEvent]) -> int:
        """Save multiple events"""
        if not events:
            return 0
        
        db = self._get_db()
        docs = [e.dict() for e in events]
        result = db.routing_events.insert_many(docs)
        
        return len(result.inserted_ids)
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        request_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get routing events"""
        db = self._get_db()
        
        query = {}
        if event_type:
            query["event_type"] = event_type
        if request_id:
            query["request_id"] = request_id
        
        cursor = db.routing_events.find(
            query,
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        
        return list(cursor)
    
    # ============================================
    # Venue Statistics
    # ============================================
    
    def update_venue_stats(
        self,
        exchange: str,
        symbol: str,
        stats: Dict
    ) -> None:
        """Update venue statistics"""
        db = self._get_db()
        
        db.venue_stats.update_one(
            {"exchange": exchange.upper(), "symbol": symbol.upper()},
            {
                "$set": {
                    **stats,
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
    
    def get_venue_stats(
        self,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Dict]:
        """Get venue statistics"""
        db = self._get_db()
        
        query = {}
        if exchange:
            query["exchange"] = exchange.upper()
        if symbol:
            query["symbol"] = symbol.upper()
        
        return list(db.venue_stats.find(query, {"_id": 0}))
    
    # ============================================
    # Analytics
    # ============================================
    
    def get_routing_analytics(self, days: int = 7) -> Dict:
        """Get routing analytics"""
        db = self._get_db()
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Decisions by exchange
        exchange_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$selected_exchange",
                "count": {"$sum": 1},
                "avg_confidence": {"$avg": "$confidence"},
                "avg_slippage_bps": {"$avg": "$expected_slippage_bps"}
            }}
        ]
        exchange_stats = list(db.routing_decisions.aggregate(exchange_pipeline))
        
        # Decisions by policy
        policy_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$policy_used",
                "count": {"$sum": 1}
            }}
        ]
        policy_stats = list(db.routing_decisions.aggregate(policy_pipeline))
        
        # Event types
        event_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$event_type",
                "count": {"$sum": 1}
            }}
        ]
        event_stats = list(db.routing_events.aggregate(event_pipeline))
        
        return {
            "period_days": days,
            "by_exchange": {
                s["_id"]: {
                    "count": s["count"],
                    "avg_confidence": round(s["avg_confidence"], 3),
                    "avg_slippage_bps": round(s["avg_slippage_bps"], 2)
                }
                for s in exchange_stats
            },
            "by_policy": {s["_id"]: s["count"] for s in policy_stats},
            "by_event_type": {s["_id"]: s["count"] for s in event_stats}
        }
    
    def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """Cleanup old routing data"""
        db = self._get_db()
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        decisions_deleted = db.routing_decisions.delete_many(
            {"timestamp": {"$lt": cutoff}}
        ).deleted_count
        
        events_deleted = db.routing_events.delete_many(
            {"timestamp": {"$lt": cutoff}}
        ).deleted_count
        
        plans_deleted = db.execution_plans.delete_many({
            "created_at": {"$lt": cutoff},
            "status": {"$in": ["COMPLETED", "FAILED", "CANCELLED"]}
        }).deleted_count
        
        return {
            "decisions_deleted": decisions_deleted,
            "events_deleted": events_deleted,
            "plans_deleted": plans_deleted
        }
