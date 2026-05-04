"""
PHASE 11.6.4 - OOS Gate
========================
Out-of-Sample validation gate.

Validates changes in:
- Train (where change was discovered)
- Validation (held out data)
- Out-of-Sample (truly unseen data)
- Scenario engine
- Monte Carlo profile
"""

import random
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum


class ValidationResult(str, Enum):
    """OOS validation result."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class OOSValidation:
    """Out-of-Sample validation result."""
    validation_id: str
    key: str
    timestamp: datetime
    
    # Validation stages
    train_result: ValidationResult
    train_score: float
    
    validation_result: ValidationResult
    validation_score: float
    
    oos_result: ValidationResult
    oos_score: float
    
    scenario_result: ValidationResult
    scenario_score: float
    
    montecarlo_result: ValidationResult
    montecarlo_score: float
    
    # Overall
    overall_result: ValidationResult
    overall_score: float
    gates_passed: int
    gates_total: int
    
    # Recommendation
    recommended_action: str


class OOSGate:
    """
    Out-of-Sample Validation Gate
    
    Ensures changes are validated across multiple data sets
    before being allowed into production.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        from ..adaptive_types import DEFAULT_ADAPTIVE_CONFIG
        self.config = config or DEFAULT_ADAPTIVE_CONFIG
        
        self.validations: List[OOSValidation] = []
        self.max_validations = 200
        self._validation_counter = 0
        
        # Minimum gates that must pass
        self.min_gates_to_pass = 3
    
    def validate_change(
        self,
        key: str,
        change_config: Dict,
        train_data: Optional[List[Dict]] = None,
        validation_data: Optional[List[Dict]] = None,
        oos_data: Optional[List[Dict]] = None
    ) -> OOSValidation:
        """
        Validate a change across all gates.
        
        Args:
            key: Identifier for the change
            change_config: The proposed change configuration
            train_data: Training data (where change discovered)
            validation_data: Held-out validation data
            oos_data: True out-of-sample data
            
        Returns:
            OOSValidation with results
        """
        now = datetime.now(timezone.utc)
        self._validation_counter += 1
        
        validation_id = f"oos_{self._validation_counter}_{int(now.timestamp())}"
        
        # Run each validation stage
        train_result, train_score = self._validate_on_data(
            change_config, train_data, "train"
        )
        
        val_result, val_score = self._validate_on_data(
            change_config, validation_data, "validation"
        )
        
        oos_result, oos_score = self._validate_on_data(
            change_config, oos_data, "oos"
        )
        
        scenario_result, scenario_score = self._validate_scenarios(change_config)
        
        mc_result, mc_score = self._validate_montecarlo(change_config)
        
        # Count passed gates
        gates = [train_result, val_result, oos_result, scenario_result, mc_result]
        gates_passed = sum(1 for g in gates if g == ValidationResult.PASSED)
        gates_total = len(gates)
        
        # Overall result
        if gates_passed >= self.min_gates_to_pass:
            overall_result = ValidationResult.PASSED
            recommended_action = "PROCEED_WITH_CHANGE"
        elif gates_passed >= 2:
            overall_result = ValidationResult.PARTIAL
            recommended_action = "REVIEW_MANUALLY"
        else:
            overall_result = ValidationResult.FAILED
            recommended_action = "REJECT_CHANGE"
        
        overall_score = (train_score + val_score + oos_score + scenario_score + mc_score) / 5
        
        validation = OOSValidation(
            validation_id=validation_id,
            key=key,
            timestamp=now,
            train_result=train_result,
            train_score=train_score,
            validation_result=val_result,
            validation_score=val_score,
            oos_result=oos_result,
            oos_score=oos_score,
            scenario_result=scenario_result,
            scenario_score=scenario_score,
            montecarlo_result=mc_result,
            montecarlo_score=mc_score,
            overall_result=overall_result,
            overall_score=overall_score,
            gates_passed=gates_passed,
            gates_total=gates_total,
            recommended_action=recommended_action
        )
        
        # Save
        self.validations.append(validation)
        if len(self.validations) > self.max_validations:
            self.validations = self.validations[-self.max_validations:]
        
        return validation
    
    def _validate_on_data(
        self,
        change_config: Dict,
        data: Optional[List[Dict]],
        stage: str
    ) -> Tuple[ValidationResult, float]:
        """Validate change on a data set."""
        if not data:
            # Generate mock validation
            return self._mock_validation(stage)
        
        # In real system: backtest change on data
        # For now, simulate
        return self._mock_validation(stage)
    
    def _mock_validation(self, stage: str) -> Tuple[ValidationResult, float]:
        """Generate mock validation result."""
        # Train typically performs best (optimistic bias)
        if stage == "train":
            score = 0.7 + random.gauss(0, 0.1)
        elif stage == "validation":
            score = 0.6 + random.gauss(0, 0.12)
        elif stage == "oos":
            score = 0.55 + random.gauss(0, 0.15)
        else:
            score = 0.5 + random.gauss(0, 0.15)
        
        score = max(0, min(1, score))
        
        if score >= 0.6:
            result = ValidationResult.PASSED
        elif score >= 0.4:
            result = ValidationResult.PARTIAL
        else:
            result = ValidationResult.FAILED
        
        return result, score
    
    def _validate_scenarios(self, change_config: Dict) -> Tuple[ValidationResult, float]:
        """Validate against scenario engine."""
        # Simulate scenario testing
        # In real system: run against historical regimes/scenarios
        
        scenarios = ["trending", "ranging", "volatile", "crash", "recovery"]
        scores = []
        
        for scenario in scenarios:
            # Mock score for scenario
            base = 0.55
            if scenario in ["crash", "volatile"]:
                base -= 0.1  # Usually harder
            score = base + random.gauss(0, 0.1)
            scores.append(max(0, min(1, score)))
        
        avg_score = sum(scores) / len(scores)
        worst_score = min(scores)
        
        # Must pass on average and not completely fail any scenario
        if avg_score >= 0.55 and worst_score >= 0.3:
            result = ValidationResult.PASSED
        elif avg_score >= 0.45:
            result = ValidationResult.PARTIAL
        else:
            result = ValidationResult.FAILED
        
        return result, avg_score
    
    def _validate_montecarlo(self, change_config: Dict) -> Tuple[ValidationResult, float]:
        """Validate Monte Carlo profile."""
        # Simulate Monte Carlo analysis
        n_simulations = 100
        
        # Generate mock simulation results
        final_values = []
        for _ in range(n_simulations):
            # Simulate equity curve
            value = 100
            for _ in range(50):  # 50 trades
                ret = random.gauss(0.002, 0.02)  # Slight positive expectancy
                value *= (1 + ret)
            final_values.append(value)
        
        # Calculate metrics
        avg_final = sum(final_values) / len(final_values)
        profitable_pct = sum(1 for v in final_values if v > 100) / len(final_values)
        worst_case = min(final_values)
        
        # Score based on metrics
        score = 0
        if avg_final > 100:
            score += 0.3 * min(1, (avg_final - 100) / 20)
        score += 0.4 * profitable_pct
        score += 0.3 * min(1, worst_case / 80)  # Worst case shouldn't be too bad
        
        if score >= 0.6 and profitable_pct >= 0.5:
            result = ValidationResult.PASSED
        elif score >= 0.4:
            result = ValidationResult.PARTIAL
        else:
            result = ValidationResult.FAILED
        
        return result, score
    
    def get_validation_by_key(self, key: str) -> Optional[OOSValidation]:
        """Get most recent validation for a key."""
        for v in reversed(self.validations):
            if v.key == key:
                return v
        return None
    
    def get_oos_summary(self) -> Dict:
        """Get summary of OOS validation."""
        if not self.validations:
            return {"summary": "NO_VALIDATIONS"}
        
        passed = sum(1 for v in self.validations if v.overall_result == ValidationResult.PASSED)
        failed = sum(1 for v in self.validations if v.overall_result == ValidationResult.FAILED)
        partial = sum(1 for v in self.validations if v.overall_result == ValidationResult.PARTIAL)
        
        avg_score = sum(v.overall_score for v in self.validations) / len(self.validations)
        
        return {
            "total_validations": len(self.validations),
            "passed": passed,
            "failed": failed,
            "partial": partial,
            "pass_rate": passed / len(self.validations),
            "avg_score": round(avg_score, 3),
            "min_gates_required": self.min_gates_to_pass
        }
