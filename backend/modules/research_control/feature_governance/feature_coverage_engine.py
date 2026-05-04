"""
PHASE 17.1 — Feature Coverage Engine
=====================================
Evaluates feature data availability and validity.

Coverage measures:
- Data availability rate
- Null/NaN rate
- Valid observation percentage
- Temporal coverage gaps

High coverage = feature is reliably available
Low coverage = feature has data quality issues
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.research_control.feature_governance.feature_governance_types import (
    GovernanceDimension,
    DimensionResult,
    CoverageInput,
)


# ══════════════════════════════════════════════════════════════
# COVERAGE THRESHOLDS
# ══════════════════════════════════════════════════════════════

COVERAGE_THRESHOLDS = {
    "coverage_good": 0.95,      # > 95% coverage = GOOD
    "coverage_warning": 0.80,   # > 80% coverage = WARNING
    "coverage_poor": 0.50,      # > 50% coverage = POOR
    # < 50% = CRITICAL
}


# ══════════════════════════════════════════════════════════════
# COVERAGE ENGINE
# ══════════════════════════════════════════════════════════════

class FeatureCoverageEngine:
    """
    Feature Coverage Engine - PHASE 17.1
    
    Evaluates how reliably available a feature's data is.
    """
    
    def __init__(self):
        pass
    
    def evaluate(self, feature_name: str, input_data: CoverageInput) -> DimensionResult:
        """
        Evaluate coverage for a feature.
        
        Args:
            feature_name: Name of the feature
            input_data: Coverage statistics
        
        Returns:
            DimensionResult with coverage score
        """
        total = input_data.total_observations
        valid = input_data.valid_observations
        null_rate = input_data.null_rate
        
        if total == 0:
            return DimensionResult(
                dimension=GovernanceDimension.COVERAGE,
                score=0.0,
                status="POOR",
                reason="No observations available",
                inputs=input_data.to_dict(),
            )
        
        # Calculate coverage rate
        coverage_rate = valid / total if total > 0 else 0
        
        # Score is simply the coverage rate (already 0-1)
        coverage_score = coverage_rate
        
        # Determine status
        if coverage_score >= COVERAGE_THRESHOLDS["coverage_good"]:
            status = "GOOD"
            reason = f"Excellent coverage ({coverage_score * 100:.1f}%)"
        elif coverage_score >= COVERAGE_THRESHOLDS["coverage_warning"]:
            status = "WARNING"
            reason = f"Good coverage with some gaps ({coverage_score * 100:.1f}%)"
        elif coverage_score >= COVERAGE_THRESHOLDS["coverage_poor"]:
            status = "WARNING"
            reason = f"Coverage needs attention ({coverage_score * 100:.1f}%)"
        else:
            status = "POOR"
            reason = f"Critical coverage issues ({coverage_score * 100:.1f}%)"
        
        return DimensionResult(
            dimension=GovernanceDimension.COVERAGE,
            score=coverage_score,
            status=status,
            reason=reason,
            inputs={
                **input_data.to_dict(),
                "coverage_score": round(coverage_score, 4),
            },
        )
    
    def evaluate_from_rate(
        self,
        feature_name: str,
        coverage_rate: float,
    ) -> DimensionResult:
        """
        Evaluate with pre-computed coverage rate (for testing).
        """
        coverage_score = min(1.0, max(0.0, coverage_rate))
        
        if coverage_score >= COVERAGE_THRESHOLDS["coverage_good"]:
            status = "GOOD"
            reason = f"Excellent coverage"
        elif coverage_score >= COVERAGE_THRESHOLDS["coverage_warning"]:
            status = "WARNING"
            reason = f"Good coverage with some gaps"
        elif coverage_score >= COVERAGE_THRESHOLDS["coverage_poor"]:
            status = "WARNING"
            reason = f"Coverage needs attention"
        else:
            status = "POOR"
            reason = f"Critical coverage issues"
        
        return DimensionResult(
            dimension=GovernanceDimension.COVERAGE,
            score=coverage_score,
            status=status,
            reason=reason,
            inputs={
                "coverage_rate": coverage_rate,
            },
        )


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FeatureCoverageEngine] = None


def get_coverage_engine() -> FeatureCoverageEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FeatureCoverageEngine()
    return _engine
