"""
PHASE 4.1 — Wrong Early Taxonomy

Official classification of early entry reasons.
This is the foundation for all diagnostic logic.
"""

from enum import Enum
from typing import Dict, List


class WrongEarlyReason(Enum):
    """Enumeration of all wrong early reasons."""
    
    # === Breakout-related ===
    BREAKOUT_NOT_CONFIRMED = "breakout_not_confirmed"
    # Price touched trigger but didn't close above/below it
    
    TRIGGER_TOUCHED_NOT_ACCEPTED = "trigger_touched_but_not_accepted"
    # Trigger was touched but market rejected it immediately
    
    # === Retest-related ===
    RETEST_NOT_COMPLETED = "retest_not_completed"
    # Entered on breakout without waiting for retest
    
    # === Extension-related ===
    ENTERED_ON_EXTENSION = "entered_on_extension"
    # Entered after price already moved significantly from trigger
    
    # === Reversal-related ===
    REVERSAL_WITHOUT_EXHAUSTION = "reversal_without_exhaustion"
    # Entered reversal before exhaustion was confirmed
    
    # === Continuation-related ===
    CONTINUATION_BEFORE_RESET = "continuation_before_reset"
    # Entered continuation before pullback/reset completed
    
    # === Multi-timeframe ===
    LTF_CONFLICT = "ltf_conflict"
    # Lower timeframe showed conflicting signal
    
    # === Volatility ===
    VOLATILITY_HOSTILE = "volatility_hostile"
    # Market conditions too chaotic for entry
    
    # === Structure ===
    STRUCTURE_NOT_ACCEPTED = "structure_not_accepted"
    # Price hasn't shown acceptance of new structure level
    
    # === Confirmation ===
    ENTERED_BEFORE_CLOSE_CONFIRMATION = "entered_before_close_confirmation"
    # Entered before candle close confirmed the move
    
    # === Liquidity ===
    LIQUIDITY_SWEEP_NOT_RESOLVED = "liquidity_sweep_not_resolved"
    # Entered during/before liquidity sweep resolution
    
    # === Mean Reversion ===
    MEAN_REVERSION_TOO_EARLY = "mean_reversion_too_early"
    # Entered mean reversion while market still extending
    
    # === Unknown ===
    UNKNOWN = "unknown"
    # Could not determine specific reason


# List version for easy iteration
WRONG_EARLY_REASONS: List[str] = [r.value for r in WrongEarlyReason]


# Reason descriptions for documentation/UI
REASON_DESCRIPTIONS: Dict[str, str] = {
    "breakout_not_confirmed": "Price touched trigger but didn't close above/below it",
    "trigger_touched_but_not_accepted": "Trigger was touched but market rejected immediately",
    "retest_not_completed": "Entered on breakout without waiting for retest",
    "entered_on_extension": "Entered after price moved too far from trigger (>1.5 ATR)",
    "reversal_without_exhaustion": "Entered reversal before exhaustion confirmed",
    "continuation_before_reset": "Entered continuation before pullback completed",
    "ltf_conflict": "Lower timeframe showed conflicting signal",
    "volatility_hostile": "Market conditions too chaotic for clean entry",
    "structure_not_accepted": "Price hasn't accepted new structure level",
    "entered_before_close_confirmation": "Entered before candle close confirmed move",
    "liquidity_sweep_not_resolved": "Entered during unresolved liquidity sweep",
    "mean_reversion_too_early": "Entered mean reversion while market still extending",
    "unknown": "Could not determine specific reason"
}


# Reason severity levels (for prioritization)
REASON_SEVERITY: Dict[str, str] = {
    "breakout_not_confirmed": "high",
    "trigger_touched_but_not_accepted": "high",
    "retest_not_completed": "medium",
    "entered_on_extension": "high",
    "reversal_without_exhaustion": "high",
    "continuation_before_reset": "medium",
    "ltf_conflict": "medium",
    "volatility_hostile": "high",
    "structure_not_accepted": "medium",
    "entered_before_close_confirmation": "medium",
    "liquidity_sweep_not_resolved": "high",
    "mean_reversion_too_early": "high",
    "unknown": "low"
}


# Suggested fixes for each reason type
REASON_SUGGESTED_FIX: Dict[str, str] = {
    "breakout_not_confirmed": "Wait for candle close above/below trigger",
    "trigger_touched_but_not_accepted": "Require acceptance candle after touch",
    "retest_not_completed": "Implement retest-first entry mode",
    "entered_on_extension": "Add extension filter (max 1.5 ATR from trigger)",
    "reversal_without_exhaustion": "Require exhaustion confirmation",
    "continuation_before_reset": "Wait for pullback completion signal",
    "ltf_conflict": "Add LTF alignment check before entry",
    "volatility_hostile": "Add volatility gate filter",
    "structure_not_accepted": "Require structure acceptance confirmation",
    "entered_before_close_confirmation": "Switch to enter_on_close mode",
    "liquidity_sweep_not_resolved": "Wait for sweep resolution",
    "mean_reversion_too_early": "Wait for momentum exhaustion",
    "unknown": "Manual review required"
}
