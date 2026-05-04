"""
PHASE 6.2 - Scenario Repository
================================
Persistence layer for scenario data in MongoDB.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pymongo import MongoClient
from pymongo.database import Database
import os

from .scenario_types import (
    ScenarioDefinition, ScenarioRun, ScenarioResult,
    ScenarioStatus, ScenarioType, ScenarioVerdict
)


class ScenarioRepository:
    """
    Repository for persisting scenario data
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
        # Scenarios collection
        if "scenarios" not in self.db.list_collection_names():
            self.db.create_collection("scenarios")
        
        self.db.scenarios.create_index("scenario_id", unique=True)
        self.db.scenarios.create_index("scenario_type")
        self.db.scenarios.create_index("severity")
        
        # Runs collection
        if "scenario_runs" not in self.db.list_collection_names():
            self.db.create_collection("scenario_runs")
        
        self.db.scenario_runs.create_index("run_id", unique=True)
        self.db.scenario_runs.create_index("scenario_id")
        self.db.scenario_runs.create_index([("scenario_id", 1), ("started_at", -1)])
        
        # Results collection
        if "scenario_results" not in self.db.list_collection_names():
            self.db.create_collection("scenario_results")
        
        self.db.scenario_results.create_index([("scenario_id", 1), ("run_id", 1)], unique=True)
        self.db.scenario_results.create_index("verdict")
        self.db.scenario_results.create_index([("system_stability_score", -1)])
    
    # ==================== Scenarios ====================
    
    def save_scenario(self, scenario: ScenarioDefinition) -> bool:
        """Save or update scenario"""
        try:
            data = scenario.to_dict()
            data["_id"] = scenario.scenario_id
            
            self.db.scenarios.update_one(
                {"scenario_id": scenario.scenario_id},
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving scenario: {e}")
            return False
    
    def get_scenario(self, scenario_id: str) -> Optional[Dict]:
        """Get scenario by ID"""
        doc = self.db.scenarios.find_one(
            {"scenario_id": scenario_id},
            {"_id": 0}
        )
        return doc
    
    def get_all_scenarios(self) -> List[Dict]:
        """Get all scenarios"""
        docs = self.db.scenarios.find({}, {"_id": 0})
        return list(docs)
    
    def get_scenarios_by_type(self, scenario_type: str) -> List[Dict]:
        """Get scenarios by type"""
        docs = self.db.scenarios.find({"scenario_type": scenario_type}, {"_id": 0})
        return list(docs)
    
    def get_scenarios_by_severity(self, severity: str) -> List[Dict]:
        """Get scenarios by severity"""
        docs = self.db.scenarios.find({"severity": severity}, {"_id": 0})
        return list(docs)
    
    def delete_scenario(self, scenario_id: str) -> bool:
        """Delete scenario"""
        result = self.db.scenarios.delete_one({"scenario_id": scenario_id})
        return result.deleted_count > 0
    
    # ==================== Runs ====================
    
    def save_run(self, run: ScenarioRun) -> bool:
        """Save scenario run"""
        try:
            data = run.to_dict()
            data["_id"] = run.run_id
            
            self.db.scenario_runs.update_one(
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
        doc = self.db.scenario_runs.find_one({"run_id": run_id}, {"_id": 0})
        return doc
    
    def get_runs_for_scenario(self, scenario_id: str, limit: int = 10) -> List[Dict]:
        """Get runs for a scenario"""
        docs = self.db.scenario_runs.find(
            {"scenario_id": scenario_id},
            {"_id": 0}
        ).sort("started_at", -1).limit(limit)
        return list(docs)
    
    def get_recent_runs(self, limit: int = 20) -> List[Dict]:
        """Get recent runs"""
        docs = self.db.scenario_runs.find(
            {},
            {"_id": 0}
        ).sort("started_at", -1).limit(limit)
        return list(docs)
    
    # ==================== Results ====================
    
    def save_result(self, result: ScenarioResult) -> bool:
        """Save scenario result"""
        try:
            data = result.to_dict()
            data["_id"] = f"{result.scenario_id}_{result.run_id}"
            
            self.db.scenario_results.update_one(
                {"scenario_id": result.scenario_id, "run_id": result.run_id},
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving result: {e}")
            return False
    
    def get_result(self, scenario_id: str, run_id: str) -> Optional[Dict]:
        """Get result for a specific run"""
        doc = self.db.scenario_results.find_one(
            {"scenario_id": scenario_id, "run_id": run_id},
            {"_id": 0}
        )
        return doc
    
    def get_results_for_scenario(self, scenario_id: str, limit: int = 10) -> List[Dict]:
        """Get all results for a scenario"""
        docs = self.db.scenario_results.find(
            {"scenario_id": scenario_id},
            {"_id": 0}
        ).sort("computed_at", -1).limit(limit)
        return list(docs)
    
    def get_latest_result(self, scenario_id: str) -> Optional[Dict]:
        """Get latest result for a scenario"""
        doc = self.db.scenario_results.find_one(
            {"scenario_id": scenario_id},
            {"_id": 0},
            sort=[("computed_at", -1)]
        )
        return doc
    
    def get_top_scenarios(self, limit: int = 10) -> List[Dict]:
        """Get scenarios with best stability scores"""
        pipeline = [
            {"$match": {"verdict": {"$in": ["RESILIENT", "STABLE"]}}},
            {"$sort": {"system_stability_score": -1}},
            {"$limit": limit},
            {"$project": {"_id": 0}}
        ]
        return list(self.db.scenario_results.aggregate(pipeline))
    
    def get_weak_scenarios(self, limit: int = 10) -> List[Dict]:
        """Get scenarios with worst performance"""
        pipeline = [
            {"$match": {"verdict": {"$in": ["WEAK", "BROKEN"]}}},
            {"$sort": {"system_stability_score": 1}},
            {"$limit": limit},
            {"$project": {"_id": 0}}
        ]
        return list(self.db.scenario_results.aggregate(pipeline))
    
    def get_results_by_verdict(self, verdict: str) -> List[Dict]:
        """Get results by verdict"""
        docs = self.db.scenario_results.find(
            {"verdict": verdict},
            {"_id": 0}
        ).sort("computed_at", -1)
        return list(docs)
    
    # ==================== Statistics ====================
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        total_scenarios = self.db.scenarios.count_documents({})
        total_runs = self.db.scenario_runs.count_documents({})
        total_results = self.db.scenario_results.count_documents({})
        
        # Type breakdown
        type_pipeline = [
            {"$group": {"_id": "$scenario_type", "count": {"$sum": 1}}}
        ]
        type_counts = {
            doc["_id"]: doc["count"]
            for doc in self.db.scenarios.aggregate(type_pipeline)
        }
        
        # Verdict breakdown
        verdict_pipeline = [
            {"$group": {"_id": "$verdict", "count": {"$sum": 1}}}
        ]
        verdict_counts = {
            doc["_id"]: doc["count"]
            for doc in self.db.scenario_results.aggregate(verdict_pipeline)
        }
        
        # Average metrics
        avg_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_stability": {"$avg": "$system_stability_score"},
                    "avg_drawdown": {"$avg": "$avg_max_drawdown"},
                    "avg_survival": {"$avg": {"$divide": ["$strategies_survived", "$total_strategies"]}}
                }
            }
        ]
        avg_results = list(self.db.scenario_results.aggregate(avg_pipeline))
        avg_metrics = avg_results[0] if avg_results else {}
        
        return {
            "total_scenarios": total_scenarios,
            "total_runs": total_runs,
            "total_results": total_results,
            "by_type": type_counts,
            "by_verdict": verdict_counts,
            "average_metrics": {
                "stability_score": round(avg_metrics.get("avg_stability", 0), 3),
                "max_drawdown": round(avg_metrics.get("avg_drawdown", 0), 4),
                "survival_rate": round(avg_metrics.get("avg_survival", 0), 3)
            }
        }
