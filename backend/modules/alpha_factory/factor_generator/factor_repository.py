"""
PHASE 13.3 - Factor Repository
===============================
MongoDB persistence for Factor Generator.

Collections:
- alpha_factors
- alpha_factor_runs
- alpha_factor_families
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from core.database import MongoRepository, get_database

from .factor_types import Factor, FactorBatchRun, FactorFamily, FactorStatus


class FactorRepository(MongoRepository):
    """
    Repository for Factor Generator data.
    """
    
    def __init__(self):
        super().__init__()
        self.collection_name = "alpha_factors"
        self._init_indexes()
    
    def _init_indexes(self):
        """Initialize MongoDB indexes."""
        if not self.connected:
            return
        
        try:
            db = self.db
            if db is None:
                return
            
            # Factors collection
            db.alpha_factors.create_index([("factor_id", 1)], unique=True)
            db.alpha_factors.create_index([("family", 1)])
            db.alpha_factors.create_index([("template", 1)])
            db.alpha_factors.create_index([("status", 1)])
            db.alpha_factors.create_index([("created_at", -1)])
            
            # Runs collection
            db.alpha_factor_runs.create_index([("run_id", 1)], unique=True)
            db.alpha_factor_runs.create_index([("started_at", -1)])
            
            print("[FactorRepository] Indexes created")
            
        except Exception as e:
            print(f"[FactorRepository] Index error: {e}")
    
    def save_factor(self, factor: Factor) -> bool:
        """Save a factor."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = factor.to_dict()
            db.alpha_factors.update_one(
                {"factor_id": factor.factor_id},
                {"$set": doc},
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"[FactorRepository] Save error: {e}")
            return False
    
    def get_factor(self, factor_id: str) -> Optional[Factor]:
        """Get a factor by ID."""
        if not self.connected:
            return None
        
        try:
            db = self.db
            if db is None:
                return None
            
            doc = db.alpha_factors.find_one(
                {"factor_id": factor_id},
                {"_id": 0}
            )
            
            if doc:
                return Factor.from_dict(doc)
            return None
            
        except Exception as e:
            print(f"[FactorRepository] Get error: {e}")
            return None
    
    def list_factors(
        self,
        family: Optional[str] = None,
        template: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Factor]:
        """List factors with filters."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            query = {}
            if family:
                query["family"] = family
            if template:
                query["template"] = template
            if status:
                query["status"] = status
            
            cursor = db.alpha_factors.find(
                query,
                {"_id": 0}
            ).limit(limit).sort("created_at", -1)
            
            return [Factor.from_dict(doc) for doc in cursor]
            
        except Exception as e:
            print(f"[FactorRepository] List error: {e}")
            return []
    
    def count_factors(
        self,
        family: Optional[str] = None,
        template: Optional[str] = None
    ) -> int:
        """Count factors."""
        if not self.connected:
            return 0
        
        try:
            db = self.db
            if db is None:
                return 0
            
            query = {}
            if family:
                query["family"] = family
            if template:
                query["template"] = template
            
            return db.alpha_factors.count_documents(query)
            
        except Exception as e:
            print(f"[FactorRepository] Count error: {e}")
            return 0
    
    def search_factors(self, query: str, limit: int = 50) -> List[Factor]:
        """Search factors."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            cursor = db.alpha_factors.find(
                {
                    "$or": [
                        {"factor_id": {"$regex": query, "$options": "i"}},
                        {"name": {"$regex": query, "$options": "i"}},
                        {"description": {"$regex": query, "$options": "i"}},
                        {"tags": {"$in": [query.lower()]}}
                    ]
                },
                {"_id": 0}
            ).limit(limit)
            
            return [Factor.from_dict(doc) for doc in cursor]
            
        except Exception as e:
            print(f"[FactorRepository] Search error: {e}")
            return []
    
    def save_run(self, run: FactorBatchRun) -> bool:
        """Save a batch run."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = run.to_dict()
            db.alpha_factor_runs.update_one(
                {"run_id": run.run_id},
                {"$set": doc},
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"[FactorRepository] Run save error: {e}")
            return False
    
    def get_runs(self, limit: int = 10) -> List[Dict]:
        """Get recent runs."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            cursor = db.alpha_factor_runs.find(
                {},
                {"_id": 0}
            ).sort("started_at", -1).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            print(f"[FactorRepository] Get runs error: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get repository statistics."""
        if not self.connected:
            return {"connected": False}
        
        try:
            db = self.db
            if db is None:
                return {"connected": False}
            
            # Count by family
            family_counts = {}
            for family in FactorFamily:
                family_counts[family.value] = db.alpha_factors.count_documents(
                    {"family": family.value}
                )
            
            # Count by template
            template_pipeline = [
                {"$group": {"_id": "$template", "count": {"$sum": 1}}}
            ]
            template_counts = {}
            for doc in db.alpha_factors.aggregate(template_pipeline):
                template_counts[doc["_id"]] = doc["count"]
            
            return {
                "connected": True,
                "total_factors": db.alpha_factors.count_documents({}),
                "total_runs": db.alpha_factor_runs.count_documents({}),
                "family_counts": family_counts,
                "template_counts": template_counts
            }
            
        except Exception as e:
            return {"connected": True, "error": str(e)}
    
    def get_family_stats(self) -> Dict[str, int]:
        """Get count by family."""
        stats = self.get_stats()
        return stats.get("family_counts", {})
    
    def clear_factors(self) -> int:
        """Clear all factors (for regeneration)."""
        if not self.connected:
            return 0
        
        try:
            db = self.db
            if db is None:
                return 0
            
            result = db.alpha_factors.delete_many({})
            return result.deleted_count
            
        except Exception as e:
            print(f"[FactorRepository] Clear error: {e}")
            return 0
