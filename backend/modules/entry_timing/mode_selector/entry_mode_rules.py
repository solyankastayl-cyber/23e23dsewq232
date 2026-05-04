"""
PHASE 4.2 — Entry Mode Rules

Rule definitions for mode selection.
Integrates with Phase 4.1 diagnostics to learn from past mistakes.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .entry_mode_types import EntryMode


@dataclass
class RuleResult:
    """Result of a rule evaluation."""
    triggered: bool
    mode: Optional[EntryMode]
    reason: str
    confidence: float
    priority: int


class EntryModeRules:
    """
    Collection of rules for entry mode selection.
    
    Rules are evaluated in priority order.
    First matching rule determines the mode.
    """
    
    def __init__(self):
        # Thresholds (can be tuned based on diagnostics)
        self.extension_threshold_atr = 1.5
        self.extension_skip_threshold_atr = 2.5
        self.high_confidence_threshold = 0.80
        self.low_confidence_threshold = 0.60
        self.breakout_strength_threshold = 0.7
    
    def evaluate_all(
        self,
        context: Dict,
        prediction: Dict,
        setup: Dict,
        diagnostics: Dict
    ) -> List[RuleResult]:
        """
        Evaluate all rules and return matching results.
        
        Returns list of triggered rules sorted by priority.
        """
        results = []
        
        # Rule 1: LTF Conflict → SKIP
        r = self._rule_ltf_conflict(context, diagnostics)
        if r.triggered:
            results.append(r)
        
        # Rule 2: Extreme Extension → SKIP
        r = self._rule_extreme_extension(context, diagnostics)
        if r.triggered:
            results.append(r)
        
        # Rule 3: High Extension → WAIT_PULLBACK
        r = self._rule_high_extension(context, diagnostics)
        if r.triggered:
            results.append(r)
        
        # Rule 4: Hostile Volatility → WAIT_CONFIRMATION
        r = self._rule_hostile_volatility(context, diagnostics)
        if r.triggered:
            results.append(r)
        
        # Rule 5: Breakout No Close → ENTER_ON_CLOSE
        r = self._rule_breakout_no_close(context, setup, diagnostics)
        if r.triggered:
            results.append(r)
        
        # Rule 6: No Structure Acceptance → WAIT_RETEST
        r = self._rule_no_structure_acceptance(context, diagnostics)
        if r.triggered:
            results.append(r)
        
        # Rule 7: Liquidity Sweep Active → WAIT_CONFIRMATION
        r = self._rule_liquidity_sweep(context, diagnostics)
        if r.triggered:
            results.append(r)
        
        # Rule 8: Strong Setup → ENTER_NOW
        r = self._rule_strong_setup(context, prediction, diagnostics)
        if r.triggered:
            results.append(r)
        
        # Rule 9: Low Confidence → ENTER_ON_CLOSE
        r = self._rule_low_confidence(prediction, diagnostics)
        if r.triggered:
            results.append(r)
        
        # Sort by priority (highest first)
        results.sort(key=lambda x: -x.priority)
        
        return results
    
    def _rule_ltf_conflict(self, context: Dict, diagnostics: Dict) -> RuleResult:
        """Skip if lower timeframe shows conflict."""
        ltf_alignment = context.get("ltf_alignment", "aligned")
        top_reasons = diagnostics.get("top_wrong_early_reasons", [])
        
        # Boost priority if this is a common mistake
        priority = 100
        if "ltf_conflict" in top_reasons:
            priority = 110  # Even higher priority
        
        if ltf_alignment in ["conflict", "opposing", "divergent"]:
            return RuleResult(
                triggered=True,
                mode=EntryMode.SKIP_CONFLICTED,
                reason="ltf_conflict",
                confidence=0.90,
                priority=priority
            )
        
        return RuleResult(triggered=False, mode=None, reason="", confidence=0, priority=0)
    
    def _rule_extreme_extension(self, context: Dict, diagnostics: Dict) -> RuleResult:
        """Skip if price extended way too far."""
        extension = context.get("extension_atr", 0)
        
        if extension > self.extension_skip_threshold_atr:
            return RuleResult(
                triggered=True,
                mode=EntryMode.SKIP_LATE_ENTRY,
                reason="extreme_extension",
                confidence=0.95,
                priority=95
            )
        
        return RuleResult(triggered=False, mode=None, reason="", confidence=0, priority=0)
    
    def _rule_high_extension(self, context: Dict, diagnostics: Dict) -> RuleResult:
        """Wait for pullback if extension is high but not extreme."""
        extension = context.get("extension_atr", 0)
        top_reasons = diagnostics.get("top_wrong_early_reasons", [])
        
        # Lower threshold if extension is a common mistake
        threshold = self.extension_threshold_atr
        if "entered_on_extension" in top_reasons:
            threshold = 1.2  # More strict
        
        if extension > threshold:
            return RuleResult(
                triggered=True,
                mode=EntryMode.WAIT_PULLBACK,
                reason="extension_too_high",
                confidence=0.85,
                priority=75
            )
        
        return RuleResult(triggered=False, mode=None, reason="", confidence=0, priority=0)
    
    def _rule_hostile_volatility(self, context: Dict, diagnostics: Dict) -> RuleResult:
        """Wait for confirmation in hostile volatility."""
        vol_state = context.get("volatility_state", "normal")
        top_reasons = diagnostics.get("top_wrong_early_reasons", [])
        
        priority = 70
        if "volatility_hostile" in top_reasons:
            priority = 80
        
        if vol_state in ["high", "extreme", "hostile"]:
            return RuleResult(
                triggered=True,
                mode=EntryMode.WAIT_CONFIRMATION,
                reason="volatility_hostile",
                confidence=0.80,
                priority=priority
            )
        
        return RuleResult(triggered=False, mode=None, reason="", confidence=0, priority=0)
    
    def _rule_breakout_no_close(self, context: Dict, setup: Dict, diagnostics: Dict) -> RuleResult:
        """Require close confirmation for breakout setups."""
        setup_type = setup.get("type", "").upper()
        close_confirmation = context.get("close_confirmation", True)
        top_reasons = diagnostics.get("top_wrong_early_reasons", [])
        
        priority = 65
        if "breakout_not_confirmed" in top_reasons:
            priority = 75
        
        if setup_type == "BREAKOUT" and not close_confirmation:
            return RuleResult(
                triggered=True,
                mode=EntryMode.ENTER_ON_CLOSE,
                reason="breakout_needs_close_confirmation",
                confidence=0.80,
                priority=priority
            )
        
        return RuleResult(triggered=False, mode=None, reason="", confidence=0, priority=0)
    
    def _rule_no_structure_acceptance(self, context: Dict, diagnostics: Dict) -> RuleResult:
        """Wait for retest if structure not accepted."""
        structure_accepted = context.get("structure_acceptance", True)
        retest_available = context.get("retest_available", False)
        top_reasons = diagnostics.get("top_wrong_early_reasons", [])
        
        priority = 60
        if "structure_not_accepted" in top_reasons:
            priority = 70
        
        if not structure_accepted and retest_available:
            return RuleResult(
                triggered=True,
                mode=EntryMode.WAIT_RETEST,
                reason="structure_not_accepted",
                confidence=0.75,
                priority=priority
            )
        
        return RuleResult(triggered=False, mode=None, reason="", confidence=0, priority=0)
    
    def _rule_liquidity_sweep(self, context: Dict, diagnostics: Dict) -> RuleResult:
        """Wait if liquidity sweep not resolved."""
        sweep_active = context.get("liquidity_sweep_active", False)
        sweep_resolved = context.get("liquidity_sweep_resolved", True)
        top_reasons = diagnostics.get("top_wrong_early_reasons", [])
        
        priority = 65
        if "liquidity_sweep_not_resolved" in top_reasons:
            priority = 75
        
        if sweep_active or not sweep_resolved:
            return RuleResult(
                triggered=True,
                mode=EntryMode.WAIT_CONFIRMATION,
                reason="liquidity_sweep_pending",
                confidence=0.80,
                priority=priority
            )
        
        return RuleResult(triggered=False, mode=None, reason="", confidence=0, priority=0)
    
    def _rule_strong_setup(self, context: Dict, prediction: Dict, diagnostics: Dict) -> RuleResult:
        """Enter now if setup is strong and aligned."""
        confidence = prediction.get("confidence", 0.5)
        ltf_alignment = context.get("ltf_alignment", "unknown")
        breakout_strength = context.get("breakout_strength", 0.5)
        
        is_strong = (
            confidence > self.high_confidence_threshold and
            ltf_alignment == "aligned" and
            breakout_strength > self.breakout_strength_threshold
        )
        
        if is_strong:
            return RuleResult(
                triggered=True,
                mode=EntryMode.ENTER_NOW,
                reason="strong_aligned_setup",
                confidence=0.85,
                priority=50
            )
        
        return RuleResult(triggered=False, mode=None, reason="", confidence=0, priority=0)
    
    def _rule_low_confidence(self, prediction: Dict, diagnostics: Dict) -> RuleResult:
        """Use close confirmation for lower confidence setups."""
        confidence = prediction.get("confidence", 0.5)
        
        if confidence < self.low_confidence_threshold:
            return RuleResult(
                triggered=True,
                mode=EntryMode.ENTER_ON_CLOSE,
                reason="low_confidence_needs_confirmation",
                confidence=0.70,
                priority=45
            )
        
        return RuleResult(triggered=False, mode=None, reason="", confidence=0, priority=0)
    
    def update_thresholds_from_diagnostics(self, summary: Dict):
        """
        Dynamically adjust thresholds based on diagnostic data.
        
        This enables self-correction based on actual wrong early patterns.
        """
        distribution = summary.get("distribution", {})
        
        # If extension errors are > 20%, be more strict
        if distribution.get("entered_on_extension", 0) > 0.20:
            self.extension_threshold_atr = 1.2
        
        # If breakout errors are > 15%, require more confirmation
        if distribution.get("breakout_not_confirmed", 0) > 0.15:
            self.breakout_strength_threshold = 0.8
