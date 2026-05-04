"""
Validation Engine

PHASE 46 — Full System Validation & Crash Audit

Main orchestrator for all validation tests.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import time

from .validation_types import (
    ValidationResult,
    ValidationReport,
    ValidationConfig,
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
)
from .coefficient_audit import CoefficientAuditor, get_coefficient_auditor
from .integration_audit import IntegrationAuditor, get_integration_auditor
from .logic_validation import LogicValidator, get_logic_validator


class ValidationEngine:
    """
    Main Validation Engine
    
    Orchestrates all validation tests and produces reports.
    """
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()
        
        self._coefficient_auditor = CoefficientAuditor(self.config.coefficient_config)
        self._integration_auditor = IntegrationAuditor(self.config.integration_config)
        self._logic_validator = LogicValidator()
        
        self._last_report: Optional[ValidationReport] = None
        self._reports_history: List[ValidationReport] = []
    
    async def run_full_validation(self) -> ValidationReport:
        """Run complete system validation."""
        start_time = time.time()
        
        report = ValidationReport()
        
        # Run all audits
        coefficient_results = self._coefficient_auditor.run_full_audit()
        integration_results = self._integration_auditor.run_full_audit()
        logic_results = self._logic_validator.run_full_validation()
        
        # Add results to report
        report.coefficient_results = coefficient_results
        report.integration_results = integration_results
        report.logic_results = logic_results
        
        # Calculate scores
        report.coefficient_score = self._coefficient_auditor.get_score()
        report.integration_score = self._integration_auditor.get_score()
        report.logic_score = self._logic_validator.get_score()
        
        # Get stress/chaos scores
        report.stress_score = await self._get_stress_score()
        report.chaos_score = await self._get_chaos_score()
        
        # Calculate overall score
        report.system_score = (
            report.coefficient_score * self.config.coefficient_weight +
            report.integration_score * self.config.integration_weight +
            report.logic_score * self.config.logic_weight +
            report.stress_score * self.config.stress_weight +
            report.chaos_score * self.config.chaos_weight
        )
        
        # Determine status
        if report.system_score >= self.config.stable_threshold:
            report.status = "STABLE"
        elif report.system_score >= self.config.warning_threshold:
            report.status = "WARNING"
        elif report.system_score >= self.config.critical_threshold:
            report.status = "UNSTABLE"
        else:
            report.status = "CRITICAL"
        
        # Count results
        all_results = (
            coefficient_results + 
            integration_results +
            logic_results
        )
        
        report.tests_run = len(all_results)
        report.tests_passed = sum(1 for r in all_results if r.status == ValidationStatus.PASSED)
        report.tests_failed = sum(1 for r in all_results if r.status == ValidationStatus.FAILED)
        report.warnings = sum(1 for r in all_results if r.severity == ValidationSeverity.WARNING)
        report.critical = sum(1 for r in all_results if r.severity == ValidationSeverity.CRITICAL)
        
        # Collect failed tests
        report.failed_tests = [
            r.test_name for r in all_results 
            if r.status == ValidationStatus.FAILED
        ]
        
        # Collect critical issues
        report.critical_issues = [
            f"{r.test_name}: {r.message}" for r in all_results 
            if r.severity == ValidationSeverity.CRITICAL and r.status != ValidationStatus.PASSED
        ]
        
        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)
        
        # Finalize
        report.duration_seconds = time.time() - start_time
        
        self._last_report = report
        self._reports_history.append(report)
        
        return report
    
    async def run_coefficient_audit(self) -> List[ValidationResult]:
        """Run only coefficient audit."""
        return self._coefficient_auditor.run_full_audit()
    
    async def run_integration_audit(self) -> List[ValidationResult]:
        """Run only integration audit."""
        return self._integration_auditor.run_full_audit()
    
    async def run_logic_validation(self) -> List[ValidationResult]:
        """Run only logic validation."""
        return self._logic_validator.run_full_validation()
    
    async def _get_stress_score(self) -> float:
        """Get stress test score from existing engine."""
        try:
            from modules.stress_testing import get_stress_engine
            engine = get_stress_engine()
            summary = engine.get_summary()
            
            pass_rate = summary.get("pass_rate", 0)
            return pass_rate * 100
        except Exception:
            return 50.0  # Default if not available
    
    async def _get_chaos_score(self) -> float:
        """Get chaos test score from existing engine."""
        try:
            from modules.system_chaos import get_chaos_engine
            engine = get_chaos_engine()
            summary = engine.get_summary()
            
            recovery_rate = summary.get("recovery_rate", 0)
            return recovery_rate * 100
        except Exception:
            return 50.0  # Default if not available
    
    def _generate_recommendations(self, report: ValidationReport) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if report.coefficient_score < 80:
            recommendations.append("Review and fix weight consistency issues in scoring formulas")
        
        if report.integration_score < 80:
            recommendations.append("Debug integration chain failures before deployment")
        
        if report.stress_score < 70:
            recommendations.append("Optimize system for higher throughput before production")
        
        if report.chaos_score < 90:
            recommendations.append("Improve fault tolerance and recovery mechanisms")
        
        if report.system_score < 90:
            recommendations.append("System not ready for Stage C - resolve critical issues first")
        elif report.system_score >= 90:
            recommendations.append("System meets Stage C readiness criteria")
        
        return recommendations
    
    def get_last_report(self) -> Optional[ValidationReport]:
        """Get the last validation report."""
        return self._last_report
    
    def get_reports_history(self, limit: int = 10) -> List[ValidationReport]:
        """Get validation report history."""
        return self._reports_history[-limit:]
    
    def get_summary(self) -> Dict:
        """Get validation engine summary."""
        return {
            "last_validation": self._last_report.timestamp.isoformat() if self._last_report else None,
            "last_score": self._last_report.system_score if self._last_report else None,
            "last_status": self._last_report.status if self._last_report else None,
            "total_validations": len(self._reports_history),
            "config": {
                "stable_threshold": self.config.stable_threshold,
                "warning_threshold": self.config.warning_threshold,
                "critical_threshold": self.config.critical_threshold,
            },
        }


# Singleton
_validation_engine: Optional[ValidationEngine] = None

def get_validation_engine() -> ValidationEngine:
    global _validation_engine
    if _validation_engine is None:
        _validation_engine = ValidationEngine()
    return _validation_engine
