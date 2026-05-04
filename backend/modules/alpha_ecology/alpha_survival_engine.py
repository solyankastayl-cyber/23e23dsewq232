"""
PHASE 15.5 — Alpha Survival Engine
===================================
Analyzes signal survival across different market regimes.

Purpose:
    Most signals work only in specific market conditions.
    A trend signal works in trends, mean reversion in ranges.
    When the regime changes, fragile signals break.
    
    This engine tests signals across regimes to identify:
    - ROBUST: Works in most regimes
    - REGIME_DEPENDENT: Works in some regimes
    - FRAGILE: Works in only one regime

Market Regimes:
    - TREND_UP: Bullish trending market
    - TREND_DOWN: Bearish trending market
    - RANGE: Sideways/consolidation
    - HIGH_VOL: High volatility expansion
    - LOW_VOL: Low volatility compression

Formula:
    survival_score = positive_regimes / total_regimes
    regime_dependency = std(performance across regimes)

Survival States:
    - ROBUST: > 0.70 (works everywhere)
    - REGIME_DEPENDENT: 0.40-0.70 (works in some regimes)
    - FRAGILE: < 0.40 (works only in specific conditions)

Key Principle:
    Survival NEVER blocks a signal.
    It rewards robust signals and reduces exposure to fragile ones.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import math
import random

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_types import SurvivalState

# MongoDB
from pymongo import MongoClient, DESCENDING

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# MARKET REGIMES
# ══════════════════════════════════════════════════════════════

class MarketRegime(str, Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    HIGH_VOL = "HIGH_VOL"
    LOW_VOL = "LOW_VOL"


ALL_REGIMES = list(MarketRegime)


# ══════════════════════════════════════════════════════════════
# SURVIVAL THRESHOLDS
# ══════════════════════════════════════════════════════════════

SURVIVAL_THRESHOLDS = {
    # Score to state mapping
    "fragile_max": 0.40,
    "regime_dependent_max": 0.70,
    # Above regime_dependent_max = ROBUST
    
    # Minimum performance to count as positive
    "positive_threshold": 0.0,
}


SURVIVAL_MODIFIERS = {
    SurvivalState.ROBUST: {
        "confidence_modifier": 1.05,
        "size_modifier": 1.05,
    },
    SurvivalState.STABLE: {
        "confidence_modifier": 1.0,
        "size_modifier": 1.0,
    },
    SurvivalState.FRAGILE: {
        "confidence_modifier": 0.80,
        "size_modifier": 0.80,
    },
}


# ══════════════════════════════════════════════════════════════
# SIGNAL REGIME PROFILES (baseline characteristics)
# ══════════════════════════════════════════════════════════════

SIGNAL_REGIME_PROFILES = {
    # Trend-following signals excel in trends
    "trend_breakout": {
        MarketRegime.TREND_UP: 0.72,
        MarketRegime.TREND_DOWN: 0.65,
        MarketRegime.RANGE: -0.15,
        MarketRegime.HIGH_VOL: 0.45,
        MarketRegime.LOW_VOL: 0.20,
    },
    "trend_pullback": {
        MarketRegime.TREND_UP: 0.68,
        MarketRegime.TREND_DOWN: 0.62,
        MarketRegime.RANGE: 0.05,
        MarketRegime.HIGH_VOL: 0.35,
        MarketRegime.LOW_VOL: 0.25,
    },
    "momentum_continuation": {
        MarketRegime.TREND_UP: 0.65,
        MarketRegime.TREND_DOWN: 0.58,
        MarketRegime.RANGE: -0.10,
        MarketRegime.HIGH_VOL: 0.55,
        MarketRegime.LOW_VOL: 0.15,
    },
    "channel_breakout": {
        MarketRegime.TREND_UP: 0.55,
        MarketRegime.TREND_DOWN: 0.50,
        MarketRegime.RANGE: 0.30,
        MarketRegime.HIGH_VOL: 0.60,
        MarketRegime.LOW_VOL: -0.10,
    },
    
    # Mean reversion signals excel in ranges
    "mean_reversion": {
        MarketRegime.TREND_UP: -0.20,
        MarketRegime.TREND_DOWN: -0.25,
        MarketRegime.RANGE: 0.65,
        MarketRegime.HIGH_VOL: 0.15,
        MarketRegime.LOW_VOL: 0.55,
    },
    "support_bounce": {
        MarketRegime.TREND_UP: 0.40,
        MarketRegime.TREND_DOWN: -0.15,
        MarketRegime.RANGE: 0.55,
        MarketRegime.HIGH_VOL: 0.20,
        MarketRegime.LOW_VOL: 0.45,
    },
    "resistance_rejection": {
        MarketRegime.TREND_UP: -0.10,
        MarketRegime.TREND_DOWN: 0.45,
        MarketRegime.RANGE: 0.50,
        MarketRegime.HIGH_VOL: 0.15,
        MarketRegime.LOW_VOL: 0.40,
    },
    
    # Volatility signals
    "volatility_breakout": {
        MarketRegime.TREND_UP: 0.45,
        MarketRegime.TREND_DOWN: 0.40,
        MarketRegime.RANGE: 0.10,
        MarketRegime.HIGH_VOL: 0.70,
        MarketRegime.LOW_VOL: -0.25,
    },
    
    # Pattern signals
    "double_bottom": {
        MarketRegime.TREND_UP: 0.35,
        MarketRegime.TREND_DOWN: 0.55,
        MarketRegime.RANGE: 0.45,
        MarketRegime.HIGH_VOL: 0.30,
        MarketRegime.LOW_VOL: 0.40,
    },
    "double_top": {
        MarketRegime.TREND_UP: 0.50,
        MarketRegime.TREND_DOWN: 0.30,
        MarketRegime.RANGE: 0.45,
        MarketRegime.HIGH_VOL: 0.25,
        MarketRegime.LOW_VOL: 0.35,
    },
}


# ══════════════════════════════════════════════════════════════
# SURVIVAL RESULT CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class AlphaSurvivalResult:
    """
    Output from Alpha Survival Engine.
    
    Measures signal survival across market regimes.
    """
    signal_id: str
    signal_type: str
    timestamp: datetime
    
    # Regime performance
    regime_performance: Dict[str, float]
    
    # Aggregated metrics
    survival_score: float
    regime_dependency: float  # std of performance
    positive_regimes: int
    negative_regimes: int
    
    # Current regime context
    current_regime: MarketRegime
    current_regime_performance: float
    
    # State
    survival_state: SurvivalState
    
    # Modifiers
    confidence_modifier: float
    size_modifier: float
    
    # Explainability
    reason: str
    best_regime: str
    worst_regime: str
    
    def to_dict(self) -> Dict:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "timestamp": self.timestamp.isoformat(),
            "regime_performance": {
                k: round(v, 4) for k, v in self.regime_performance.items()
            },
            "survival_score": round(self.survival_score, 4),
            "regime_dependency": round(self.regime_dependency, 4),
            "positive_regimes": self.positive_regimes,
            "negative_regimes": self.negative_regimes,
            "current_regime": self.current_regime.value,
            "current_regime_performance": round(self.current_regime_performance, 4),
            "survival_state": self.survival_state.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "size_modifier": round(self.size_modifier, 4),
            "reason": self.reason,
            "best_regime": self.best_regime,
            "worst_regime": self.worst_regime,
        }


@dataclass
class SymbolSurvivalSnapshot:
    """Aggregated survival state for a symbol."""
    symbol: str
    timestamp: datetime
    current_regime: MarketRegime
    
    # Per-signal survival
    signal_survivals: List[AlphaSurvivalResult]
    
    # Aggregated
    avg_survival_score: float
    robust_signals_count: int
    regime_dependent_count: int
    fragile_signals_count: int
    
    # Overall
    overall_survival_state: SurvivalState
    overall_confidence_modifier: float
    overall_size_modifier: float
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "current_regime": self.current_regime.value,
            "signal_survivals": [s.to_dict() for s in self.signal_survivals],
            "avg_survival_score": round(self.avg_survival_score, 4),
            "robust_signals_count": self.robust_signals_count,
            "regime_dependent_count": self.regime_dependent_count,
            "fragile_signals_count": self.fragile_signals_count,
            "overall_survival_state": self.overall_survival_state.value,
            "overall_confidence_modifier": round(self.overall_confidence_modifier, 4),
            "overall_size_modifier": round(self.overall_size_modifier, 4),
        }


# ══════════════════════════════════════════════════════════════
# ALPHA SURVIVAL ENGINE
# ══════════════════════════════════════════════════════════════

class AlphaSurvivalEngine:
    """
    Alpha Survival Engine - PHASE 15.5
    
    Tests signal survival across different market regimes to identify
    robust vs fragile alphas.
    
    Key Insight:
        Most signals are regime-dependent.
        A robust signal works across multiple regimes.
        A fragile signal only works in specific conditions.
    
    Key Principle:
        Survival NEVER blocks a signal.
        It rewards robust signals and reduces exposure to fragile ones.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
    
    def analyze_signal(
        self,
        symbol: str,
        signal_type: str,
    ) -> AlphaSurvivalResult:
        """
        Analyze survival for a specific signal.
        
        Args:
            symbol: Trading pair
            signal_type: Signal to analyze
        
        Returns:
            AlphaSurvivalResult with survival state and modifiers
        """
        now = datetime.now(timezone.utc)
        
        # Get regime performance
        regime_perf = self._get_regime_performance(symbol, signal_type)
        
        # Count positive/negative regimes
        positive = sum(1 for p in regime_perf.values() if p > SURVIVAL_THRESHOLDS["positive_threshold"])
        negative = len(ALL_REGIMES) - positive
        
        # Compute survival score
        survival_score = positive / len(ALL_REGIMES)
        
        # Compute regime dependency (std)
        regime_dependency = self._compute_regime_dependency(regime_perf)
        
        # Get current regime
        current_regime = self._detect_current_regime(symbol)
        current_perf = regime_perf.get(current_regime.value, 0.0)
        
        # Determine state
        survival_state = self._determine_survival_state(survival_score)
        
        # Get modifiers
        modifiers = SURVIVAL_MODIFIERS[survival_state]
        conf_mod = modifiers["confidence_modifier"]
        size_mod = modifiers["size_modifier"]
        
        # Adjust for current regime performance
        if current_perf < 0:
            # Signal is weak in current regime
            conf_mod *= 0.9
            size_mod *= 0.9
        elif current_perf > 0.5:
            # Signal is strong in current regime
            conf_mod = min(1.1, conf_mod * 1.05)
            size_mod = min(1.1, size_mod * 1.02)
        
        # Find best/worst regimes
        best_regime = max(regime_perf, key=regime_perf.get)
        worst_regime = min(regime_perf, key=regime_perf.get)
        
        # Build reason
        reason = self._build_reason(survival_state, survival_score, current_regime, current_perf)
        
        return AlphaSurvivalResult(
            signal_id=f"{symbol}_{signal_type}",
            signal_type=signal_type,
            timestamp=now,
            regime_performance=regime_perf,
            survival_score=survival_score,
            regime_dependency=regime_dependency,
            positive_regimes=positive,
            negative_regimes=negative,
            current_regime=current_regime,
            current_regime_performance=current_perf,
            survival_state=survival_state,
            confidence_modifier=max(0.5, conf_mod),  # Never below 0.5
            size_modifier=max(0.5, size_mod),
            reason=reason,
            best_regime=best_regime,
            worst_regime=worst_regime,
        )
    
    def analyze_symbol(self, symbol: str) -> SymbolSurvivalSnapshot:
        """
        Analyze survival for all signals of a symbol.
        """
        now = datetime.now(timezone.utc)
        
        from modules.alpha_ecology.alpha_decay_engine import SIGNAL_TYPES
        
        # Detect current regime
        current_regime = self._detect_current_regime(symbol)
        
        # Analyze each signal
        signal_survivals = []
        for signal_type in SIGNAL_TYPES:
            result = self.analyze_signal(symbol, signal_type)
            signal_survivals.append(result)
        
        # Count states
        robust = sum(1 for s in signal_survivals if s.survival_state == SurvivalState.ROBUST)
        regime_dep = sum(1 for s in signal_survivals if s.survival_state == SurvivalState.STABLE)
        fragile = sum(1 for s in signal_survivals if s.survival_state == SurvivalState.FRAGILE)
        
        # Average survival
        avg_survival = sum(s.survival_score for s in signal_survivals) / len(signal_survivals)
        
        # Overall state
        overall_state = self._determine_overall_state(robust, regime_dep, fragile, avg_survival)
        
        # Aggregate modifiers
        overall_conf = sum(s.confidence_modifier for s in signal_survivals) / len(signal_survivals)
        overall_size = sum(s.size_modifier for s in signal_survivals) / len(signal_survivals)
        
        return SymbolSurvivalSnapshot(
            symbol=symbol,
            timestamp=now,
            current_regime=current_regime,
            signal_survivals=signal_survivals,
            avg_survival_score=avg_survival,
            robust_signals_count=robust,
            regime_dependent_count=regime_dep,
            fragile_signals_count=fragile,
            overall_survival_state=overall_state,
            overall_confidence_modifier=overall_conf,
            overall_size_modifier=overall_size,
        )
    
    def get_modifier_for_symbol(self, symbol: str) -> Dict[str, float]:
        """
        Get survival modifiers for Trading Product integration.
        """
        snapshot = self.analyze_symbol(symbol)
        
        return {
            "survival_confidence_modifier": snapshot.overall_confidence_modifier,
            "survival_size_modifier": snapshot.overall_size_modifier,
            "survival_state": snapshot.overall_survival_state.value,
            "avg_survival_score": snapshot.avg_survival_score,
            "current_regime": snapshot.current_regime.value,
            "robust_signals": snapshot.robust_signals_count,
            "fragile_signals": snapshot.fragile_signals_count,
        }
    
    # ═══════════════════════════════════════════════════════════════
    # REGIME PERFORMANCE
    # ═══════════════════════════════════════════════════════════════
    
    def _get_regime_performance(
        self,
        symbol: str,
        signal_type: str,
    ) -> Dict[str, float]:
        """
        Get signal performance across regimes.
        
        Uses stored data or baseline profiles with variance.
        """
        # Try to get from database
        perf_data = self.db.signal_regime_performance.find_one({
            "symbol": symbol,
            "signal_type": signal_type,
        })
        
        if perf_data and "regime_performance" in perf_data:
            return perf_data["regime_performance"]
        
        # Use baseline profiles with symbol-specific variance
        baseline = SIGNAL_REGIME_PROFILES.get(signal_type, {})
        
        if not baseline:
            # Generate default profile
            baseline = {
                regime: random.uniform(-0.1, 0.5)
                for regime in ALL_REGIMES
            }
        
        # Add variance based on symbol
        result = {}
        for regime in ALL_REGIMES:
            base_val = baseline.get(regime, 0.2)
            variance = random.uniform(-0.1, 0.1)
            result[regime.value] = base_val + variance
        
        return result
    
    def _compute_regime_dependency(self, regime_perf: Dict[str, float]) -> float:
        """
        Compute regime dependency as standard deviation of performance.
        
        High std = signal is regime-dependent.
        Low std = signal is consistent across regimes.
        """
        if not regime_perf:
            return 0.0
        
        values = list(regime_perf.values())
        n = len(values)
        
        if n < 2:
            return 0.0
        
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(variance)
        
        return std
    
    def _detect_current_regime(self, symbol: str) -> MarketRegime:
        """
        Detect current market regime for a symbol.
        """
        # Get recent candles
        candles = list(self.db.candles.find({
            "symbol": symbol,
            "timeframe": "1d"
        }).sort("timestamp", DESCENDING).limit(20))
        
        if len(candles) < 10:
            return MarketRegime.RANGE
        
        # Compute metrics
        closes = [c.get("close", 0) for c in candles]
        
        # Trend detection
        recent_close = closes[0]
        old_close = closes[-1]
        price_change = (recent_close - old_close) / old_close if old_close > 0 else 0
        
        # Volatility detection
        returns = []
        for i in range(len(closes) - 1):
            if closes[i + 1] > 0:
                ret = (closes[i] - closes[i + 1]) / closes[i + 1]
                returns.append(ret)
        
        if returns:
            avg_ret = sum(abs(r) for r in returns) / len(returns)
        else:
            avg_ret = 0.02
        
        # Determine regime
        if price_change > 0.10:
            return MarketRegime.TREND_UP
        elif price_change < -0.10:
            return MarketRegime.TREND_DOWN
        elif avg_ret > 0.04:
            return MarketRegime.HIGH_VOL
        elif avg_ret < 0.015:
            return MarketRegime.LOW_VOL
        else:
            return MarketRegime.RANGE
    
    # ═══════════════════════════════════════════════════════════════
    # STATE DETERMINATION
    # ═══════════════════════════════════════════════════════════════
    
    def _determine_survival_state(self, score: float) -> SurvivalState:
        """Determine survival state from score."""
        if score < SURVIVAL_THRESHOLDS["fragile_max"]:
            return SurvivalState.FRAGILE
        elif score < SURVIVAL_THRESHOLDS["regime_dependent_max"]:
            return SurvivalState.STABLE  # REGIME_DEPENDENT maps to STABLE
        else:
            return SurvivalState.ROBUST
    
    def _determine_overall_state(
        self,
        robust: int,
        regime_dep: int,
        fragile: int,
        avg_survival: float,
    ) -> SurvivalState:
        """Determine overall survival state for symbol."""
        total = robust + regime_dep + fragile
        
        if total == 0:
            return SurvivalState.STABLE
        
        robust_pct = robust / total
        fragile_pct = fragile / total
        
        if robust_pct >= 0.5:
            return SurvivalState.ROBUST
        elif fragile_pct >= 0.4:
            return SurvivalState.FRAGILE
        else:
            return SurvivalState.STABLE
    
    def _build_reason(
        self,
        state: SurvivalState,
        score: float,
        current_regime: MarketRegime,
        current_perf: float,
    ) -> str:
        """Build human-readable reason."""
        regime_note = f"current_{current_regime.value}"
        
        if state == SurvivalState.ROBUST:
            return f"robust_survival_{score:.0%}_{regime_note}"
        elif state == SurvivalState.STABLE:
            return f"regime_dependent_{score:.0%}_{regime_note}"
        else:
            return f"fragile_survival_{score:.0%}_{regime_note}"


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[AlphaSurvivalEngine] = None


def get_alpha_survival_engine() -> AlphaSurvivalEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = AlphaSurvivalEngine()
    return _engine
