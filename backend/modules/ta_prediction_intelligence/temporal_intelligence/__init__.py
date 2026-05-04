"""
Temporal Intelligence (Layer above features + buffer).

   snapshot intelligence  →  temporal intelligence

Reads the HybridTemporalBuffer history for (symbol, tf) and produces a
context that EXPLAINS how the market state EVOLVED, not just what it is now:

  * trend_evolution      : strengthening / weakening / reversing / flat / stable
  * momentum_evolution   : accelerating / decelerating / stable
  * volatility_evolution : expanding / compressing / stable
  * regime_memory        : stability, flip_frequency, current_duration
  * persistence          : bars since trend_phase / momentum_state / interaction_type changed
  * transition_pressure  : reversal / continuation / instability (each 0..1)
  * sequence_patterns    : detected multi-bar sequence (or None)

Architectural rules (locked):
  • READ-ONLY over feature snapshots; never mutates buffer or source records.
  • Does NOT touch bias / confidence / conflict / interaction / scenarios /
    calibration / dataset — those remain bit-identical.
  • No ML, no random, no I/O.
  • history < MIN_HISTORY  →  all fields default to unknown / 0.0 + summary=
    "insufficient_history". NO fake data.
"""
from .types import TemporalIntelligenceContext, MIN_HISTORY
from .state_evolution import (
    trend_evolution, momentum_evolution, volatility_evolution,
)
from .regime_memory import regime_stats
from .persistence import count_persistence
from .transition_pressure import compute_transition_pressure
from .sequence_patterns import detect_sequence
from .temporal_context_builder import build_temporal_context

__all__ = [
    "TemporalIntelligenceContext",
    "MIN_HISTORY",
    "trend_evolution",
    "momentum_evolution",
    "volatility_evolution",
    "regime_stats",
    "count_persistence",
    "compute_transition_pressure",
    "detect_sequence",
    "build_temporal_context",
]
