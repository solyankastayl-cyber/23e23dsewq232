"""
Idea Types
===========
Data structures for Idea System.

Idea = saved setup analysis that can be:
- Versioned (updated over time)
- Validated (check if prediction was correct)
- Exported (as content/screenshot)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


class IdeaStatus(Enum):
    """Status of an idea."""
    ACTIVE = "active"
    INVALIDATED = "invalidated"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ValidationResult(Enum):
    """Result of idea validation."""
    CORRECT = "correct"
    PARTIALLY_CORRECT = "partially_correct"
    INVALIDATED = "invalidated"
    PENDING = "pending"


@dataclass
class IdeaVersion:
    """A single version of an idea."""
    version: int
    timestamp: datetime
    setup_snapshot: Dict  # Full setup data at this point
    technical_bias: str
    confidence: float
    ai_explanation: Optional[str] = None
    price_at_creation: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "setup_snapshot": self.setup_snapshot,
            "technical_bias": self.technical_bias,
            "confidence": round(self.confidence, 4),
            "ai_explanation": self.ai_explanation,
            "price_at_creation": self.price_at_creation,
        }


@dataclass
class IdeaValidation:
    """Validation result for an idea."""
    validated_at: datetime
    result: ValidationResult
    price_at_validation: float
    price_change_pct: float
    target_hit: bool = False
    invalidation_hit: bool = False
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "validated_at": self.validated_at.isoformat(),
            "result": self.result.value,
            "price_at_validation": self.price_at_validation,
            "price_change_pct": round(self.price_change_pct, 4),
            "target_hit": self.target_hit,
            "invalidation_hit": self.invalidation_hit,
            "notes": self.notes,
        }


@dataclass
class Idea:
    """
    A saved trading idea.
    
    Ideas are:
    - Versioned (can be updated with new analysis)
    - Validated (system checks if prediction was correct)
    - Exportable (for content creation)
    """
    idea_id: str
    user_id: Optional[str]
    
    # Asset info
    asset: str
    timeframe: str
    
    # Current state
    status: IdeaStatus = IdeaStatus.ACTIVE
    current_version: int = 1
    
    # Versions history
    versions: List[IdeaVersion] = field(default_factory=list)
    
    # Validation history
    validations: List[IdeaValidation] = field(default_factory=list)
    
    # Latest data (from most recent version)
    technical_bias: str = "neutral"
    confidence: float = 0.0
    setup_type: Optional[str] = None
    
    # Accuracy tracking
    accuracy_score: Optional[float] = None
    total_predictions: int = 0
    correct_predictions: int = 0
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    
    def to_dict(self) -> dict:
        """Full idea data."""
        return {
            "idea_id": self.idea_id,
            "user_id": self.user_id,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "status": self.status.value,
            "current_version": self.current_version,
            "versions": [v.to_dict() for v in self.versions],
            "validations": [v.to_dict() for v in self.validations],
            "technical_bias": self.technical_bias,
            "confidence": round(self.confidence, 4),
            "setup_type": self.setup_type,
            "accuracy_score": round(self.accuracy_score, 4) if self.accuracy_score else None,
            "total_predictions": self.total_predictions,
            "correct_predictions": self.correct_predictions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "notes": self.notes,
        }
    
    def to_summary_dict(self) -> dict:
        """Compact summary for listings."""
        latest_version = self.versions[-1] if self.versions else None
        return {
            "idea_id": self.idea_id,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "status": self.status.value,
            "technical_bias": self.technical_bias,
            "confidence": round(self.confidence, 4),
            "setup_type": self.setup_type,
            "current_version": self.current_version,
            "accuracy_score": round(self.accuracy_score, 4) if self.accuracy_score else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    def to_timeline_dict(self) -> dict:
        """Timeline view of idea evolution."""
        timeline = []
        
        for v in self.versions:
            timeline.append({
                "type": "version",
                "timestamp": v.timestamp.isoformat(),
                "version": v.version,
                "technical_bias": v.technical_bias,
                "confidence": v.confidence,
                "price": v.price_at_creation,
            })
        
        for val in self.validations:
            timeline.append({
                "type": "validation",
                "timestamp": val.validated_at.isoformat(),
                "result": val.result.value,
                "price": val.price_at_validation,
                "price_change_pct": val.price_change_pct,
            })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])
        
        return {
            "idea_id": self.idea_id,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "timeline": timeline,
        }
