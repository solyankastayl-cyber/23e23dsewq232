"""Data Validator - Validates consistency between terminal state components"""

from typing import Dict, Any, Optional
from .validation_types import ValidationResult, ValidationSeverity


class DataValidator:
    MAX_ENTRY_DEVIATION = 0.20
    MAX_FAVORABLE_SPREAD = 3.0
    MIN_STRONG_CONFIDENCE = 0.6
    VALID_TIMEFRAMES = ["1H", "4H", "1D"]

    def validate_execution_vs_market(self, execution: Optional[Dict], market_price: Optional[float]) -> ValidationResult:
        if not execution or execution.get("entry") is None:
            return ValidationResult(valid=True, type="no_execution", message="No execution plan set", severity=ValidationSeverity.INFO)
        
        if not market_price or market_price <= 0:
            return ValidationResult(valid=True, type="no_market_price", message="No market price available", severity=ValidationSeverity.WARNING)
        
        entry = execution["entry"]
        deviation = abs(entry - market_price) / market_price
        deviation_pct = round(deviation * 100, 2)
        
        if deviation > self.MAX_ENTRY_DEVIATION:
            return ValidationResult(
                valid=False, type="ENTRY_PRICE_MISMATCH",
                message=f"Entry ${entry:,.2f} deviates {deviation_pct}% from market ${market_price:,.2f}",
                severity=ValidationSeverity.CRITICAL,
                details={"entry": entry, "market_price": market_price, "deviation_pct": deviation_pct}
            )
        
        return ValidationResult(valid=True, type="execution_price_ok", message=f"Entry within {deviation_pct}% of market", severity=ValidationSeverity.INFO)

    def validate_position_vs_symbol(self, position: Optional[Dict], symbol: str) -> ValidationResult:
        if not position or not position.get("has_position"):
            return ValidationResult(valid=True, type="no_position", message="No open position", severity=ValidationSeverity.INFO)
        
        position_symbol = position.get("symbol", "").upper()
        terminal_symbol = symbol.upper()
        
        if position_symbol and position_symbol != terminal_symbol:
            return ValidationResult(
                valid=False, type="POSITION_SYMBOL_MISMATCH",
                message=f"Position {position_symbol} != Terminal {terminal_symbol}",
                severity=ValidationSeverity.CRITICAL
            )
        
        return ValidationResult(valid=True, type="position_symbol_ok", message=f"Position matches {terminal_symbol}", severity=ValidationSeverity.INFO)

    def validate_micro_source(self, micro: Optional[Dict]) -> ValidationResult:
        if not micro:
            return ValidationResult(valid=True, type="no_micro", message="No microstructure data", severity=ValidationSeverity.WARNING)
        
        source = micro.get("source", "unknown")
        if source != "live":
            return ValidationResult(valid=True, type="SIMULATION_MODE", message=f"Using {source} data", severity=ValidationSeverity.WARNING)
        
        return ValidationResult(valid=True, type="micro_live", message="Live microstructure", severity=ValidationSeverity.INFO)

    def validate_decision_confidence(self, decision: Optional[Dict], micro_source: str = "live") -> ValidationResult:
        if not decision:
            return ValidationResult(valid=True, type="no_decision", message="No decision data", severity=ValidationSeverity.INFO)
        
        confidence = decision.get("confidence", 0)
        action = decision.get("action", "WAIT")
        
        if confidence > 0.7 and micro_source != "live":
            return ValidationResult(valid=True, type="HIGH_CONFIDENCE_MOCK", message=f"High confidence with simulated data", severity=ValidationSeverity.WARNING)
        
        if action.startswith("GO") and confidence < self.MIN_STRONG_CONFIDENCE:
            return ValidationResult(valid=True, type="LOW_CONFIDENCE_ACTION", message=f"GO with low confidence", severity=ValidationSeverity.WARNING)
        
        return ValidationResult(valid=True, type="decision_ok", message="Decision confidence OK", severity=ValidationSeverity.INFO)

    def validate_execution_levels(self, execution: Optional[Dict]) -> ValidationResult:
        if not execution:
            return ValidationResult(valid=True, type="no_execution", message="No execution", severity=ValidationSeverity.INFO)
        
        entry, stop, target = execution.get("entry"), execution.get("stop"), execution.get("target")
        if not all([entry, stop, target]):
            return ValidationResult(valid=True, type="incomplete_levels", message="Levels incomplete", severity=ValidationSeverity.INFO)
        
        if stop > entry:
            return ValidationResult(valid=False, type="INVALID_STOP_LEVEL", message=f"Stop > Entry", severity=ValidationSeverity.CRITICAL)
        if target < entry:
            return ValidationResult(valid=False, type="INVALID_TARGET_LEVEL", message=f"Target < Entry", severity=ValidationSeverity.CRITICAL)
        
        rr = execution.get("rr")
        if rr and rr < 0.5:
            return ValidationResult(valid=True, type="LOW_RR", message=f"Low R:R {rr}", severity=ValidationSeverity.WARNING)
        
        return ValidationResult(valid=True, type="execution_levels_ok", message="Levels valid", severity=ValidationSeverity.INFO)

    def validate_timeframe_consistency(self, state: Dict[str, Any]) -> ValidationResult:
        """
        Validate that all components use the same timeframe.
        Critical check for system consistency.
        """
        system_tf = state.get("timeframe", "4H")
        execution = state.get("execution", {})
        decision = state.get("decision", {})
        
        # Check execution timeframe
        exec_tf = execution.get("timeframe")
        if exec_tf and exec_tf != system_tf:
            return ValidationResult(
                valid=False,
                type="TIMEFRAME_MISMATCH",
                message=f"Execution TF ({exec_tf}) != System TF ({system_tf})",
                severity=ValidationSeverity.CRITICAL,
                details={"system_tf": system_tf, "execution_tf": exec_tf}
            )
        
        # Check decision timeframe
        decision_tf = decision.get("timeframe")
        if decision_tf and decision_tf != system_tf:
            return ValidationResult(
                valid=False,
                type="TIMEFRAME_MISMATCH", 
                message=f"Decision TF ({decision_tf}) != System TF ({system_tf})",
                severity=ValidationSeverity.CRITICAL,
                details={"system_tf": system_tf, "decision_tf": decision_tf}
            )
        
        # Valid timeframe
        if system_tf not in self.VALID_TIMEFRAMES:
            return ValidationResult(
                valid=False,
                type="INVALID_TIMEFRAME",
                message=f"Invalid timeframe: {system_tf}",
                severity=ValidationSeverity.CRITICAL,
                details={"timeframe": system_tf, "valid": self.VALID_TIMEFRAMES}
            )
        
        return ValidationResult(
            valid=True,
            type="timeframe_consistent",
            message=f"All components using {system_tf}",
            severity=ValidationSeverity.INFO,
            details={"timeframe": system_tf}
        )
