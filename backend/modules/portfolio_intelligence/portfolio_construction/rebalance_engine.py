"""
PHASE 10 - Rebalance Engine
============================
Periodic portfolio rebalancing.

Triggers:
- Time-based (every 24h)
- Regime change
- After drawdown
- Drift threshold exceeded
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta

from .portfolio_types import (
    StrategyAllocation, RebalanceRecommendation, RebalanceAction,
    DrawdownState, DEFAULT_PORTFOLIO_CONFIG
)


class RebalanceEngine:
    """
    Portfolio Rebalancing Engine
    
    Determines when and how to rebalance portfolio allocations.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_PORTFOLIO_CONFIG
        self.history: List[RebalanceRecommendation] = []
        self.max_history = 100
        self.last_rebalance: Optional[datetime] = None
        self.last_regime: Optional[str] = None
    
    def evaluate_rebalance(
        self,
        current_allocations: Dict[str, StrategyAllocation],
        target_allocations: Dict[str, float],
        drawdown_state: DrawdownState,
        current_regime: Optional[str] = None
    ) -> RebalanceRecommendation:
        """
        Evaluate if rebalancing is needed.
        
        Args:
            current_allocations: Current strategy allocations
            target_allocations: Target allocation weights
            drawdown_state: Current drawdown state
            current_regime: Current market regime
            
        Returns:
            RebalanceRecommendation with action and details
        """
        now = datetime.now(timezone.utc)
        reasons = []
        urgency = 0.0
        
        # Check time-based trigger
        time_trigger, time_urgency = self._check_time_trigger(now)
        if time_trigger:
            reasons.append("Time-based rebalance due")
            urgency = max(urgency, time_urgency)
        
        # Check drift trigger
        drift_trigger, drift_urgency, max_drift = self._check_drift_trigger(
            current_allocations, target_allocations
        )
        if drift_trigger:
            reasons.append(f"Allocation drift exceeded threshold ({max_drift:.1%})")
            urgency = max(urgency, drift_urgency)
        
        # Check regime change trigger
        regime_trigger = self._check_regime_trigger(current_regime)
        if regime_trigger:
            reasons.append(f"Regime change detected: {self.last_regime} → {current_regime}")
            urgency = max(urgency, 0.6)
        
        # Check drawdown trigger
        dd_trigger, dd_urgency = self._check_drawdown_trigger(drawdown_state)
        if dd_trigger:
            reasons.append(f"Drawdown state: {drawdown_state.value}")
            urgency = max(urgency, dd_urgency)
        
        # Determine action
        if drawdown_state == DrawdownState.EMERGENCY:
            action = RebalanceAction.URGENT_REBALANCE
            trigger_reason = "Emergency drawdown"
            exec_time = "IMMEDIATE"
        elif drawdown_state == DrawdownState.CRITICAL:
            action = RebalanceAction.REDUCE_EXPOSURE
            trigger_reason = "Critical drawdown"
            exec_time = "IMMEDIATE"
        elif urgency > 0.7:
            action = RebalanceAction.REBALANCE_REQUIRED
            trigger_reason = reasons[0] if reasons else "Multiple triggers"
            exec_time = "IMMEDIATE"
        elif urgency > 0.4:
            action = RebalanceAction.MINOR_ADJUSTMENT
            trigger_reason = reasons[0] if reasons else "Minor drift"
            exec_time = "END_OF_DAY"
        elif urgency > 0.2:
            action = RebalanceAction.MINOR_ADJUSTMENT
            trigger_reason = reasons[0] if reasons else "Low priority adjustment"
            exec_time = "NEXT_SESSION"
        else:
            action = RebalanceAction.NO_ACTION
            trigger_reason = "No rebalance needed"
            exec_time = "N/A"
        
        # Calculate deltas
        deltas = self._calculate_deltas(current_allocations, target_allocations)
        
        # Estimate turnover and cost
        turnover = sum(abs(d) for d in deltas.values()) / 2  # Round-trip
        cost_bps = turnover * 5  # Assume 5 bps per trade
        
        result = RebalanceRecommendation(
            timestamp=now,
            action=action,
            urgency=urgency,
            allocations_delta=deltas,
            trigger_reason=trigger_reason,
            rebalance_reasons=reasons,
            recommended_execution_time=exec_time,
            estimated_turnover=turnover,
            estimated_cost_bps=cost_bps
        )
        
        # Update tracking
        if action in [RebalanceAction.REBALANCE_REQUIRED, RebalanceAction.URGENT_REBALANCE]:
            self.last_rebalance = now
        
        if current_regime:
            self.last_regime = current_regime
        
        self._add_to_history(result)
        
        return result
    
    def _check_time_trigger(self, now: datetime) -> tuple:
        """Check if time-based rebalance is due."""
        if self.last_rebalance is None:
            return True, 0.3  # First time, low urgency
        
        hours_since = (now - self.last_rebalance).total_seconds() / 3600
        
        if hours_since >= 48:  # 2 days
            return True, 0.6
        elif hours_since >= 24:  # 1 day
            return True, 0.4
        
        return False, 0.0
    
    def _check_drift_trigger(
        self,
        current: Dict[str, StrategyAllocation],
        target: Dict[str, float]
    ) -> tuple:
        """Check if allocation drift exceeds threshold."""
        threshold = self.config["rebalance_threshold"]
        
        max_drift = 0.0
        for sid, alloc in current.items():
            target_weight = target.get(sid, 0)
            drift = abs(alloc.current_weight - target_weight)
            max_drift = max(max_drift, drift)
        
        if max_drift > threshold * 2:
            return True, 0.8, max_drift
        elif max_drift > threshold:
            return True, 0.5, max_drift
        
        return False, 0.0, max_drift
    
    def _check_regime_trigger(self, current_regime: Optional[str]) -> bool:
        """Check if regime has changed."""
        if current_regime is None or self.last_regime is None:
            return False
        
        return current_regime != self.last_regime
    
    def _check_drawdown_trigger(self, state: DrawdownState) -> tuple:
        """Check if drawdown requires rebalance."""
        if state == DrawdownState.EMERGENCY:
            return True, 1.0
        elif state == DrawdownState.CRITICAL:
            return True, 0.9
        elif state == DrawdownState.WARNING:
            return True, 0.6
        elif state == DrawdownState.CAUTION:
            return True, 0.3
        
        return False, 0.0
    
    def _calculate_deltas(
        self,
        current: Dict[str, StrategyAllocation],
        target: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate allocation changes needed."""
        deltas = {}
        
        for sid, alloc in current.items():
            target_weight = target.get(sid, 0)
            deltas[sid] = target_weight - alloc.current_weight
        
        # Add any targets not in current
        for sid, weight in target.items():
            if sid not in deltas:
                deltas[sid] = weight
        
        return deltas
    
    def execute_rebalance(
        self,
        recommendation: RebalanceRecommendation
    ) -> Dict:
        """
        Execute rebalance (returns execution plan).
        
        In real system, this would trigger actual trades.
        """
        if recommendation.action == RebalanceAction.NO_ACTION:
            return {
                "executed": False,
                "reason": "No rebalance needed"
            }
        
        # Generate execution plan
        trades = []
        for sid, delta in recommendation.allocations_delta.items():
            if abs(delta) > 0.01:  # Ignore tiny changes
                trades.append({
                    "strategy_id": sid,
                    "action": "INCREASE" if delta > 0 else "DECREASE",
                    "change": round(abs(delta), 4),
                    "priority": "HIGH" if abs(delta) > 0.1 else "NORMAL"
                })
        
        # Sort by priority
        trades.sort(key=lambda x: (0 if x["priority"] == "HIGH" else 1, -abs(x["change"])))
        
        return {
            "executed": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": recommendation.action.value,
            "trades": trades,
            "estimated_turnover": round(recommendation.estimated_turnover, 4),
            "estimated_cost_bps": round(recommendation.estimated_cost_bps, 2)
        }
    
    def _add_to_history(self, result: RebalanceRecommendation):
        """Add result to history."""
        self.history.append(result)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_rebalance_summary(self) -> Dict:
        """Get summary of rebalancing activity."""
        if not self.history:
            return {"summary": "NO_HISTORY"}
        
        recent = self.history[-1]
        
        # Count actions in history
        action_counts = {}
        for r in self.history:
            a = r.action.value
            action_counts[a] = action_counts.get(a, 0) + 1
        
        return {
            "current_action": recent.action.value,
            "urgency": round(recent.urgency, 3),
            "trigger_reason": recent.trigger_reason,
            "last_rebalance": self.last_rebalance.isoformat() if self.last_rebalance else None,
            "action_history": action_counts,
            "total_evaluations": len(self.history)
        }
