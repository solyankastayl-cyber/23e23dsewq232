"""
PHASE 13.2 - Feature Registry
==============================
Central registry for all features.
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone

from core.database import MongoRepository, get_database

from .feature_types import (
    Feature, FeatureCategory, FeatureTransform, 
    FeatureStatus, DEFAULT_FEATURES
)

try:
    from pymongo import DESCENDING, ASCENDING
    MONGO_OK = True
except ImportError:
    MONGO_OK = False


class FeatureRegistry(MongoRepository):
    """
    Feature Registry - Central catalog of all features.
    
    Features:
    - CRUD operations for features
    - Category filtering
    - Transform tracking
    - Feature dependencies
    """
    
    def __init__(self, auto_seed: bool = True):
        super().__init__()
        self.collection_name = "alpha_features"
        self._in_memory_cache: Dict[str, Feature] = {}
        self._init_collections()
        
        if auto_seed:
            self._seed_default_features()
    
    def _init_collections(self):
        """Initialize MongoDB collections and indexes."""
        if not self.connected:
            print("[FeatureRegistry] Running in memory-only mode")
            return
        
        try:
            db = self.db
            if db is None:
                return
            
            # Main features collection
            db.alpha_features.create_index([("feature_id", 1)], unique=True)
            db.alpha_features.create_index([("category", 1)])
            db.alpha_features.create_index([("tags", 1)])
            db.alpha_features.create_index([("status", 1)])
            db.alpha_features.create_index([("transform", 1)])
            
            # Usage tracking
            db.alpha_feature_usage.create_index([("feature_id", 1), ("used_at", -1)])
            
            # Performance tracking
            db.alpha_feature_performance.create_index([("feature_id", 1), ("timestamp", -1)])
            
            print("[FeatureRegistry] Indexes created")
            
        except Exception as e:
            print(f"[FeatureRegistry] Index error: {e}")
    
    def _seed_default_features(self):
        """Seed default features if not present."""
        try:
            existing_count = self.count_features()
            
            if existing_count < len(DEFAULT_FEATURES):
                seeded = 0
                for feature in DEFAULT_FEATURES:
                    if not self.get_feature(feature.feature_id):
                        feature.created_at = datetime.now(timezone.utc)
                        self.register_feature(feature)
                        seeded += 1
                
                if seeded > 0:
                    print(f"[FeatureRegistry] Seeded {seeded} default features")
            
        except Exception as e:
            print(f"[FeatureRegistry] Seed error: {e}")
    
    # ===== CRUD Operations =====
    
    def register_feature(self, feature: Feature) -> bool:
        """Register a new feature."""
        if not feature.created_at:
            feature.created_at = datetime.now(timezone.utc)
        
        # Update cache
        self._in_memory_cache[feature.feature_id] = feature
        
        if not self.connected:
            return True
        
        try:
            doc = feature.to_dict()
            doc["_created_at"] = datetime.now(timezone.utc)
            
            db = self.db
            if db is not None:
                db.alpha_features.update_one(
                    {"feature_id": feature.feature_id},
                    {"$set": doc},
                    upsert=True
                )
            return True
            
        except Exception as e:
            print(f"[FeatureRegistry] Register error: {e}")
            return False
    
    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """Get a feature by ID."""
        # Check cache first
        if feature_id in self._in_memory_cache:
            return self._in_memory_cache[feature_id]
        
        if not self.connected:
            return None
        
        try:
            db = self.db
            if db is None:
                return None
            
            doc = db.alpha_features.find_one(
                {"feature_id": feature_id},
                {"_id": 0, "_created_at": 0}
            )
            
            if doc:
                feature = Feature.from_dict(doc)
                self._in_memory_cache[feature_id] = feature
                return feature
            
            return None
            
        except Exception as e:
            print(f"[FeatureRegistry] Get error: {e}")
            return None
    
    def update_feature(self, feature_id: str, updates: Dict) -> bool:
        """Update a feature."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Update cache
        if feature_id in self._in_memory_cache:
            for key, value in updates.items():
                if hasattr(self._in_memory_cache[feature_id], key):
                    setattr(self._in_memory_cache[feature_id], key, value)
        
        if not self.connected:
            return True
        
        try:
            db = self.db
            if db is None:
                return False
            
            result = db.alpha_features.update_one(
                {"feature_id": feature_id},
                {"$set": updates}
            )
            return result.modified_count > 0
            
        except Exception as e:
            print(f"[FeatureRegistry] Update error: {e}")
            return False
    
    def delete_feature(self, feature_id: str) -> bool:
        """Delete a feature (marks as deprecated)."""
        if feature_id in self._in_memory_cache:
            del self._in_memory_cache[feature_id]
        
        return self.update_feature(feature_id, {"status": FeatureStatus.DEPRECATED.value})
    
    # ===== Query Operations =====
    
    def list_features(
        self,
        category: Optional[FeatureCategory] = None,
        tags: Optional[List[str]] = None,
        transform: Optional[FeatureTransform] = None,
        status: FeatureStatus = FeatureStatus.ACTIVE,
        limit: int = 500
    ) -> List[Feature]:
        """List features with optional filters."""
        
        # Build query
        query = {}
        if category:
            query["category"] = category.value
        if tags:
            query["tags"] = {"$in": tags}
        if transform:
            query["transform"] = transform.value
        if status:
            query["status"] = status.value
        
        # Try database first
        if self.connected:
            try:
                db = self.db
                if db is not None:
                    cursor = db.alpha_features.find(
                        query,
                        {"_id": 0, "_created_at": 0}
                    ).limit(limit)
                    
                    return [Feature.from_dict(doc) for doc in cursor]
                    
            except Exception as e:
                print(f"[FeatureRegistry] List error: {e}")
        
        # Fallback to cache
        features = []
        for feature in self._in_memory_cache.values():
            if category and feature.category != category:
                continue
            if tags and not any(t in feature.tags for t in tags):
                continue
            if transform and feature.transform != transform:
                continue
            if status and feature.status != status:
                continue
            features.append(feature)
            if len(features) >= limit:
                break
        
        return features
    
    def get_features_by_category(self, category: FeatureCategory) -> List[Feature]:
        """Get all features of a specific category."""
        return self.list_features(category=category)
    
    def search_features(self, query: str, limit: int = 50) -> List[Feature]:
        """Search features by text query."""
        query_lower = query.lower()
        
        if self.connected:
            try:
                db = self.db
                if db is not None:
                    cursor = db.alpha_features.find(
                        {
                            "$or": [
                                {"feature_id": {"$regex": query, "$options": "i"}},
                                {"description": {"$regex": query, "$options": "i"}},
                                {"tags": {"$in": [query_lower]}}
                            ]
                        },
                        {"_id": 0}
                    ).limit(limit)
                    
                    return [Feature.from_dict(doc) for doc in cursor]
                    
            except Exception as e:
                print(f"[FeatureRegistry] Search error: {e}")
        
        # Fallback to cache
        results = []
        for feature in self._in_memory_cache.values():
            if (query_lower in feature.feature_id.lower() or
                query_lower in feature.description.lower() or
                any(query_lower in t for t in feature.tags)):
                results.append(feature)
                if len(results) >= limit:
                    break
        
        return results
    
    # ===== Statistics =====
    
    def count_features(self, category: Optional[FeatureCategory] = None) -> int:
        """Count features, optionally by category."""
        query = {}
        if category:
            query["category"] = category.value
        
        if self.connected:
            try:
                db = self.db
                if db is not None:
                    return db.alpha_features.count_documents(query)
            except Exception:
                pass
        
        # Fallback to cache
        if category:
            return sum(1 for f in self._in_memory_cache.values() if f.category == category)
        return len(self._in_memory_cache)
    
    def get_stats(self) -> Dict:
        """Get registry statistics."""
        stats = {
            "connected": self.connected,
            "total_features": 0,
            "features_by_category": {},
            "features_by_transform": {},
            "active_features": 0
        }
        
        # Count by category
        for cat in FeatureCategory:
            count = self.count_features(cat)
            stats["features_by_category"][cat.value] = count
            stats["total_features"] += count
        
        # Count active
        active_features = self.list_features(status=FeatureStatus.ACTIVE)
        stats["active_features"] = len(active_features)
        
        # Count by transform
        transforms = {}
        for feature in active_features:
            t = feature.transform.value if isinstance(feature.transform, FeatureTransform) else feature.transform
            transforms[t] = transforms.get(t, 0) + 1
        stats["features_by_transform"] = transforms
        
        return stats
    
    def get_category_breakdown(self) -> Dict[str, int]:
        """Get count of features by category."""
        return {cat.value: self.count_features(cat) for cat in FeatureCategory}
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags."""
        tags = set()
        features = self.list_features(limit=1000)
        for feature in features:
            tags.update(feature.tags)
        return sorted(list(tags))
    
    def get_dependencies(self, feature_id: str) -> Dict[str, List[str]]:
        """Get feature dependencies."""
        feature = self.get_feature(feature_id)
        if not feature:
            return {}
        
        return {
            "inputs": feature.inputs,
            "depends_on": feature.depends_on
        }


# Global singleton instance
_registry_instance: Optional[FeatureRegistry] = None


def get_feature_registry() -> FeatureRegistry:
    """Get singleton registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = FeatureRegistry()
    return _registry_instance
