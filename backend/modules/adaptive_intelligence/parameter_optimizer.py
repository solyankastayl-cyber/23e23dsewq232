"""
PHASE 11.2 - Parameter Optimizer
=================================
Optimizes strategy parameters using various methods.

Methods:
- Grid search
- Bayesian optimization
- Rolling optimization

Parameters:
- lookback_window
- stop_distance
- take_profit_ratio
- volatility_threshold
- structure_confirmation_level
"""

import random
import math
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone

from .adaptive_types import (
    ParameterAdjustment, ChangeDecision, OptimizationMethod,
    DEFAULT_ADAPTIVE_CONFIG
)


class ParameterOptimizer:
    """
    Strategy Parameter Optimizer
    
    Optimizes strategy parameters to improve performance
    while respecting safety constraints.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_ADAPTIVE_CONFIG
        self.optimization_history: Dict[str, List[ParameterAdjustment]] = {}
        self.parameter_bounds: Dict[str, Dict[str, Tuple[float, float]]] = {}
        self.max_history = 100
    
    def set_parameter_bounds(
        self,
        strategy_id: str,
        parameter_name: str,
        min_val: float,
        max_val: float
    ):
        """Set bounds for a parameter."""
        if strategy_id not in self.parameter_bounds:
            self.parameter_bounds[strategy_id] = {}
        
        self.parameter_bounds[strategy_id][parameter_name] = (min_val, max_val)
    
    def optimize_parameter(
        self,
        strategy_id: str,
        parameter_name: str,
        current_value: float,
        performance_data: List[Dict],
        method: OptimizationMethod = OptimizationMethod.BAYESIAN
    ) -> ParameterAdjustment:
        """
        Optimize a single parameter.
        
        Args:
            strategy_id: Strategy identifier
            parameter_name: Name of parameter to optimize
            current_value: Current parameter value
            performance_data: Historical performance data
            method: Optimization method to use
            
        Returns:
            ParameterAdjustment with recommendation
        """
        now = datetime.now(timezone.utc)
        
        # Get bounds
        bounds = self.parameter_bounds.get(strategy_id, {}).get(
            parameter_name, (current_value * 0.5, current_value * 1.5)
        )
        
        # Run optimization
        if method == OptimizationMethod.GRID_SEARCH:
            optimal, improvement, confidence = self._grid_search(
                current_value, bounds, performance_data
            )
        elif method == OptimizationMethod.BAYESIAN:
            optimal, improvement, confidence = self._bayesian_optimize(
                current_value, bounds, performance_data
            )
        else:
            optimal, improvement, confidence = self._rolling_optimize(
                current_value, bounds, performance_data
            )
        
        # Calculate change magnitude
        if current_value != 0:
            change_magnitude = abs(optimal - current_value) / abs(current_value)
        else:
            change_magnitude = abs(optimal - current_value)
        
        # Check limits
        max_change = self.config["max_parameter_change_pct"]
        within_limits = change_magnitude <= max_change
        
        # If change too large, clip it
        if not within_limits:
            direction = 1 if optimal > current_value else -1
            optimal = current_value * (1 + direction * max_change)
            change_magnitude = max_change
        
        # Check cooldown
        cooldown_clear = self._check_cooldown(strategy_id, parameter_name)
        
        # Determine decision
        if not within_limits:
            decision = ChangeDecision.TOO_LARGE
            rejection = "Change magnitude exceeds safety limits"
        elif not cooldown_clear:
            decision = ChangeDecision.PENDING_COOLDOWN
            rejection = "Cooldown period not elapsed"
        elif confidence < self.config["min_confidence_for_change"]:
            decision = ChangeDecision.REJECTED
            rejection = "Insufficient confidence"
        else:
            decision = ChangeDecision.PENDING_OOS
            rejection = None
        
        adjustment = ParameterAdjustment(
            parameter_name=parameter_name,
            strategy_id=strategy_id,
            timestamp=now,
            current_value=current_value,
            suggested_value=optimal,
            optimal_range=bounds,
            expected_improvement=improvement,
            confidence=confidence,
            change_magnitude=change_magnitude,
            within_limits=within_limits,
            cooldown_clear=cooldown_clear,
            decision=decision,
            rejection_reason=rejection
        )
        
        # Save to history
        self._add_to_history(strategy_id, parameter_name, adjustment)
        
        return adjustment
    
    def _grid_search(
        self,
        current: float,
        bounds: Tuple[float, float],
        data: List[Dict]
    ) -> Tuple[float, float, float]:
        """Grid search optimization."""
        min_val, max_val = bounds
        step = (max_val - min_val) / 10
        
        best_val = current
        best_score = self._evaluate_parameter(current, data)
        
        test_val = min_val
        while test_val <= max_val:
            score = self._evaluate_parameter(test_val, data)
            if score > best_score:
                best_score = score
                best_val = test_val
            test_val += step
        
        improvement = (best_score - self._evaluate_parameter(current, data)) / max(0.001, best_score)
        confidence = 0.6 + random.random() * 0.3  # 0.6-0.9
        
        return best_val, improvement, confidence
    
    def _bayesian_optimize(
        self,
        current: float,
        bounds: Tuple[float, float],
        data: List[Dict]
    ) -> Tuple[float, float, float]:
        """Bayesian optimization (simplified surrogate)."""
        min_val, max_val = bounds
        
        # Simulate Bayesian optimization with acquisition function
        n_samples = 20
        samples = []
        
        for _ in range(n_samples):
            # Expected improvement acquisition
            candidate = random.uniform(min_val, max_val)
            score = self._evaluate_parameter(candidate, data)
            
            # Add exploration bonus for values far from current
            exploration = 0.1 * abs(candidate - current) / (max_val - min_val)
            samples.append((candidate, score + exploration))
        
        # Find best
        best_candidate, best_score = max(samples, key=lambda x: x[1])
        current_score = self._evaluate_parameter(current, data)
        
        improvement = (best_score - current_score) / max(0.001, best_score)
        confidence = 0.7 + random.random() * 0.25  # 0.7-0.95
        
        return best_candidate, improvement, confidence
    
    def _rolling_optimize(
        self,
        current: float,
        bounds: Tuple[float, float],
        data: List[Dict]
    ) -> Tuple[float, float, float]:
        """Rolling window optimization."""
        if len(data) < 10:
            return current, 0.0, 0.5
        
        window_size = self.config.get("rolling_window_size", 50)
        recent_data = data[-window_size:]
        
        # Find parameter that worked best in recent data
        min_val, max_val = bounds
        best_val = current
        best_score = 0
        
        for _ in range(10):
            test_val = random.uniform(min_val, max_val)
            score = self._evaluate_parameter(test_val, recent_data)
            if score > best_score:
                best_score = score
                best_val = test_val
        
        current_score = self._evaluate_parameter(current, recent_data)
        improvement = (best_score - current_score) / max(0.001, best_score)
        confidence = 0.65 + random.random() * 0.25
        
        return best_val, improvement, confidence
    
    def _evaluate_parameter(self, param_value: float, data: List[Dict]) -> float:
        """Evaluate parameter performance (mock evaluation)."""
        if not data:
            return 0.5
        
        # Simulate evaluation - in real system would backtest
        base_score = sum(d.get("pnl", 0) for d in data) / len(data)
        
        # Add some noise based on parameter
        noise = random.gauss(0, 0.01)
        
        return base_score + noise
    
    def _check_cooldown(self, strategy_id: str, parameter_name: str) -> bool:
        """Check if cooldown has passed since last change."""
        key = f"{strategy_id}_{parameter_name}"
        history = self.optimization_history.get(key, [])
        
        if not history:
            return True
        
        last_change = history[-1]
        if last_change.decision != ChangeDecision.APPROVED:
            return True
        
        hours_since = (datetime.now(timezone.utc) - last_change.timestamp).total_seconds() / 3600
        cooldown_hours = self.config["parameter_cooldown_hours"]
        
        return hours_since >= cooldown_hours
    
    def _add_to_history(
        self,
        strategy_id: str,
        parameter_name: str,
        adjustment: ParameterAdjustment
    ):
        """Add adjustment to history."""
        key = f"{strategy_id}_{parameter_name}"
        
        if key not in self.optimization_history:
            self.optimization_history[key] = []
        
        self.optimization_history[key].append(adjustment)
        
        if len(self.optimization_history[key]) > self.max_history:
            self.optimization_history[key] = self.optimization_history[key][-self.max_history:]
    
    def get_pending_adjustments(self) -> List[ParameterAdjustment]:
        """Get all pending parameter adjustments."""
        pending = []
        
        for key, history in self.optimization_history.items():
            if history and history[-1].decision in [
                ChangeDecision.PENDING_OOS,
                ChangeDecision.PENDING_SHADOW
            ]:
                pending.append(history[-1])
        
        return pending
    
    def get_optimization_summary(self) -> Dict:
        """Get summary of optimization activity."""
        total_optimizations = sum(len(h) for h in self.optimization_history.values())
        
        approved = 0
        rejected = 0
        pending = 0
        
        for history in self.optimization_history.values():
            for adj in history:
                if adj.decision == ChangeDecision.APPROVED:
                    approved += 1
                elif adj.decision == ChangeDecision.REJECTED:
                    rejected += 1
                elif adj.decision in [ChangeDecision.PENDING_OOS, ChangeDecision.PENDING_SHADOW]:
                    pending += 1
        
        return {
            "total_optimizations": total_optimizations,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "parameters_tracked": len(self.optimization_history)
        }
