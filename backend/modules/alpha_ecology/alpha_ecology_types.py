"""
PHASE 15 — Alpha Ecology Types
===============================
Contracts for Alpha Ecology Layer.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# DECAY STATE ENUM
# ══════════════════════════════════════════════════════════════

class DecayState(str, Enum):
    """Signal decay classification."""
    DECAYING = "DECAYING"      # Signal performance degrading
    STABLE = "STABLE"          # Signal performance consistent
    IMPROVING = "IMPROVING"    # Signal performance improving


# ══════════════════════════════════════════════════════════════
# CROWDING STATE ENUM (PHASE 15.2)
# ══════════════════════════════════════════════════════════════

class CrowdingState(str, Enum):
    """Market crowding level."""
    LOW_CROWDING = "LOW_CROWDING"
    MEDIUM_CROWDING = "MEDIUM_CROWDING"
    HIGH_CROWDING = "HIGH_CROWDING"
    EXTREME_CROWDING = "EXTREME_CROWDING"


# ══════════════════════════════════════════════════════════════
# CORRELATION STATE ENUM (PHASE 15.3)
# ══════════════════════════════════════════════════════════════

class CorrelationState(str, Enum):
    """Signal correlation level."""
    HIGHLY_CORRELATED = "HIGHLY_CORRELATED"
    PARTIAL = "PARTIAL"
    UNIQUE = "UNIQUE"


# ══════════════════════════════════════════════════════════════
# REDUNDANCY STATE ENUM (PHASE 15.4)
# ══════════════════════════════════════════════════════════════

class RedundancyState(str, Enum):
    """Signal redundancy level."""
    REDUNDANT = "REDUNDANT"
    NORMAL = "NORMAL"
    DIVERSIFIED = "DIVERSIFIED"


# ══════════════════════════════════════════════════════════════
# SURVIVAL STATE ENUM (PHASE 15.5)
# ══════════════════════════════════════════════════════════════

class SurvivalState(str, Enum):
    """Cross-regime signal survival."""
    FRAGILE = "FRAGILE"    # Works only in specific conditions
    STABLE = "STABLE"      # Works in most conditions
    ROBUST = "ROBUST"      # Works across all conditions


# ══════════════════════════════════════════════════════════════
# DECAY ENGINE CONTRACTS
# ══════════════════════════════════════════════════════════════

@dataclass
class SignalPerformanceWindow:
    """Performance metrics for a time window."""
    window_name: str  # "recent", "historical", "baseline"
    start_date: datetime
    end_date: datetime
    total_signals: int
    winning_signals: int
    losing_signals: int
    win_rate: float
    avg_return: float
    profit_factor: float
    sharpe_ratio: float
    
    def to_dict(self) -> Dict:
        return {
            "window_name": self.window_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_signals": self.total_signals,
            "winning_signals": self.winning_signals,
            "losing_signals": self.losing_signals,
            "win_rate": round(self.win_rate, 4),
            "avg_return": round(self.avg_return, 4),
            "profit_factor": round(self.profit_factor, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
        }


@dataclass
class SignalDecayResult:
    """
    Output from Alpha Decay Engine for a single signal.
    
    Compares recent vs historical performance to detect decay.
    """
    signal_id: str
    signal_type: str  # e.g., "trend_breakout", "momentum", "reversal"
    timestamp: datetime
    
    # Performance windows
    recent_performance: SignalPerformanceWindow
    historical_performance: SignalPerformanceWindow
    
    # Decay metrics
    decay_ratio: float  # recent_wr / historical_wr
    performance_delta: float  # recent_pf - historical_pf
    consistency_score: float  # How consistent is the signal
    
    # Final state
    decay_state: DecayState
    confidence: float
    
    # Modifiers for downstream
    confidence_modifier: float  # 0.7 - 1.1
    size_modifier: float  # 0.6 - 1.0
    
    # Explainability
    reason: str
    drivers: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "timestamp": self.timestamp.isoformat(),
            "recent_performance": self.recent_performance.to_dict(),
            "historical_performance": self.historical_performance.to_dict(),
            "decay_ratio": round(self.decay_ratio, 4),
            "performance_delta": round(self.performance_delta, 4),
            "consistency_score": round(self.consistency_score, 4),
            "decay_state": self.decay_state.value,
            "confidence": round(self.confidence, 4),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "size_modifier": round(self.size_modifier, 4),
            "reason": self.reason,
            "drivers": self.drivers,
        }


@dataclass
class SymbolDecaySnapshot:
    """Aggregated decay state for a symbol across all signals."""
    symbol: str
    timestamp: datetime
    
    # Per-signal decay results
    signal_decays: List[SignalDecayResult]
    
    # Aggregated metrics
    avg_decay_ratio: float
    decaying_signals_count: int
    stable_signals_count: int
    improving_signals_count: int
    
    # Overall state
    overall_decay_state: DecayState
    overall_confidence_modifier: float
    overall_size_modifier: float
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "signal_decays": [s.to_dict() for s in self.signal_decays],
            "avg_decay_ratio": round(self.avg_decay_ratio, 4),
            "decaying_signals_count": self.decaying_signals_count,
            "stable_signals_count": self.stable_signals_count,
            "improving_signals_count": self.improving_signals_count,
            "overall_decay_state": self.overall_decay_state.value,
            "overall_confidence_modifier": round(self.overall_confidence_modifier, 4),
            "overall_size_modifier": round(self.overall_size_modifier, 4),
        }


# ══════════════════════════════════════════════════════════════
# ECOLOGY AGGREGATOR CONTRACTS (PHASE 15.6)
# ══════════════════════════════════════════════════════════════

@dataclass
class AlphaEcologyState:
    """
    Unified Alpha Ecology state combining all sub-engines.
    
    PHASE 15.6 - Full implementation.
    """
    symbol: str
    timestamp: datetime
    
    # Individual states
    decay_state: DecayState
    crowding_state: CrowdingState
    correlation_state: CorrelationState
    redundancy_state: RedundancyState
    survival_state: SurvivalState
    
    # Overall score
    ecology_score: float  # 0.0 - 1.0
    ecology_quality: str  # "HEALTHY", "STRESSED", "CRITICAL"
    
    # Modifiers
    final_confidence_modifier: float
    final_size_modifier: float
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "decay_state": self.decay_state.value,
            "crowding_state": self.crowding_state.value,
            "correlation_state": self.correlation_state.value,
            "redundancy_state": self.redundancy_state.value,
            "survival_state": self.survival_state.value,
            "ecology_score": round(self.ecology_score, 4),
            "ecology_quality": self.ecology_quality,
            "final_confidence_modifier": round(self.final_confidence_modifier, 4),
            "final_size_modifier": round(self.final_size_modifier, 4),
        }
