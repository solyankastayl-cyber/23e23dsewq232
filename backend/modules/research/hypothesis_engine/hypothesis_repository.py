"""
PHASE 6.1 - Hypothesis Repository
==================================
Persistence layer for hypothesis data in MongoDB.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from pymongo.database import Database
import os

from .hypothesis_types import (
    HypothesisDefinition, HypothesisRun, HypothesisResult,
    HypothesisStatus, HypothesisCategory, HypothesisVerdict
)


class HypothesisRepository:
    """
    Repository for persisting hypothesis data
    """
    
    def __init__(self, db: Database = None):
        if db is None:
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "ta_engine")
            client = MongoClient(mongo_url)
            db = client[db_name]
        
        self.db = db
        self._ensure_collections()
    
    def _ensure_collections(self):
        """Ensure collections and indexes exist"""
        # Hypotheses collection
        if "hypotheses" not in self.db.list_collection_names():
            self.db.create_collection("hypotheses")
        
        self.db.hypotheses.create_index("hypothesis_id", unique=True)
        self.db.hypotheses.create_index("category")
        self.db.hypotheses.create_index("status")
        
        # Runs collection
        if "hypothesis_runs" not in self.db.list_collection_names():
            self.db.create_collection("hypothesis_runs")
        
        self.db.hypothesis_runs.create_index("run_id", unique=True)
        self.db.hypothesis_runs.create_index("hypothesis_id")
        self.db.hypothesis_runs.create_index([("hypothesis_id", 1), ("started_at", -1)])
        
        # Results collection
        if "hypothesis_results" not in self.db.list_collection_names():
            self.db.create_collection("hypothesis_results")
        
        self.db.hypothesis_results.create_index([("hypothesis_id", 1), ("run_id", 1)], unique=True)
        self.db.hypothesis_results.create_index("verdict")
        self.db.hypothesis_results.create_index([("win_rate", -1)])
    
    # ==================== Hypotheses ====================
    
    def save_hypothesis(self, hypothesis: HypothesisDefinition) -> bool:
        """Save or update hypothesis"""
        try:
            data = hypothesis.to_dict()
            data["_id"] = hypothesis.hypothesis_id
            
            self.db.hypotheses.update_one(
                {"hypothesis_id": hypothesis.hypothesis_id},
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving hypothesis: {e}")
            return False
    
    def get_hypothesis(self, hypothesis_id: str) -> Optional[Dict]:
        """Get hypothesis by ID"""
        doc = self.db.hypotheses.find_one(
            {"hypothesis_id": hypothesis_id},
            {"_id": 0}
        )
        return doc
    
    def get_all_hypotheses(self) -> List[Dict]:
        """Get all hypotheses"""
        docs = self.db.hypotheses.find({}, {"_id": 0})
        return list(docs)
    
    def get_hypotheses_by_status(self, status: str) -> List[Dict]:
        """Get hypotheses by status"""
        docs = self.db.hypotheses.find({"status": status}, {"_id": 0})
        return list(docs)
    
    def get_hypotheses_by_category(self, category: str) -> List[Dict]:
        """Get hypotheses by category"""
        docs = self.db.hypotheses.find({"category": category}, {"_id": 0})
        return list(docs)
    
    def update_hypothesis_status(self, hypothesis_id: str, status: str) -> bool:
        """Update hypothesis status"""
        result = self.db.hypotheses.update_one(
            {"hypothesis_id": hypothesis_id},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        return result.modified_count > 0
    
    def delete_hypothesis(self, hypothesis_id: str) -> bool:
        """Delete hypothesis"""
        result = self.db.hypotheses.delete_one({"hypothesis_id": hypothesis_id})
        return result.deleted_count > 0
    
    # ==================== Runs ====================
    
    def save_run(self, run: HypothesisRun) -> bool:
        """Save hypothesis run"""
        try:
            data = run.to_dict()
            data["_id"] = run.run_id
            
            self.db.hypothesis_runs.update_one(
                {"run_id": run.run_id},
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving run: {e}")
            return False
    
    def get_run(self, run_id: str) -> Optional[Dict]:
        """Get run by ID"""
        doc = self.db.hypothesis_runs.find_one({"run_id": run_id}, {"_id": 0})
        return doc
    
    def get_runs_for_hypothesis(self, hypothesis_id: str, limit: int = 10) -> List[Dict]:
        """Get runs for a hypothesis"""
        docs = self.db.hypothesis_runs.find(
            {"hypothesis_id": hypothesis_id},
            {"_id": 0}
        ).sort("started_at", -1).limit(limit)
        return list(docs)
    
    def get_recent_runs(self, limit: int = 20) -> List[Dict]:
        """Get recent runs across all hypotheses"""
        docs = self.db.hypothesis_runs.find(
            {},
            {"_id": 0}
        ).sort("started_at", -1).limit(limit)
        return list(docs)
    
    # ==================== Results ====================
    
    def save_result(self, result: HypothesisResult) -> bool:
        """Save hypothesis result"""
        try:
            data = result.to_dict()
            data["_id"] = f"{result.hypothesis_id}_{result.run_id}"
            
            self.db.hypothesis_results.update_one(
                {"hypothesis_id": result.hypothesis_id, "run_id": result.run_id},
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving result: {e}")
            return False
    
    def get_result(self, hypothesis_id: str, run_id: str) -> Optional[Dict]:
        """Get result for a specific run"""
        doc = self.db.hypothesis_results.find_one(
            {"hypothesis_id": hypothesis_id, "run_id": run_id},
            {"_id": 0}
        )
        return doc
    
    def get_results_for_hypothesis(self, hypothesis_id: str, limit: int = 10) -> List[Dict]:
        """Get all results for a hypothesis"""
        docs = self.db.hypothesis_results.find(
            {"hypothesis_id": hypothesis_id},
            {"_id": 0}
        ).sort("computed_at", -1).limit(limit)
        return list(docs)
    
    def get_latest_result(self, hypothesis_id: str) -> Optional[Dict]:
        """Get latest result for a hypothesis"""
        doc = self.db.hypothesis_results.find_one(
            {"hypothesis_id": hypothesis_id},
            {"_id": 0},
            sort=[("computed_at", -1)]
        )
        return doc
    
    def get_top_hypotheses(self, limit: int = 10) -> List[Dict]:
        """Get top performing hypotheses by win rate"""
        pipeline = [
            {"$match": {"verdict": {"$in": ["VALID", "PROMISING"]}}},
            {"$sort": {"win_rate": -1, "profit_factor": -1}},
            {"$limit": limit},
            {"$project": {"_id": 0}}
        ]
        return list(self.db.hypothesis_results.aggregate(pipeline))
    
    def get_weak_hypotheses(self, limit: int = 10) -> List[Dict]:
        """Get weak performing hypotheses"""
        pipeline = [
            {"$match": {"verdict": {"$in": ["WEAK", "REJECTED"]}}},
            {"$sort": {"win_rate": 1}},
            {"$limit": limit},
            {"$project": {"_id": 0}}
        ]
        return list(self.db.hypothesis_results.aggregate(pipeline))
    
    def get_results_by_verdict(self, verdict: str) -> List[Dict]:
        """Get results by verdict"""
        docs = self.db.hypothesis_results.find(
            {"verdict": verdict},
            {"_id": 0}
        ).sort("computed_at", -1)
        return list(docs)
    
    # ==================== Statistics ====================
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        total_hypotheses = self.db.hypotheses.count_documents({})
        total_runs = self.db.hypothesis_runs.count_documents({})
        total_results = self.db.hypothesis_results.count_documents({})
        
        # Status breakdown
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_counts = {
            doc["_id"]: doc["count"]
            for doc in self.db.hypotheses.aggregate(status_pipeline)
        }
        
        # Verdict breakdown
        verdict_pipeline = [
            {"$group": {"_id": "$verdict", "count": {"$sum": 1}}}
        ]
        verdict_counts = {
            doc["_id"]: doc["count"]
            for doc in self.db.hypothesis_results.aggregate(verdict_pipeline)
        }
        
        # Average metrics
        avg_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_win_rate": {"$avg": "$win_rate"},
                    "avg_profit_factor": {"$avg": "$profit_factor"},
                    "avg_confidence": {"$avg": "$confidence_score"}
                }
            }
        ]
        avg_results = list(self.db.hypothesis_results.aggregate(avg_pipeline))
        avg_metrics = avg_results[0] if avg_results else {}
        
        return {
            "total_hypotheses": total_hypotheses,
            "total_runs": total_runs,
            "total_results": total_results,
            "by_status": status_counts,
            "by_verdict": verdict_counts,
            "average_metrics": {
                "win_rate": round(avg_metrics.get("avg_win_rate", 0), 4),
                "profit_factor": round(avg_metrics.get("avg_profit_factor", 0), 2),
                "confidence": round(avg_metrics.get("avg_confidence", 0), 3)
            }
        }
