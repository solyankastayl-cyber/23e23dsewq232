"""
AF3 Combined Alpha Truth Models
"""
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional


@dataclass
class CombinedAlphaTruth:
    """
    Combined truth from Alpha Factory (historical) + V1 Validation (live).
    
    Verdicts:
    - STRONG_CONFIRMED_EDGE: Historical edge confirmed by live validation
    - STRONG_BUT_DECAYING: Historical edge NOT confirmed live (edge decay)
    - WEAK_EDGE: Edge present but unconvincing
    - NO_EDGE: No edge in history or live
    """
    scope: str  # "symbol" or "entry_mode"
    scope_key: str  # e.g., "BTCUSDT" or "GO_FULL"
    
    alpha_metrics: Dict[str, Any]
    validation_metrics: Dict[str, Any]
    
    combined_verdict: str
    confidence: float
    reasons: List[str]
    
    # Computed scores
    alpha_score: float = 0.0
    validation_score: float = 0.0
    combined_score: float = 0.0
    
    # Decay detection
    decay_detected: bool = False
    decay_severity: str = "none"  # none, mild, severe
    
    timestamp: str = ""
    
    def to_dict(self):
        return asdict(self)


@dataclass
class AF3Action:
    """Action generated from combined truth evaluation"""
    scope: str
    scope_key: str
    
    action: str  # INCREASE_ALLOCATION, REDUCE_RISK, DISABLE_SYMBOL, KEEP, etc.
    magnitude: float
    reason: str
    
    # Source truth
    combined_verdict: str
    confidence: float
    
    # Flags
    urgent: bool = False
    requires_approval: bool = False
    
    def to_dict(self):
        return asdict(self)


@dataclass
class ValidationBridgeSummary:
    """Summary of validation bridge evaluation"""
    total_symbols: int
    strong_confirmed: int
    strong_decaying: int
    weak_edge: int
    no_edge: int
    
    actions_generated: int
    high_priority_actions: int
    
    overall_health: str  # "healthy", "warning", "critical"
    
    def to_dict(self):
        return asdict(self)
