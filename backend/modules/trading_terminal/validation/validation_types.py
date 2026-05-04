"""
Validation Types for Data Consistency Layer
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    valid: bool
    type: str
    message: str
    severity: ValidationSeverity
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "type": self.type,
            "message": self.message,
            "severity": self.severity.value,
            "details": self.details
        }


@dataclass
class AggregatedValidation:
    is_valid: bool
    critical_count: int
    warning_count: int
    info_count: int
    issues: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "issues": self.issues
        }
