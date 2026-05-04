"""
System Validation Types

PHASE 46 — Full System Validation & Crash Audit

Common types and contracts for validation framework.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


class ValidationSeverity(str, Enum):
    """Severity levels for validation results."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ValidationStatus(str, Enum):
    """Status of validation test."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class ValidationCategory(str, Enum):
    """Categories of validation tests."""
    COEFFICIENT = "COEFFICIENT"
    INTEGRATION = "INTEGRATION"
    LOGIC = "LOGIC"
    STRESS = "STRESS"
    CHAOS = "CHAOS"


class ValidationResult(BaseModel):
    """Single validation test result."""
    test_id: str
    test_name: str
    category: ValidationCategory
    status: ValidationStatus
    severity: ValidationSeverity = ValidationSeverity.INFO
    
    message: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
    
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    
    execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WeightAuditResult(BaseModel):
    """Result of weight consistency audit."""
    formula_name: str
    weights: Dict[str, float]
    
    sum_check: bool = False
    sum_value: float = 0.0
    sum_expected: float = 1.0
    
    bounds_check: bool = False
    out_of_bounds: List[str] = Field(default_factory=list)
    
    duplicate_check: bool = False
    duplicates_found: List[str] = Field(default_factory=list)
    
    passed: bool = False
    issues: List[str] = Field(default_factory=list)


class SensitivityResult(BaseModel):
    """Result of sensitivity analysis."""
    parameter_name: str
    base_value: float
    
    variations: Dict[str, float] = Field(default_factory=dict)  # "-20%": value, etc.
    impact: Dict[str, Dict[str, float]] = Field(default_factory=dict)  # metric -> variation -> change
    
    is_stable: bool = True
    max_deviation: float = 0.0
    critical_threshold: float = 0.3  # 30% change is critical
    
    issues: List[str] = Field(default_factory=list)


class DominanceResult(BaseModel):
    """Result of dominance audit."""
    layer_name: str
    contribution_pct: float
    
    is_dominant: bool = False
    dominance_threshold: float = 40.0
    
    competing_layers: Dict[str, float] = Field(default_factory=dict)
    
    issues: List[str] = Field(default_factory=list)


class IntegrationChainResult(BaseModel):
    """Result of integration chain test."""
    chain_name: str
    chain_steps: List[str]
    
    null_data_test: ValidationStatus = ValidationStatus.SKIPPED
    conflicting_data_test: ValidationStatus = ValidationStatus.SKIPPED
    stale_data_test: ValidationStatus = ValidationStatus.SKIPPED
    extreme_values_test: ValidationStatus = ValidationStatus.SKIPPED
    
    passed: bool = False
    failed_steps: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    """Complete validation report."""
    report_id: str = Field(default_factory=lambda: f"val_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_seconds: float = 0.0
    
    # Scores
    system_score: float = 0.0
    coefficient_score: float = 0.0
    integration_score: float = 0.0
    logic_score: float = 0.0
    stress_score: float = 0.0
    chaos_score: float = 0.0
    
    # Status
    status: str = "UNKNOWN"  # STABLE, WARNING, UNSTABLE, CRITICAL
    
    # Counts
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    warnings: int = 0
    critical: int = 0
    
    # Results by category
    coefficient_results: List[ValidationResult] = Field(default_factory=list)
    integration_results: List[ValidationResult] = Field(default_factory=list)
    logic_results: List[ValidationResult] = Field(default_factory=list)
    stress_results: List[ValidationResult] = Field(default_factory=list)
    chaos_results: List[ValidationResult] = Field(default_factory=list)
    
    # Summary
    failed_tests: List[str] = Field(default_factory=list)
    critical_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class CoefficientAuditConfig(BaseModel):
    """Configuration for coefficient audit."""
    check_weight_sums: bool = True
    check_bounds: bool = True
    check_duplicates: bool = True
    
    weight_sum_tolerance: float = 0.01  # 1% tolerance
    min_weight: float = 0.0
    max_weight: float = 1.0
    
    sensitivity_variations: List[float] = Field(default_factory=lambda: [-0.2, -0.1, 0.0, 0.1, 0.2])
    sensitivity_threshold: float = 0.3  # 30% change is critical
    
    dominance_threshold: float = 0.4  # 40% is dominant


class IntegrationAuditConfig(BaseModel):
    """Configuration for integration audit."""
    test_null_data: bool = True
    test_conflicting_data: bool = True
    test_stale_data: bool = True
    test_extreme_values: bool = True
    
    stale_threshold_seconds: int = 300  # 5 minutes
    
    chains_to_test: List[str] = Field(default_factory=lambda: [
        "CHAIN_A",  # TA → Hypothesis → Portfolio → Execution
        "CHAIN_B",  # Fractal → Similarity → Hypothesis → Scenario
        "CHAIN_C",  # Microstructure → Liquidity Impact → Execution Brain
        "CHAIN_D",  # Outcome → Memory → Graph → Reflexivity → Hypothesis
        "CHAIN_E",  # Capital Flow → Portfolio Rotation → Risk Budget
    ])


class LogicValidationConfig(BaseModel):
    """Configuration for logic validation."""
    test_determinism: bool = True
    test_lookahead: bool = True
    test_boundaries: bool = True
    test_nan_handling: bool = True
    
    determinism_iterations: int = 3
    boundary_test_window_sizes: List[int] = Field(default_factory=lambda: [10, 20, 50, 100, 200])


class ValidationConfig(BaseModel):
    """Master configuration for validation engine."""
    coefficient_config: CoefficientAuditConfig = Field(default_factory=CoefficientAuditConfig)
    integration_config: IntegrationAuditConfig = Field(default_factory=IntegrationAuditConfig)
    logic_config: LogicValidationConfig = Field(default_factory=LogicValidationConfig)
    
    # Scoring weights
    coefficient_weight: float = 0.30
    integration_weight: float = 0.25
    logic_weight: float = 0.20
    stress_weight: float = 0.15
    chaos_weight: float = 0.10
    
    # Thresholds
    stable_threshold: float = 90.0
    warning_threshold: float = 70.0
    critical_threshold: float = 50.0
