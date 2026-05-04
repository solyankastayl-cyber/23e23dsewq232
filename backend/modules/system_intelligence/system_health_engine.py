"""
PHASE 12.3 - System Health Engine
==================================
Monitors overall system health.

Evaluates:
- Signal quality
- Execution quality
- Portfolio stability
- Risk budget usage
- Edge strength
"""

import random
from typing import Dict, Optional, List
from datetime import datetime, timezone

from .system_types import (
    SystemHealthState, SystemHealthSnapshot, SystemAction,
    DEFAULT_SYSTEM_CONFIG
)


class SystemHealthEngine:
    """
    System Health Monitoring Engine
    
    Continuously monitors all system components
    and provides health assessments.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_SYSTEM_CONFIG
        self.health_history: List[SystemHealthSnapshot] = []
        self.max_history = 100
        self.active_issues: List[str] = []
    
    def analyze_health(
        self,
        signal_metrics: Optional[Dict] = None,
        execution_metrics: Optional[Dict] = None,
        portfolio_metrics: Optional[Dict] = None,
        risk_metrics: Optional[Dict] = None,
        edge_metrics: Optional[Dict] = None
    ) -> SystemHealthSnapshot:
        """
        Analyze overall system health.
        
        Args:
            signal_metrics: Signal quality metrics
            execution_metrics: Execution quality metrics
            portfolio_metrics: Portfolio stability metrics
            risk_metrics: Risk budget usage
            edge_metrics: Edge strength metrics
            
        Returns:
            SystemHealthSnapshot
        """
        now = datetime.now(timezone.utc)
        
        # Calculate component health scores
        signal_quality = self._assess_signal_quality(signal_metrics)
        execution_quality = self._assess_execution_quality(execution_metrics)
        portfolio_stability = self._assess_portfolio_stability(portfolio_metrics)
        risk_budget_usage = self._assess_risk_budget(risk_metrics)
        edge_strength = self._assess_edge_strength(edge_metrics)
        
        # Calculate overall health score
        health_score = (
            signal_quality * 0.20 +
            execution_quality * 0.20 +
            portfolio_stability * 0.25 +
            (1 - risk_budget_usage) * 0.15 +  # Lower risk usage is better
            edge_strength * 0.20
        )
        
        # Identify issues
        issues = self._identify_issues(
            signal_quality, execution_quality, portfolio_stability,
            risk_budget_usage, edge_strength
        )
        critical_issues = sum(1 for i in issues if "CRITICAL" in i)
        
        # Determine health state
        health_state = self._determine_health_state(health_score, critical_issues)
        
        # Recommend action
        action = self._recommend_action(health_state, issues)
        
        snapshot = SystemHealthSnapshot(
            timestamp=now,
            health_state=health_state,
            health_score=health_score,
            signal_quality=signal_quality,
            execution_quality=execution_quality,
            portfolio_stability=portfolio_stability,
            risk_budget_usage=risk_budget_usage,
            edge_strength=edge_strength,
            active_issues=issues,
            critical_issues=critical_issues,
            recommended_action=action
        )
        
        # Update state
        self.active_issues = issues
        self._add_to_history(snapshot)
        
        return snapshot
    
    def _assess_signal_quality(self, metrics: Optional[Dict]) -> float:
        """Assess signal generation quality."""
        if not metrics:
            # Mock assessment
            return 0.7 + random.gauss(0, 0.1)
        
        # In real system: check signal hit rate, false positive rate, etc.
        hit_rate = metrics.get("hit_rate", 0.6)
        confidence_calibration = metrics.get("confidence_calibration", 0.7)
        
        return (hit_rate + confidence_calibration) / 2
    
    def _assess_execution_quality(self, metrics: Optional[Dict]) -> float:
        """Assess execution quality."""
        if not metrics:
            return 0.75 + random.gauss(0, 0.08)
        
        # In real system: check slippage, fill rates, latency
        slippage_score = 1 - min(1, metrics.get("avg_slippage_bps", 5) / 20)
        fill_rate = metrics.get("fill_rate", 0.95)
        
        return (slippage_score + fill_rate) / 2
    
    def _assess_portfolio_stability(self, metrics: Optional[Dict]) -> float:
        """Assess portfolio stability."""
        if not metrics:
            return 0.8 + random.gauss(0, 0.1)
        
        # In real system: check drawdown, volatility vs target, concentration
        drawdown_score = 1 - min(1, metrics.get("current_drawdown", 0.05) / 0.15)
        vol_alignment = 1 - abs(metrics.get("vol_deviation", 0.02)) * 5
        
        return (drawdown_score * 0.6 + vol_alignment * 0.4)
    
    def _assess_risk_budget(self, metrics: Optional[Dict]) -> float:
        """Assess risk budget usage (lower is better health)."""
        if not metrics:
            return 0.6 + random.gauss(0, 0.1)
        
        return min(1.0, metrics.get("risk_budget_used", 0.6))
    
    def _assess_edge_strength(self, metrics: Optional[Dict]) -> float:
        """Assess overall edge strength."""
        if not metrics:
            return 0.65 + random.gauss(0, 0.1)
        
        # In real system: aggregate from edge decay detector
        avg_pf = metrics.get("avg_profit_factor", 1.3)
        healthy_pct = metrics.get("healthy_edges_pct", 0.7)
        
        pf_score = min(1, (avg_pf - 0.9) / 1.1)  # PF 0.9 = 0, PF 2.0 = 1
        
        return (pf_score + healthy_pct) / 2
    
    def _identify_issues(
        self,
        signal: float,
        execution: float,
        portfolio: float,
        risk: float,
        edge: float
    ) -> List[str]:
        """Identify system issues."""
        issues = []
        
        if signal < 0.5:
            issues.append("CRITICAL: Signal quality degraded")
        elif signal < 0.6:
            issues.append("WARNING: Signal quality below threshold")
        
        if execution < 0.5:
            issues.append("CRITICAL: Execution quality degraded")
        elif execution < 0.7:
            issues.append("WARNING: Execution issues detected")
        
        if portfolio < 0.5:
            issues.append("CRITICAL: Portfolio stability compromised")
        elif portfolio < 0.6:
            issues.append("WARNING: Portfolio stability concerns")
        
        if risk > 0.9:
            issues.append("CRITICAL: Risk budget nearly exhausted")
        elif risk > 0.8:
            issues.append("WARNING: High risk budget usage")
        
        if edge < 0.4:
            issues.append("CRITICAL: Multiple edges failing")
        elif edge < 0.5:
            issues.append("WARNING: Edge strength declining")
        
        return issues
    
    def _determine_health_state(
        self,
        score: float,
        critical_count: int
    ) -> SystemHealthState:
        """Determine overall health state."""
        
        # Critical issues override
        if critical_count >= 3:
            return SystemHealthState.EMERGENCY
        if critical_count >= 2:
            return SystemHealthState.CRITICAL
        if critical_count >= 1:
            return SystemHealthState.WARNING
        
        # Score-based
        if score >= self.config["health_optimal_threshold"]:
            return SystemHealthState.OPTIMAL
        if score >= self.config["health_healthy_threshold"]:
            return SystemHealthState.HEALTHY
        if score >= self.config["health_degraded_threshold"]:
            return SystemHealthState.DEGRADED
        if score >= self.config["health_warning_threshold"]:
            return SystemHealthState.WARNING
        
        return SystemHealthState.CRITICAL
    
    def _recommend_action(
        self,
        state: SystemHealthState,
        issues: List[str]
    ) -> SystemAction:
        """Recommend action based on health."""
        
        if state == SystemHealthState.EMERGENCY:
            return SystemAction.EMERGENCY_EXIT
        if state == SystemHealthState.CRITICAL:
            return SystemAction.PAUSE_TRADING
        if state == SystemHealthState.WARNING:
            return SystemAction.REDUCE_RISK
        if state == SystemHealthState.DEGRADED:
            return SystemAction.REDUCE_RISK
        
        return SystemAction.NO_ACTION
    
    def _add_to_history(self, snapshot: SystemHealthSnapshot):
        """Add snapshot to history."""
        self.health_history.append(snapshot)
        if len(self.health_history) > self.max_history:
            self.health_history = self.health_history[-self.max_history:]
    
    def get_health_summary(self) -> Dict:
        """Get health summary."""
        if not self.health_history:
            return {"summary": "NO_HISTORY"}
        
        recent = self.health_history[-1]
        
        # Calculate trend
        if len(self.health_history) >= 5:
            recent_scores = [h.health_score for h in self.health_history[-5:]]
            trend = "IMPROVING" if recent_scores[-1] > recent_scores[0] else "DECLINING" if recent_scores[-1] < recent_scores[0] else "STABLE"
        else:
            trend = "INSUFFICIENT_DATA"
        
        return {
            "health_state": recent.health_state.value,
            "health_score": round(recent.health_score, 3),
            "critical_issues": recent.critical_issues,
            "active_issues": len(recent.active_issues),
            "recommended_action": recent.recommended_action.value,
            "trend": trend
        }
