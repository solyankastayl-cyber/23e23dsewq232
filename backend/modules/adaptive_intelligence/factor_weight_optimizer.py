"""
PHASE 11.3 - Factor Weight Optimizer
=====================================
Adjusts weights of various factors in the system.

Factors:
- Alpha factors
- Ensemble weights
- Structure signals
- Liquidity signals
- Microstructure signals
"""

import random
from typing import List, Dict, Optional
from datetime import datetime, timezone

from .adaptive_types import (
    FactorWeight, ChangeDecision, DEFAULT_ADAPTIVE_CONFIG
)


class FactorWeightOptimizer:
    """
    Factor Weight Optimization Engine
    
    Adjusts weights of different factors based on
    their recent performance and contribution.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_ADAPTIVE_CONFIG
        self.weight_history: Dict[str, List[FactorWeight]] = {}
        self.current_weights: Dict[str, float] = {}
        self.factor_performance: Dict[str, List[float]] = {}
        self.max_history = 100
    
    def initialize_weights(self, factors: Dict[str, Dict]):
        """
        Initialize factor weights.
        
        Args:
            factors: Dict of factor_name -> {category, initial_weight}
        """
        for name, info in factors.items():
            self.current_weights[name] = info.get("initial_weight", 1.0)
            self.factor_performance[name] = []
    
    def record_factor_performance(
        self,
        factor_name: str,
        accuracy: float,
        contribution: float
    ):
        """Record factor performance for later optimization."""
        if factor_name not in self.factor_performance:
            self.factor_performance[factor_name] = []
        
        self.factor_performance[factor_name].append({
            "accuracy": accuracy,
            "contribution": contribution,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Keep last 100 records
        if len(self.factor_performance[factor_name]) > 100:
            self.factor_performance[factor_name] = self.factor_performance[factor_name][-100:]
    
    def optimize_weights(
        self,
        factors: Dict[str, str],  # factor_name -> category
        performance_data: Optional[List[Dict]] = None
    ) -> List[FactorWeight]:
        """
        Optimize weights for all factors.
        
        Args:
            factors: Dict of factor_name -> category
            performance_data: Optional recent performance data
            
        Returns:
            List of FactorWeight adjustments
        """
        now = datetime.now(timezone.utc)
        adjustments = []
        
        for factor_name, category in factors.items():
            adjustment = self._optimize_single_weight(
                factor_name, category, performance_data
            )
            adjustments.append(adjustment)
        
        return adjustments
    
    def _optimize_single_weight(
        self,
        factor_name: str,
        category: str,
        performance_data: Optional[List[Dict]]
    ) -> FactorWeight:
        """Optimize a single factor weight."""
        now = datetime.now(timezone.utc)
        
        current_weight = self.current_weights.get(factor_name, 1.0)
        
        # Calculate factor performance
        perf_history = self.factor_performance.get(factor_name, [])
        
        if perf_history:
            recent_accuracy = sum(p["accuracy"] for p in perf_history[-20:]) / min(20, len(perf_history))
            recent_contribution = sum(p["contribution"] for p in perf_history[-20:]) / min(20, len(perf_history))
        else:
            # Generate mock performance
            recent_accuracy = 0.5 + random.gauss(0, 0.1)
            recent_contribution = random.gauss(0.01, 0.02)
        
        # Calculate suggested weight change
        # Higher accuracy/contribution = increase weight
        performance_score = (recent_accuracy - 0.5) * 2 + recent_contribution * 10
        
        # Determine weight adjustment
        max_change = self.config["max_weight_change_pct"]
        
        if performance_score > 0.2:
            weight_change = min(max_change, performance_score * 0.1)
            trend = "UP"
        elif performance_score < -0.2:
            weight_change = max(-max_change, performance_score * 0.1)
            trend = "DOWN"
        else:
            weight_change = 0
            trend = "STABLE"
        
        suggested_weight = current_weight * (1 + weight_change)
        suggested_weight = max(0.1, min(2.0, suggested_weight))  # Bounds
        
        # Check cooldown
        cooldown_clear = self._check_weight_cooldown(factor_name)
        
        # Determine decision
        if abs(weight_change) < 0.01:
            decision = ChangeDecision.APPROVED  # No change needed
        elif not cooldown_clear:
            decision = ChangeDecision.PENDING_COOLDOWN
        elif abs(weight_change) > max_change:
            decision = ChangeDecision.TOO_LARGE
        else:
            decision = ChangeDecision.PENDING_OOS
        
        factor_weight = FactorWeight(
            factor_name=factor_name,
            category=category,
            timestamp=now,
            current_weight=current_weight,
            suggested_weight=suggested_weight,
            weight_change=weight_change,
            contribution_to_pnl=recent_contribution,
            signal_accuracy=recent_accuracy,
            weight_trend=trend,
            decision=decision
        )
        
        # Save to history
        self._add_to_history(factor_name, factor_weight)
        
        return factor_weight
    
    def apply_weight_change(self, factor_name: str, new_weight: float):
        """Apply approved weight change."""
        self.current_weights[factor_name] = new_weight
    
    def _check_weight_cooldown(self, factor_name: str) -> bool:
        """Check if cooldown has passed."""
        history = self.weight_history.get(factor_name, [])
        
        if not history:
            return True
        
        # Find last approved change
        last_approved = None
        for h in reversed(history):
            if h.decision == ChangeDecision.APPROVED:
                last_approved = h
                break
        
        if not last_approved:
            return True
        
        hours_since = (datetime.now(timezone.utc) - last_approved.timestamp).total_seconds() / 3600
        cooldown_hours = self.config["weight_cooldown_hours"]
        
        return hours_since >= cooldown_hours
    
    def _add_to_history(self, factor_name: str, weight: FactorWeight):
        """Add weight to history."""
        if factor_name not in self.weight_history:
            self.weight_history[factor_name] = []
        
        self.weight_history[factor_name].append(weight)
        
        if len(self.weight_history[factor_name]) > self.max_history:
            self.weight_history[factor_name] = self.weight_history[factor_name][-self.max_history:]
    
    def get_current_weights(self) -> Dict[str, float]:
        """Get current factor weights."""
        return self.current_weights.copy()
    
    def get_pending_changes(self) -> List[FactorWeight]:
        """Get pending weight changes."""
        pending = []
        
        for factor, history in self.weight_history.items():
            if history and history[-1].decision in [
                ChangeDecision.PENDING_OOS,
                ChangeDecision.PENDING_SHADOW
            ]:
                pending.append(history[-1])
        
        return pending
    
    def get_weight_summary(self) -> Dict:
        """Get summary of weight optimization."""
        increasing = []
        decreasing = []
        stable = []
        
        for factor, history in self.weight_history.items():
            if history:
                trend = history[-1].weight_trend
                if trend == "UP":
                    increasing.append(factor)
                elif trend == "DOWN":
                    decreasing.append(factor)
                else:
                    stable.append(factor)
        
        return {
            "total_factors": len(self.current_weights),
            "increasing": increasing,
            "decreasing": decreasing,
            "stable": stable,
            "pending_changes": len(self.get_pending_changes())
        }
