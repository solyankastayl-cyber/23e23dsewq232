"""
System Validation Module

PHASE 46 — Full System Validation & Crash Audit

Validates:
- Coefficient consistency (weights, bounds, duplicates)
- Integration chains (data flow between modules)
- Logic correctness (determinism, lookahead bias)
- Stress testing results
- Chaos testing results
"""

from .validation_types import (
    ValidationResult,
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
    ValidationReport,
    ValidationConfig,
    WeightAuditResult,
    SensitivityResult,
    DominanceResult,
    IntegrationChainResult,
    CoefficientAuditConfig,
    IntegrationAuditConfig,
    LogicValidationConfig,
)

from .coefficient_audit import (
    CoefficientAuditor,
    get_coefficient_auditor,
)

from .integration_audit import (
    IntegrationAuditor,
    get_integration_auditor,
)

from .logic_validation import (
    LogicValidator,
    get_logic_validator,
)

from .validation_engine import (
    ValidationEngine,
    get_validation_engine,
)

from .validation_routes import router as validation_router

__all__ = [
    # Types
    "ValidationResult",
    "ValidationStatus",
    "ValidationSeverity",
    "ValidationCategory",
    "ValidationReport",
    "ValidationConfig",
    "WeightAuditResult",
    "SensitivityResult",
    "DominanceResult",
    "IntegrationChainResult",
    "CoefficientAuditConfig",
    "IntegrationAuditConfig",
    "LogicValidationConfig",
    # Auditors
    "CoefficientAuditor",
    "get_coefficient_auditor",
    "IntegrationAuditor",
    "get_integration_auditor",
    "LogicValidator",
    "get_logic_validator",
    # Engine
    "ValidationEngine",
    "get_validation_engine",
    # Routes
    "validation_router",
]
