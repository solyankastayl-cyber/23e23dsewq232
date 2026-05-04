"""
Idea Repository — Data access layer for Ideas
=============================================

Handles:
  - Idea CRUD
  - Version management
  - Favorites
  - Queries

Uses MongoDB for persistence.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Idea, IdeaVersion, IdeaStatus, Favorite


class IdeaRepository:
    """
    Repository for idea persistence.
    
    In-memory implementation for now, MongoDB integration ready.
    """

    def __init__(self, db=None):
        """
        Initialize repository.
        
        Args:
            db: MongoDB database instance (optional, uses in-memory if None)
        """
        self.db = db
        
        # In-memory storage (used when db is None)
        self._ideas: Dict[str, Dict[str, Any]] = {}
        self._versions: Dict[str, Dict[str, Any]] = {}
        self._favorites: List[Dict[str, Any]] = []

    # ---------------------------------------------------------
    # IDEAS
    # ---------------------------------------------------------
    def create_idea(
        self,
        asset: str,
        timeframe: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create new idea."""
        idea_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        idea = {
            "id": idea_id,
            "asset": asset,
            "timeframe": timeframe,
            "user_id": user_id,
            "current_version_id": None,
            "version_count": 0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        if self.db:
            self.db.ideas.insert_one({**idea, "_id": idea_id})
        else:
            self._ideas[idea_id] = idea
        
        return idea

    def get_idea(self, idea_id: str) -> Optional[Dict[str, Any]]:
        """Get idea by ID."""
        if self.db:
            idea = self.db.ideas.find_one({"id": idea_id}, {"_id": 0})
            return idea
        return self._ideas.get(idea_id)

    def get_ideas_by_asset(self, asset: str) -> List[Dict[str, Any]]:
        """Get all ideas for an asset."""
        if self.db:
            return list(self.db.ideas.find({"asset": asset}, {"_id": 0}))
        return [i for i in self._ideas.values() if i["asset"] == asset]

    def get_ideas_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all ideas for a user."""
        if self.db:
            return list(self.db.ideas.find({"user_id": user_id}, {"_id": 0}))
        return [i for i in self._ideas.values() if i.get("user_id") == user_id]

    def get_all_ideas(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all ideas (for listing)."""
        if self.db:
            return list(
                self.db.ideas.find({}, {"_id": 0})
                .sort("created_at", -1)
                .limit(limit)
            )
        ideas = list(self._ideas.values())
        ideas.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return ideas[:limit]

    def update_idea(self, idea_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update idea fields."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        if self.db:
            self.db.ideas.update_one({"id": idea_id}, {"$set": updates})
            return self.get_idea(idea_id)
        else:
            if idea_id in self._ideas:
                self._ideas[idea_id].update(updates)
                return self._ideas[idea_id]
        return None

    # ---------------------------------------------------------
    # VERSIONS
    # ---------------------------------------------------------
    def create_version(
        self,
        idea_id: str,
        version_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create new version for idea."""
        version_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Get idea to determine version number
        idea = self.get_idea(idea_id)
        if not idea:
            raise ValueError(f"Idea {idea_id} not found")
        
        version_number = idea.get("version_count", 0) + 1
        previous_version_id = idea.get("current_version_id")
        
        version = {
            "id": version_id,
            "idea_id": idea_id,
            "version_number": version_number,
            "previous_version_id": previous_version_id,
            "created_at": now.isoformat(),
            "status": IdeaStatus.ACTIVE.value,
            **version_data,
        }
        
        if self.db:
            self.db.idea_versions.insert_one({**version, "_id": version_id})
        else:
            self._versions[version_id] = version
        
        # Update idea with new current version
        self.update_idea(idea_id, {
            "current_version_id": version_id,
            "version_count": version_number,
        })
        
        return version

    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Get version by ID."""
        if self.db:
            return self.db.idea_versions.find_one({"id": version_id}, {"_id": 0})
        return self._versions.get(version_id)

    def get_versions_by_idea(self, idea_id: str) -> List[Dict[str, Any]]:
        """Get all versions for an idea (newest first)."""
        if self.db:
            return list(
                self.db.idea_versions
                .find({"idea_id": idea_id}, {"_id": 0})
                .sort("version_number", -1)
            )
        versions = [v for v in self._versions.values() if v["idea_id"] == idea_id]
        return sorted(versions, key=lambda x: x["version_number"], reverse=True)

    def get_current_version(self, idea_id: str) -> Optional[Dict[str, Any]]:
        """Get current (latest) version for idea."""
        idea = self.get_idea(idea_id)
        if not idea or not idea.get("current_version_id"):
            return None
        return self.get_version(idea["current_version_id"])

    def update_version_status(
        self,
        version_id: str,
        status: IdeaStatus,
    ) -> Optional[Dict[str, Any]]:
        """Update version status."""
        if self.db:
            self.db.idea_versions.update_one(
                {"id": version_id},
                {"$set": {"status": status.value}}
            )
            return self.get_version(version_id)
        else:
            if version_id in self._versions:
                self._versions[version_id]["status"] = status.value
                return self._versions[version_id]
        return None

    # ---------------------------------------------------------
    # FAVORITES
    # ---------------------------------------------------------
    def add_favorite(self, user_id: str, idea_id: str) -> Dict[str, Any]:
        """Add idea to user's favorites."""
        favorite_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        favorite = {
            "id": favorite_id,
            "user_id": user_id,
            "idea_id": idea_id,
            "created_at": now.isoformat(),
        }
        
        if self.db:
            # Check if already favorited
            existing = self.db.favorites.find_one({
                "user_id": user_id,
                "idea_id": idea_id
            })
            if existing:
                return {"id": existing.get("id"), **existing}
            self.db.favorites.insert_one({**favorite, "_id": favorite_id})
        else:
            # Check if already favorited
            for fav in self._favorites:
                if fav["user_id"] == user_id and fav["idea_id"] == idea_id:
                    return fav
            self._favorites.append(favorite)
        
        return favorite

    def remove_favorite(self, user_id: str, idea_id: str) -> bool:
        """Remove idea from user's favorites."""
        if self.db:
            result = self.db.favorites.delete_one({
                "user_id": user_id,
                "idea_id": idea_id
            })
            return result.deleted_count > 0
        else:
            for i, fav in enumerate(self._favorites):
                if fav["user_id"] == user_id and fav["idea_id"] == idea_id:
                    self._favorites.pop(i)
                    return True
        return False

    def get_favorites_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all favorites for a user."""
        if self.db:
            return list(self.db.favorites.find({"user_id": user_id}, {"_id": 0}))
        return [f for f in self._favorites if f["user_id"] == user_id]

    def is_favorited(self, user_id: str, idea_id: str) -> bool:
        """Check if idea is favorited by user."""
        if self.db:
            return self.db.favorites.find_one({
                "user_id": user_id,
                "idea_id": idea_id
            }) is not None
        return any(
            f["user_id"] == user_id and f["idea_id"] == idea_id
            for f in self._favorites
        )


# ---------------------------------------------------------
# Singleton / Factory
# ---------------------------------------------------------
_idea_repository_instance: Optional[IdeaRepository] = None


def get_idea_repository(db=None) -> IdeaRepository:
    """Get singleton instance of IdeaRepository."""
    global _idea_repository_instance
    if _idea_repository_instance is None:
        _idea_repository_instance = IdeaRepository(db)
    return _idea_repository_instance
