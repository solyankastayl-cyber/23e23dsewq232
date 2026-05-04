"""
My Ideas — Repository Layer
===========================
MongoDB operations for ideas + versions.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from .models import IdeaRecord, IdeaVersionRecord, IdeaSnapshot


class IdeasRepository:
    def __init__(self, db):
        self.ideas = db["ta_ideas"]
        self.versions = db["ta_idea_versions"]
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create indexes for efficient queries."""
        try:
            self.ideas.create_index("idea_id", unique=True)
            self.ideas.create_index([("updated_at", -1)])
            self.ideas.create_index([("status", 1), ("updated_at", -1)])
            self.ideas.create_index([("symbol", 1), ("updated_at", -1)])

            self.versions.create_index("version_id", unique=True)
            self.versions.create_index([("idea_id", 1), ("version_number", -1)])
            self.versions.create_index([("created_at", -1)])
        except Exception:
            pass  # Indexes may already exist

    def create_idea(
        self,
        title: str,
        snapshot: IdeaSnapshot,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        idea_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())

        idea = IdeaRecord(
            idea_id=idea_id,
            title=title,
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            status="active",
            current_version_id=version_id,
            version_count=1,
            tags=tags or [],
            notes=notes,
            created_at=now,
            updated_at=now,
        )

        version = IdeaVersionRecord(
            version_id=version_id,
            idea_id=idea_id,
            version_number=1,
            snapshot=snapshot,
            note="Initial version",
            created_at=now,
        )

        idea_dict = idea.model_dump()
        version_dict = version.model_dump()
        
        # Convert datetime for MongoDB
        idea_dict["created_at"] = idea_dict["created_at"].isoformat()
        idea_dict["updated_at"] = idea_dict["updated_at"].isoformat()
        version_dict["created_at"] = version_dict["created_at"].isoformat()

        self.ideas.insert_one(idea_dict)
        self.versions.insert_one(version_dict)

        return {
            **idea_dict,
            "current_version": version_dict,
        }

    def list_ideas(
        self, 
        status: Optional[str] = None, 
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}
        if status:
            query["status"] = status
        if symbol:
            query["symbol"] = symbol.upper()

        items = list(
            self.ideas.find(query, {"_id": 0})
            .sort("updated_at", -1)
            .limit(limit)
        )
        return items

    def get_idea(self, idea_id: str) -> Optional[Dict[str, Any]]:
        return self.ideas.find_one({"idea_id": idea_id}, {"_id": 0})

    def get_current_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        return self.versions.find_one({"version_id": version_id}, {"_id": 0})

    def get_versions(self, idea_id: str) -> List[Dict[str, Any]]:
        return list(
            self.versions.find({"idea_id": idea_id}, {"_id": 0})
            .sort("version_number", -1)
        )

    def create_new_version(
        self,
        idea_id: str,
        snapshot: IdeaSnapshot,
        note: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        idea = self.get_idea(idea_id)
        if not idea:
            return None

        now = datetime.now(timezone.utc)
        next_version = int(idea.get("version_count", 0)) + 1
        version_id = str(uuid.uuid4())

        version = IdeaVersionRecord(
            version_id=version_id,
            idea_id=idea_id,
            version_number=next_version,
            snapshot=snapshot,
            note=note,
            created_at=now,
        )

        version_dict = version.model_dump()
        version_dict["created_at"] = version_dict["created_at"].isoformat()

        self.versions.insert_one(version_dict)

        self.ideas.update_one(
            {"idea_id": idea_id},
            {
                "$set": {
                    "current_version_id": version_id,
                    "symbol": snapshot.symbol,
                    "timeframe": snapshot.timeframe,
                    "updated_at": now.isoformat(),
                },
                "$inc": {
                    "version_count": 1
                }
            }
        )

        updated_idea = self.get_idea(idea_id)
        return {
            **updated_idea,
            "current_version": version_dict,
        }

    def update_idea_meta(
        self,
        idea_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        if title is not None:
            payload["title"] = title
        if status is not None:
            payload["status"] = status
        if tags is not None:
            payload["tags"] = tags
        if notes is not None:
            payload["notes"] = notes

        self.ideas.update_one({"idea_id": idea_id}, {"$set": payload})
        return self.get_idea(idea_id)

    def delete_idea(self, idea_id: str) -> bool:
        """Delete idea and all its versions."""
        idea = self.get_idea(idea_id)
        if not idea:
            return False
        
        self.versions.delete_many({"idea_id": idea_id})
        self.ideas.delete_one({"idea_id": idea_id})
        return True
