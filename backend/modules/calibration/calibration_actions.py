"""
PHASE 2.9.5 — Calibration Actions Engine

Generates actionable recommendations:
- disable_asset: Remove from universe
- reduce_risk: Lower position size
- increase_threshold: Raise confidence requirement
- cut_cluster_exposure: Reduce cluster weight
- isolate_strategy: Disable specific strategy
- keep: No change needed
- increase_allocation: Can increase risk

Not just analytics — actual decision layer.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """Types of calibration actions."""
    DISABLE = "disable"
    REDUCE_RISK = "reduce_risk"
    INCREASE_THRESHOLD = "increase_threshold"
    CUT_CLUSTER_EXPOSURE = "cut_cluster_exposure"
    ISOLATE_STRATEGY = "isolate_strategy"
    KEEP = "keep"
    INCREASE_ALLOCATION = "increase_allocation"


@dataclass
class CalibrationAction:
    """Single calibration action."""
    key: str  # asset/cluster/strategy identifier
    action: ActionType
    severity: str  # "critical", "warning", "suggestion"
    reason: str
    confidence: float  # How confident in this action
    parameters: Optional[Dict] = None  # Additional parameters for the action


class CalibrationActions:
    """
    Generates actionable calibration recommendations.
    
    Combines inputs from:
    - Edge classification
    - Degradation detection
    - Failure analysis
    
    Outputs concrete actions the system should take.
    """
    
    def generate(
        self,
        edge_map: Dict[str, Dict],
        degradation_map: Dict[str, Dict],
        failure_map: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Generate calibration actions.
        
        Args:
            edge_map: {key: {edge_class, confidence, ...}} from EdgeClassifier
            degradation_map: {key: {degrading, severity, ...}} from DegradationEngine
            failure_map: Optional failure analysis from FailureMap
        
        Returns:
            List of action dicts: [{key, action, severity, reason, confidence, parameters}]
        """
        actions = []
        
        # Process each key
        all_keys = set(edge_map.keys()) | set(degradation_map.keys())
        
        for key in all_keys:
            edge = edge_map.get(key, {})
            degradation = degradation_map.get(key, {})
            
            action = self._determine_action(key, edge, degradation)
            
            if action:
                actions.append({
                    "key": action.key,
                    "action": action.action.value,
                    "severity": action.severity,
                    "reason": action.reason,
                    "confidence": round(action.confidence, 4),
                    "parameters": action.parameters or {}
                })
        
        # Add failure-based actions if available
        if failure_map:
            failure_actions = self._generate_failure_actions(failure_map)
            actions.extend(failure_actions)
        
        # Sort by severity
        severity_order = {"critical": 0, "warning": 1, "suggestion": 2}
        actions.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        return actions
    
    def _determine_action(
        self,
        key: str,
        edge: Dict,
        degradation: Dict
    ) -> Optional[CalibrationAction]:
        """Determine action for a single key."""
        edge_class = edge.get("edge_class", "unknown")
        is_degrading = degradation.get("degrading", False)
        deg_severity = degradation.get("severity", "none")
        
        # Priority 1: No edge -> DISABLE
        if edge_class == "no_edge":
            return CalibrationAction(
                key=key,
                action=ActionType.DISABLE,
                severity="critical",
                reason=f"No edge detected: {', '.join(edge.get('reasons', []))}",
                confidence=edge.get("confidence", 0.7)
            )
        
        # Priority 2: Severe degradation -> REDUCE_RISK or DISABLE
        if deg_severity == "severe":
            if edge_class in ["weak", "unstable"]:
                return CalibrationAction(
                    key=key,
                    action=ActionType.DISABLE,
                    severity="critical",
                    reason=f"Severe degradation with {edge_class} edge",
                    confidence=0.8
                )
            else:
                return CalibrationAction(
                    key=key,
                    action=ActionType.REDUCE_RISK,
                    severity="warning",
                    reason=f"Severe degradation detected in {degradation.get('metric', 'performance')}",
                    confidence=0.75,
                    parameters={"risk_reduction": 0.5}
                )
        
        # Priority 3: Unstable edge -> REDUCE_RISK
        if edge_class == "unstable":
            return CalibrationAction(
                key=key,
                action=ActionType.REDUCE_RISK,
                severity="warning",
                reason="Edge exists but unstable; reduce exposure",
                confidence=0.7,
                parameters={"risk_reduction": 0.3}
            )
        
        # Priority 4: Moderate degradation -> INCREASE_THRESHOLD
        if deg_severity == "moderate":
            return CalibrationAction(
                key=key,
                action=ActionType.INCREASE_THRESHOLD,
                severity="warning",
                reason=f"Moderate degradation in {degradation.get('metric', 'performance')}",
                confidence=0.65,
                parameters={"threshold_increase": 0.1}
            )
        
        # Priority 5: Weak edge + mild degradation -> watch/threshold
        if edge_class == "weak" and is_degrading:
            return CalibrationAction(
                key=key,
                action=ActionType.INCREASE_THRESHOLD,
                severity="suggestion",
                reason="Weak edge showing mild degradation",
                confidence=0.55,
                parameters={"threshold_increase": 0.05}
            )
        
        # Priority 6: Strong edge, no degradation -> KEEP or INCREASE
        if edge_class == "strong" and not is_degrading:
            return CalibrationAction(
                key=key,
                action=ActionType.INCREASE_ALLOCATION,
                severity="suggestion",
                reason="Strong stable edge; can increase allocation",
                confidence=edge.get("confidence", 0.8),
                parameters={"allocation_increase": 0.2}
            )
        
        # Default: KEEP
        if edge_class in ["strong", "weak"]:
            return CalibrationAction(
                key=key,
                action=ActionType.KEEP,
                severity="suggestion",
                reason="Performance within acceptable range",
                confidence=0.5
            )
        
        return None
    
    def _generate_failure_actions(self, failure_map: Dict) -> List[Dict]:
        """Generate actions based on failure analysis."""
        actions = []
        
        summary = failure_map.get("summary", {})
        dominant_type = summary.get("dominant_failure_type")
        dominant_rate = summary.get("dominant_failure_rate", 0)
        
        if dominant_rate > 0.3:
            action_mapping = {
                "wrong_early": {
                    "action": "adjust_stops",
                    "reason": f"High wrong_early rate ({dominant_rate:.1%}); widen stops",
                    "parameters": {"stop_adjustment": 1.2}
                },
                "late_entry": {
                    "action": "improve_entry",
                    "reason": f"High late_entry rate ({dominant_rate:.1%}); use limit orders",
                    "parameters": {"entry_type": "limit"}
                },
                "low_confidence": {
                    "action": "raise_threshold",
                    "reason": f"High low_confidence failures ({dominant_rate:.1%})",
                    "parameters": {"min_confidence": 0.6}
                },
                "regime_mismatch": {
                    "action": "add_regime_filter",
                    "reason": f"Regime mismatch causing losses ({dominant_rate:.1%})",
                    "parameters": {"require_regime_stability": True}
                }
            }
            
            if dominant_type in action_mapping:
                mapping = action_mapping[dominant_type]
                actions.append({
                    "key": "global",
                    "action": mapping["action"],
                    "severity": "warning" if dominant_rate > 0.4 else "suggestion",
                    "reason": mapping["reason"],
                    "confidence": 0.7,
                    "parameters": mapping["parameters"]
                })
        
        # Per-symbol high failure actions
        by_symbol = failure_map.get("by_symbol", {})
        for symbol, data in by_symbol.items():
            if data.get("failure_rate", 0) > 0.6:
                actions.append({
                    "key": symbol,
                    "action": "disable",
                    "severity": "critical",
                    "reason": f"Symbol {symbol} has {data['failure_rate']:.1%} failure rate",
                    "confidence": 0.8,
                    "parameters": {}
                })
        
        return actions
    
    def summarize(self, actions: List[Dict]) -> Dict:
        """Summarize generated actions."""
        action_counts = {}
        severity_counts = {"critical": 0, "warning": 0, "suggestion": 0}
        
        for a in actions:
            action_type = a.get("action", "unknown")
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
            
            severity = a.get("severity", "suggestion")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        critical_actions = [a for a in actions if a.get("severity") == "critical"]
        
        return {
            "total_actions": len(actions),
            "by_action_type": action_counts,
            "by_severity": severity_counts,
            "critical_actions": critical_actions,
            "immediate_attention_required": len(critical_actions) > 0,
            "recommendation": self._get_overall_recommendation(actions)
        }
    
    def _get_overall_recommendation(self, actions: List[Dict]) -> str:
        """Get overall system recommendation."""
        critical = sum(1 for a in actions if a.get("severity") == "critical")
        warnings = sum(1 for a in actions if a.get("severity") == "warning")
        disables = sum(1 for a in actions if a.get("action") == "disable")
        
        if critical > 5:
            return "CRITICAL: Multiple severe issues detected. Consider pausing trading."
        elif disables > 10:
            return "WARNING: Many assets need to be disabled. Universe needs cleanup."
        elif critical > 0:
            return f"ATTENTION: {critical} critical issue(s) require immediate action."
        elif warnings > 5:
            return "CAUTION: Multiple warnings. Review risk parameters."
        else:
            return "OK: System performing within acceptable parameters."
    
    def filter_by_severity(self, actions: List[Dict], severity: str) -> List[Dict]:
        """Filter actions by severity level."""
        return [a for a in actions if a.get("severity") == severity]
    
    def filter_by_action(self, actions: List[Dict], action_type: str) -> List[Dict]:
        """Filter actions by action type."""
        return [a for a in actions if a.get("action") == action_type]
