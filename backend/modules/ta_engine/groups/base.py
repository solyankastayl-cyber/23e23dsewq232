"""
TA Engine - Group Layer Base
All 10 layers MUST return this exact structure
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass
class Window:
    """Pattern/finding time window"""
    start: int  # Unix timestamp of first touch
    end: int    # Unix timestamp of last touch
    
    def to_dict(self):
        return {"start": self.start, "end": self.end}


@dataclass
class Geometry:
    """Geometric quality metrics"""
    valid: bool = True
    clean: bool = True
    touches: int = 0
    symmetry: float = 0.0
    parallel: float = 0.0  # For channels
    
    def to_dict(self):
        return asdict(self)


@dataclass 
class Relevance:
    """How relevant is this finding to current price"""
    distance_to_price: float = 0.0  # % distance
    is_active: bool = True
    is_recent: bool = True
    recency_score: float = 1.0
    
    def to_dict(self):
        return asdict(self)


@dataclass
class RenderData:
    """Data needed to draw on chart"""
    boundaries: List[Dict] = field(default_factory=list)
    levels: List[Dict] = field(default_factory=list)
    anchors: List[Dict] = field(default_factory=list)
    markers: List[Dict] = field(default_factory=list)
    zones: List[Dict] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "boundaries": self.boundaries,
            "levels": self.levels,
            "anchors": self.anchors,
            "markers": self.markers,
            "zones": self.zones,
        }


@dataclass
class Finding:
    """
    UNIVERSAL finding structure.
    ALL groups MUST return findings in this format.
    """
    type: str                           # e.g., "falling_wedge", "support", "hammer"
    bias: str = "neutral"               # "bullish", "bearish", "neutral"
    score: float = 0.0                  # Quality score 0-1
    confidence: float = 0.0             # Confidence 0-1
    
    window: Optional[Window] = None
    geometry: Optional[Geometry] = None
    relevance: Optional[Relevance] = None
    render: Optional[RenderData] = None
    
    # Extra metadata
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "bias": self.bias,
            "score": self.score,
            "confidence": self.confidence,
            "window": self.window.to_dict() if self.window else None,
            "geometry": self.geometry.to_dict() if self.geometry else None,
            "relevance": self.relevance.to_dict() if self.relevance else None,
            "render": self.render.to_dict() if self.render else None,
            "meta": self.meta,
        }


@dataclass
class GroupResult:
    """
    UNIVERSAL group output structure.
    ALL 10 layers MUST return this.
    """
    group: str                          # Group name: "structure", "figures", etc.
    findings: List[Finding] = field(default_factory=list)
    
    # Group-level summary (optional, group-specific)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    # Processing metadata
    processed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    candle_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "group": self.group,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "processed_at": self.processed_at,
            "candle_count": self.candle_count,
        }
    
    def best(self) -> Optional[Finding]:
        """Get highest scoring finding"""
        if not self.findings:
            return None
        return max(self.findings, key=lambda f: f.score)


# ═══════════════════════════════════════════════════════════════
# GROUP NAMES (FIXED, DO NOT CHANGE)
# ═══════════════════════════════════════════════════════════════

GROUP_STRUCTURE = "structure"
GROUP_TRENDLINES = "trendlines"
GROUP_CHANNELS = "channels"
GROUP_FIGURES = "figures"
GROUP_LEVELS = "levels"
GROUP_FIBONACCI = "fibonacci"
GROUP_CANDLES = "candles"
GROUP_ELLIOTT = "elliott"
GROUP_REGIME = "regime"
GROUP_CONFIRMATION = "confirmation"

ALL_GROUPS = [
    GROUP_STRUCTURE,
    GROUP_TRENDLINES,
    GROUP_CHANNELS,
    GROUP_FIGURES,
    GROUP_LEVELS,
    GROUP_FIBONACCI,
    GROUP_CANDLES,
    GROUP_ELLIOTT,
    GROUP_REGIME,
    GROUP_CONFIRMATION,
]


# ═══════════════════════════════════════════════════════════════
# BIAS CONSTANTS
# ═══════════════════════════════════════════════════════════════

BIAS_BULLISH = "bullish"
BIAS_BEARISH = "bearish"
BIAS_NEUTRAL = "neutral"


# ═══════════════════════════════════════════════════════════════
# BASE LAYER CLASS
# ═══════════════════════════════════════════════════════════════

class BaseLayer:
    """
    Abstract base class for all 10 layers.
    Each layer MUST implement run() method.
    """
    
    GROUP_NAME = "base"  # Override in subclass
    
    def run(self, basis: Dict) -> GroupResult:
        """
        Run layer analysis.
        
        Args:
            basis: Common chart basis with pivots, swings, candles, etc.
            
        Returns:
            GroupResult with findings
        """
        raise NotImplementedError("Subclass must implement run()")
    
    def _create_result(self, findings: List[Finding], summary: Dict = None) -> GroupResult:
        """Helper to create properly formatted result"""
        return GroupResult(
            group=self.GROUP_NAME,
            findings=findings,
            summary=summary or {},
        )
