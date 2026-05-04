"""
Pattern Candidate Model
=======================
Unified data model for chart patterns with lifecycle support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PatternLine:
    """A single line in a pattern (upper/lower/neckline)."""
    name: str                       # upper / lower / neckline / midline
    points: List[Dict[str, float]]  # [{"time": ..., "value": ...}, ...]
    touches: int = 0
    slope: Optional[float] = None


@dataclass
class PatternWindow:
    """Local window where pattern was detected."""
    start_index: int
    end_index: int
    start_time: int
    end_time: int
    timeframe: str


@dataclass
class PatternScores:
    """Scoring breakdown for pattern quality."""
    geometry: float = 0.0       # 35% - line angles, convergence
    touch_quality: float = 0.0  # 20% - number of valid touches
    containment: float = 0.0    # 15% - price within boundaries
    context_fit: float = 0.0    # 15% - regime/structure alignment
    recency: float = 0.0        # 10% - how recent is the pattern
    cleanliness: float = 0.0    # 5%  - noise/wicks outside

    @property
    def total(self) -> float:
        return round(
            self.geometry * 0.35 +
            self.touch_quality * 0.20 +
            self.containment * 0.15 +
            self.context_fit * 0.15 +
            self.recency * 0.10 +
            self.cleanliness * 0.05,
            4,
        )


@dataclass
class PatternCandidate:
    """
    Complete pattern candidate with lifecycle.
    
    States:
    - forming: pattern still building
    - active: valid pattern, tradeable
    - broken: boundary breached
    - invalidated: context changed
    - expired: too old to be relevant
    """
    pattern_id: str
    type: str                      # descending_triangle / ascending_triangle / channel / wedge / double_top / hs
    direction_bias: str            # bullish / bearish / neutral
    state: str                     # forming / active / broken / invalidated / expired

    window: PatternWindow
    lines: List[PatternLine] = field(default_factory=list)

    breakout_level: Optional[float] = None
    invalidation_level: Optional[float] = None

    apex_time: Optional[int] = None
    completion_time: Optional[int] = None

    broken: bool = False
    invalidated: bool = False
    expired: bool = False

    scores: PatternScores = field(default_factory=PatternScores)

    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "type": self.type,
            "direction_bias": self.direction_bias,
            "state": self.state,
            "window": {
                "start_index": self.window.start_index,
                "end_index": self.window.end_index,
                "start_time": self.window.start_time,
                "end_time": self.window.end_time,
                "timeframe": self.window.timeframe,
            },
            "lines": [
                {
                    "name": line.name,
                    "points": line.points,
                    "touches": line.touches,
                    "slope": line.slope,
                }
                for line in self.lines
            ],
            "breakout_level": self.breakout_level,
            "invalidation_level": self.invalidation_level,
            "apex_time": self.apex_time,
            "completion_time": self.completion_time,
            "broken": self.broken,
            "invalidated": self.invalidated,
            "expired": self.expired,
            "scores": {
                "geometry": self.scores.geometry,
                "touch_quality": self.scores.touch_quality,
                "containment": self.scores.containment,
                "context_fit": self.scores.context_fit,
                "recency": self.scores.recency,
                "cleanliness": self.scores.cleanliness,
                "total": self.scores.total,
            },
            "meta": self.meta,
        }
