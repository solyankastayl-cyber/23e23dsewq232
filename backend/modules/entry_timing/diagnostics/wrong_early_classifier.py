"""
PHASE 4.1 — Wrong Early Classifier

Core classification logic that determines WHY an entry was early.
Uses rule-based classification with priority ordering.
"""

from typing import Dict, Optional, List, Tuple
from datetime import datetime, timezone

from .wrong_early_taxonomy import WrongEarlyReason, REASON_SEVERITY


class WrongEarlyClassifier:
    """
    Classifies wrong early entries by analyzing context.
    
    Uses hierarchical rule matching with priority:
    1. High-severity structural issues first
    2. Medium-severity timing issues
    3. Low-severity ambiguous cases
    """
    
    def __init__(self):
        # Classification thresholds
        self.extension_threshold_atr = 1.5
        self.high_volatility_threshold = 0.8
        self.extreme_volatility_threshold = 1.2
    
    def classify(self, data: Dict) -> Dict:
        """
        Classify why an entry was early.
        
        Args:
            data: Full trade context including prediction, setup, execution, context
        
        Returns:
            Classification result with reason, confidence, and details
        """
        execution_result = data.get("execution_result", {})
        
        # Not a wrong early case
        if not execution_result.get("wrong_early", False):
            return {
                "wrong_early": False,
                "reason": None,
                "reason_enum": None,
                "confidence": 1.0,
                "details": {},
                "severity": None,
                "classified_at": datetime.now(timezone.utc).isoformat()
            }
        
        ctx = data.get("context", {})
        prediction = data.get("prediction", {})
        setup = data.get("setup", {})
        
        # Try to classify with priority ordering
        reason, confidence, details = self._classify_with_rules(
            ctx=ctx,
            prediction=prediction,
            setup=setup,
            execution_result=execution_result
        )
        
        return {
            "wrong_early": True,
            "reason": reason.value,
            "reason_enum": reason,
            "confidence": confidence,
            "details": details,
            "severity": REASON_SEVERITY.get(reason.value, "low"),
            "classified_at": datetime.now(timezone.utc).isoformat(),
            "symbol": data.get("symbol"),
            "timeframe": data.get("timeframe"),
            "direction": prediction.get("direction"),
            "execution_type": setup.get("execution_type")
        }
    
    def _classify_with_rules(
        self,
        ctx: Dict,
        prediction: Dict,
        setup: Dict,
        execution_result: Dict
    ) -> Tuple[WrongEarlyReason, float, Dict]:
        """
        Apply classification rules in priority order.
        
        Returns: (reason, confidence, details)
        """
        direction = prediction.get("direction", "").upper()
        execution_type = setup.get("execution_type", "").upper()
        
        # === HIGH SEVERITY: Structural Issues ===
        
        # 1. Breakout not confirmed (highest priority for breakout setups)
        if execution_type == "BREAKOUT":
            close_above = ctx.get("close_above_trigger")
            close_below = ctx.get("close_below_trigger")
            
            if direction == "LONG" and close_above is False:
                return (
                    WrongEarlyReason.BREAKOUT_NOT_CONFIRMED,
                    0.95,
                    {"trigger_level": setup.get("entry"), "close_confirmed": False}
                )
            
            if direction == "SHORT" and close_below is False:
                return (
                    WrongEarlyReason.BREAKOUT_NOT_CONFIRMED,
                    0.95,
                    {"trigger_level": setup.get("entry"), "close_confirmed": False}
                )
        
        # 2. Entered on extension (chased price)
        extension_atr = ctx.get("extension_at_entry_atr", 0)
        if extension_atr > self.extension_threshold_atr:
            return (
                WrongEarlyReason.ENTERED_ON_EXTENSION,
                0.90,
                {"extension_atr": extension_atr, "threshold": self.extension_threshold_atr}
            )
        
        # 3. Reversal without exhaustion
        if execution_type == "REVERSAL" or ctx.get("reversal_candidate", False):
            if not ctx.get("exhaustion_confirmed", True):
                return (
                    WrongEarlyReason.REVERSAL_WITHOUT_EXHAUSTION,
                    0.85,
                    {"exhaustion_confirmed": False, "setup_type": "reversal"}
                )
        
        # 4. Volatility hostile
        volatility_state = ctx.get("volatility_state", "normal")
        if volatility_state in ["high", "extreme", "hostile"]:
            vol_value = ctx.get("volatility_value", 0)
            if vol_value > self.extreme_volatility_threshold or volatility_state == "extreme":
                return (
                    WrongEarlyReason.VOLATILITY_HOSTILE,
                    0.80,
                    {"volatility_state": volatility_state, "volatility_value": vol_value}
                )
        
        # 5. Liquidity sweep not resolved
        if ctx.get("liquidity_sweep_active", False) or ctx.get("liquidity_sweep_resolved") is False:
            return (
                WrongEarlyReason.LIQUIDITY_SWEEP_NOT_RESOLVED,
                0.85,
                {"sweep_active": True, "resolved": ctx.get("liquidity_sweep_resolved", False)}
            )
        
        # === MEDIUM SEVERITY: Timing Issues ===
        
        # 6. Retest not completed
        if not ctx.get("retest_completed", True):
            return (
                WrongEarlyReason.RETEST_NOT_COMPLETED,
                0.75,
                {"retest_completed": False, "expected_retest_zone": ctx.get("retest_zone")}
            )
        
        # 7. LTF conflict
        ltf_alignment = ctx.get("ltf_alignment", "aligned")
        if ltf_alignment in ["conflict", "opposing", "divergent"]:
            return (
                WrongEarlyReason.LTF_CONFLICT,
                0.80,
                {"ltf_alignment": ltf_alignment, "ltf_direction": ctx.get("ltf_direction")}
            )
        
        # 8. Structure not accepted
        if ctx.get("structure_acceptance") is False:
            return (
                WrongEarlyReason.STRUCTURE_NOT_ACCEPTED,
                0.70,
                {"structure_accepted": False, "structure_level": ctx.get("structure_level")}
            )
        
        # 9. Continuation before reset
        if execution_type == "CONTINUATION":
            if not ctx.get("pullback_completed", True) or not ctx.get("reset_completed", True):
                return (
                    WrongEarlyReason.CONTINUATION_BEFORE_RESET,
                    0.75,
                    {"pullback_completed": ctx.get("pullback_completed"), "reset_completed": ctx.get("reset_completed")}
                )
        
        # 10. Entered before close confirmation
        if ctx.get("entered_before_close", False) or ctx.get("close_confirmation") is False:
            return (
                WrongEarlyReason.ENTERED_BEFORE_CLOSE_CONFIRMATION,
                0.70,
                {"close_confirmed": False, "entry_candle_open": ctx.get("entry_candle_open")}
            )
        
        # 11. Trigger touched but not accepted
        if ctx.get("trigger_touched", True) and ctx.get("trigger_accepted") is False:
            return (
                WrongEarlyReason.TRIGGER_TOUCHED_NOT_ACCEPTED,
                0.75,
                {"trigger_touched": True, "trigger_accepted": False}
            )
        
        # 12. Mean reversion too early
        if execution_type == "MEAN_REVERSION":
            if ctx.get("market_extending", False) or not ctx.get("momentum_exhausted", True):
                return (
                    WrongEarlyReason.MEAN_REVERSION_TOO_EARLY,
                    0.80,
                    {"market_extending": ctx.get("market_extending"), "momentum_exhausted": ctx.get("momentum_exhausted")}
                )
        
        # === LOW SEVERITY: Fallback ===
        
        # If we couldn't classify, return unknown
        return (
            WrongEarlyReason.UNKNOWN,
            0.50,
            {"raw_context": ctx, "note": "Could not determine specific reason"}
        )
    
    def classify_batch(self, data_list: List[Dict]) -> List[Dict]:
        """Classify multiple entries."""
        return [self.classify(data) for data in data_list]
