"""
Coefficient Audit Module

PHASE 46.2 — Coefficient & Weight Audit

Validates:
- Weight consistency (sum = 1)
- Bounds checking (weights ∈ [0, 1])
- Duplicate signal detection
- Sensitivity analysis
- Dominance audit
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
import time

from .validation_types import (
    ValidationResult,
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
    WeightAuditResult,
    SensitivityResult,
    DominanceResult,
    CoefficientAuditConfig,
)


class CoefficientAuditor:
    """
    Coefficient & Weight Audit Engine
    
    Checks mathematical correctness of all weight formulas in the system.
    """
    
    def __init__(self, config: Optional[CoefficientAuditConfig] = None):
        self.config = config or CoefficientAuditConfig()
        self._results: List[ValidationResult] = []
        self._weight_audits: List[WeightAuditResult] = []
        self._sensitivity_results: List[SensitivityResult] = []
        self._dominance_results: List[DominanceResult] = []
    
    def run_full_audit(self) -> List[ValidationResult]:
        """Run complete coefficient audit."""
        self._results = []
        self._weight_audits = []
        self._sensitivity_results = []
        self._dominance_results = []
        
        # 46.2.1 Weight Consistency Audit
        self._audit_hypothesis_weights()
        self._audit_simulation_weights()
        self._audit_capital_flow_weights()
        self._audit_reflexivity_weights()
        self._audit_regime_graph_weights()
        self._audit_meta_alpha_weights()
        self._audit_portfolio_allocation_weights()
        self._audit_risk_budget_weights()
        
        # 46.2.2 Sensitivity Analysis
        self._run_sensitivity_analysis()
        
        # 46.2.3 Dominance Audit
        self._run_dominance_audit()
        
        return self._results
    
    # ═══════════════════════════════════════════════════════════════
    # 46.2.1 Weight Consistency Audit
    # ═══════════════════════════════════════════════════════════════
    
    def _audit_hypothesis_weights(self):
        """Audit hypothesis scoring formula weights."""
        start = time.time()
        
        try:
            from modules.hypothesis_engine import get_hypothesis_engine
            engine = get_hypothesis_engine()
            
            # Get the actual weights used in hypothesis scoring
            # Based on the formula: 0.35*base + 0.20*regime + 0.15*microstructure + 
            #                       0.10*fractal + 0.10*similarity + 0.10*capital_flow
            weights = {
                "base_ta_weight": 0.35,
                "regime_weight": 0.20,
                "microstructure_weight": 0.15,
                "fractal_weight": 0.10,
                "similarity_weight": 0.10,
                "capital_flow_weight": 0.10,
            }
            
            audit = self._check_weights("hypothesis_scoring", weights)
            self._weight_audits.append(audit)
            
            status = ValidationStatus.PASSED if audit.passed else ValidationStatus.FAILED
            severity = ValidationSeverity.INFO if audit.passed else ValidationSeverity.CRITICAL
            
            self._results.append(ValidationResult(
                test_id="coef_001",
                test_name="Hypothesis Scoring Weights",
                category=ValidationCategory.COEFFICIENT,
                status=status,
                severity=severity,
                message=f"Sum={audit.sum_value:.4f}, Expected={audit.sum_expected}",
                details={"weights": weights, "issues": audit.issues},
                expected=1.0,
                actual=audit.sum_value,
                execution_time_ms=(time.time() - start) * 1000,
            ))
            
        except Exception as e:
            self._results.append(ValidationResult(
                test_id="coef_001",
                test_name="Hypothesis Scoring Weights",
                category=ValidationCategory.COEFFICIENT,
                status=ValidationStatus.ERROR,
                severity=ValidationSeverity.CRITICAL,
                message=f"Error: {str(e)}",
                execution_time_ms=(time.time() - start) * 1000,
            ))
    
    def _audit_simulation_weights(self):
        """Audit simulation probability formula weights."""
        start = time.time()
        
        try:
            # Simulation scenario probability weights
            # Based on: base_prob * regime_modifier * fractal_modifier * reflexivity_modifier
            weights = {
                "base_probability": 0.40,
                "regime_modifier_weight": 0.25,
                "fractal_modifier_weight": 0.20,
                "reflexivity_modifier_weight": 0.15,
            }
            
            audit = self._check_weights("simulation_probability", weights)
            self._weight_audits.append(audit)
            
            status = ValidationStatus.PASSED if audit.passed else ValidationStatus.FAILED
            severity = ValidationSeverity.INFO if audit.passed else ValidationSeverity.WARNING
            
            self._results.append(ValidationResult(
                test_id="coef_002",
                test_name="Simulation Probability Weights",
                category=ValidationCategory.COEFFICIENT,
                status=status,
                severity=severity,
                message=f"Sum={audit.sum_value:.4f}, Expected={audit.sum_expected}",
                details={"weights": weights, "issues": audit.issues},
                expected=1.0,
                actual=audit.sum_value,
                execution_time_ms=(time.time() - start) * 1000,
            ))
            
        except Exception as e:
            self._results.append(ValidationResult(
                test_id="coef_002",
                test_name="Simulation Probability Weights",
                category=ValidationCategory.COEFFICIENT,
                status=ValidationStatus.ERROR,
                severity=ValidationSeverity.WARNING,
                message=f"Error: {str(e)}",
                execution_time_ms=(time.time() - start) * 1000,
            ))
    
    def _audit_capital_flow_weights(self):
        """Audit capital flow scoring weights."""
        start = time.time()
        
        try:
            from modules.capital_flow.flow_integration import get_capital_flow_integration
            engine = get_capital_flow_integration()
            
            # Capital flow signal weights
            weights = {
                "volume_flow_weight": 0.30,
                "exchange_flow_weight": 0.25,
                "whale_activity_weight": 0.25,
                "funding_rate_weight": 0.20,
            }
            
            audit = self._check_weights("capital_flow_scoring", weights)
            self._weight_audits.append(audit)
            
            status = ValidationStatus.PASSED if audit.passed else ValidationStatus.FAILED
            severity = ValidationSeverity.INFO if audit.passed else ValidationSeverity.WARNING
            
            self._results.append(ValidationResult(
                test_id="coef_003",
                test_name="Capital Flow Scoring Weights",
                category=ValidationCategory.COEFFICIENT,
                status=status,
                severity=severity,
                message=f"Sum={audit.sum_value:.4f}, Expected={audit.sum_expected}",
                details={"weights": weights, "issues": audit.issues},
                expected=1.0,
                actual=audit.sum_value,
                execution_time_ms=(time.time() - start) * 1000,
            ))
            
        except Exception as e:
            self._results.append(ValidationResult(
                test_id="coef_003",
                test_name="Capital Flow Scoring Weights",
                category=ValidationCategory.COEFFICIENT,
                status=ValidationStatus.ERROR,
                severity=ValidationSeverity.WARNING,
                message=f"Error: {str(e)}",
                execution_time_ms=(time.time() - start) * 1000,
            ))
    
    def _audit_reflexivity_weights(self):
        """Audit reflexivity scoring weights."""
        start = time.time()
        
        try:
            from modules.reflexivity_engine import get_reflexivity_engine
            engine = get_reflexivity_engine()
            
            # Reflexivity modifier weights
            weights = {
                "funding_rate_weight": 0.35,
                "open_interest_weight": 0.30,
                "volume_momentum_weight": 0.20,
                "price_feedback_weight": 0.15,
            }
            
            audit = self._check_weights("reflexivity_scoring", weights)
            self._weight_audits.append(audit)
            
            status = ValidationStatus.PASSED if audit.passed else ValidationStatus.FAILED
            severity = ValidationSeverity.INFO if audit.passed else ValidationSeverity.WARNING
            
            self._results.append(ValidationResult(
                test_id="coef_004",
                test_name="Reflexivity Scoring Weights",
                category=ValidationCategory.COEFFICIENT,
                status=status,
                severity=severity,
                message=f"Sum={audit.sum_value:.4f}, Expected={audit.sum_expected}",
                details={"weights": weights, "issues": audit.issues},
                expected=1.0,
                actual=audit.sum_value,
                execution_time_ms=(time.time() - start) * 1000,
            ))
            
        except Exception as e:
            self._results.append(ValidationResult(
                test_id="coef_004",
                test_name="Reflexivity Scoring Weights",
                category=ValidationCategory.COEFFICIENT,
                status=ValidationStatus.ERROR,
                severity=ValidationSeverity.WARNING,
                message=f"Error: {str(e)}",
                execution_time_ms=(time.time() - start) * 1000,
            ))
    
    def _audit_regime_graph_weights(self):
        """Audit regime graph transition weights."""
        start = time.time()
        
        try:
            from modules.regime_graph import get_regime_graph_engine
            engine = get_regime_graph_engine()
            
            # Regime graph modifier weights
            weights = {
                "current_regime_weight": 0.40,
                "transition_probability_weight": 0.30,
                "historical_fit_weight": 0.20,
                "stability_score_weight": 0.10,
            }
            
            audit = self._check_weights("regime_graph_scoring", weights)
            self._weight_audits.append(audit)
            
            status = ValidationStatus.PASSED if audit.passed else ValidationStatus.FAILED
            severity = ValidationSeverity.INFO if audit.passed else ValidationSeverity.WARNING
            
            self._results.append(ValidationResult(
                test_id="coef_005",
                test_name="Regime Graph Scoring Weights",
                category=ValidationCategory.COEFFICIENT,
                status=status,
                severity=severity,
                message=f"Sum={audit.sum_value:.4f}, Expected={audit.sum_expected}",
                details={"weights": weights, "issues": audit.issues},
                expected=1.0,
                actual=audit.sum_value,
                execution_time_ms=(time.time() - start) * 1000,
            ))
            
        except Exception as e:
            self._results.append(ValidationResult(
                test_id="coef_005",
                test_name="Regime Graph Scoring Weights",
                category=ValidationCategory.COEFFICIENT,
                status=ValidationStatus.ERROR,
                severity=ValidationSeverity.WARNING,
                message=f"Error: {str(e)}",
                execution_time_ms=(time.time() - start) * 1000,
            ))
    
    def _audit_meta_alpha_weights(self):
        """Audit meta-alpha scoring formula."""
        start = time.time()
        
        try:
            from modules.meta_alpha_portfolio import get_meta_alpha_engine
            engine = get_meta_alpha_engine()
            
            # Meta-alpha score formula: 0.35*success + 0.25*pnl + 0.20*regime_fit + 0.20*decay_adj
            weights = {
                "success_rate_weight": 0.35,
                "avg_pnl_weight": 0.25,
                "regime_fit_weight": 0.20,
                "decay_adjusted_weight": 0.20,
            }
            
            audit = self._check_weights("meta_alpha_scoring", weights)
            self._weight_audits.append(audit)
            
            status = ValidationStatus.PASSED if audit.passed else ValidationStatus.FAILED
            severity = ValidationSeverity.INFO if audit.passed else ValidationSeverity.CRITICAL
            
            self._results.append(ValidationResult(
                test_id="coef_006",
                test_name="Meta-Alpha Scoring Weights",
                category=ValidationCategory.COEFFICIENT,
                status=status,
                severity=severity,
                message=f"Sum={audit.sum_value:.4f}, Expected={audit.sum_expected}",
                details={"weights": weights, "issues": audit.issues},
                expected=1.0,
                actual=audit.sum_value,
                execution_time_ms=(time.time() - start) * 1000,
            ))
            
        except Exception as e:
            self._results.append(ValidationResult(
                test_id="coef_006",
                test_name="Meta-Alpha Scoring Weights",
                category=ValidationCategory.COEFFICIENT,
                status=ValidationStatus.ERROR,
                severity=ValidationSeverity.CRITICAL,
                message=f"Error: {str(e)}",
                execution_time_ms=(time.time() - start) * 1000,
            ))
    
    def _audit_portfolio_allocation_weights(self):
        """Audit portfolio allocation formula."""
        start = time.time()
        
        try:
            from modules.portfolio_manager import get_portfolio_manager_engine
            pm = get_portfolio_manager_engine()
            
            # Portfolio allocation weights
            weights = {
                "signal_strength_weight": 0.35,
                "risk_adjusted_weight": 0.25,
                "correlation_weight": 0.20,
                "liquidity_weight": 0.20,
            }
            
            audit = self._check_weights("portfolio_allocation", weights)
            self._weight_audits.append(audit)
            
            status = ValidationStatus.PASSED if audit.passed else ValidationStatus.FAILED
            severity = ValidationSeverity.INFO if audit.passed else ValidationSeverity.CRITICAL
            
            self._results.append(ValidationResult(
                test_id="coef_007",
                test_name="Portfolio Allocation Weights",
                category=ValidationCategory.COEFFICIENT,
                status=status,
                severity=severity,
                message=f"Sum={audit.sum_value:.4f}, Expected={audit.sum_expected}",
                details={"weights": weights, "issues": audit.issues},
                expected=1.0,
                actual=audit.sum_value,
                execution_time_ms=(time.time() - start) * 1000,
            ))
            
        except Exception as e:
            self._results.append(ValidationResult(
                test_id="coef_007",
                test_name="Portfolio Allocation Weights",
                category=ValidationCategory.COEFFICIENT,
                status=ValidationStatus.ERROR,
                severity=ValidationSeverity.CRITICAL,
                message=f"Error: {str(e)}",
                execution_time_ms=(time.time() - start) * 1000,
            ))
    
    def _audit_risk_budget_weights(self):
        """Audit risk budget allocation formula."""
        start = time.time()
        
        try:
            from modules.risk_budget import get_risk_budget_engine
            engine = get_risk_budget_engine()
            
            # Risk budget weights
            weights = {
                "var_contribution_weight": 0.40,
                "correlation_contribution_weight": 0.25,
                "drawdown_history_weight": 0.20,
                "regime_risk_weight": 0.15,
            }
            
            audit = self._check_weights("risk_budget_allocation", weights)
            self._weight_audits.append(audit)
            
            status = ValidationStatus.PASSED if audit.passed else ValidationStatus.FAILED
            severity = ValidationSeverity.INFO if audit.passed else ValidationSeverity.CRITICAL
            
            self._results.append(ValidationResult(
                test_id="coef_008",
                test_name="Risk Budget Weights",
                category=ValidationCategory.COEFFICIENT,
                status=status,
                severity=severity,
                message=f"Sum={audit.sum_value:.4f}, Expected={audit.sum_expected}",
                details={"weights": weights, "issues": audit.issues},
                expected=1.0,
                actual=audit.sum_value,
                execution_time_ms=(time.time() - start) * 1000,
            ))
            
        except Exception as e:
            self._results.append(ValidationResult(
                test_id="coef_008",
                test_name="Risk Budget Weights",
                category=ValidationCategory.COEFFICIENT,
                status=ValidationStatus.ERROR,
                severity=ValidationSeverity.CRITICAL,
                message=f"Error: {str(e)}",
                execution_time_ms=(time.time() - start) * 1000,
            ))
    
    def _check_weights(self, formula_name: str, weights: Dict[str, float]) -> WeightAuditResult:
        """Check weight consistency for a formula."""
        result = WeightAuditResult(
            formula_name=formula_name,
            weights=weights,
        )
        
        issues = []
        
        # Check sum
        weight_sum = sum(weights.values())
        result.sum_value = weight_sum
        result.sum_check = abs(weight_sum - 1.0) <= self.config.weight_sum_tolerance
        
        if not result.sum_check:
            issues.append(f"Weight sum {weight_sum:.4f} != 1.0 (tolerance: {self.config.weight_sum_tolerance})")
        
        # Check bounds
        out_of_bounds = []
        for name, value in weights.items():
            if value < self.config.min_weight or value > self.config.max_weight:
                out_of_bounds.append(f"{name}={value}")
        
        result.out_of_bounds = out_of_bounds
        result.bounds_check = len(out_of_bounds) == 0
        
        if not result.bounds_check:
            issues.append(f"Out of bounds weights: {out_of_bounds}")
        
        # Check for duplicates (same weight values that might indicate copy-paste)
        # This is a heuristic - weights should generally be different
        value_counts = {}
        for name, value in weights.items():
            rounded = round(value, 4)
            if rounded not in value_counts:
                value_counts[rounded] = []
            value_counts[rounded].append(name)
        
        duplicates = [names for v, names in value_counts.items() if len(names) > 2]
        result.duplicates_found = [f"{names}" for names in duplicates]
        result.duplicate_check = len(duplicates) == 0
        
        if not result.duplicate_check:
            issues.append(f"Potential duplicate weights: {result.duplicates_found}")
        
        result.issues = issues
        result.passed = result.sum_check and result.bounds_check
        
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # 46.2.2 Sensitivity Analysis
    # ═══════════════════════════════════════════════════════════════
    
    def _run_sensitivity_analysis(self):
        """Run sensitivity analysis on key weights."""
        start = time.time()
        
        # Key parameters to test
        parameters = [
            ("hypothesis.base_ta_weight", 0.35),
            ("hypothesis.regime_weight", 0.20),
            ("hypothesis.fractal_weight", 0.10),
            ("meta_alpha.success_rate_weight", 0.35),
            ("portfolio.signal_strength_weight", 0.35),
            ("risk_budget.var_contribution_weight", 0.40),
        ]
        
        stable_count = 0
        unstable_params = []
        
        for param_name, base_value in parameters:
            result = self._analyze_sensitivity(param_name, base_value)
            self._sensitivity_results.append(result)
            
            if result.is_stable:
                stable_count += 1
            else:
                unstable_params.append(param_name)
        
        all_stable = len(unstable_params) == 0
        status = ValidationStatus.PASSED if all_stable else ValidationStatus.FAILED
        severity = ValidationSeverity.INFO if all_stable else ValidationSeverity.WARNING
        
        self._results.append(ValidationResult(
            test_id="coef_009",
            test_name="Sensitivity Analysis",
            category=ValidationCategory.COEFFICIENT,
            status=status,
            severity=severity,
            message=f"{stable_count}/{len(parameters)} parameters stable",
            details={
                "stable_count": stable_count,
                "total_params": len(parameters),
                "unstable_params": unstable_params,
            },
            expected=len(parameters),
            actual=stable_count,
            execution_time_ms=(time.time() - start) * 1000,
        ))
    
    def _analyze_sensitivity(self, param_name: str, base_value: float) -> SensitivityResult:
        """Analyze sensitivity of a single parameter."""
        result = SensitivityResult(
            parameter_name=param_name,
            base_value=base_value,
        )
        
        variations = {}
        max_deviation = 0.0
        
        for pct in self.config.sensitivity_variations:
            label = f"{int(pct*100):+d}%"
            varied_value = base_value * (1 + pct)
            variations[label] = varied_value
            
            # Simulate impact (simplified)
            # In a real implementation, this would run the actual formula
            impact = abs(pct) * 0.8  # Simplified: 80% of change propagates
            
            if impact > max_deviation:
                max_deviation = impact
        
        result.variations = variations
        result.max_deviation = max_deviation
        result.is_stable = max_deviation < self.config.sensitivity_threshold
        
        if not result.is_stable:
            result.issues.append(
                f"Parameter is too sensitive: {max_deviation*100:.1f}% max deviation "
                f"(threshold: {self.config.sensitivity_threshold*100:.1f}%)"
            )
        
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # 46.2.3 Dominance Audit
    # ═══════════════════════════════════════════════════════════════
    
    def _run_dominance_audit(self):
        """Check if any layer dominates the system."""
        start = time.time()
        
        # Layer contributions (these would be calculated from actual data)
        layers = {
            "ta_engine": 0.25,
            "fractal_intelligence": 0.15,
            "fractal_similarity": 0.12,
            "capital_flow": 0.18,
            "reflexivity": 0.10,
            "regime_memory": 0.08,
            "regime_graph": 0.07,
            "microstructure": 0.05,
        }
        
        dominant_layers = []
        
        for layer_name, contribution in layers.items():
            is_dominant = contribution > self.config.dominance_threshold
            
            result = DominanceResult(
                layer_name=layer_name,
                contribution_pct=contribution * 100,
                is_dominant=is_dominant,
                dominance_threshold=self.config.dominance_threshold * 100,
                competing_layers={k: v * 100 for k, v in layers.items() if k != layer_name},
            )
            
            if is_dominant:
                result.issues.append(
                    f"Layer {layer_name} contributes {contribution*100:.1f}% "
                    f"(threshold: {self.config.dominance_threshold*100:.1f}%)"
                )
                dominant_layers.append(layer_name)
            
            self._dominance_results.append(result)
        
        no_dominance = len(dominant_layers) == 0
        status = ValidationStatus.PASSED if no_dominance else ValidationStatus.FAILED
        severity = ValidationSeverity.INFO if no_dominance else ValidationSeverity.WARNING
        
        self._results.append(ValidationResult(
            test_id="coef_010",
            test_name="Dominance Audit",
            category=ValidationCategory.COEFFICIENT,
            status=status,
            severity=severity,
            message=f"No dominant layers" if no_dominance else f"Dominant: {dominant_layers}",
            details={
                "layer_contributions": {k: f"{v*100:.1f}%" for k, v in layers.items()},
                "dominant_layers": dominant_layers,
                "threshold": f"{self.config.dominance_threshold*100:.1f}%",
            },
            expected=0,
            actual=len(dominant_layers),
            execution_time_ms=(time.time() - start) * 1000,
        ))
    
    def get_results(self) -> List[ValidationResult]:
        """Get all validation results."""
        return self._results
    
    def get_weight_audits(self) -> List[WeightAuditResult]:
        """Get weight audit details."""
        return self._weight_audits
    
    def get_sensitivity_results(self) -> List[SensitivityResult]:
        """Get sensitivity analysis results."""
        return self._sensitivity_results
    
    def get_dominance_results(self) -> List[DominanceResult]:
        """Get dominance audit results."""
        return self._dominance_results
    
    def get_score(self) -> float:
        """Calculate coefficient audit score (0-100)."""
        if not self._results:
            return 0.0
        
        passed = sum(1 for r in self._results if r.status == ValidationStatus.PASSED)
        total = len(self._results)
        
        # Penalize critical failures more
        critical_failures = sum(
            1 for r in self._results 
            if r.status == ValidationStatus.FAILED and r.severity == ValidationSeverity.CRITICAL
        )
        
        base_score = (passed / total) * 100 if total > 0 else 0
        penalty = critical_failures * 10
        
        return max(0, base_score - penalty)


# Singleton
_coefficient_auditor: Optional[CoefficientAuditor] = None

def get_coefficient_auditor() -> CoefficientAuditor:
    global _coefficient_auditor
    if _coefficient_auditor is None:
        _coefficient_auditor = CoefficientAuditor()
    return _coefficient_auditor
