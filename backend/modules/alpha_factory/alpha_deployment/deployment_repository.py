"""
PHASE 13.7 - Deployment Repository
====================================
MongoDB persistence for Alpha Deployment.

Collections:
- alpha_deployments: Deployed factors
- alpha_signals_live: Live signals
- alpha_deployment_history: Deployment history
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta

from core.database import MongoRepository, get_database

from .deployment_types import (
    DeployedAlpha,
    AlphaSignal,
    DeploymentDecision,
    DeploymentStatus,
    DeploymentSnapshot
)


class DeploymentRepository(MongoRepository):
    """
    Repository for Alpha Deployment data.
    """
    
    def __init__(self):
        super().__init__()
        self.collection_name = "alpha_deployments"
        self._init_indexes()
    
    def _init_indexes(self):
        """Initialize MongoDB indexes."""
        if not self.connected:
            return
        
        try:
            db = self.db
            if db is None:
                return
            
            # Deployments collection
            db.alpha_deployments.create_index([("deployment_id", 1)], unique=True)
            db.alpha_deployments.create_index([("factor_id", 1)], unique=True)
            db.alpha_deployments.create_index([("status", 1)])
            db.alpha_deployments.create_index([("factor_family", 1)])
            db.alpha_deployments.create_index([("composite_score", -1)])
            
            # Signals collection
            db.alpha_signals_live.create_index([("signal_id", 1)], unique=True)
            db.alpha_signals_live.create_index([("deployment_id", 1)])
            db.alpha_signals_live.create_index([("symbol", 1), ("timestamp", -1)])
            db.alpha_signals_live.create_index([("timestamp", -1)])
            # TTL index - signals expire after 24 hours
            db.alpha_signals_live.create_index(
                [("timestamp", 1)],
                expireAfterSeconds=86400
            )
            
            # History collection
            db.alpha_deployment_history.create_index([("decision_id", 1)], unique=True)
            db.alpha_deployment_history.create_index([("factor_id", 1)])
            db.alpha_deployment_history.create_index([("decided_at", -1)])
            db.alpha_deployment_history.create_index([("action", 1)])
            
            # Snapshots
            db.alpha_deployment_snapshots.create_index([("snapshot_id", 1)], unique=True)
            db.alpha_deployment_snapshots.create_index([("created_at", -1)])
            
            print("[DeploymentRepository] Indexes created")
            
        except Exception as e:
            print(f"[DeploymentRepository] Index error: {e}")
    
    # ========== Deployment CRUD ==========
    
    def save_deployment(self, deployment: DeployedAlpha) -> bool:
        """Save or update a deployment."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = deployment.to_dict()
            doc["_updated_at"] = datetime.now(timezone.utc)
            
            db.alpha_deployments.update_one(
                {"factor_id": deployment.factor_id},
                {"$set": doc},
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"[DeploymentRepository] Save error: {e}")
            return False
    
    def get_deployment(self, factor_id: str) -> Optional[DeployedAlpha]:
        """Get deployment by factor ID."""
        if not self.connected:
            return None
        
        try:
            db = self.db
            if db is None:
                return None
            
            doc = db.alpha_deployments.find_one(
                {"factor_id": factor_id},
                {"_id": 0, "_updated_at": 0, "_created_at": 0}
            )
            
            if doc:
                return DeployedAlpha.from_dict(doc)
            return None
            
        except Exception as e:
            print(f"[DeploymentRepository] Get error: {e}")
            return None
    
    def get_deployment_by_id(self, deployment_id: str) -> Optional[DeployedAlpha]:
        """Get deployment by deployment ID."""
        if not self.connected:
            return None
        
        try:
            db = self.db
            if db is None:
                return None
            
            doc = db.alpha_deployments.find_one(
                {"deployment_id": deployment_id},
                {"_id": 0, "_updated_at": 0, "_created_at": 0}
            )
            
            if doc:
                return DeployedAlpha.from_dict(doc)
            return None
            
        except Exception as e:
            print(f"[DeploymentRepository] Get by ID error: {e}")
            return None
    
    def get_deployments(
        self,
        status: Optional[DeploymentStatus] = None,
        family: Optional[str] = None,
        active_only: bool = False,
        shadow_only: bool = False,
        limit: int = 100
    ) -> List[DeployedAlpha]:
        """Get deployments with filters."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            query = {}
            if status:
                query["status"] = status.value
            if family:
                query["factor_family"] = family
            if active_only:
                query["status"] = DeploymentStatus.ACTIVE.value
            if shadow_only:
                query["status"] = DeploymentStatus.SHADOW.value
            
            cursor = db.alpha_deployments.find(
                query,
                {"_id": 0, "_updated_at": 0, "_created_at": 0}
            ).sort("composite_score", -1).limit(limit)
            
            return [DeployedAlpha.from_dict(doc) for doc in cursor]
            
        except Exception as e:
            print(f"[DeploymentRepository] Get deployments error: {e}")
            return []
    
    def get_active_deployments(self) -> List[DeployedAlpha]:
        """Get all active deployments."""
        return self.get_deployments(status=DeploymentStatus.ACTIVE, limit=500)
    
    def get_shadow_deployments(self) -> List[DeployedAlpha]:
        """Get all shadow deployments."""
        return self.get_deployments(status=DeploymentStatus.SHADOW, limit=500)
    
    def update_deployment_status(
        self,
        factor_id: str,
        status: DeploymentStatus,
        reason: Optional[str] = None
    ) -> bool:
        """Update deployment status."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            update = {
                "status": status.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            if reason:
                update["pause_reason"] = reason
            
            if status == DeploymentStatus.ACTIVE:
                update["deployed_at"] = datetime.now(timezone.utc).isoformat()
                update["shadow_mode"] = False
            elif status == DeploymentStatus.SHADOW:
                update["shadow_mode"] = True
            
            result = db.alpha_deployments.update_one(
                {"factor_id": factor_id},
                {"$set": update}
            )
            return result.modified_count > 0
            
        except Exception as e:
            print(f"[DeploymentRepository] Update status error: {e}")
            return False
    
    def delete_deployment(self, factor_id: str) -> bool:
        """Delete a deployment."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            result = db.alpha_deployments.delete_one({"factor_id": factor_id})
            return result.deleted_count > 0
            
        except Exception as e:
            print(f"[DeploymentRepository] Delete error: {e}")
            return False
    
    def count_by_status(self) -> Dict[str, int]:
        """Count deployments by status."""
        if not self.connected:
            return {}
        
        try:
            db = self.db
            if db is None:
                return {}
            
            pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            
            result = {}
            for doc in db.alpha_deployments.aggregate(pipeline):
                result[doc["_id"]] = doc["count"]
            
            return result
            
        except Exception as e:
            print(f"[DeploymentRepository] Count error: {e}")
            return {}
    
    def count_by_family(self) -> Dict[str, int]:
        """Count deployments by family."""
        if not self.connected:
            return {}
        
        try:
            db = self.db
            if db is None:
                return {}
            
            pipeline = [
                {"$match": {"status": {"$in": ["active", "shadow"]}}},
                {"$group": {"_id": "$factor_family", "count": {"$sum": 1}}}
            ]
            
            result = {}
            for doc in db.alpha_deployments.aggregate(pipeline):
                if doc["_id"]:
                    result[doc["_id"]] = doc["count"]
            
            return result
            
        except Exception as e:
            print(f"[DeploymentRepository] Count by family error: {e}")
            return {}
    
    # ========== Signal CRUD ==========
    
    def save_signal(self, signal: AlphaSignal) -> bool:
        """Save a live signal."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = signal.to_dict()
            db.alpha_signals_live.insert_one(doc)
            return True
            
        except Exception as e:
            print(f"[DeploymentRepository] Save signal error: {e}")
            return False
    
    def save_signals_batch(self, signals: List[AlphaSignal]) -> int:
        """Save multiple signals."""
        if not self.connected or not signals:
            return 0
        
        try:
            db = self.db
            if db is None:
                return 0
            
            docs = [s.to_dict() for s in signals]
            result = db.alpha_signals_live.insert_many(docs)
            return len(result.inserted_ids)
            
        except Exception as e:
            print(f"[DeploymentRepository] Save signals batch error: {e}")
            return 0
    
    def get_signals(
        self,
        symbol: Optional[str] = None,
        deployment_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AlphaSignal]:
        """Get recent signals."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            query = {}
            if symbol:
                query["symbol"] = symbol
            if deployment_id:
                query["deployment_id"] = deployment_id
            
            cursor = db.alpha_signals_live.find(
                query,
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit)
            
            return [AlphaSignal.from_dict(doc) for doc in cursor]
            
        except Exception as e:
            print(f"[DeploymentRepository] Get signals error: {e}")
            return []
    
    def get_recent_signals(self, symbol: str, hours: int = 1) -> List[AlphaSignal]:
        """Get signals from last N hours."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            cursor = db.alpha_signals_live.find(
                {
                    "symbol": symbol,
                    "timestamp": {"$gte": cutoff.isoformat()}
                },
                {"_id": 0}
            ).sort("timestamp", -1)
            
            return [AlphaSignal.from_dict(doc) for doc in cursor]
            
        except Exception as e:
            print(f"[DeploymentRepository] Get recent signals error: {e}")
            return []
    
    def count_signals(self, hours: int = 24) -> int:
        """Count signals in time window."""
        if not self.connected:
            return 0
        
        try:
            db = self.db
            if db is None:
                return 0
            
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            return db.alpha_signals_live.count_documents({
                "timestamp": {"$gte": cutoff.isoformat()}
            })
            
        except Exception as e:
            return 0
    
    # ========== History ==========
    
    def save_decision(self, decision: DeploymentDecision) -> bool:
        """Save deployment decision to history."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = decision.to_dict()
            db.alpha_deployment_history.insert_one(doc)
            return True
            
        except Exception as e:
            print(f"[DeploymentRepository] Save decision error: {e}")
            return False
    
    def get_history(
        self,
        factor_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get deployment history."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            query = {}
            if factor_id:
                query["factor_id"] = factor_id
            if action:
                query["action"] = action
            
            cursor = db.alpha_deployment_history.find(
                query,
                {"_id": 0}
            ).sort("decided_at", -1).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            print(f"[DeploymentRepository] Get history error: {e}")
            return []
    
    # ========== Snapshots ==========
    
    def save_snapshot(self, snapshot: DeploymentSnapshot) -> bool:
        """Save deployment snapshot."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = snapshot.to_dict()
            db.alpha_deployment_snapshots.insert_one(doc)
            return True
            
        except Exception as e:
            print(f"[DeploymentRepository] Save snapshot error: {e}")
            return False
    
    def get_snapshots(self, limit: int = 10) -> List[Dict]:
        """Get recent snapshots."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            cursor = db.alpha_deployment_snapshots.find(
                {},
                {"_id": 0}
            ).sort("created_at", -1).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            print(f"[DeploymentRepository] Get snapshots error: {e}")
            return []
    
    # ========== Stats ==========
    
    def get_stats(self) -> Dict:
        """Get repository statistics."""
        if not self.connected:
            return {"connected": False}
        
        try:
            db = self.db
            if db is None:
                return {"connected": False}
            
            status_counts = self.count_by_status()
            family_counts = self.count_by_family()
            
            total = db.alpha_deployments.count_documents({})
            signals_24h = self.count_signals(24)
            history_count = db.alpha_deployment_history.count_documents({})
            
            # Average metrics
            pipeline = [
                {"$match": {"status": {"$in": ["active", "shadow"]}}},
                {"$group": {
                    "_id": None,
                    "avg_score": {"$avg": "$composite_score"},
                    "avg_ic": {"$avg": "$ic"},
                    "avg_sharpe": {"$avg": "$sharpe"}
                }}
            ]
            
            avg_metrics = {}
            for doc in db.alpha_deployments.aggregate(pipeline):
                avg_metrics = {
                    "avg_composite_score": round(doc.get("avg_score", 0), 4),
                    "avg_ic": round(doc.get("avg_ic", 0), 4),
                    "avg_sharpe": round(doc.get("avg_sharpe", 0), 2)
                }
            
            return {
                "connected": True,
                "total_deployments": total,
                "by_status": status_counts,
                "by_family": family_counts,
                "signals_24h": signals_24h,
                "history_count": history_count,
                "avg_metrics": avg_metrics
            }
            
        except Exception as e:
            return {"connected": True, "error": str(e)}
    
    def clear_deployments(self) -> Dict:
        """Clear all deployment data."""
        if not self.connected:
            return {"cleared": False}
        
        try:
            db = self.db
            if db is None:
                return {"cleared": False}
            
            deployments = db.alpha_deployments.delete_many({}).deleted_count
            signals = db.alpha_signals_live.delete_many({}).deleted_count
            history = db.alpha_deployment_history.delete_many({}).deleted_count
            
            return {
                "cleared": True,
                "deployments_deleted": deployments,
                "signals_deleted": signals,
                "history_deleted": history
            }
            
        except Exception as e:
            print(f"[DeploymentRepository] Clear error: {e}")
            return {"cleared": False, "error": str(e)}
