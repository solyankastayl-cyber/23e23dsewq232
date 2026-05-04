"""
My Ideas — Data Models
======================
Storage model for ideas with versioning.
"""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class IdeaSnapshot(BaseModel):
    """Full snapshot of system state at moment of save."""
    symbol: str
    timeframe: str
    current_price: float

    decision: Dict[str, Any]
    scenarios: List[Dict[str, Any]]
    trade_setup: Optional[Dict[str, Any]] = None
    explanation: Optional[Dict[str, Any]] = None

    primary_pattern: Optional[Dict[str, Any]] = None
    alternative_patterns: List[Dict[str, Any]] = Field(default_factory=list)

    structure_context: Optional[Dict[str, Any]] = None
    mtf_context: Optional[Dict[str, Any]] = None
    base_layer: Optional[Dict[str, Any]] = None


class IdeaRecord(BaseModel):
    """Idea card (meta only)."""
    idea_id: str
    title: str
    symbol: str
    timeframe: str
    status: str = "active"  # active / archived / invalidated

    current_version_id: Optional[str] = None
    version_count: int = 0

    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class IdeaVersionRecord(BaseModel):
    """Version snapshot."""
    version_id: str
    idea_id: str
    version_number: int

    snapshot: IdeaSnapshot
    note: Optional[str] = None

    created_at: datetime
