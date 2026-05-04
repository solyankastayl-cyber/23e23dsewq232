"""
TT4 - Trade Classifier
======================
Classifies trade results, exit reasons, and diagnostic flags.
"""

from typing import Dict, Any


class TradeClassifier:
    """Classifies trade outcomes and diagnostics"""
    
    # Thresholds
    BE_THRESHOLD = 0.001  # 0.1% = breakeven
    SLIPPAGE_THRESHOLD = 0.001  # 0.1% slippage warning
    
    def classify_result(self, pnl: float, entry_price: float = 0.0) -> str:
        """
        Classify trade result as WIN/LOSS/BE.
        
        Uses percentage-based threshold relative to entry if provided,
        otherwise uses absolute threshold.
        """
        if entry_price > 0:
            pnl_pct = abs(pnl / entry_price)
            threshold = entry_price * self.BE_THRESHOLD
        else:
            threshold = 1e-6
            
        if pnl > threshold:
            return "WIN"
        if pnl < -threshold:
            return "LOSS"
        return "BE"

    def classify_exit_reason(self, position: Dict[str, Any]) -> str:
        """
        Determine exit reason from position data.
        
        Priority: close_reason > exit_reason > inferred from price
        """
        # Check explicit reason
        reason = position.get("close_reason") or position.get("exit_reason")
        if reason:
            return str(reason).upper()
        
        # Infer from price vs levels
        exit_price = position.get("mark_price") or position.get("exit_price")
        stop = position.get("stop")
        target = position.get("target")
        side = str(position.get("side", "")).upper()
        
        if exit_price and target:
            if side == "LONG" and exit_price >= target:
                return "TARGET"
            if side == "SHORT" and exit_price <= target:
                return "TARGET"
                
        if exit_price and stop:
            if side == "LONG" and exit_price <= stop:
                return "STOP"
            if side == "SHORT" and exit_price >= stop:
                return "STOP"
        
        return "UNKNOWN"

    def classify_diagnostics(self, context: Dict[str, Any]) -> Dict[str, bool]:
        """
        Extract diagnostic flags from context.
        
        Flags:
        - wrong_early: Entered before optimal timing
        - late_entry: Entered after optimal timing  
        - mtf_conflict: Multi-timeframe disagreement
        - missed_target: Price hit target but didn't close
        """
        return {
            "wrong_early": bool(context.get("wrong_early", False)),
            "late_entry": bool(context.get("late_entry", False)),
            "mtf_conflict": bool(context.get("mtf_conflict", False)),
            "missed_target": bool(context.get("missed_target", False)),
        }

    def calculate_slippage(self, planned_entry: float, actual_entry: float, side: str) -> float:
        """
        Calculate slippage (negative = unfavorable).
        
        For LONG: slippage = planned - actual (positive if got better price)
        For SHORT: slippage = actual - planned (positive if got better price)
        """
        if not planned_entry or not actual_entry:
            return 0.0
            
        if side.upper() == "LONG":
            return planned_entry - actual_entry
        else:  # SHORT
            return actual_entry - planned_entry

    def is_significant_slippage(self, slippage: float, entry_price: float) -> bool:
        """Check if slippage exceeds threshold"""
        if not entry_price:
            return False
        return abs(slippage / entry_price) > self.SLIPPAGE_THRESHOLD
