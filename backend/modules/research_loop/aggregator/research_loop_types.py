"""
PHASE 20.4 — Research Loop Types
================================
Type definitions for Research Loop Aggregator.

Core contracts:
- ResearchLoopState: Unified self-improving loop state
- LoopSignal: Individual signal strength
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# LOOP STATE ENUM
# ══════════════════════════════════════════════════════════════

class LoopState(str, Enum):
    """Research loop overall state."""
    HEALTHY = "HEALTHY"       # System stable, minimal issues
    ADAPTING = "ADAPTING"     # Actively rebalancing, no crisis
    DEGRADED = "DEGRADED"     # Multiple issues, needs attention
    CRITICAL = "CRITICAL"     # System-wide problems, intervention needed


# ══════════════════════════════════════════════════════════════
# LOOP STATE THRESHOLDS
# ══════════════════════════════════════════════════════════════

LOOP_STATE_THRESHOLDS = {
    LoopState.HEALTHY: 0.75,    # score >= 0.75
    LoopState.ADAPTING: 0.55,   # score >= 0.55
    LoopState.DEGRADED: 0.35,   # score >= 0.35
    # score < 0.35 = CRITICAL
}


# ══════════════════════════════════════════════════════════════
# LOOP MODIFIERS BY STATE
# ══════════════════════════════════════════════════════════════

LOOP_MODIFIERS = {
    LoopState.HEALTHY: {
        "confidence_modifier": 1.03,
        "capital_modifier": 1.05,
    },
    LoopState.ADAPTING: {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    LoopState.DEGRADED: {
        "confidence_modifier": 0.92,
        "capital_modifier": 0.90,
    },
    LoopState.CRITICAL: {
        "confidence_modifier": 0.80,
        "capital_modifier": 0.75,
    },
}


# ══════════════════════════════════════════════════════════════
# LOOP SCORE WEIGHTS
# ══════════════════════════════════════════════════════════════

LOOP_SCORE_WEIGHTS = {
    "healthy_factor_ratio": 0.30,
    "promotion_health": 0.20,
    "adjustment_stability": 0.20,
    "critical_pattern_pressure": -0.15,
    "retire_freeze_pressure": -0.15,
}


# ══════════════════════════════════════════════════════════════
# LOOP SIGNAL
# ══════════════════════════════════════════════════════════════

@dataclass
class LoopSignal:
    """Individual signal in the research loop."""
    name: str
    value: float          # 0..1 for positive, 0..1 for negative pressure
    weight: float         # Weight in final score
    contribution: float   # weight * value (can be negative)
    status: str           # STRONG / MODERATE / WEAK / CRITICAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "weight": self.weight,
            "contribution": round(self.contribution, 4),
            "status": self.status,
        }


# ══════════════════════════════════════════════════════════════
# RESEARCH LOOP STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class ResearchLoopState:
    """
    Unified Research Loop State.
    
    Aggregates:
    - Failure Pattern Engine
    - Factor Weight Adjustment
    - Adaptive Promotion / Demotion
    """
    # Overall state
    loop_state: LoopState
    loop_score: float
    
    # Factor counts
    total_factors: int
    healthy_factors: int
    watchlist_factors: int
    degraded_factors: int
    retired_factors: int
    
    # Critical patterns from Failure Pattern Engine
    critical_failure_patterns: List[str]
    
    # Recommendations from Factor Weight Adjustment
    recommended_increases: List[str]
    recommended_decreases: List[str]
    
    # Recommendations from Adaptive Promotion
    recommended_promotions: List[str]
    recommended_demotions: List[str]
    recommended_freezes: List[str]
    recommended_retires: List[str]
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Signal analysis
    strongest_signal: str
    weakest_signal: str
    
    # Explainability
    reason: str
    
    # Detailed signals
    signals: List[LoopSignal] = field(default_factory=list)
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "loop_state": self.loop_state.value,
            "loop_score": round(self.loop_score, 4),
            
            "total_factors": self.total_factors,
            "healthy_factors": self.healthy_factors,
            "watchlist_factors": self.watchlist_factors,
            "degraded_factors": self.degraded_factors,
            "retired_factors": self.retired_factors,
            
            "critical_failure_patterns": self.critical_failure_patterns,
            
            "recommended_increases": self.recommended_increases,
            "recommended_decreases": self.recommended_decreases,
            "recommended_promotions": self.recommended_promotions,
            "recommended_demotions": self.recommended_demotions,
            "recommended_freezes": self.recommended_freezes,
            "recommended_retires": self.recommended_retires,
            
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            
            "strongest_signal": self.strongest_signal,
            "weakest_signal": self.weakest_signal,
            
            "reason": self.reason,
            
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with signal details."""
        result = self.to_dict()
        result["signals"] = [s.to_dict() for s in self.signals]
        return result
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "loop_state": self.loop_state.value,
            "loop_score": round(self.loop_score, 4),
            "total_factors": self.total_factors,
            "healthy_factors": self.healthy_factors,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "strongest_signal": self.strongest_signal,
            "weakest_signal": self.weakest_signal,
        }


# ══════════════════════════════════════════════════════════════
# RESEARCH LOOP HISTORY ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass
class ResearchLoopHistoryEntry:
    """Single history entry for research loop state."""
    loop_state: LoopState
    loop_score: float
    healthy_factors: int
    total_factors: int
    critical_patterns_count: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "loop_state": self.loop_state.value,
            "loop_score": round(self.loop_score, 4),
            "healthy_factors": self.healthy_factors,
            "total_factors": self.total_factors,
            "critical_patterns_count": self.critical_patterns_count,
            "timestamp": self.timestamp.isoformat(),
        }
