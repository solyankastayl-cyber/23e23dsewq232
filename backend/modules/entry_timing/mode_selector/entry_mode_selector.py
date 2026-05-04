"""
PHASE 4.2 — Entry Mode Selector

Main selector that determines entry mode based on context and diagnostics.
Integrates with Phase 4.1 to learn from past wrong early mistakes.
"""

from typing import Dict, Optional, List
from datetime import datetime, timezone

from .entry_mode_types import EntryMode, MODE_DESCRIPTIONS, MODE_RISK_LEVELS
from .entry_mode_rules import EntryModeRules, RuleResult


class EntryModeSelector:
    """
    Selects the appropriate entry mode for a trade setup.
    
    Key principle: Does NOT change the direction or signal.
    Only controls TIMING of entry.
    
    Flow:
    signal → entry_decision → trade
    """
    
    def __init__(self):
        self.rules = EntryModeRules()
        self._last_diagnostics_update: Optional[datetime] = None
    
    def select(self, data: Dict) -> Dict:
        """
        Select entry mode for a trade.
        
        Args:
            data: {
                "prediction": {"direction": "LONG", "confidence": 0.78, ...},
                "setup": {"entry": 62410, "type": "BREAKOUT", ...},
                "context": {"extension_atr": 1.6, "ltf_alignment": "aligned", ...},
                "diagnostics": {"top_wrong_early_reasons": [...]}
            }
        
        Returns:
            {
                "entry_mode": "WAIT_PULLBACK",
                "reason": "extension_too_high",
                "confidence": 0.85,
                "allows_entry": True,
                "risk_level": "low",
                "matched_rules": [...]
            }
        """
        prediction = data.get("prediction", {})
        setup = data.get("setup", {})
        context = data.get("context", {})
        diagnostics = data.get("diagnostics", {})
        
        # Evaluate all rules
        matched_rules = self.rules.evaluate_all(
            context=context,
            prediction=prediction,
            setup=setup,
            diagnostics=diagnostics
        )
        
        # Select best mode (highest priority match or default)
        if matched_rules:
            best = matched_rules[0]
            selected_mode = best.mode
            reason = best.reason
            confidence = best.confidence
        else:
            # Default: ENTER_NOW
            selected_mode = EntryMode.ENTER_NOW
            reason = "default_no_rules_triggered"
            confidence = 0.60
        
        # Build result
        mode_value = selected_mode.value
        
        return {
            "entry_mode": mode_value,
            "reason": reason,
            "confidence": confidence,
            "allows_entry": mode_value not in ["SKIP_LATE_ENTRY", "SKIP_CONFLICTED"],
            "risk_level": MODE_RISK_LEVELS.get(mode_value, "unknown"),
            "description": MODE_DESCRIPTIONS.get(mode_value, ""),
            "matched_rules": [
                {
                    "mode": r.mode.value if r.mode else None,
                    "reason": r.reason,
                    "confidence": r.confidence,
                    "priority": r.priority
                }
                for r in matched_rules[:5]  # Top 5 matches
            ],
            "input_summary": {
                "direction": prediction.get("direction"),
                "confidence": prediction.get("confidence"),
                "setup_type": setup.get("type"),
                "extension_atr": context.get("extension_atr"),
                "ltf_alignment": context.get("ltf_alignment"),
                "volatility_state": context.get("volatility_state")
            },
            "selected_at": datetime.now(timezone.utc).isoformat()
        }
    
    def select_batch(self, data_list: List[Dict]) -> List[Dict]:
        """Select modes for multiple trades."""
        return [self.select(data) for data in data_list]
    
    def update_from_diagnostics(self, diagnostics_summary: Dict):
        """
        Update rule thresholds based on diagnostic patterns.
        
        This enables self-correction based on actual errors.
        """
        self.rules.update_thresholds_from_diagnostics(diagnostics_summary)
        self._last_diagnostics_update = datetime.now(timezone.utc)
    
    def get_mode_for_reason(self, wrong_early_reason: str) -> str:
        """
        Get recommended mode to prevent a specific wrong early reason.
        
        Useful for understanding what mode would have prevented an error.
        """
        reason_to_mode = {
            "breakout_not_confirmed": "ENTER_ON_CLOSE",
            "trigger_touched_but_not_accepted": "ENTER_ON_CLOSE",
            "retest_not_completed": "WAIT_RETEST",
            "entered_on_extension": "WAIT_PULLBACK",
            "reversal_without_exhaustion": "WAIT_CONFIRMATION",
            "continuation_before_reset": "WAIT_PULLBACK",
            "ltf_conflict": "SKIP_CONFLICTED",
            "volatility_hostile": "WAIT_CONFIRMATION",
            "structure_not_accepted": "WAIT_RETEST",
            "entered_before_close_confirmation": "ENTER_ON_CLOSE",
            "liquidity_sweep_not_resolved": "WAIT_CONFIRMATION",
            "mean_reversion_too_early": "WAIT_CONFIRMATION",
            "unknown": "ENTER_ON_CLOSE"  # Default to safer mode
        }
        
        return reason_to_mode.get(wrong_early_reason, "ENTER_NOW")
    
    def simulate_selection(self, context_scenario: str) -> Dict:
        """
        Simulate mode selection for common scenarios.
        
        Useful for testing and demonstration.
        """
        scenarios = {
            "high_extension": {
                "prediction": {"direction": "LONG", "confidence": 0.75, "tradeable": True},
                "setup": {"entry": 62410, "type": "BREAKOUT"},
                "context": {"extension_atr": 1.8, "ltf_alignment": "aligned", "volatility_state": "normal"},
                "diagnostics": {"top_wrong_early_reasons": ["entered_on_extension"]}
            },
            "ltf_conflict": {
                "prediction": {"direction": "LONG", "confidence": 0.80, "tradeable": True},
                "setup": {"entry": 62410, "type": "BREAKOUT"},
                "context": {"extension_atr": 0.5, "ltf_alignment": "conflict", "volatility_state": "normal"},
                "diagnostics": {"top_wrong_early_reasons": ["ltf_conflict"]}
            },
            "breakout_no_close": {
                "prediction": {"direction": "LONG", "confidence": 0.78, "tradeable": True},
                "setup": {"entry": 62410, "type": "BREAKOUT"},
                "context": {"extension_atr": 0.8, "ltf_alignment": "aligned", "close_confirmation": False},
                "diagnostics": {"top_wrong_early_reasons": ["breakout_not_confirmed"]}
            },
            "strong_setup": {
                "prediction": {"direction": "LONG", "confidence": 0.85, "tradeable": True},
                "setup": {"entry": 62410, "type": "BREAKOUT"},
                "context": {
                    "extension_atr": 0.5, "ltf_alignment": "aligned", 
                    "close_confirmation": True, "breakout_strength": 0.8,
                    "volatility_state": "normal"
                },
                "diagnostics": {"top_wrong_early_reasons": []}
            },
            "hostile_volatility": {
                "prediction": {"direction": "LONG", "confidence": 0.75, "tradeable": True},
                "setup": {"entry": 62410, "type": "BREAKOUT"},
                "context": {"extension_atr": 0.6, "ltf_alignment": "aligned", "volatility_state": "extreme"},
                "diagnostics": {"top_wrong_early_reasons": ["volatility_hostile"]}
            }
        }
        
        scenario_data = scenarios.get(context_scenario)
        if not scenario_data:
            return {"error": f"Unknown scenario: {context_scenario}", "available": list(scenarios.keys())}
        
        result = self.select(scenario_data)
        result["scenario"] = context_scenario
        result["scenario_data"] = scenario_data
        
        return result
