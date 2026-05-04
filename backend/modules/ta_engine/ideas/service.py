"""
My Ideas — Service Layer
========================
Business logic for ideas management.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .models import IdeaSnapshot
from .repository import IdeasRepository


class IdeasService:
    def __init__(self, repo: IdeasRepository):
        self.repo = repo

    def _default_title(self, snapshot: IdeaSnapshot) -> str:
        bias = snapshot.decision.get("bias", "neutral").upper()
        return f"{snapshot.symbol} {snapshot.timeframe} — {bias}"

    def create_idea(
        self,
        snapshot_payload: Dict[str, Any],
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        snapshot = IdeaSnapshot(**snapshot_payload)
        final_title = title or self._default_title(snapshot)

        return self.repo.create_idea(
            title=final_title,
            snapshot=snapshot,
            tags=tags,
            notes=notes,
        )

    def list_ideas(
        self, 
        status: Optional[str] = None, 
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        return self.repo.list_ideas(status=status, symbol=symbol, limit=limit)

    def get_idea_with_current_version(self, idea_id: str) -> Optional[Dict[str, Any]]:
        idea = self.repo.get_idea(idea_id)
        if not idea:
            return None

        current_version = None
        if idea.get("current_version_id"):
            current_version = self.repo.get_current_version(idea["current_version_id"])

        return {
            **idea,
            "current_version": current_version,
        }

    def get_idea_versions(self, idea_id: str) -> Optional[List[Dict[str, Any]]]:
        idea = self.repo.get_idea(idea_id)
        if not idea:
            return None
        return self.repo.get_versions(idea_id)

    def refresh_idea(
        self,
        idea_id: str,
        snapshot_payload: Dict[str, Any],
        note: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        snapshot = IdeaSnapshot(**snapshot_payload)
        return self.repo.create_new_version(
            idea_id=idea_id,
            snapshot=snapshot,
            note=note or "Refreshed with latest market state",
        )

    def update_idea_meta(
        self,
        idea_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return self.repo.update_idea_meta(
            idea_id=idea_id,
            title=title,
            status=status,
            tags=tags,
            notes=notes,
        )

    def delete_idea(self, idea_id: str) -> bool:
        return self.repo.delete_idea(idea_id)
