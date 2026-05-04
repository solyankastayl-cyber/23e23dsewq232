"""
Idea Service
=============
Service for managing ideas.

Provides:
- Create/Update/Delete ideas
- Version management
- Validation system
- Export functionality
"""

import os
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pymongo import MongoClient, DESCENDING
from bson import ObjectId

from modules.ta_engine.ideas.idea_types import (
    Idea,
    IdeaVersion,
    IdeaValidation,
    IdeaStatus,
    ValidationResult,
)
from modules.ta_engine.setup.setup_builder import get_setup_builder

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


class IdeaService:
    """Service for managing trading ideas."""
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.collection = self.db.ideas
        self.setup_builder = get_setup_builder()
    
    def create_idea(
        self,
        asset: str,
        timeframe: str,
        user_id: Optional[str] = None,
        tags: List[str] = None,
        notes: str = "",
        snapshot: Optional[Dict] = None,
    ) -> Idea:
        """
        Create a new idea.
        
        If snapshot is provided, uses it directly (from frontend).
        Otherwise, runs setup analysis.
        """
        idea_id = str(uuid.uuid4())[:12]
        now = datetime.now(timezone.utc)
        
        if snapshot:
            # Use provided snapshot (from frontend Save Idea button)
            version = IdeaVersion(
                version=1,
                timestamp=now,
                setup_snapshot=snapshot,
                technical_bias=snapshot.get('context', {}).get('mtf_bias', 'neutral'),
                confidence=snapshot.get('probability', {}).get('up', 0.5),
                price_at_creation=snapshot.get('levels', {}).get('top', 0),
            )
            
            idea = Idea(
                idea_id=idea_id,
                user_id=user_id,
                asset=asset.upper(),
                timeframe=timeframe,
                versions=[version],
                technical_bias=snapshot.get('context', {}).get('mtf_bias', 'neutral'),
                confidence=snapshot.get('probability', {}).get('up', 0.5),
                setup_type=snapshot.get('pattern', 'unknown'),
                created_at=now,
                updated_at=now,
                tags=tags or [],
                notes=notes,
            )
        else:
            # Run setup analysis (legacy flow)
            result = self.setup_builder.build(asset.upper(), timeframe)
            
            # Get current price
            current_price = 0.0
            if result.top_setup:
                current_price = result.top_setup.current_price
            
            # Create first version
            setup_snapshot = result.to_dict()
            version = IdeaVersion(
                version=1,
                timestamp=now,
                setup_snapshot=setup_snapshot,
                technical_bias=result.technical_bias.value,
                confidence=result.bias_confidence,
                price_at_creation=current_price,
            )
            
            idea = Idea(
                idea_id=idea_id,
                user_id=user_id,
                asset=asset.upper(),
                timeframe=timeframe,
                versions=[version],
                technical_bias=result.technical_bias.value,
                confidence=result.bias_confidence,
                setup_type=result.top_setup.setup_type.value if result.top_setup else None,
                created_at=now,
                updated_at=now,
                tags=tags or [],
                notes=notes,
            )
        
        # Save to DB
        self._save_idea(idea)
        
        return idea
    
    def update_idea(self, idea_id: str) -> Optional[Idea]:
        """
        Update an idea with fresh analysis, creating a new version.
        """
        idea = self.get_idea(idea_id)
        if not idea:
            return None
        
        # Run fresh analysis
        result = self.setup_builder.build(idea.asset, idea.timeframe)
        
        now = datetime.now(timezone.utc)
        current_price = result.top_setup.current_price if result.top_setup else 0.0
        
        # Create new version
        new_version = IdeaVersion(
            version=idea.current_version + 1,
            timestamp=now,
            setup_snapshot=result.to_dict(),
            technical_bias=result.technical_bias.value,
            confidence=result.bias_confidence,
            price_at_creation=current_price,
        )
        
        # Update idea
        idea.versions.append(new_version)
        idea.current_version += 1
        idea.technical_bias = result.technical_bias.value
        idea.confidence = result.bias_confidence
        idea.setup_type = result.top_setup.setup_type.value if result.top_setup else None
        idea.updated_at = now
        
        # Save
        self._save_idea(idea)
        
        return idea
    
    def validate_idea(
        self,
        idea_id: str,
        current_price: Optional[float] = None,
    ) -> Optional[Idea]:
        """
        Validate an idea by checking if prediction was correct.
        """
        idea = self.get_idea(idea_id)
        if not idea or not idea.versions:
            return None
        
        # Get original version data
        original_version = idea.versions[0]
        original_price = original_version.price_at_creation
        original_bias = original_version.technical_bias
        
        # Get setup snapshot for targets/invalidation
        setup_data = original_version.setup_snapshot
        top_setup = setup_data.get("top_setup", {})
        
        targets = top_setup.get("targets", [])
        invalidation = top_setup.get("invalidation")
        
        # Use provided price or fetch current
        if current_price is None:
            result = self.setup_builder.build(idea.asset, idea.timeframe)
            current_price = result.top_setup.current_price if result.top_setup else original_price
        
        # Calculate price change
        if original_price > 0:
            price_change_pct = ((current_price - original_price) / original_price) * 100
        else:
            price_change_pct = 0.0
        
        # Determine validation result
        target_hit = False
        invalidation_hit = False
        result = ValidationResult.PENDING
        
        if original_bias == "bullish":
            # Check if price moved up
            if targets and current_price >= targets[0]:
                target_hit = True
                result = ValidationResult.CORRECT
            elif invalidation and current_price <= invalidation:
                invalidation_hit = True
                result = ValidationResult.INVALIDATED
            elif price_change_pct > 2:
                result = ValidationResult.PARTIALLY_CORRECT
            elif price_change_pct < -2:
                result = ValidationResult.INVALIDATED
        
        elif original_bias == "bearish":
            # Check if price moved down
            if targets and current_price <= targets[0]:
                target_hit = True
                result = ValidationResult.CORRECT
            elif invalidation and current_price >= invalidation:
                invalidation_hit = True
                result = ValidationResult.INVALIDATED
            elif price_change_pct < -2:
                result = ValidationResult.PARTIALLY_CORRECT
            elif price_change_pct > 2:
                result = ValidationResult.INVALIDATED
        
        # Create validation record
        validation = IdeaValidation(
            validated_at=datetime.now(timezone.utc),
            result=result,
            price_at_validation=current_price,
            price_change_pct=price_change_pct,
            target_hit=target_hit,
            invalidation_hit=invalidation_hit,
        )
        
        # Update idea
        idea.validations.append(validation)
        idea.total_predictions += 1
        
        if result == ValidationResult.CORRECT:
            idea.correct_predictions += 1
            idea.status = IdeaStatus.COMPLETED
        elif result == ValidationResult.INVALIDATED:
            idea.status = IdeaStatus.INVALIDATED
        elif result == ValidationResult.PARTIALLY_CORRECT:
            idea.correct_predictions += 0.5
        
        # Update accuracy score
        if idea.total_predictions > 0:
            idea.accuracy_score = idea.correct_predictions / idea.total_predictions
        
        idea.updated_at = datetime.now(timezone.utc)
        
        # Save
        self._save_idea(idea)
        
        return idea
    
    def get_idea(self, idea_id: str) -> Optional[Idea]:
        """Get an idea by ID."""
        doc = self.collection.find_one({"idea_id": idea_id}, {"_id": 0})
        if not doc:
            return None
        return self._doc_to_idea(doc)
    
    def list_ideas(
        self,
        user_id: Optional[str] = None,
        asset: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Idea]:
        """List ideas with filters."""
        query = {}
        if user_id:
            query["user_id"] = user_id
        if asset:
            query["asset"] = asset.upper()
        if status:
            query["status"] = status
        
        cursor = self.collection.find(query, {"_id": 0}).sort("updated_at", DESCENDING).limit(limit)
        return [self._doc_to_idea(doc) for doc in cursor]
    
    def delete_idea(self, idea_id: str) -> bool:
        """Delete an idea."""
        result = self.collection.delete_one({"idea_id": idea_id})
        return result.deleted_count > 0
    
    def archive_idea(self, idea_id: str) -> Optional[Idea]:
        """Archive an idea."""
        idea = self.get_idea(idea_id)
        if not idea:
            return None
        
        idea.status = IdeaStatus.ARCHIVED
        idea.updated_at = datetime.now(timezone.utc)
        self._save_idea(idea)
        return idea
    
    def add_version(self, idea_id: str, snapshot: Dict) -> Optional[Idea]:
        """
        Add new version to idea (from auto-worker).
        """
        idea = self.get_idea(idea_id)
        if not idea:
            return None
        
        now = datetime.now(timezone.utc)
        
        new_version = IdeaVersion(
            version=idea.current_version + 1,
            timestamp=now,
            setup_snapshot=snapshot,
            technical_bias=snapshot.get("context", {}).get("mtf_bias", "neutral"),
            confidence=snapshot.get("probability", {}).get("up", 0.5),
            price_at_creation=snapshot.get("levels", {}).get("top", 0),
        )
        
        idea.versions.append(new_version)
        idea.current_version += 1
        idea.updated_at = now
        
        self._save_idea(idea)
        return idea
    
    def resolve_idea(
        self,
        idea_id: str,
        result: str,
        outcome: str,
        result_price: float,
        pnl_pct: Optional[float] = None,
    ) -> Optional[Idea]:
        """
        Resolve an idea with final result (from auto-worker).
        
        Args:
            result: "correct" | "wrong" | "neutral"
            outcome: "success_up" | "success_down" | "invalidated"
        """
        idea = self.get_idea(idea_id)
        if not idea:
            return None
        
        now = datetime.now(timezone.utc)
        
        # Update status
        if result == "correct":
            idea.status = IdeaStatus.COMPLETED
            idea.correct_predictions += 1
        elif result == "wrong":
            idea.status = IdeaStatus.INVALIDATED
        else:
            idea.status = IdeaStatus.COMPLETED
        
        idea.total_predictions += 1
        if idea.total_predictions > 0:
            idea.accuracy_score = idea.correct_predictions / idea.total_predictions
        
        idea.updated_at = now
        
        # Store result in last version snapshot
        if idea.versions:
            last_version = idea.versions[-1]
            if last_version.setup_snapshot is None:
                last_version.setup_snapshot = {}
            last_version.setup_snapshot["result"] = {
                "status": result,
                "outcome": outcome,
                "result_price": result_price,
                "pnl_pct": pnl_pct,
                "resolved_at": now.isoformat(),
            }
        
        self._save_idea(idea)
        return idea
    
    def get_idea_timeline(self, idea_id: str) -> Optional[Dict]:
        """Get timeline view of idea."""
        idea = self.get_idea(idea_id)
        if not idea:
            return None
        return idea.to_timeline_dict()
    
    def _save_idea(self, idea: Idea):
        """Save idea to MongoDB."""
        doc = {
            "idea_id": idea.idea_id,
            "user_id": idea.user_id,
            "asset": idea.asset,
            "timeframe": idea.timeframe,
            "status": idea.status.value,
            "current_version": idea.current_version,
            "versions": [v.to_dict() for v in idea.versions],
            "validations": [v.to_dict() for v in idea.validations],
            "technical_bias": idea.technical_bias,
            "confidence": idea.confidence,
            "setup_type": idea.setup_type,
            "accuracy_score": idea.accuracy_score,
            "total_predictions": idea.total_predictions,
            "correct_predictions": idea.correct_predictions,
            "created_at": idea.created_at.isoformat(),
            "updated_at": idea.updated_at.isoformat(),
            "tags": idea.tags,
            "notes": idea.notes,
        }
        
        self.collection.update_one(
            {"idea_id": idea.idea_id},
            {"$set": doc},
            upsert=True
        )
    
    def _doc_to_idea(self, doc: Dict) -> Idea:
        """Convert MongoDB document to Idea object."""
        versions = []
        for v in doc.get("versions", []):
            versions.append(IdeaVersion(
                version=v["version"],
                timestamp=datetime.fromisoformat(v["timestamp"]),
                setup_snapshot=v["setup_snapshot"],
                technical_bias=v["technical_bias"],
                confidence=v["confidence"],
                ai_explanation=v.get("ai_explanation"),
                price_at_creation=v.get("price_at_creation", 0),
            ))
        
        validations = []
        for v in doc.get("validations", []):
            validations.append(IdeaValidation(
                validated_at=datetime.fromisoformat(v["validated_at"]),
                result=ValidationResult(v["result"]),
                price_at_validation=v["price_at_validation"],
                price_change_pct=v["price_change_pct"],
                target_hit=v.get("target_hit", False),
                invalidation_hit=v.get("invalidation_hit", False),
                notes=v.get("notes", ""),
            ))
        
        return Idea(
            idea_id=doc["idea_id"],
            user_id=doc.get("user_id"),
            asset=doc["asset"],
            timeframe=doc["timeframe"],
            status=IdeaStatus(doc.get("status", "active")),
            current_version=doc.get("current_version", 1),
            versions=versions,
            validations=validations,
            technical_bias=doc.get("technical_bias", "neutral"),
            confidence=doc.get("confidence", 0),
            setup_type=doc.get("setup_type"),
            accuracy_score=doc.get("accuracy_score"),
            total_predictions=doc.get("total_predictions", 0),
            correct_predictions=doc.get("correct_predictions", 0),
            created_at=datetime.fromisoformat(doc["created_at"]) if doc.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(doc["updated_at"]) if doc.get("updated_at") else datetime.now(timezone.utc),
            tags=doc.get("tags", []),
            notes=doc.get("notes", ""),
        )


# Singleton
_service: Optional[IdeaService] = None


def get_idea_service() -> IdeaService:
    global _service
    if _service is None:
        _service = IdeaService()
    return _service
