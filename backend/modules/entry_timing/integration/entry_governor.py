"""
PHASE 4.5 + 4.8.1 — Entry Governor

Makes the final entry decision with MTF + Microstructure awareness.
Decisions: GO / GO_FULL / GO_REDUCED / WAIT / WAIT_MICROSTRUCTURE / SKIP
"""

from typing import Dict

from .microstructure_merge_engine import MicrostructureMergeEngine


class EntryGovernor:
    """
    Makes final entry decision based on all Entry Timing Stack components,
    including MTF and Microstructure layers.
    """

    def __init__(self):
        self.micro_merge = MicrostructureMergeEngine()

    def evaluate(self, data: Dict) -> Dict:
        """
        Evaluate and return final entry decision.

        Pipeline:
        1. Base timing decision (prediction + mode + strategy + quality + MTF)
        2. Merge with microstructure (if provided)
        """
        prediction = data.get("prediction", {})
        mode = data.get("entry_mode", {})
        strategy = data.get("execution_strategy", {})
        quality = data.get("entry_quality", {})
        mtf = data.get("mtf", {})
        micro = data.get("microstructure", {})

        # Step 1: Base timing decision
        timing_result = self._evaluate_timing(prediction, mode, strategy, quality, mtf)

        # Step 2: Merge with microstructure (if micro data exists)
        if micro:
            merged = self.micro_merge.merge(timing_result, micro)
            return {
                "final_entry_decision": merged["merged_decision"],
                "reason": merged["reason"],
                "timing_decision": timing_result["final_entry_decision"],
                "timing_reason": timing_result["reason"],
                "micro_applied": True,
            }

        # No microstructure data — use timing only
        return {
            "final_entry_decision": timing_result["final_entry_decision"],
            "reason": timing_result["reason"],
            "timing_decision": timing_result["final_entry_decision"],
            "timing_reason": timing_result["reason"],
            "micro_applied": False,
        }

    def _evaluate_timing(self, prediction, mode, strategy, quality, mtf):
        """Evaluate base timing decision from prediction, mode, strategy, quality, MTF."""
        if not prediction.get("tradeable", True):
            return self._result("SKIP", "prediction_not_tradeable")

        if not strategy.get("valid", True):
            return self._result("SKIP", "invalid_execution_strategy")

        # MTF blocks
        mtf_decision = mtf.get("decision", "")
        if mtf_decision in ["SKIP_HTF_CONFLICT"]:
            return self._result("SKIP", "htf_conflict")

        if mtf_decision in ["WAIT_LTF_CONFIRMATION"]:
            return self._result("WAIT", "ltf_confirmation_pending")

        # Entry mode
        entry_mode = mode.get("entry_mode") if isinstance(mode, dict) else mode

        if entry_mode in ["SKIP_LATE_ENTRY", "SKIP_CONFLICTED"]:
            return self._result("SKIP", entry_mode.lower())

        # Quality score
        score = quality.get("entry_quality_score", 0.5)
        grade = quality.get("entry_quality_grade", "C")

        # Wait modes
        if entry_mode in ["WAIT_RETEST", "WAIT_PULLBACK", "WAIT_CONFIRMATION", "ENTER_ON_CLOSE"]:
            if score < 0.45:
                return self._result("SKIP", "wait_mode_but_low_quality")
            return self._result("WAIT", f"wait_{entry_mode.lower()}")

        # GO decisions with MTF boost
        if score >= 0.80 and mtf_decision == "ENTER_AGGRESSIVE":
            return self._result("GO", "high_entry_quality_and_mtf_aligned")

        if score >= 0.80 or grade == "A":
            return self._result("GO", "high_entry_quality")

        if score >= 0.55 or grade in ["B", "C"]:
            return self._result("GO_REDUCED", "medium_entry_quality")

        return self._result("SKIP", "low_entry_quality")

    def _result(self, decision: str, reason: str) -> Dict:
        return {
            "final_entry_decision": decision,
            "reason": reason,
            "decision_reason": reason,
        }
