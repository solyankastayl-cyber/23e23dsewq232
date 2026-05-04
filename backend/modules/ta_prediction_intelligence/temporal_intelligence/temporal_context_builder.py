"""
Temporal Context Builder — main orchestrator.

Reads an in-memory slice of snapshots (as stored by HybridTemporalBuffer),
runs evolution classifiers + regime memory + persistence + pressure +
sequence detection, and produces a canonical TemporalIntelligenceContext.

Pure + deterministic. Missing / too-short history → the default unknown
object with ready=False and summary="insufficient_history".
"""
from __future__ import annotations

from typing import Any, Dict, List

from .persistence import count_persistence
from .regime_memory import regime_stats
from .sequence_patterns import detect_sequence
from .state_evolution import (
    momentum_evolution,
    trend_evolution,
    volatility_evolution,
)
from .transition_pressure import compute_transition_pressure
from .types import MIN_HISTORY, TemporalIntelligenceContext


def _summary(
    trend: str,
    momentum: str,
    volatility: str,
    pressure: Dict[str, Any],
    sequence: str,
    ready: bool,
) -> str:
    if not ready:
        return "insufficient_history"
    if sequence:
        return f"Detected temporal sequence: {sequence}."
    if pressure["reversal_pressure"] > 0.6:
        return "Reversal pressure is building."
    if pressure["continuation_pressure"] > 0.6:
        return "Continuation pressure is dominant."
    if pressure["instability_pressure"] > 0.6:
        return "Market state is unstable."
    return f"Trend is {trend}, momentum is {momentum}, volatility is {volatility}."


def build_temporal_context(
    symbol: str,
    tf: str,
    history: List[Any],
) -> TemporalIntelligenceContext:
    ready = bool(history) and len(history) >= MIN_HISTORY
    regime = regime_stats(history)
    pressure = compute_transition_pressure(history)
    seq_name, seq_conf = detect_sequence(history) if ready else (None, 0.0)
    trend = trend_evolution(history) if ready else "unknown"
    momentum = momentum_evolution(history) if ready else "unknown"
    vol = volatility_evolution(history) if ready else "unknown"
    summary = _summary(trend, momentum, vol, pressure, seq_name, ready)

    ctx = TemporalIntelligenceContext(
        symbol=(symbol or "").upper(),
        timeframe=(tf or "").upper(),
        window_size=len(history or []),
        trend_evolution=trend,
        momentum_evolution=momentum,
        volatility_evolution=vol,
        regime_stability_score=regime["regime_stability_score"],
        regime_flip_frequency=regime["regime_flip_frequency"],
        regime_duration_bars=regime["regime_duration_bars"],
        trend_persistence=count_persistence(history, "trend_phase"),
        momentum_persistence=count_persistence(history, "momentum_state"),
        interaction_persistence=count_persistence(history, "interaction_type"),
        reversal_pressure=pressure["reversal_pressure"],
        continuation_pressure=pressure["continuation_pressure"],
        instability_pressure=pressure["instability_pressure"],
        detected_sequence=seq_name,
        sequence_confidence=seq_conf,
        summary=summary,
        drivers=pressure["drivers"],
        risks=pressure["risks"],
        min_history=MIN_HISTORY,
        ready=ready,
    )
    return ctx
