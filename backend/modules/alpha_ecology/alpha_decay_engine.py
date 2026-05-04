"""
PHASE 15.1 — Alpha Decay Engine
================================
Tracks signal performance degradation over time.

Purpose:
    Detect when a signal is "decaying" - working worse than historically.
    This is critical because signals that worked before can stop working
    due to market structure changes, increased competition, or regime shifts.

Architecture:
    SignalHistory → Performance Windows → Decay Analysis → Modifiers

Key Metrics:
    - decay_ratio: recent_win_rate / historical_win_rate
    - performance_delta: recent_profit_factor - historical_profit_factor
    - consistency_score: stability of performance over time

Output States:
    - DECAYING: Signal degrading (confidence/size down)
    - STABLE: Signal consistent (no change)
    - IMPROVING: Signal getting better (confidence/size up)

Integration:
    Feeds into Decision Layer and Position Sizing as risk modifiers.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import random

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_types import (
    DecayState,
    SignalPerformanceWindow,
    SignalDecayResult,
    SymbolDecaySnapshot,
)

# MongoDB
from pymongo import MongoClient, DESCENDING

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# DECAY THRESHOLDS
# ══════════════════════════════════════════════════════════════

DECAY_THRESHOLDS = {
    # Decay ratio thresholds (recent_wr / historical_wr)
    "decaying_max": 0.85,      # Below this = DECAYING
    "stable_min": 0.85,        # Between stable_min and improving_min = STABLE
    "improving_min": 1.10,     # Above this = IMPROVING
    
    # Performance delta thresholds (recent_pf - historical_pf)
    "pf_decaying_max": -0.3,   # PF dropped by 0.3+
    "pf_improving_min": 0.2,   # PF improved by 0.2+
    
    # Minimum signals for analysis
    "min_recent_signals": 10,
    "min_historical_signals": 30,
    
    # Window sizes (days)
    "recent_window_days": 30,
    "historical_window_days": 180,
}


DECAY_MODIFIERS = {
    DecayState.DECAYING: {
        "confidence_modifier": 0.80,
        "size_modifier": 0.70,
    },
    DecayState.STABLE: {
        "confidence_modifier": 1.0,
        "size_modifier": 1.0,
    },
    DecayState.IMPROVING: {
        "confidence_modifier": 1.10,
        "size_modifier": 1.05,
    },
}


# ══════════════════════════════════════════════════════════════
# SIGNAL TYPES REGISTRY
# ══════════════════════════════════════════════════════════════

SIGNAL_TYPES = [
    "trend_breakout",
    "momentum_continuation",
    "mean_reversion",
    "volatility_breakout",
    "support_bounce",
    "resistance_rejection",
    "trend_pullback",
    "channel_breakout",
    "double_bottom",
    "double_top",
]


# ══════════════════════════════════════════════════════════════
# ALPHA DECAY ENGINE
# ══════════════════════════════════════════════════════════════

class AlphaDecayEngine:
    """
    Alpha Decay Engine - PHASE 15.1
    
    Tracks signal performance degradation to identify signals that
    are losing their edge over time.
    
    Key Principle:
        Signals decay. What worked before may not work now.
        We detect this early and reduce exposure.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Ensure collection exists
        if "signal_performance" not in self.db.list_collection_names():
            self.db.create_collection("signal_performance")
            self.db.signal_performance.create_index([
                ("symbol", 1), ("signal_type", 1), ("timestamp", DESCENDING)
            ])
    
    def analyze_signal(
        self, 
        symbol: str, 
        signal_type: str,
    ) -> SignalDecayResult:
        """
        Analyze decay for a specific signal type.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
            signal_type: Type of signal (trend_breakout, momentum, etc.)
        
        Returns:
            SignalDecayResult with decay state and modifiers
        """
        now = datetime.now(timezone.utc)
        
        # Get performance windows
        recent = self._get_performance_window(
            symbol, signal_type, 
            DECAY_THRESHOLDS["recent_window_days"],
            "recent"
        )
        historical = self._get_performance_window(
            symbol, signal_type,
            DECAY_THRESHOLDS["historical_window_days"],
            "historical"
        )
        
        # Compute decay metrics
        decay_ratio = self._compute_decay_ratio(recent, historical)
        performance_delta = self._compute_performance_delta(recent, historical)
        consistency = self._compute_consistency(symbol, signal_type)
        
        # Determine decay state
        decay_state = self._determine_decay_state(
            decay_ratio, performance_delta, recent, historical
        )
        
        # Compute modifiers
        conf_mod, size_mod = self._compute_modifiers(
            decay_state, decay_ratio, performance_delta
        )
        
        # Build reason
        reason = self._build_reason(
            decay_state, decay_ratio, performance_delta, recent, historical
        )
        
        # Compute confidence in decay assessment
        confidence = self._compute_confidence(recent, historical, consistency)
        
        return SignalDecayResult(
            signal_id=f"{symbol}_{signal_type}",
            signal_type=signal_type,
            timestamp=now,
            recent_performance=recent,
            historical_performance=historical,
            decay_ratio=decay_ratio,
            performance_delta=performance_delta,
            consistency_score=consistency,
            decay_state=decay_state,
            confidence=confidence,
            confidence_modifier=conf_mod,
            size_modifier=size_mod,
            reason=reason,
            drivers={
                "recent_win_rate": recent.win_rate,
                "historical_win_rate": historical.win_rate,
                "recent_pf": recent.profit_factor,
                "historical_pf": historical.profit_factor,
                "decay_ratio": decay_ratio,
                "performance_delta": performance_delta,
            },
        )
    
    def analyze_symbol(self, symbol: str) -> SymbolDecaySnapshot:
        """
        Analyze decay across all signal types for a symbol.
        
        Args:
            symbol: Trading pair
        
        Returns:
            SymbolDecaySnapshot with aggregated decay state
        """
        now = datetime.now(timezone.utc)
        
        # Analyze each signal type
        signal_decays = []
        for signal_type in SIGNAL_TYPES:
            decay_result = self.analyze_signal(symbol, signal_type)
            signal_decays.append(decay_result)
        
        # Count states
        decaying = sum(1 for s in signal_decays if s.decay_state == DecayState.DECAYING)
        stable = sum(1 for s in signal_decays if s.decay_state == DecayState.STABLE)
        improving = sum(1 for s in signal_decays if s.decay_state == DecayState.IMPROVING)
        
        # Compute average decay ratio
        avg_decay = sum(s.decay_ratio for s in signal_decays) / len(signal_decays)
        
        # Determine overall state
        overall_state = self._determine_overall_state(
            decaying, stable, improving, avg_decay
        )
        
        # Compute overall modifiers (weighted by confidence)
        overall_conf_mod = self._aggregate_modifier(
            signal_decays, "confidence_modifier"
        )
        overall_size_mod = self._aggregate_modifier(
            signal_decays, "size_modifier"
        )
        
        return SymbolDecaySnapshot(
            symbol=symbol,
            timestamp=now,
            signal_decays=signal_decays,
            avg_decay_ratio=avg_decay,
            decaying_signals_count=decaying,
            stable_signals_count=stable,
            improving_signals_count=improving,
            overall_decay_state=overall_state,
            overall_confidence_modifier=overall_conf_mod,
            overall_size_modifier=overall_size_mod,
        )
    
    def get_modifier_for_symbol(self, symbol: str) -> Dict[str, float]:
        """
        Get decay modifiers for integration with Trading Decision.
        
        Returns dict with confidence and size modifiers.
        """
        snapshot = self.analyze_symbol(symbol)
        
        return {
            "decay_confidence_modifier": snapshot.overall_confidence_modifier,
            "decay_size_modifier": snapshot.overall_size_modifier,
            "decay_state": snapshot.overall_decay_state.value,
            "decaying_signals": snapshot.decaying_signals_count,
            "total_signals": len(snapshot.signal_decays),
        }
    
    # ═══════════════════════════════════════════════════════════════
    # PERFORMANCE WINDOW COMPUTATION
    # ═══════════════════════════════════════════════════════════════
    
    def _get_performance_window(
        self,
        symbol: str,
        signal_type: str,
        window_days: int,
        window_name: str,
    ) -> SignalPerformanceWindow:
        """
        Get or compute performance window for a signal.
        
        Uses stored signal history or generates synthetic data
        for bootstrap purposes.
        """
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=window_days)
        
        # Try to get from database
        records = list(self.db.signal_performance.find({
            "symbol": symbol,
            "signal_type": signal_type,
            "timestamp": {"$gte": start_date, "$lte": now}
        }))
        
        # If no records, generate synthetic based on strategy baseline
        if len(records) < DECAY_THRESHOLDS["min_recent_signals"]:
            return self._generate_synthetic_window(
                symbol, signal_type, start_date, now, window_name
            )
        
        # Compute metrics from records
        total = len(records)
        winning = sum(1 for r in records if r.get("outcome", 0) > 0)
        losing = total - winning
        win_rate = winning / total if total > 0 else 0.5
        
        returns = [r.get("return_pct", 0) for r in records]
        avg_return = sum(returns) / len(returns) if returns else 0
        
        # Profit factor
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 2.0
        
        # Sharpe (simplified)
        if len(returns) > 1:
            mean_ret = avg_return
            std_ret = (sum((r - mean_ret) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe = (mean_ret / std_ret) if std_ret > 0 else 0
        else:
            sharpe = 0
        
        return SignalPerformanceWindow(
            window_name=window_name,
            start_date=start_date,
            end_date=now,
            total_signals=total,
            winning_signals=winning,
            losing_signals=losing,
            win_rate=win_rate,
            avg_return=avg_return,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe,
        )
    
    def _generate_synthetic_window(
        self,
        symbol: str,
        signal_type: str,
        start_date: datetime,
        end_date: datetime,
        window_name: str,
    ) -> SignalPerformanceWindow:
        """
        Generate synthetic performance based on strategy baselines.
        
        Uses the strategy registry from bootstrap to create realistic
        performance distributions.
        """
        # Get baseline from strategy registry
        strategy = self.db.strategies.find_one({"id": signal_type.upper()})
        
        if strategy:
            base_wr = strategy.get("wr", 0.55)
            base_pf = strategy.get("pf", 1.8)
        else:
            # Default baselines for unknown signals
            base_wr = 0.55
            base_pf = 1.8
        
        # Add variance based on window
        if window_name == "recent":
            # Recent has more variance and potential decay
            wr_variance = random.uniform(-0.08, 0.05)
            pf_variance = random.uniform(-0.4, 0.2)
        else:
            # Historical is baseline
            wr_variance = random.uniform(-0.03, 0.03)
            pf_variance = random.uniform(-0.2, 0.2)
        
        win_rate = max(0.3, min(0.8, base_wr + wr_variance))
        profit_factor = max(0.8, min(3.0, base_pf + pf_variance))
        
        # Generate signal counts
        days = (end_date - start_date).days
        signals_per_day = 0.5  # Average signals per day
        total_signals = int(days * signals_per_day)
        
        winning = int(total_signals * win_rate)
        losing = total_signals - winning
        
        # Derive other metrics
        avg_return = 0.02 * (win_rate - 0.5) + random.uniform(-0.005, 0.005)
        sharpe = (profit_factor - 1) * 0.5 + random.uniform(-0.2, 0.2)
        
        return SignalPerformanceWindow(
            window_name=window_name,
            start_date=start_date,
            end_date=end_date,
            total_signals=max(10, total_signals),
            winning_signals=max(3, winning),
            losing_signals=max(2, losing),
            win_rate=win_rate,
            avg_return=avg_return,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # DECAY METRICS COMPUTATION
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_decay_ratio(
        self,
        recent: SignalPerformanceWindow,
        historical: SignalPerformanceWindow,
    ) -> float:
        """
        Compute decay ratio: recent_wr / historical_wr
        
        < 1.0 means signal is decaying
        = 1.0 means signal is stable
        > 1.0 means signal is improving
        """
        if historical.win_rate == 0:
            return 1.0
        
        return recent.win_rate / historical.win_rate
    
    def _compute_performance_delta(
        self,
        recent: SignalPerformanceWindow,
        historical: SignalPerformanceWindow,
    ) -> float:
        """
        Compute performance delta: recent_pf - historical_pf
        
        Negative = signal degrading
        Zero = stable
        Positive = improving
        """
        return recent.profit_factor - historical.profit_factor
    
    def _compute_consistency(
        self,
        symbol: str,
        signal_type: str,
    ) -> float:
        """
        Compute consistency score based on rolling performance stability.
        
        Returns 0.0 - 1.0 where 1.0 is perfectly consistent.
        """
        # Get monthly performance buckets
        now = datetime.now(timezone.utc)
        monthly_wrs = []
        
        for months_ago in range(6):
            start = now - timedelta(days=30 * (months_ago + 1))
            end = now - timedelta(days=30 * months_ago)
            
            records = list(self.db.signal_performance.find({
                "symbol": symbol,
                "signal_type": signal_type,
                "timestamp": {"$gte": start, "$lt": end}
            }))
            
            if records:
                wr = sum(1 for r in records if r.get("outcome", 0) > 0) / len(records)
                monthly_wrs.append(wr)
        
        # If no data, use synthetic
        if len(monthly_wrs) < 3:
            # Generate synthetic monthly performance
            base_wr = 0.55
            monthly_wrs = [
                max(0.35, min(0.75, base_wr + random.uniform(-0.1, 0.1)))
                for _ in range(6)
            ]
        
        # Compute standard deviation of win rates
        if len(monthly_wrs) > 1:
            mean_wr = sum(monthly_wrs) / len(monthly_wrs)
            variance = sum((wr - mean_wr) ** 2 for wr in monthly_wrs) / len(monthly_wrs)
            std_dev = variance ** 0.5
            
            # Convert to 0-1 score (lower std = higher consistency)
            # std of 0.1 = score 0.5, std of 0 = score 1.0, std of 0.2 = score 0.0
            consistency = max(0.0, 1.0 - (std_dev / 0.2))
        else:
            consistency = 0.5
        
        return consistency
    
    # ═══════════════════════════════════════════════════════════════
    # STATE DETERMINATION
    # ═══════════════════════════════════════════════════════════════
    
    def _determine_decay_state(
        self,
        decay_ratio: float,
        performance_delta: float,
        recent: SignalPerformanceWindow,
        historical: SignalPerformanceWindow,
    ) -> DecayState:
        """
        Determine decay state from metrics.
        
        Uses both win rate ratio and profit factor delta.
        """
        # Primary: decay ratio
        if decay_ratio < DECAY_THRESHOLDS["decaying_max"]:
            return DecayState.DECAYING
        
        if decay_ratio > DECAY_THRESHOLDS["improving_min"]:
            return DecayState.IMPROVING
        
        # Secondary: performance delta
        if performance_delta < DECAY_THRESHOLDS["pf_decaying_max"]:
            return DecayState.DECAYING
        
        if performance_delta > DECAY_THRESHOLDS["pf_improving_min"]:
            return DecayState.IMPROVING
        
        return DecayState.STABLE
    
    def _determine_overall_state(
        self,
        decaying: int,
        stable: int,
        improving: int,
        avg_decay: float,
    ) -> DecayState:
        """Determine overall decay state for symbol."""
        total = decaying + stable + improving
        
        if total == 0:
            return DecayState.STABLE
        
        # Majority rule with decay ratio tie-breaker
        decay_pct = decaying / total
        improve_pct = improving / total
        
        if decay_pct >= 0.5:
            return DecayState.DECAYING
        
        if improve_pct >= 0.4 and avg_decay > 1.05:
            return DecayState.IMPROVING
        
        return DecayState.STABLE
    
    # ═══════════════════════════════════════════════════════════════
    # MODIFIER COMPUTATION
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_modifiers(
        self,
        decay_state: DecayState,
        decay_ratio: float,
        performance_delta: float,
    ) -> Tuple[float, float]:
        """
        Compute confidence and size modifiers based on decay state.
        
        Returns: (confidence_modifier, size_modifier)
        """
        base = DECAY_MODIFIERS[decay_state]
        conf_mod = base["confidence_modifier"]
        size_mod = base["size_modifier"]
        
        # Fine-tune based on severity
        if decay_state == DecayState.DECAYING:
            # More severe decay = lower modifiers
            if decay_ratio < 0.7:
                conf_mod *= 0.9
                size_mod *= 0.85
            elif decay_ratio < 0.8:
                conf_mod *= 0.95
                size_mod *= 0.9
        
        elif decay_state == DecayState.IMPROVING:
            # Stronger improvement = higher modifiers (capped)
            if decay_ratio > 1.2:
                conf_mod = min(1.15, conf_mod * 1.05)
                size_mod = min(1.1, size_mod * 1.03)
        
        return (conf_mod, size_mod)
    
    def _aggregate_modifier(
        self,
        signal_decays: List[SignalDecayResult],
        modifier_name: str,
    ) -> float:
        """
        Aggregate modifiers weighted by confidence.
        """
        if not signal_decays:
            return 1.0
        
        total_weight = sum(s.confidence for s in signal_decays)
        if total_weight == 0:
            return 1.0
        
        weighted_sum = sum(
            getattr(s, modifier_name) * s.confidence 
            for s in signal_decays
        )
        
        return weighted_sum / total_weight
    
    # ═══════════════════════════════════════════════════════════════
    # EXPLAINABILITY
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_confidence(
        self,
        recent: SignalPerformanceWindow,
        historical: SignalPerformanceWindow,
        consistency: float,
    ) -> float:
        """
        Compute confidence in decay assessment.
        
        Based on sample size and consistency.
        """
        # Sample size factor
        recent_sample = min(recent.total_signals / DECAY_THRESHOLDS["min_recent_signals"], 1.0)
        hist_sample = min(historical.total_signals / DECAY_THRESHOLDS["min_historical_signals"], 1.0)
        sample_factor = (recent_sample + hist_sample) / 2
        
        # Combine with consistency
        confidence = sample_factor * 0.6 + consistency * 0.4
        
        return max(0.3, min(1.0, confidence))
    
    def _build_reason(
        self,
        decay_state: DecayState,
        decay_ratio: float,
        performance_delta: float,
        recent: SignalPerformanceWindow,
        historical: SignalPerformanceWindow,
    ) -> str:
        """Build human-readable reason for decay state."""
        
        if decay_state == DecayState.DECAYING:
            if decay_ratio < 0.7:
                return f"severe_decay_wr_{recent.win_rate:.0%}_vs_{historical.win_rate:.0%}"
            return f"moderate_decay_wr_{recent.win_rate:.0%}_vs_{historical.win_rate:.0%}"
        
        if decay_state == DecayState.IMPROVING:
            return f"signal_improving_wr_{recent.win_rate:.0%}_vs_{historical.win_rate:.0%}"
        
        return f"signal_stable_wr_{recent.win_rate:.0%}_consistent"
    
    # ═══════════════════════════════════════════════════════════════
    # SIGNAL HISTORY MANAGEMENT
    # ═══════════════════════════════════════════════════════════════
    
    def record_signal_outcome(
        self,
        symbol: str,
        signal_type: str,
        outcome: float,  # +1 win, -1 loss
        return_pct: float,
    ):
        """
        Record a signal outcome for future decay analysis.
        
        Call this after each trade completes.
        """
        self.db.signal_performance.insert_one({
            "symbol": symbol,
            "signal_type": signal_type,
            "timestamp": datetime.now(timezone.utc),
            "outcome": outcome,
            "return_pct": return_pct,
        })
    
    def seed_signal_history(self, symbol: str, days: int = 180):
        """
        Seed signal history for testing.
        
        Generates realistic signal outcomes based on strategy baselines.
        """
        now = datetime.now(timezone.utc)
        
        for signal_type in SIGNAL_TYPES:
            # Get baseline
            strategy = self.db.strategies.find_one({"id": signal_type.upper()})
            base_wr = strategy.get("wr", 0.55) if strategy else 0.55
            
            # Generate signals with decay pattern
            for day in range(days):
                timestamp = now - timedelta(days=day)
                
                # Simulate decay: recent signals have lower win rate
                decay_factor = 1.0 - (0.15 * (1 - day / days))  # 15% decay over time
                adjusted_wr = base_wr * decay_factor
                
                # Generate 0-2 signals per day
                num_signals = random.randint(0, 2)
                for _ in range(num_signals):
                    outcome = 1 if random.random() < adjusted_wr else -1
                    return_pct = random.uniform(0.01, 0.05) if outcome > 0 else random.uniform(-0.03, -0.01)
                    
                    self.db.signal_performance.insert_one({
                        "symbol": symbol,
                        "signal_type": signal_type,
                        "timestamp": timestamp,
                        "outcome": outcome,
                        "return_pct": return_pct,
                    })


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[AlphaDecayEngine] = None


def get_alpha_decay_engine() -> AlphaDecayEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = AlphaDecayEngine()
    return _engine
