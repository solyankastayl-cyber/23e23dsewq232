"""
Execution Quality Rules
=======================

Phase 3.1: 6 Gates + Verdict logic.

Gates:
  1. match_coverage >= 0.7
  2. execution_quality > -0.001
  3. winrate_paper >= winrate_shadow - 0.05
  4. policy_rejection_rate <= 0.35
  5. cooldown_miss_rate <= 0.20
  6. matched_pairs >= 20

Verdict:
  - AUTO_RUN_READY: All gates pass
  - AUTO_RUN_LIMITED: Quality ok but warnings
  - AUTO_RUN_BLOCKED: Quality negative or coverage weak
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Thresholds (6 Gates)
MIN_MATCH_COVERAGE = 0.7
MIN_EXECUTION_QUALITY = -0.001
MAX_WINRATE_DELTA = -0.05
MAX_POLICY_REJECTION_RATE = 0.35
MAX_COOLDOWN_MISS_RATE = 0.20
MIN_MATCHED_PAIRS = 20


class ExecutionQualityRules:
    """
    Evaluates execution quality and returns verdict.
    
    Verdict states:
      - ready: All gates pass, auto-run can be enabled
      - limited: Quality acceptable but warnings present
      - blocked: Quality issues, auto-run should not be enabled
    """
    
    @staticmethod
    def evaluate_verdict(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate verdict based on metrics.
        
        Args:
            metrics: Execution quality metrics
        
        Returns:
            {
                "state": "ready" | "limited" | "blocked",
                "reason": "...",
                "gates_passed": ["gate1", ...],
                "gates_failed": ["gate2", ...]
            }
        """
        summary = metrics.get("summary", {})
        frictions = metrics.get("frictions", {})
        
        # Extract values
        matched_pairs = summary.get("matched_pairs", 0)
        match_coverage = summary.get("match_coverage", 0)
        execution_quality = summary.get("execution_quality", 0)
        winrate_delta = summary.get("winrate_delta", 0)
        policy_rejection_rate = frictions.get("policy_rejection_rate", 0)
        cooldown_miss_rate = frictions.get("cooldown_miss_rate", 0)
        
        # Evaluate gates
        gates_passed = []
        gates_failed = []
        
        # Gate 1: Coverage
        if match_coverage >= MIN_MATCH_COVERAGE:
            gates_passed.append("gate1_coverage")
        else:
            gates_failed.append(f"gate1_coverage (actual: {match_coverage:.2%})")
        
        # Gate 2: Execution quality
        if execution_quality > MIN_EXECUTION_QUALITY:
            gates_passed.append("gate2_execution_quality")
        else:
            gates_failed.append(f"gate2_execution_quality (actual: {execution_quality:.4f})")
        
        # Gate 3: Winrate delta
        if winrate_delta >= MAX_WINRATE_DELTA:
            gates_passed.append("gate3_winrate")
        else:
            gates_failed.append(f"gate3_winrate (actual: {winrate_delta:.2%})")
        
        # Gate 4: Policy rejection
        if policy_rejection_rate <= MAX_POLICY_REJECTION_RATE:
            gates_passed.append("gate4_policy_rejection")
        else:
            gates_failed.append(f"gate4_policy_rejection (actual: {policy_rejection_rate:.2%})")
        
        # Gate 5: Cooldown miss
        if cooldown_miss_rate <= MAX_COOLDOWN_MISS_RATE:
            gates_passed.append("gate5_cooldown_miss")
        else:
            gates_failed.append(f"gate5_cooldown_miss (actual: {cooldown_miss_rate:.2%})")
        
        # Gate 6: Minimum pairs
        if matched_pairs >= MIN_MATCHED_PAIRS:
            gates_passed.append("gate6_min_pairs")
        else:
            gates_failed.append(f"gate6_min_pairs (actual: {matched_pairs})")
        
        # Determine verdict
        if len(gates_failed) == 0:
            state = "ready"
            reason = "All gates passed, auto-run can be enabled"
        elif len(gates_failed) <= 2 and execution_quality > MIN_EXECUTION_QUALITY:
            state = "limited"
            reason = f"Quality acceptable but warnings: {', '.join(gates_failed)}"
        else:
            state = "blocked"
            reason = f"Quality issues detected: {', '.join(gates_failed)}"
        
        return {
            "state": state,
            "reason": reason,
            "gates_passed": gates_passed,
            "gates_failed": gates_failed
        }
    
    @staticmethod
    def get_thresholds() -> Dict[str, Any]:
        """
        Get all threshold values.
        
        Returns:
            Dictionary of thresholds
        """
        return {
            "min_match_coverage": MIN_MATCH_COVERAGE,
            "min_execution_quality": MIN_EXECUTION_QUALITY,
            "max_winrate_delta": MAX_WINRATE_DELTA,
            "max_policy_rejection_rate": MAX_POLICY_REJECTION_RATE,
            "max_cooldown_miss_rate": MAX_COOLDOWN_MISS_RATE,
            "min_matched_pairs": MIN_MATCHED_PAIRS
        }
