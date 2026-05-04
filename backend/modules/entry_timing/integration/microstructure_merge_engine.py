"""
PHASE 4.8.1 — Microstructure Merge Engine

Merges Entry Timing Stack decision with Microstructure decision
into one final unified entry decision.

Rules:
- Micro hard block overrides timing GO
- Timing SKIP/WAIT is preserved
- Micro weakness can downgrade GO → GO_REDUCED
- Perfect alignment = GO_FULL
"""

from typing import Dict


class MicrostructureMergeEngine:
    """
    Merges timing-layer and micro-layer into one final decision.
    """

    def merge(self, timing_result: dict, micro_result: dict) -> dict:
        """
        Merge timing decision with microstructure evaluation.

        Args:
            timing_result: From EntryGovernor {final_entry_decision, decision_reason}
            micro_result: From MicrostructureDecisionEngine {entry_permission, decision, microstructure_score, ...}

        Returns:
            Merged decision with reason
        """
        timing_decision = timing_result.get("final_entry_decision", "SKIP")
        micro_permission = micro_result.get("entry_permission", False)
        micro_decision = micro_result.get("decision", "WAIT_MICRO_CONFIRMATION")
        micro_score = micro_result.get("microstructure_score", 0.0)

        # Hard micro block — override any timing GO
        if not micro_permission:
            if micro_decision in ["WAIT_SWEEP", "WAIT_LIQUIDITY_CLEAR", "WAIT_MICRO_CONFIRMATION"]:
                return {
                    "merged_decision": "WAIT_MICROSTRUCTURE",
                    "reason": micro_decision,
                }
            return {
                "merged_decision": "SKIP",
                "reason": micro_decision,
            }

        # Timing already says wait/skip — preserve
        if timing_decision in ["WAIT", "SKIP"]:
            return {
                "merged_decision": timing_decision,
                "reason": timing_result.get("decision_reason", "timing_block"),
            }

        # Timing GO + weak micro → downgrade
        if timing_decision == "GO" and micro_score < 0.55:
            return {
                "merged_decision": "GO_REDUCED",
                "reason": "microstructure_weak",
            }

        if timing_decision == "GO_REDUCED" and micro_score < 0.55:
            return {
                "merged_decision": "WAIT_MICROSTRUCTURE",
                "reason": "timing_reduced_and_micro_weak",
            }

        # Best case: timing GO + strong micro
        if timing_decision == "GO" and micro_score >= 0.75:
            return {
                "merged_decision": "GO_FULL",
                "reason": "timing_and_micro_aligned",
            }

        # Timing GO/GO_REDUCED + decent micro
        if timing_decision in ["GO", "GO_REDUCED"]:
            return {
                "merged_decision": "GO_REDUCED",
                "reason": "timing_ok_micro_ok",
            }

        # Fallback
        return {
            "merged_decision": "WAIT",
            "reason": "fallback_wait",
        }
