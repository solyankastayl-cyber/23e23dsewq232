"""
Outcome Tracking Engine

PHASE 30.4 — Outcome Tracking Engine

Makes the system self-learning by tracking hypothesis outcomes.

Pipeline:
hypothesis → decision → outcome → accuracy

Key features:
- Multi-horizon evaluation (5m, 15m, 60m, 240m)
- Direction-based success evaluation
- PnL calculation with tolerance
- Performance aggregation
- Correlation metrics (confidence vs accuracy)

This is the foundation of all quant systems.
"""

from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import math

from .outcome_tracking_types import (
    HypothesisOutcome,
    HypothesisPerformance,
    SymbolOutcomeSummary,
    PendingHypothesisEvaluation,
    EVALUATION_HORIZONS,
    SUCCESS_TOLERANCE,
    NEUTRAL_VOLATILITY_THRESHOLD,
)
from .capital_allocation_types import HypothesisCapitalAllocation


# ══════════════════════════════════════════════════════════════
# Outcome Tracking Engine
# ══════════════════════════════════════════════════════════════

class OutcomeTrackingEngine:
    """
    Outcome Tracking Engine — PHASE 30.4
    
    Tracks hypothesis outcomes and calculates performance metrics.
    
    Responsibilities:
    1. Store pending hypotheses for evaluation
    2. Evaluate outcomes at multiple horizons
    3. Calculate PnL and success
    4. Aggregate performance by hypothesis type
    5. Calculate correlation metrics
    """
    
    def __init__(self):
        # Pending evaluations by symbol
        self._pending: Dict[str, List[PendingHypothesisEvaluation]] = {}
        # Completed outcomes by symbol
        self._outcomes: Dict[str, List[HypothesisOutcome]] = {}
        # Performance cache
        self._performance_cache: Dict[str, Dict[str, HypothesisPerformance]] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Register Hypothesis for Tracking
    # ═══════════════════════════════════════════════════════════
    
    def register_hypothesis(
        self,
        allocation: HypothesisCapitalAllocation,
        current_price: float,
    ) -> int:
        """
        Register hypotheses from capital allocation for outcome tracking.
        
        Returns: Number of hypotheses registered
        """
        symbol = allocation.symbol
        if symbol not in self._pending:
            self._pending[symbol] = []
        
        registered = 0
        now = datetime.now(timezone.utc)
        
        for alloc in allocation.allocations:
            pending = PendingHypothesisEvaluation(
                symbol=symbol,
                hypothesis_type=alloc.hypothesis_type,
                directional_bias=alloc.directional_bias,
                confidence=alloc.confidence,
                reliability=alloc.reliability,
                capital_weight=alloc.capital_weight,
                price_at_creation=current_price,
                created_at=now,
                horizons_evaluated=[],
            )
            self._pending[symbol].append(pending)
            registered += 1
        
        return registered
    
    # ═══════════════════════════════════════════════════════════
    # 2. PnL Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_pnl(
        self,
        price_at_creation: float,
        evaluation_price: float,
        directional_bias: str,
    ) -> float:
        """
        Calculate PnL percent.
        
        For LONG: (eval - create) / create
        For SHORT: (create - eval) / create (inverted)
        For NEUTRAL: absolute change (for tracking)
        """
        if price_at_creation <= 0:
            return 0.0
        
        price_change = (evaluation_price - price_at_creation) / price_at_creation
        
        if directional_bias == "SHORT":
            # Invert for short positions
            return round(-price_change * 100, 4)
        else:
            return round(price_change * 100, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 3. Direction Evaluation
    # ═══════════════════════════════════════════════════════════
    
    def determine_actual_direction(
        self,
        price_at_creation: float,
        evaluation_price: float,
    ) -> str:
        """
        Determine actual price direction.
        
        Returns: UP, DOWN, or FLAT
        """
        if price_at_creation <= 0:
            return "FLAT"
        
        change_pct = abs((evaluation_price - price_at_creation) / price_at_creation)
        
        if change_pct < NEUTRAL_VOLATILITY_THRESHOLD:
            return "FLAT"
        elif evaluation_price > price_at_creation:
            return "UP"
        else:
            return "DOWN"
    
    def get_expected_direction(self, directional_bias: str) -> str:
        """
        Get expected direction from directional bias.
        """
        if directional_bias == "LONG":
            return "UP"
        elif directional_bias == "SHORT":
            return "DOWN"
        else:
            return "FLAT"
    
    # ═══════════════════════════════════════════════════════════
    # 4. Success Determination
    # ═══════════════════════════════════════════════════════════
    
    def evaluate_success(
        self,
        directional_bias: str,
        pnl_percent: float,
        price_at_creation: float,
        evaluation_price: float,
    ) -> bool:
        """
        Determine if hypothesis was successful.
        
        LONG: success if price_change > tolerance
        SHORT: success if price_change < -tolerance (pnl > tolerance after inversion)
        NEUTRAL: success if |price_change| < volatility_threshold
        """
        price_change_pct = (evaluation_price - price_at_creation) / price_at_creation if price_at_creation > 0 else 0
        
        if directional_bias == "LONG":
            return price_change_pct > SUCCESS_TOLERANCE
        elif directional_bias == "SHORT":
            return price_change_pct < -SUCCESS_TOLERANCE
        else:  # NEUTRAL
            return abs(price_change_pct) < NEUTRAL_VOLATILITY_THRESHOLD
    
    # ═══════════════════════════════════════════════════════════
    # 5. Single Hypothesis Evaluation
    # ═══════════════════════════════════════════════════════════
    
    def evaluate_hypothesis(
        self,
        pending: PendingHypothesisEvaluation,
        evaluation_price: float,
        horizon_minutes: int,
    ) -> HypothesisOutcome:
        """
        Evaluate a single hypothesis outcome.
        """
        pnl = self.calculate_pnl(
            pending.price_at_creation,
            evaluation_price,
            pending.directional_bias,
        )
        
        actual_direction = self.determine_actual_direction(
            pending.price_at_creation,
            evaluation_price,
        )
        
        expected_direction = self.get_expected_direction(pending.directional_bias)
        
        success = self.evaluate_success(
            pending.directional_bias,
            pnl,
            pending.price_at_creation,
            evaluation_price,
        )
        
        outcome = HypothesisOutcome(
            symbol=pending.symbol,
            hypothesis_type=pending.hypothesis_type,
            directional_bias=pending.directional_bias,
            price_at_creation=pending.price_at_creation,
            evaluation_price=evaluation_price,
            horizon_minutes=horizon_minutes,
            expected_direction=expected_direction,
            actual_direction=actual_direction,
            pnl_percent=pnl,
            success=success,
            confidence=pending.confidence,
            reliability=pending.reliability,
            capital_weight=pending.capital_weight,
            created_at=pending.created_at,
        )
        
        return outcome
    
    # ═══════════════════════════════════════════════════════════
    # 6. Batch Evaluation (Scheduler Entry Point)
    # ═══════════════════════════════════════════════════════════
    
    def evaluate_pending(
        self,
        symbol: str,
        current_price: float,
        current_time: Optional[datetime] = None,
    ) -> List[HypothesisOutcome]:
        """
        Evaluate all pending hypotheses for a symbol at appropriate horizons.
        
        Called by scheduler every 5 minutes.
        """
        if symbol not in self._pending:
            return []
        
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        outcomes = []
        remaining_pending = []
        
        for pending in self._pending[symbol]:
            age_minutes = (current_time - pending.created_at).total_seconds() / 60
            
            # Check each horizon
            for horizon in EVALUATION_HORIZONS:
                if horizon in pending.horizons_evaluated:
                    continue
                
                # Allow 1 minute tolerance for evaluation
                if age_minutes >= horizon - 1:
                    outcome = self.evaluate_hypothesis(pending, current_price, horizon)
                    outcomes.append(outcome)
                    self._store_outcome(outcome)
                    pending.horizons_evaluated.append(horizon)
                    
                    # TASK 93: Auto-write to regime memory
                    self._write_to_memory(outcome)
            
            # Keep pending if not all horizons evaluated
            if len(pending.horizons_evaluated) < len(EVALUATION_HORIZONS):
                # But remove if too old (beyond max horizon + buffer)
                max_horizon = max(EVALUATION_HORIZONS)
                if age_minutes < max_horizon + 60:  # 1 hour buffer
                    remaining_pending.append(pending)
        
        self._pending[symbol] = remaining_pending
        
        # Invalidate performance cache
        if outcomes:
            self._performance_cache.pop(symbol, None)
        
        return outcomes
    
    def _write_to_memory(self, outcome: HypothesisOutcome) -> None:
        """
        TASK 93: Auto-write outcome to regime memory.
        
        Links OutcomeTrackingEngine → RegimeMemoryRegistry
        """
        try:
            from modules.regime_memory.memory_auto_writer import get_memory_auto_writer
            writer = get_memory_auto_writer()
            writer.write_from_outcome(outcome)
        except Exception as e:
            # Don't break tracking if memory write fails
            print(f"[OutcomeTracking] Memory write warning: {e}")
    
    # ═══════════════════════════════════════════════════════════
    # 7. Performance Aggregation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_performance(
        self,
        symbol: str,
        hypothesis_type: Optional[str] = None,
    ) -> List[HypothesisPerformance]:
        """
        Calculate aggregated performance metrics.
        """
        outcomes = self._outcomes.get(symbol, [])
        if not outcomes:
            return []
        
        # Group by hypothesis type
        by_type: Dict[str, List[HypothesisOutcome]] = defaultdict(list)
        for outcome in outcomes:
            if hypothesis_type and outcome.hypothesis_type != hypothesis_type:
                continue
            by_type[outcome.hypothesis_type].append(outcome)
        
        performances = []
        for h_type, type_outcomes in by_type.items():
            perf = self._calculate_type_performance(h_type, type_outcomes)
            performances.append(perf)
        
        return sorted(performances, key=lambda p: p.success_rate, reverse=True)
    
    def _calculate_type_performance(
        self,
        hypothesis_type: str,
        outcomes: List[HypothesisOutcome],
    ) -> HypothesisPerformance:
        """
        Calculate performance for a single hypothesis type.
        """
        if not outcomes:
            return HypothesisPerformance(hypothesis_type=hypothesis_type)
        
        total = len(outcomes)
        successes = sum(1 for o in outcomes if o.success)
        
        success_rate = successes / total
        avg_pnl = sum(o.pnl_percent for o in outcomes) / total
        avg_confidence = sum(o.confidence for o in outcomes) / total
        avg_reliability = sum(o.reliability for o in outcomes) / total
        
        # Success rate by horizon
        horizon_success = {}
        for horizon in EVALUATION_HORIZONS:
            horizon_outcomes = [o for o in outcomes if o.horizon_minutes == horizon]
            if horizon_outcomes:
                horizon_success[horizon] = sum(1 for o in horizon_outcomes if o.success) / len(horizon_outcomes)
            else:
                horizon_success[horizon] = 0.0
        
        # Calculate correlations
        conf_corr = self._calculate_correlation(
            [o.confidence for o in outcomes],
            [1.0 if o.success else 0.0 for o in outcomes],
        )
        rel_corr = self._calculate_correlation(
            [o.reliability for o in outcomes],
            [1.0 if o.success else 0.0 for o in outcomes],
        )
        
        return HypothesisPerformance(
            hypothesis_type=hypothesis_type,
            total_predictions=total,
            success_rate=round(success_rate, 4),
            avg_pnl=round(avg_pnl, 4),
            avg_confidence=round(avg_confidence, 4),
            avg_reliability=round(avg_reliability, 4),
            confidence_accuracy_correlation=round(conf_corr, 4),
            reliability_accuracy_correlation=round(rel_corr, 4),
            success_rate_5m=round(horizon_success.get(5, 0.0), 4),
            success_rate_15m=round(horizon_success.get(15, 0.0), 4),
            success_rate_60m=round(horizon_success.get(60, 0.0), 4),
            success_rate_240m=round(horizon_success.get(240, 0.0), 4),
        )
    
    def _calculate_correlation(
        self,
        x: List[float],
        y: List[float],
    ) -> float:
        """
        Calculate Pearson correlation coefficient.
        """
        n = len(x)
        if n < 2:
            return 0.0
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        
        var_x = sum((xi - mean_x) ** 2 for xi in x)
        var_y = sum((yi - mean_y) ** 2 for yi in y)
        
        denominator = math.sqrt(var_x * var_y)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    # ═══════════════════════════════════════════════════════════
    # 8. Summary Calculation
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, symbol: str) -> SymbolOutcomeSummary:
        """
        Get overall outcome summary for a symbol.
        """
        outcomes = self._outcomes.get(symbol, [])
        
        if not outcomes:
            return SymbolOutcomeSummary(symbol=symbol)
        
        total = len(outcomes)
        successes = sum(1 for o in outcomes if o.success)
        
        # By direction
        long_outcomes = [o for o in outcomes if o.directional_bias == "LONG"]
        short_outcomes = [o for o in outcomes if o.directional_bias == "SHORT"]
        neutral_outcomes = [o for o in outcomes if o.directional_bias == "NEUTRAL"]
        
        long_success = sum(1 for o in long_outcomes if o.success) / len(long_outcomes) if long_outcomes else 0.0
        short_success = sum(1 for o in short_outcomes if o.success) / len(short_outcomes) if short_outcomes else 0.0
        neutral_success = sum(1 for o in neutral_outcomes if o.success) / len(neutral_outcomes) if neutral_outcomes else 0.0
        
        # Performance by type
        performances = self.calculate_performance(symbol)
        
        best_perf = max(performances, key=lambda p: p.success_rate) if performances else None
        worst_perf = min(performances, key=lambda p: p.success_rate) if performances else None
        
        # Average correlation
        avg_corr = sum(p.confidence_accuracy_correlation for p in performances) / len(performances) if performances else 0.0
        
        return SymbolOutcomeSummary(
            symbol=symbol,
            total_outcomes=total,
            overall_success_rate=round(successes / total, 4),
            overall_avg_pnl=round(sum(o.pnl_percent for o in outcomes) / total, 4),
            long_success_rate=round(long_success, 4),
            short_success_rate=round(short_success, 4),
            neutral_success_rate=round(neutral_success, 4),
            best_hypothesis_type=best_perf.hypothesis_type if best_perf else "NONE",
            best_success_rate=best_perf.success_rate if best_perf else 0.0,
            worst_hypothesis_type=worst_perf.hypothesis_type if worst_perf else "NONE",
            worst_success_rate=worst_perf.success_rate if worst_perf else 0.0,
            avg_confidence_accuracy_correlation=round(avg_corr, 4),
            last_evaluated_at=max(o.evaluated_at for o in outcomes) if outcomes else None,
        )
    
    # ═══════════════════════════════════════════════════════════
    # 9. Storage
    # ═══════════════════════════════════════════════════════════
    
    def _store_outcome(self, outcome: HypothesisOutcome) -> None:
        """Store outcome in memory."""
        symbol = outcome.symbol
        if symbol not in self._outcomes:
            self._outcomes[symbol] = []
        self._outcomes[symbol].append(outcome)
    
    def get_outcomes(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[HypothesisOutcome]:
        """Get recent outcomes for symbol."""
        outcomes = self._outcomes.get(symbol, [])
        return sorted(outcomes, key=lambda o: o.evaluated_at, reverse=True)[:limit]
    
    def get_pending_count(self, symbol: str) -> int:
        """Get count of pending evaluations."""
        return len(self._pending.get(symbol, []))
    
    # ═══════════════════════════════════════════════════════════
    # 10. Manual Evaluation (for testing/API)
    # ═══════════════════════════════════════════════════════════
    
    def force_evaluate(
        self,
        symbol: str,
        current_price: float,
    ) -> List[HypothesisOutcome]:
        """
        Force immediate evaluation of all pending hypotheses.
        Used for testing and manual triggers.
        """
        if symbol not in self._pending:
            return []
        
        outcomes = []
        
        for pending in self._pending[symbol]:
            # Evaluate at all remaining horizons
            for horizon in EVALUATION_HORIZONS:
                if horizon not in pending.horizons_evaluated:
                    outcome = self.evaluate_hypothesis(pending, current_price, horizon)
                    outcomes.append(outcome)
                    self._store_outcome(outcome)
                    
                    # TASK 93: Auto-write to regime memory
                    self._write_to_memory(outcome)
        
        # Clear pending
        self._pending[symbol] = []
        
        # Invalidate cache
        self._performance_cache.pop(symbol, None)
        
        return outcomes


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_tracking_engine: Optional[OutcomeTrackingEngine] = None


def get_outcome_tracking_engine() -> OutcomeTrackingEngine:
    """Get singleton instance of OutcomeTrackingEngine."""
    global _tracking_engine
    if _tracking_engine is None:
        _tracking_engine = OutcomeTrackingEngine()
    return _tracking_engine
