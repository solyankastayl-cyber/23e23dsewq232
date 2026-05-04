"""
Pattern Candidate Model
=======================

Unified model for all pattern types with scoring fields.
This allows fair comparison between triangles, channels, ranges, etc.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class PatternCandidate:
    """
    Universal pattern candidate with all scoring fields.
    
    Every pattern type (triangle, channel, range, H&S) uses this model.
    This enables fair ranking between different pattern types.
    """
    # Core identification
    type: str                           # symmetrical_triangle, ascending_triangle, range, etc.
    direction: str                      # bullish / bearish / neutral
    
    # Geometry scores (from validator)
    confidence: float                   # Base confidence from validator
    geometry_score: float               # How well the geometry fits
    touch_count: int                    # Number of line touches
    containment: float                  # % of candles inside pattern
    line_scores: Dict[str, float]       # Per-line quality scores
    
    # Points for rendering
    points: Dict[str, Any]              # Extended lines for rendering
    anchor_points: Dict[str, Any]       # Original pivot points
    
    # Position info (for expiration)
    start_index: int                    # Where pattern starts
    end_index: int                      # Where pattern ends
    last_touch_index: int               # Last time price touched boundary
    
    # Ranking scores (filled by ranking engine)
    structure_score: float = 0.0        # Alignment with market structure
    level_score: float = 0.0            # Alignment with S/R levels
    recency_score: float = 0.0          # How fresh/relevant is it
    cleanliness_score: float = 0.0      # Overall quality
    total_score: float = 0.0            # Final ranking score
    
    # NEW: Production scoring fields (PSE v2.0)
    context_score: float = 0.0          # Market context fit
    relevance_score: float = 0.0        # Recency + proximity
    clarity_score: float = 0.0          # Visual clarity
    final_score: float = 0.0            # Weighted final score
    
    # Status and metadata
    status: Optional[str] = "active"    # active, forming, broken, expired, ambiguous
    touches: Optional[int] = None       # Alias for touch_count (for compatibility)
    scores: Optional[Dict[str, float]] = None  # Additional scores dict
    engine: Optional[str] = None        # V4_ANCHOR for new anchor-based engine
    
    # Trading levels
    breakout_level: Optional[float] = None
    invalidation: Optional[float] = None
    target_level: Optional[float] = None
    
    # V5 State Engine fields
    state: Optional[str] = None           # forming, maturing, breakout, breakdown, invalidated
    state_reason: Optional[str] = None    # Explanation of state
    respect_score: Optional[float] = None # How well price respects lines (0-1)
    compression_score: Optional[float] = None  # How much range is narrowing (0-1)
    reaction_score: Optional[float] = None # Strength of reactions at touches (0-1)
    
    # Range Regime Engine V2 fields
    is_active: Optional[bool] = None      # Range is still active (not broken)
    forward_bars: Optional[int] = None    # How many bars forward to extend
    breakout_state: Optional[str] = None  # none / testing / confirmed
    
    def __post_init__(self):
        """Set computed fields."""
        if self.touches is None:
            self.touches = self.touch_count
    
    def to_dict(self) -> dict:
        """Convert to API response format."""
        result = {
            "type": self.type,
            "direction": self.direction,
            "confidence": round(self.confidence, 2),
            "engine": self.engine,  # V4_ANCHOR / V5_STATE marker
            "total_score": round(self.total_score, 2),
            "final_score": round(self.final_score, 2),
            "status": self.status,
            "scores": {
                "geometry": round(self.geometry_score, 2),
                "structure": round(self.structure_score, 2),
                "level": round(self.level_score, 2),
                "recency": round(self.recency_score, 2),
                "cleanliness": round(self.cleanliness_score, 2),
                "context": round(self.context_score, 2),
                "relevance": round(self.relevance_score, 2),
                "clarity": round(self.clarity_score, 2),
            },
            "touches": self.touch_count,
            "containment": round(self.containment, 2),
            "line_scores": {k: round(v, 1) for k, v in (self.line_scores or {}).items()},
            "points": self.points,
            "anchor_points": self.anchor_points,
            "breakout_level": round(self.breakout_level, 2) if self.breakout_level else None,
            "invalidation": round(self.invalidation, 2) if self.invalidation else None,
        }
        
        # V5 State Engine fields
        if self.state:
            result["state"] = self.state
            result["state_reason"] = self.state_reason
        if self.respect_score is not None:
            result["respect_score"] = round(self.respect_score, 2)
        if self.compression_score is not None:
            result["compression_score"] = round(self.compression_score, 2)
        if self.target_level is not None:
            result["target_level"] = round(self.target_level, 2)
        
        # Range Regime Engine V2 fields
        if self.is_active is not None:
            result["is_active"] = self.is_active
        if self.forward_bars is not None:
            result["forward_bars"] = self.forward_bars
        if self.breakout_state is not None:
            result["breakout_state"] = self.breakout_state
        
        return result
