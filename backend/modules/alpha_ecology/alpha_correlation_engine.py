"""
PHASE 15.3 — Alpha Correlation Engine
======================================
Detects when multiple signals are essentially the same signal.

Purpose:
    Multiple signals may appear independent but actually represent
    the same alpha source. This causes overconfidence in the system.
    
    Example: trend_signal, momentum_signal, breakout_signal might
    all be triggered by the same underlying market move.

Method:
    1. Build feature vectors for each signal
    2. Compute correlation between signal outputs
    3. Identify highly correlated signal pairs
    4. Reduce confidence for correlated signals

Correlation States:
    - LOW: < 0.30 (signals are independent)
    - MEDIUM: 0.30-0.60 (some overlap)
    - HIGH: > 0.60 (signals are essentially the same)

Key Principle:
    Correlation NEVER blocks a signal.
    It only reduces confidence to prevent overweighting.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import math
import random

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_types import CorrelationState

# MongoDB
from pymongo import MongoClient, DESCENDING

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# CORRELATION THRESHOLDS
# ══════════════════════════════════════════════════════════════

CORRELATION_THRESHOLDS = {
    # Correlation state boundaries
    "low_max": 0.30,
    "medium_max": 0.60,
    # Above medium_max = HIGH
    
    # Minimum samples for correlation
    "min_samples": 20,
    
    # Lookback for signal history
    "lookback_days": 30,
}


CORRELATION_MODIFIERS = {
    CorrelationState.UNIQUE: {
        "confidence_modifier": 1.0,
        "size_modifier": 1.0,
    },
    CorrelationState.PARTIAL: {
        "confidence_modifier": 0.90,
        "size_modifier": 0.90,
    },
    CorrelationState.HIGHLY_CORRELATED: {
        "confidence_modifier": 0.75,
        "size_modifier": 0.75,
    },
}


# ══════════════════════════════════════════════════════════════
# SIGNAL GROUPS (known correlations)
# ══════════════════════════════════════════════════════════════

SIGNAL_GROUPS = {
    # Trend-based signals (tend to correlate)
    "trend_group": [
        "trend_breakout",
        "trend_pullback",
        "channel_breakout",
    ],
    # Momentum-based signals
    "momentum_group": [
        "momentum_continuation",
        "volatility_breakout",
    ],
    # Reversal-based signals
    "reversal_group": [
        "mean_reversion",
        "support_bounce",
        "resistance_rejection",
        "double_bottom",
        "double_top",
    ],
}


# ══════════════════════════════════════════════════════════════
# CORRELATION RESULT CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class AlphaCorrelationResult:
    """
    Output from Alpha Correlation Engine.
    
    Measures signal uniqueness relative to other signals.
    """
    signal_id: str
    signal_type: str
    timestamp: datetime
    
    # Correlations with other signals
    correlation_with_signals: Dict[str, float]
    
    # Aggregated metrics
    max_correlation: float
    max_correlated_signal: str
    avg_correlation: float
    
    # Uniqueness
    uniqueness_score: float  # 1 - max_correlation
    correlation_state: CorrelationState
    
    # Modifiers
    confidence_modifier: float
    size_modifier: float
    
    # Explainability
    reason: str
    signal_group: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "timestamp": self.timestamp.isoformat(),
            "correlation_with_signals": {
                k: round(v, 4) for k, v in self.correlation_with_signals.items()
            },
            "max_correlation": round(self.max_correlation, 4),
            "max_correlated_signal": self.max_correlated_signal,
            "avg_correlation": round(self.avg_correlation, 4),
            "uniqueness_score": round(self.uniqueness_score, 4),
            "correlation_state": self.correlation_state.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "size_modifier": round(self.size_modifier, 4),
            "reason": self.reason,
            "signal_group": self.signal_group,
        }


@dataclass
class SymbolCorrelationSnapshot:
    """Aggregated correlation state for a symbol across all signals."""
    symbol: str
    timestamp: datetime
    
    # Per-signal correlations
    signal_correlations: List[AlphaCorrelationResult]
    
    # Aggregated
    avg_uniqueness: float
    highly_correlated_count: int
    partial_count: int
    unique_count: int
    
    # Overall
    overall_correlation_state: CorrelationState
    overall_confidence_modifier: float
    overall_size_modifier: float
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "signal_correlations": [s.to_dict() for s in self.signal_correlations],
            "avg_uniqueness": round(self.avg_uniqueness, 4),
            "highly_correlated_count": self.highly_correlated_count,
            "partial_count": self.partial_count,
            "unique_count": self.unique_count,
            "overall_correlation_state": self.overall_correlation_state.value,
            "overall_confidence_modifier": round(self.overall_confidence_modifier, 4),
            "overall_size_modifier": round(self.overall_size_modifier, 4),
        }


# ══════════════════════════════════════════════════════════════
# ALPHA CORRELATION ENGINE
# ══════════════════════════════════════════════════════════════

class AlphaCorrelationEngine:
    """
    Alpha Correlation Engine - PHASE 15.3
    
    Detects when multiple signals are essentially the same,
    preventing overconfidence from correlated alphas.
    
    Key Principle:
        Correlation NEVER blocks a signal.
        It only reduces confidence to prevent overweighting.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Cache for signal vectors
        self._signal_vectors: Dict[str, Dict[str, List[float]]] = {}
    
    def analyze_signal(
        self,
        symbol: str,
        signal_type: str,
    ) -> AlphaCorrelationResult:
        """
        Analyze correlation for a specific signal.
        
        Args:
            symbol: Trading pair
            signal_type: Signal to analyze
        
        Returns:
            AlphaCorrelationResult with correlation state and modifiers
        """
        now = datetime.now(timezone.utc)
        
        # Get all signal types except current
        from modules.alpha_ecology.alpha_decay_engine import SIGNAL_TYPES
        other_signals = [s for s in SIGNAL_TYPES if s != signal_type]
        
        # Compute correlations
        correlations = {}
        for other_signal in other_signals:
            corr = self._compute_correlation(symbol, signal_type, other_signal)
            correlations[other_signal] = corr
        
        # Find max correlation
        if correlations:
            max_corr_signal = max(correlations, key=correlations.get)
            max_corr = correlations[max_corr_signal]
            avg_corr = sum(correlations.values()) / len(correlations)
        else:
            max_corr_signal = "none"
            max_corr = 0.0
            avg_corr = 0.0
        
        # Compute uniqueness
        uniqueness = 1.0 - max_corr
        
        # Determine state
        correlation_state = self._determine_correlation_state(max_corr)
        
        # Get modifiers
        modifiers = CORRELATION_MODIFIERS[correlation_state]
        conf_mod = modifiers["confidence_modifier"]
        size_mod = modifiers["size_modifier"]
        
        # Fine-tune based on severity
        if correlation_state == CorrelationState.HIGHLY_CORRELATED:
            # More correlated = lower modifiers
            severity = (max_corr - 0.60) / 0.40  # 0-1 within HIGH range
            conf_mod *= (1.0 - 0.15 * severity)  # Down to 0.64
            size_mod *= (1.0 - 0.15 * severity)
        
        # Find signal group
        signal_group = self._find_signal_group(signal_type)
        
        # Build reason
        reason = self._build_reason(correlation_state, max_corr, max_corr_signal)
        
        return AlphaCorrelationResult(
            signal_id=f"{symbol}_{signal_type}",
            signal_type=signal_type,
            timestamp=now,
            correlation_with_signals=correlations,
            max_correlation=max_corr,
            max_correlated_signal=max_corr_signal,
            avg_correlation=avg_corr,
            uniqueness_score=uniqueness,
            correlation_state=correlation_state,
            confidence_modifier=max(0.5, conf_mod),  # Never below 0.5
            size_modifier=max(0.5, size_mod),
            reason=reason,
            signal_group=signal_group,
        )
    
    def analyze_symbol(self, symbol: str) -> SymbolCorrelationSnapshot:
        """
        Analyze correlations for all signals of a symbol.
        
        Args:
            symbol: Trading pair
        
        Returns:
            SymbolCorrelationSnapshot with aggregated correlation state
        """
        now = datetime.now(timezone.utc)
        
        from modules.alpha_ecology.alpha_decay_engine import SIGNAL_TYPES
        
        # Analyze each signal
        signal_correlations = []
        for signal_type in SIGNAL_TYPES:
            result = self.analyze_signal(symbol, signal_type)
            signal_correlations.append(result)
        
        # Count states
        highly_corr = sum(1 for s in signal_correlations 
                         if s.correlation_state == CorrelationState.HIGHLY_CORRELATED)
        partial = sum(1 for s in signal_correlations 
                      if s.correlation_state == CorrelationState.PARTIAL)
        unique = sum(1 for s in signal_correlations 
                     if s.correlation_state == CorrelationState.UNIQUE)
        
        # Average uniqueness
        avg_uniqueness = sum(s.uniqueness_score for s in signal_correlations) / len(signal_correlations)
        
        # Overall state
        overall_state = self._determine_overall_state(highly_corr, partial, unique, avg_uniqueness)
        
        # Aggregate modifiers
        overall_conf_mod = sum(s.confidence_modifier for s in signal_correlations) / len(signal_correlations)
        overall_size_mod = sum(s.size_modifier for s in signal_correlations) / len(signal_correlations)
        
        return SymbolCorrelationSnapshot(
            symbol=symbol,
            timestamp=now,
            signal_correlations=signal_correlations,
            avg_uniqueness=avg_uniqueness,
            highly_correlated_count=highly_corr,
            partial_count=partial,
            unique_count=unique,
            overall_correlation_state=overall_state,
            overall_confidence_modifier=overall_conf_mod,
            overall_size_modifier=overall_size_mod,
        )
    
    def get_modifier_for_symbol(self, symbol: str) -> Dict[str, float]:
        """
        Get correlation modifiers for Trading Product integration.
        """
        snapshot = self.analyze_symbol(symbol)
        
        return {
            "correlation_confidence_modifier": snapshot.overall_confidence_modifier,
            "correlation_size_modifier": snapshot.overall_size_modifier,
            "correlation_state": snapshot.overall_correlation_state.value,
            "avg_uniqueness": snapshot.avg_uniqueness,
            "highly_correlated_count": snapshot.highly_correlated_count,
        }
    
    # ═══════════════════════════════════════════════════════════════
    # CORRELATION COMPUTATION
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_correlation(
        self,
        symbol: str,
        signal_a: str,
        signal_b: str,
    ) -> float:
        """
        Compute correlation between two signals.
        
        Uses signal output history or known group correlations.
        """
        # Check if signals are in same group (known correlation)
        group_corr = self._get_group_correlation(signal_a, signal_b)
        if group_corr is not None:
            return group_corr
        
        # Get signal vectors
        vector_a = self._get_signal_vector(symbol, signal_a)
        vector_b = self._get_signal_vector(symbol, signal_b)
        
        if len(vector_a) < CORRELATION_THRESHOLDS["min_samples"] or \
           len(vector_b) < CORRELATION_THRESHOLDS["min_samples"]:
            # Not enough data, use heuristic
            return self._estimate_correlation(signal_a, signal_b)
        
        # Align vectors to same length
        min_len = min(len(vector_a), len(vector_b))
        vector_a = vector_a[:min_len]
        vector_b = vector_b[:min_len]
        
        # Compute Pearson correlation
        return self._pearson_correlation(vector_a, vector_b)
    
    def _get_signal_vector(self, symbol: str, signal_type: str) -> List[float]:
        """
        Get signal output vector for correlation analysis.
        
        Uses stored signal history or generates synthetic data.
        """
        cache_key = f"{symbol}_{signal_type}"
        if cache_key in self._signal_vectors:
            return self._signal_vectors[cache_key]
        
        now = datetime.now(timezone.utc)
        lookback = now - timedelta(days=CORRELATION_THRESHOLDS["lookback_days"])
        
        # Get from signal performance collection
        records = list(self.db.signal_performance.find({
            "symbol": symbol,
            "signal_type": signal_type,
            "timestamp": {"$gte": lookback}
        }).sort("timestamp", 1).limit(100))
        
        if len(records) >= CORRELATION_THRESHOLDS["min_samples"]:
            # Use actual outcomes
            vector = [r.get("outcome", 0) * r.get("return_pct", 0.01) for r in records]
        else:
            # Generate synthetic based on signal characteristics
            vector = self._generate_synthetic_vector(signal_type)
        
        self._signal_vectors[cache_key] = vector
        return vector
    
    def _generate_synthetic_vector(self, signal_type: str) -> List[float]:
        """
        Generate synthetic signal vector based on signal characteristics.
        
        Different signals have different baseline characteristics.
        """
        # Signal base characteristics
        characteristics = {
            "trend_breakout": {"mean": 0.02, "std": 0.03, "trend_bias": 0.6},
            "trend_pullback": {"mean": 0.018, "std": 0.025, "trend_bias": 0.55},
            "momentum_continuation": {"mean": 0.022, "std": 0.035, "trend_bias": 0.5},
            "mean_reversion": {"mean": 0.015, "std": 0.02, "trend_bias": -0.3},
            "volatility_breakout": {"mean": 0.025, "std": 0.04, "trend_bias": 0.3},
            "support_bounce": {"mean": 0.012, "std": 0.018, "trend_bias": -0.2},
            "resistance_rejection": {"mean": 0.012, "std": 0.018, "trend_bias": -0.2},
            "channel_breakout": {"mean": 0.02, "std": 0.03, "trend_bias": 0.5},
            "double_bottom": {"mean": 0.018, "std": 0.025, "trend_bias": -0.4},
            "double_top": {"mean": 0.018, "std": 0.025, "trend_bias": -0.4},
        }
        
        char = characteristics.get(signal_type, {"mean": 0.015, "std": 0.02, "trend_bias": 0})
        
        # Generate vector with characteristics
        n_samples = 50
        vector = []
        
        # Add trend component
        trend = [char["trend_bias"] * i / n_samples for i in range(n_samples)]
        
        # Add noise
        for i in range(n_samples):
            noise = random.gauss(char["mean"], char["std"])
            vector.append(trend[i] + noise)
        
        return vector
    
    def _get_group_correlation(self, signal_a: str, signal_b: str) -> Optional[float]:
        """
        Get known correlation for signals in the same group.
        """
        for group_name, signals in SIGNAL_GROUPS.items():
            if signal_a in signals and signal_b in signals:
                # Same group = high correlation
                if group_name == "trend_group":
                    return 0.65 + random.uniform(-0.05, 0.05)
                elif group_name == "momentum_group":
                    return 0.55 + random.uniform(-0.05, 0.05)
                elif group_name == "reversal_group":
                    return 0.50 + random.uniform(-0.05, 0.05)
        
        return None
    
    def _estimate_correlation(self, signal_a: str, signal_b: str) -> float:
        """
        Estimate correlation when insufficient data.
        
        Uses signal type heuristics.
        """
        # Find groups for each signal
        group_a = self._find_signal_group(signal_a)
        group_b = self._find_signal_group(signal_b)
        
        if group_a and group_b:
            if group_a == group_b:
                # Same group
                return 0.55 + random.uniform(-0.1, 0.1)
            else:
                # Different groups
                # Trend vs reversal = low correlation
                if ("trend" in group_a and "reversal" in group_b) or \
                   ("reversal" in group_a and "trend" in group_b):
                    return 0.15 + random.uniform(-0.05, 0.1)
                # Default different group
                return 0.25 + random.uniform(-0.05, 0.1)
        
        # Unknown = assume low correlation
        return 0.20 + random.uniform(-0.05, 0.15)
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """
        Compute Pearson correlation coefficient.
        """
        n = len(x)
        if n < 2:
            return 0.0
        
        # Means
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        # Covariance and standard deviations
        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)
        
        if std_x == 0 or std_y == 0:
            return 0.0
        
        corr = cov / (std_x * std_y)
        
        # Clamp to valid range
        return max(-1.0, min(1.0, abs(corr)))
    
    # ═══════════════════════════════════════════════════════════════
    # STATE DETERMINATION
    # ═══════════════════════════════════════════════════════════════
    
    def _determine_correlation_state(self, max_corr: float) -> CorrelationState:
        """Determine correlation state from max correlation."""
        if max_corr < CORRELATION_THRESHOLDS["low_max"]:
            return CorrelationState.UNIQUE
        elif max_corr < CORRELATION_THRESHOLDS["medium_max"]:
            return CorrelationState.PARTIAL
        else:
            return CorrelationState.HIGHLY_CORRELATED
    
    def _determine_overall_state(
        self,
        highly_corr: int,
        partial: int,
        unique: int,
        avg_uniqueness: float,
    ) -> CorrelationState:
        """Determine overall correlation state for symbol."""
        total = highly_corr + partial + unique
        
        if total == 0:
            return CorrelationState.UNIQUE
        
        # Majority rule
        high_pct = highly_corr / total
        partial_pct = partial / total
        
        if high_pct >= 0.4:
            return CorrelationState.HIGHLY_CORRELATED
        elif partial_pct >= 0.5 or (partial_pct + high_pct) >= 0.6:
            return CorrelationState.PARTIAL
        else:
            return CorrelationState.UNIQUE
    
    def _find_signal_group(self, signal_type: str) -> Optional[str]:
        """Find which group a signal belongs to."""
        for group_name, signals in SIGNAL_GROUPS.items():
            if signal_type in signals:
                return group_name
        return None
    
    def _build_reason(
        self,
        state: CorrelationState,
        max_corr: float,
        max_signal: str,
    ) -> str:
        """Build human-readable reason."""
        if state == CorrelationState.UNIQUE:
            return "signal_unique_low_correlation"
        elif state == CorrelationState.PARTIAL:
            return f"partial_correlation_{max_corr:.0%}_with_{max_signal}"
        else:
            return f"high_correlation_{max_corr:.0%}_with_{max_signal}"


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[AlphaCorrelationEngine] = None


def get_alpha_correlation_engine() -> AlphaCorrelationEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = AlphaCorrelationEngine()
    return _engine
