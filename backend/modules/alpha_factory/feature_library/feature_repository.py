"""
PHASE 13.2 - Feature Repository
================================
MongoDB persistence for Feature Library.
"""

from typing import List, Dict
from datetime import datetime, timezone

from core.database import MongoRepository


class FeatureRepository(MongoRepository):
    """Repository for Feature Library data."""
    
    def __init__(self):
        super().__init__()
        self.collection_name = "alpha_features"
    
    def get_stats(self) -> Dict:
        """Get repository statistics."""
        if not self.connected:
            return {"connected": False}
        
        try:
            db = self.db
            if db is None:
                return {"connected": False}
            
            return {
                "connected": True,
                "collections": {
                    "alpha_features": db.alpha_features.count_documents({}),
                    "alpha_feature_usage": db.alpha_feature_usage.count_documents({}),
                    "alpha_feature_performance": db.alpha_feature_performance.count_documents({})
                }
            }
        except Exception as e:
            return {"connected": True, "error": str(e)}
