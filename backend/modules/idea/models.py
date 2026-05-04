"""
Idea Models — Core data structures for Idea System
==================================================

Idea = snapshot of analysis that can be:
  - Saved
  - Versioned
  - Favorited
  - Tracked

Version chain: old ideas NOT deleted, new versions linked.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class IdeaStatus(str, Enum):
    """Idea lifecycle status."""
    ACTIVE = "ACTIVE"                    # Fresh, not yet confirmed
    PLAYING_OUT = "PLAYING_OUT"          # Price approaching trigger
    PARTIALLY_VALIDATED = "PARTIALLY_VALIDATED"  # Some conditions met
    VALIDATED = "VALIDATED"              # Scenario played out
    INVALIDATED = "INVALIDATED"          # Invalidation hit
    OUTDATED = "OUTDATED"                # Structure changed significantly


@dataclass
class IdeaVersion:
    """
    Single version of an idea — immutable snapshot.
    
    Each update creates NEW version, old ones preserved.
    """
    id: str
    idea_id: str
    version_number: int
    
    # Analysis snapshot
    bias: str                    # bullish / bearish / neutral
    confidence: float
    strength: str                # strong / medium / weak
    tradeability: str            # good / conditional / low
    
    # Scenario snapshot
    scenario_direction: str
    scenario_probability: float
    scenario_title: str
    scenario_summary: str
    
    # Key levels
    trigger: str
    invalidation: str
    
    # Explanation snapshot
    explanation_summary: str
    explanation_reasoning: str
    explanation_risks: str
    short_text: str
    
    # Status
    status: IdeaStatus
    
    # Metadata
    created_at: datetime
    previous_version_id: Optional[str] = None


@dataclass
class Idea:
    """
    Main idea object — container for versions.
    
    Idea itself is lightweight, all data is in versions.
    """
    id: str
    asset: str
    timeframe: str
    
    # Current state
    current_version_id: Optional[str] = None
    version_count: int = 0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # User reference (optional)
    user_id: Optional[str] = None


@dataclass
class Favorite:
    """User's favorite idea reference."""
    id: str
    user_id: str
    idea_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class IdeaUpdateRecommendation:
    """Recommendation to update idea based on market changes."""
    idea_id: str
    reason: str                  # "structure_changed" / "bias_shifted" / "scenario_played_out"
    urgency: str                 # "low" / "medium" / "high"
    details: str
    detected_at: datetime = field(default_factory=datetime.utcnow)
