"""Canonical typed contract for Temporal Intelligence."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import List, Optional

MIN_HISTORY: int = 5  # below this every derived value defaults to "unknown" / 0


@dataclass
class TemporalIntelligenceContext:
    symbol: str
    timeframe: str
    window_size: int

    trend_evolution: str = "unknown"
    momentum_evolution: str = "unknown"
    volatility_evolution: str = "unknown"

    regime_stability_score: float = 0.0
    regime_flip_frequency: float = 0.0
    regime_duration_bars: int = 0

    trend_persistence: int = 0
    momentum_persistence: int = 0
    interaction_persistence: int = 0

    reversal_pressure: float = 0.0
    continuation_pressure: float = 0.0
    instability_pressure: float = 0.0

    detected_sequence: Optional[str] = None
    sequence_confidence: float = 0.0

    summary: str = "No temporal history available yet."
    drivers: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

    # Diagnostics (never part of the hashed vector of Step 8).
    min_history: int = MIN_HISTORY
    ready: bool = False

    def to_dict(self):
        return asdict(self)
