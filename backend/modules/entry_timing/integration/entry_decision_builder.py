"""
PHASE 4.5 + 4.8.1 — Entry Decision Builder

Builds the complete decision output with all context,
including MTF and Microstructure layers.
"""

from typing import Dict

from .entry_timing_types import DECISION_DESCRIPTIONS, DECISION_SIZE_MODIFIERS, DECISION_ALLOWS_ENTRY


class EntryDecisionBuilder:
    """
    Builds user-facing and system-facing decision output.
    """

    def build(self, data: Dict, governor_result: Dict) -> Dict:
        """
        Build complete decision output with timing + micro context.
        """
        prediction = data.get("prediction", {})
        setup = data.get("setup", {})
        mode = data.get("entry_mode", {})
        strategy = data.get("execution_strategy", {})
        quality = data.get("entry_quality", {})
        mtf = data.get("mtf", {})
        micro = data.get("microstructure", {})

        decision = governor_result["final_entry_decision"]

        result = {
            # Final decision
            "final_entry_decision": decision,
            "decision_reason": governor_result["reason"],
            "decision_description": DECISION_DESCRIPTIONS.get(decision, ""),
            "allows_entry": DECISION_ALLOWS_ENTRY.get(decision, False),
            "size_modifier": DECISION_SIZE_MODIFIERS.get(decision, 0),

            # Prediction context
            "direction": prediction.get("direction"),
            "prediction_confidence": prediction.get("confidence"),

            # Entry mode
            "entry_mode": mode.get("entry_mode") if isinstance(mode, dict) else mode,
            "entry_mode_reason": mode.get("reason") if isinstance(mode, dict) else None,

            # Execution strategy
            "execution_strategy": strategy.get("execution_strategy") if isinstance(strategy, dict) else strategy,
            "execution_strategy_reason": strategy.get("reason") if isinstance(strategy, dict) else None,
            "execution_legs": strategy.get("legs", []) if isinstance(strategy, dict) else [],

            # Entry quality
            "entry_quality_score": quality.get("entry_quality_score"),
            "entry_quality_grade": quality.get("entry_quality_grade"),
            "entry_quality_reasons": quality.get("reasons", []),

            # MTF context
            "mtf_decision": mtf.get("decision"),
            "mtf_confidence": mtf.get("confidence"),

            # Microstructure context
            "micro_applied": governor_result.get("micro_applied", False),
            "micro_decision": micro.get("decision"),
            "microstructure_score": micro.get("microstructure_score"),
            "liquidity_risk": micro.get("liquidity_risk"),
            "sweep_risk": micro.get("sweep_risk"),
            "absorption_detected": micro.get("absorption_detected"),
            "imbalance": micro.get("imbalance"),

            # Timing decision (before micro merge)
            "timing_decision": governor_result.get("timing_decision"),
            "timing_reason": governor_result.get("timing_reason"),

            # Setup
            "entry": setup.get("entry"),
            "stop_loss": setup.get("stop_loss"),
            "target": setup.get("target"),
            "rr": setup.get("rr"),
        }

        return result
