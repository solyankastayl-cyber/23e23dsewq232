"""
PHASE 23.2 — Stress Grid Engine
===============================
Calculates fragility index and resilience state from scenario results.

Core metrics:
- Fragility Index: Weighted vulnerability score
- System Resilience State: Overall system classification
"""

from typing import Dict, Any, Optional, List

from ..simulation_types import SimulationResult

from .stress_grid_types import (
    ResilienceState,
    ResilienceAction,
    RESILIENCE_THRESHOLDS,
    RESILIENCE_MODIFIERS,
    FRAGILITY_WEIGHTS,
)


class StressGridEngine:
    """
    Calculates stress grid metrics from scenario results.
    """
    
    def __init__(self):
        self.thresholds = RESILIENCE_THRESHOLDS
        self.modifiers = RESILIENCE_MODIFIERS
        self.fragility_weights = FRAGILITY_WEIGHTS
    
    def calculate_fragility_index(
        self,
        stable_count: int,
        stressed_count: int,
        fragile_count: int,
        broken_count: int,
    ) -> float:
        """
        Calculate fragility index.
        
        Formula:
        fragility_index = (
            0.50 * broken_count +
            0.30 * fragile_count +
            0.20 * stressed_count
        ) / total_scenarios
        
        Args:
            stable_count: Number of STABLE scenarios
            stressed_count: Number of STRESSED scenarios
            fragile_count: Number of FRAGILE scenarios
            broken_count: Number of BROKEN scenarios
            
        Returns:
            Fragility index (0-1)
        """
        total = stable_count + stressed_count + fragile_count + broken_count
        
        if total == 0:
            return 0.0
        
        weighted_sum = (
            self.fragility_weights["broken"] * broken_count +
            self.fragility_weights["fragile"] * fragile_count +
            self.fragility_weights["stressed"] * stressed_count +
            self.fragility_weights["stable"] * stable_count
        )
        
        return min(1.0, max(0.0, weighted_sum / total))
    
    def get_resilience_state(self, fragility_index: float) -> ResilienceState:
        """
        Determine resilience state from fragility index.
        """
        if fragility_index < self.thresholds[ResilienceState.STRONG]:
            return ResilienceState.STRONG
        elif fragility_index < self.thresholds[ResilienceState.STABLE]:
            return ResilienceState.STABLE
        elif fragility_index < self.thresholds[ResilienceState.FRAGILE]:
            return ResilienceState.FRAGILE
        else:
            return ResilienceState.CRITICAL
    
    def get_recommended_action(self, state: ResilienceState) -> ResilienceAction:
        """
        Get recommended action from resilience state.
        """
        action_map = {
            ResilienceState.STRONG: ResilienceAction.HOLD,
            ResilienceState.STABLE: ResilienceAction.HEDGE,
            ResilienceState.FRAGILE: ResilienceAction.DELEVER,
            ResilienceState.CRITICAL: ResilienceAction.REDUCE_SYSTEM_RISK,
        }
        return action_map.get(state, ResilienceAction.HOLD)
    
    def get_modifiers(self, state: ResilienceState) -> Dict[str, float]:
        """
        Get confidence and capital modifiers for resilience state.
        """
        return self.modifiers.get(state, self.modifiers[ResilienceState.STABLE])
    
    def build_reason(
        self,
        state: ResilienceState,
        fragility_index: float,
        stable_count: int,
        stressed_count: int,
        fragile_count: int,
        broken_count: int,
        worst_scenario: str,
        by_type_breakdown: Dict[str, Dict[str, int]],
    ) -> str:
        """
        Build explanation reason.
        """
        if state == ResilienceState.STRONG:
            return f"system shows strong resilience across {stable_count + stressed_count} stable/stressed scenarios"
        
        elif state == ResilienceState.STABLE:
            return f"system stable with {stable_count} stable and {stressed_count} stressed scenarios"
        
        elif state == ResilienceState.FRAGILE:
            # Find which types have most fragile/broken
            problem_types = []
            for s_type, counts in by_type_breakdown.items():
                if counts.get("fragile", 0) + counts.get("broken", 0) > 0:
                    problem_types.append(s_type.lower().replace("_", " "))
            
            if problem_types:
                return f"multiple fragile scenarios under {' and '.join(problem_types[:2])} conditions"
            return f"fragility index {fragility_index:.2f} with {fragile_count} fragile and {broken_count} broken scenarios"
        
        else:  # CRITICAL
            return f"critical fragility ({fragility_index:.2f}), {broken_count} broken scenarios, worst: {worst_scenario}"
    
    def analyze_type_vulnerabilities(
        self,
        by_type_breakdown: Dict[str, Dict[str, int]],
    ) -> Dict[str, Any]:
        """
        Analyze which scenario types cause most vulnerability.
        """
        vulnerabilities = {}
        
        for s_type, counts in by_type_breakdown.items():
            total = sum(counts.values())
            if total == 0:
                continue
            
            # Calculate type-specific fragility
            type_fragility = (
                self.fragility_weights["broken"] * counts.get("broken", 0) +
                self.fragility_weights["fragile"] * counts.get("fragile", 0) +
                self.fragility_weights["stressed"] * counts.get("stressed", 0)
            ) / total
            
            vulnerabilities[s_type] = {
                "fragility": round(type_fragility, 4),
                "broken_ratio": round(counts.get("broken", 0) / total, 4),
                "safe_ratio": round((counts.get("stable", 0) + counts.get("stressed", 0)) / total, 4),
            }
        
        return vulnerabilities
