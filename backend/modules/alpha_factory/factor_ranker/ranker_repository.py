"""
PHASE 13.4 - Ranker Repository
===============================
MongoDB persistence for Factor Ranker.

Collections:
- alpha_factor_rankings
- alpha_factor_approved
- alpha_ranking_runs
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from core.database import MongoRepository, get_database

from .factor_metrics import MetricsResult


class RankerRepository(MongoRepository):
    """
    Repository for Factor Ranker data.
    """
    
    def __init__(self):
        super().__init__()
        self.collection_name = "alpha_factor_rankings"
        self._init_indexes()
    
    def _init_indexes(self):
        """Initialize MongoDB indexes."""
        if not self.connected:
            return
        
        try:
            db = self.db
            if db is None:
                return
            
            # Rankings collection
            db.alpha_factor_rankings.create_index([("factor_id", 1)], unique=True)
            db.alpha_factor_rankings.create_index([("verdict", 1)])
            db.alpha_factor_rankings.create_index([("approved", 1)])
            db.alpha_factor_rankings.create_index([("composite_score", -1)])
            db.alpha_factor_rankings.create_index([("ic", -1)])
            
            # Runs collection
            db.alpha_ranking_runs.create_index([("run_id", 1)], unique=True)
            db.alpha_ranking_runs.create_index([("started_at", -1)])
            
            print("[RankerRepository] Indexes created")
            
        except Exception as e:
            print(f"[RankerRepository] Index error: {e}")
    
    def save_ranking(
        self, 
        result: MetricsResult, 
        factors: List[Dict] = None
    ) -> bool:
        """Save a factor ranking."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            # Get factor info
            factor_info = {}
            if factors:
                factor = next((f for f in factors if f.get("factor_id") == result.factor_id), None)
                if factor:
                    factor_info = {
                        "family": factor.get("family"),
                        "template": factor.get("template"),
                        "inputs": factor.get("inputs", []),
                        "complexity": factor.get("complexity", 1)
                    }
            
            doc = result.to_dict()
            doc.update(factor_info)
            doc["_updated_at"] = datetime.now(timezone.utc)
            
            db.alpha_factor_rankings.update_one(
                {"factor_id": result.factor_id},
                {"$set": doc},
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"[RankerRepository] Save error: {e}")
            return False
    
    def get_ranking(self, factor_id: str) -> Optional[Dict]:
        """Get ranking for a factor."""
        if not self.connected:
            return None
        
        try:
            db = self.db
            if db is None:
                return None
            
            return db.alpha_factor_rankings.find_one(
                {"factor_id": factor_id},
                {"_id": 0, "_updated_at": 0}
            )
            
        except Exception as e:
            print(f"[RankerRepository] Get error: {e}")
            return None
    
    def get_rankings(
        self,
        verdict: Optional[str] = None,
        approved_only: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """Get rankings with filters."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            query = {}
            if verdict:
                query["verdict"] = verdict
            if approved_only:
                query["approved"] = True
            
            cursor = db.alpha_factor_rankings.find(
                query,
                {"_id": 0, "_updated_at": 0}
            ).sort("composite_score", -1).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            print(f"[RankerRepository] Get rankings error: {e}")
            return []
    
    def get_top_rankings(self, n: int = 20) -> List[Dict]:
        """Get top N rankings by composite score."""
        return self.get_rankings(limit=n)
    
    def count_by_verdict(self) -> Dict[str, int]:
        """Count rankings by verdict."""
        if not self.connected:
            return {}
        
        try:
            db = self.db
            if db is None:
                return {}
            
            pipeline = [
                {"$group": {"_id": "$verdict", "count": {"$sum": 1}}}
            ]
            
            result = {}
            for doc in db.alpha_factor_rankings.aggregate(pipeline):
                result[doc["_id"]] = doc["count"]
            
            return result
            
        except Exception as e:
            print(f"[RankerRepository] Count error: {e}")
            return {}
    
    def count_approved(self) -> int:
        """Count approved factors."""
        if not self.connected:
            return 0
        
        try:
            db = self.db
            if db is None:
                return 0
            
            return db.alpha_factor_rankings.count_documents({"approved": True})
            
        except Exception as e:
            return 0
    
    def clear_rankings(self) -> int:
        """Clear all rankings."""
        if not self.connected:
            return 0
        
        try:
            db = self.db
            if db is None:
                return 0
            
            result = db.alpha_factor_rankings.delete_many({})
            return result.deleted_count
            
        except Exception as e:
            print(f"[RankerRepository] Clear error: {e}")
            return 0
    
    def save_run(self, run) -> bool:
        """Save ranking run."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = run.to_dict()
            db.alpha_ranking_runs.update_one(
                {"run_id": run.run_id},
                {"$set": doc},
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"[RankerRepository] Save run error: {e}")
            return False
    
    def get_runs(self, limit: int = 10) -> List[Dict]:
        """Get recent ranking runs."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            cursor = db.alpha_ranking_runs.find(
                {},
                {"_id": 0}
            ).sort("started_at", -1).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            print(f"[RankerRepository] Get runs error: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get repository statistics."""
        if not self.connected:
            return {"connected": False}
        
        try:
            db = self.db
            if db is None:
                return {"connected": False}
            
            verdict_counts = self.count_by_verdict()
            approved_count = self.count_approved()
            total_count = db.alpha_factor_rankings.count_documents({})
            runs_count = db.alpha_ranking_runs.count_documents({})
            
            # Average metrics
            pipeline = [
                {"$group": {
                    "_id": None,
                    "avg_ic": {"$avg": "$ic"},
                    "avg_sharpe": {"$avg": "$sharpe"},
                    "avg_stability": {"$avg": "$stability"},
                    "avg_composite": {"$avg": "$composite_score"}
                }}
            ]
            
            avg_metrics = {}
            for doc in db.alpha_factor_rankings.aggregate(pipeline):
                avg_metrics = {
                    "avg_ic": round(doc.get("avg_ic", 0), 4),
                    "avg_sharpe": round(doc.get("avg_sharpe", 0), 2),
                    "avg_stability": round(doc.get("avg_stability", 0), 2),
                    "avg_composite": round(doc.get("avg_composite", 0), 3)
                }
            
            return {
                "connected": True,
                "total_rankings": total_count,
                "approved_count": approved_count,
                "verdict_counts": verdict_counts,
                "avg_metrics": avg_metrics,
                "total_runs": runs_count
            }
            
        except Exception as e:
            return {"connected": True, "error": str(e)}
