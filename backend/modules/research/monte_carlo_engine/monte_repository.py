"""
PHASE 6.3 - Monte Carlo Repository
====================================
Persistence layer for Monte Carlo data in MongoDB.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pymongo import MongoClient
from pymongo.database import Database
import os

from .monte_types import (
    MonteCarloRun, MonteCarloResult, MonteCarloStatus, MonteCarloVerdict
)


class MonteCarloRepository:
    """
    Repository for persisting Monte Carlo data.
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
        # Runs collection
        if "monte_carlo_runs" not in self.db.list_collection_names():
            self.db.create_collection("monte_carlo_runs")
        
        self.db.monte_carlo_runs.create_index("run_id", unique=True)
        self.db.monte_carlo_runs.create_index("strategy_id")
        self.db.monte_carlo_runs.create_index([("strategy_id", 1), ("started_at", -1)])
        
        # Results collection
        if "monte_carlo_results" not in self.db.list_collection_names():
            self.db.create_collection("monte_carlo_results")
        
        self.db.monte_carlo_results.create_index("run_id", unique=True)
        self.db.monte_carlo_results.create_index("strategy_id")
        self.db.monte_carlo_results.create_index("verdict")
        self.db.monte_carlo_results.create_index([("risk_score", 1)])
    
    # ==================== Runs ====================
    
    def save_run(self, run: MonteCarloRun) -> bool:
        """Save Monte Carlo run"""
        try:
            data = run.to_dict()
            data["_id"] = run.run_id
            
            self.db.monte_carlo_runs.update_one(
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
        doc = self.db.monte_carlo_runs.find_one({"run_id": run_id}, {"_id": 0})
        return doc
    
    def get_runs_for_strategy(self, strategy_id: str, limit: int = 10) -> List[Dict]:
        """Get runs for a strategy"""
        docs = self.db.monte_carlo_runs.find(
            {"strategy_id": strategy_id},
            {"_id": 0}
        ).sort("started_at", -1).limit(limit)
        return list(docs)
    
    def get_recent_runs(self, limit: int = 20) -> List[Dict]:
        """Get recent runs"""
        docs = self.db.monte_carlo_runs.find(
            {},
            {"_id": 0}
        ).sort("started_at", -1).limit(limit)
        return list(docs)
    
    # ==================== Results ====================
    
    def save_result(self, result: MonteCarloResult) -> bool:
        """Save Monte Carlo result"""
        try:
            data = result.to_dict()
            data["_id"] = result.run_id
            
            self.db.monte_carlo_results.update_one(
                {"run_id": result.run_id},
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving result: {e}")
            return False
    
    def get_result(self, run_id: str) -> Optional[Dict]:
        """Get result by run ID"""
        doc = self.db.monte_carlo_results.find_one({"run_id": run_id}, {"_id": 0})
        return doc
    
    def get_results_for_strategy(self, strategy_id: str, limit: int = 10) -> List[Dict]:
        """Get results for a strategy"""
        docs = self.db.monte_carlo_results.find(
            {"strategy_id": strategy_id},
            {"_id": 0}
        ).sort("computed_at", -1).limit(limit)
        return list(docs)
    
    def get_latest_result(self, strategy_id: str) -> Optional[Dict]:
        """Get latest result for a strategy"""
        doc = self.db.monte_carlo_results.find_one(
            {"strategy_id": strategy_id},
            {"_id": 0},
            sort=[("computed_at", -1)]
        )
        return doc
    
    def get_top_strategies(self, limit: int = 10) -> List[Dict]:
        """Get strategies with best risk scores"""
        pipeline = [
            {"$match": {"verdict": {"$in": ["ROBUST", "ACCEPTABLE"]}}},
            {"$sort": {"risk_score": 1}},  # Lower is better
            {"$limit": limit},
            {"$project": {"_id": 0}}
        ]
        return list(self.db.monte_carlo_results.aggregate(pipeline))
    
    def get_risky_strategies(self, limit: int = 10) -> List[Dict]:
        """Get strategies with worst risk scores"""
        pipeline = [
            {"$sort": {"risk_score": -1}},  # Higher is worse
            {"$limit": limit},
            {"$project": {"_id": 0}}
        ]
        return list(self.db.monte_carlo_results.aggregate(pipeline))
    
    def get_results_by_verdict(self, verdict: str) -> List[Dict]:
        """Get results by verdict"""
        docs = self.db.monte_carlo_results.find(
            {"verdict": verdict},
            {"_id": 0}
        ).sort("computed_at", -1)
        return list(docs)
    
    # ==================== Statistics ====================
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        total_runs = self.db.monte_carlo_runs.count_documents({})
        total_results = self.db.monte_carlo_results.count_documents({})
        
        # Verdict breakdown
        verdict_pipeline = [
            {"$group": {"_id": "$verdict", "count": {"$sum": 1}}}
        ]
        verdict_counts = {
            doc["_id"]: doc["count"]
            for doc in self.db.monte_carlo_results.aggregate(verdict_pipeline)
        }
        
        # Average metrics
        avg_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_risk_score": {"$avg": "$risk_score"},
                    "avg_profit_prob": {"$avg": "$profit_probability"},
                    "avg_sharpe": {"$avg": "$sharpe_ratio_median"}
                }
            }
        ]
        avg_results = list(self.db.monte_carlo_results.aggregate(avg_pipeline))
        avg_metrics = avg_results[0] if avg_results else {}
        
        return {
            "total_runs": total_runs,
            "total_results": total_results,
            "by_verdict": verdict_counts,
            "average_metrics": {
                "risk_score": round(avg_metrics.get("avg_risk_score", 0), 3),
                "profit_probability": round(avg_metrics.get("avg_profit_prob", 0), 3),
                "sharpe_ratio": round(avg_metrics.get("avg_sharpe", 0), 3)
            }
        }
