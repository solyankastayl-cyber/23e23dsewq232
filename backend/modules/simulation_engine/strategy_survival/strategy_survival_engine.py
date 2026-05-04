"""
PHASE 23.3 — Strategy Survival Engine
=====================================
Calculates robustness score and survival state for strategies.

Robustness formula:
robustness_score = (0.40*stable + 0.25*stressed - 0.20*fragile - 0.35*broken) / total
Normalized to [0, 1]
"""

from typing import Dict, Any, Optional, List

from .strategy_survival_types import (
    StrategySurvivalStateEnum,
    StrategyAction,
    ROBUSTNESS_THRESHOLDS,
    ROBUSTNESS_MODIFIERS,
    ROBUSTNESS_WEIGHTS,
)


class StrategySurvivalEngine:
    """
    Calculates strategy robustness and survival state.
    """
    
    def __init__(self):
        self.thresholds = ROBUSTNESS_THRESHOLDS
        self.modifiers = ROBUSTNESS_MODIFIERS
        self.weights = ROBUSTNESS_WEIGHTS
    
    def calculate_robustness_score(
        self,
        stable_count: int,
        stressed_count: int,
        fragile_count: int,
        broken_count: int,
    ) -> float:
        """
        Calculate robustness score.
        
        Formula:
        robustness_score = (0.40*stable + 0.25*stressed - 0.20*fragile - 0.35*broken) / total
        Then normalized to [0, 1]
        
        Args:
            stable_count: Number of STABLE scenarios
            stressed_count: Number of STRESSED scenarios
            fragile_count: Number of FRAGILE scenarios
            broken_count: Number of BROKEN scenarios
            
        Returns:
            Robustness score (0-1)
        """
        total = stable_count + stressed_count + fragile_count + broken_count
        
        if total == 0:
            return 0.5  # Neutral if no data
        
        # Calculate ratios
        stable_ratio = stable_count / total
        stressed_ratio = stressed_count / total
        fragile_ratio = fragile_count / total
        broken_ratio = broken_count / total
        
        # Apply weights
        raw_score = (
            self.weights["stable"] * stable_ratio +
            self.weights["stressed"] * stressed_ratio +
            self.weights["fragile"] * fragile_ratio +
            self.weights["broken"] * broken_ratio
        )
        
        # Normalize from [-0.35, 0.65] to [0, 1]
        # Min possible: all broken = -0.35
        # Max possible: all stable = 0.40
        min_score = -0.35
        max_score = 0.40
        
        normalized = (raw_score - min_score) / (max_score - min_score)
        
        return max(0.0, min(1.0, normalized))
    
    def get_survival_state(self, robustness_score: float) -> StrategySurvivalStateEnum:
        """
        Determine survival state from robustness score.
        """
        if robustness_score >= self.thresholds[StrategySurvivalStateEnum.ROBUST]:
            return StrategySurvivalStateEnum.ROBUST
        elif robustness_score >= self.thresholds[StrategySurvivalStateEnum.STABLE]:
            return StrategySurvivalStateEnum.STABLE
        elif robustness_score >= self.thresholds[StrategySurvivalStateEnum.FRAGILE]:
            return StrategySurvivalStateEnum.FRAGILE
        else:
            return StrategySurvivalStateEnum.BROKEN
    
    def get_recommended_action(self, state: StrategySurvivalStateEnum) -> StrategyAction:
        """
        Get recommended action from survival state.
        """
        action_map = {
            StrategySurvivalStateEnum.ROBUST: StrategyAction.KEEP_ACTIVE,
            StrategySurvivalStateEnum.STABLE: StrategyAction.REDUCE,
            StrategySurvivalStateEnum.FRAGILE: StrategyAction.SHADOW,
            StrategySurvivalStateEnum.BROKEN: StrategyAction.DISABLE,
        }
        return action_map.get(state, StrategyAction.REDUCE)
    
    def get_modifiers(self, state: StrategySurvivalStateEnum) -> Dict[str, float]:
        """
        Get confidence and capital modifiers for survival state.
        """
        return self.modifiers.get(state, self.modifiers[StrategySurvivalStateEnum.STABLE])
    
    def build_reason(
        self,
        strategy_name: str,
        state: StrategySurvivalStateEnum,
        stable_count: int,
        broken_count: int,
        worst_scenario: str,
        by_scenario_type: Dict[str, Dict[str, int]],
    ) -> str:
        """
        Build explanation reason.
        """
        strategy_lower = strategy_name.lower().replace("_", " ")
        
        if state == StrategySurvivalStateEnum.ROBUST:
            return f"{strategy_lower} shows strong resilience across {stable_count} stable scenarios"
        
        elif state == StrategySurvivalStateEnum.STABLE:
            return f"{strategy_lower} stable with moderate stress exposure"
        
        elif state == StrategySurvivalStateEnum.FRAGILE:
            # Find problematic scenario types
            problem_types = []
            for s_type, counts in by_scenario_type.items():
                if counts.get("broken", 0) + counts.get("fragile", 0) > 1:
                    problem_types.append(s_type.lower().replace("_", " "))
            
            if problem_types:
                return f"{strategy_lower} fragile under {' and '.join(problem_types[:2])} conditions"
            return f"{strategy_lower} shows fragility in multiple scenarios"
        
        else:  # BROKEN
            return f"{strategy_lower} repeatedly breaks under stress, worst: {worst_scenario}"
    
    def analyze_strategy_vulnerabilities(
        self,
        by_scenario_type: Dict[str, Dict[str, int]],
    ) -> Dict[str, float]:
        """
        Analyze which scenario types the strategy is most vulnerable to.
        """
        vulnerabilities = {}
        
        for s_type, counts in by_scenario_type.items():
            total = sum(counts.values())
            if total == 0:
                continue
            
            # Calculate vulnerability score for this type
            vulnerability = (
                counts.get("broken", 0) * 1.0 +
                counts.get("fragile", 0) * 0.6 +
                counts.get("stressed", 0) * 0.3
            ) / total
            
            vulnerabilities[s_type] = round(vulnerability, 4)
        
        return vulnerabilities
