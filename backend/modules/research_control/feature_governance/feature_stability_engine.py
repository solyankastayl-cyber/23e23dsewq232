"""
PHASE 17.1 — Feature Stability Engine
======================================
Evaluates feature stability over time.

Stability measures:
- Variance stability (rolling std)
- Mean stability (rolling mean)
- Autocorrelation stability
- Regime consistency

High stability = feature behaves consistently
Low stability = feature is erratic/unreliable
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import math

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.research_control.feature_governance.feature_governance_types import (
    GovernanceDimension,
    DimensionResult,
    StabilityInput,
)


# ══════════════════════════════════════════════════════════════
# STABILITY THRESHOLDS
# ══════════════════════════════════════════════════════════════

STABILITY_THRESHOLDS = {
    "variance_change_max": 0.5,    # Max allowed variance change
    "mean_change_max": 0.3,       # Max allowed mean drift
    "autocorr_min": 0.3,          # Min autocorrelation for stability
}


# ══════════════════════════════════════════════════════════════
# STABILITY ENGINE
# ══════════════════════════════════════════════════════════════

class FeatureStabilityEngine:
    """
    Feature Stability Engine - PHASE 17.1
    
    Evaluates how stable a feature is over time.
    """
    
    def __init__(self):
        pass
    
    def evaluate(self, feature_name: str, input_data: StabilityInput) -> DimensionResult:
        """
        Evaluate stability for a feature.
        
        Args:
            feature_name: Name of the feature
            input_data: Historical values for stability analysis
        
        Returns:
            DimensionResult with stability score
        """
        values = input_data.values_history
        
        if len(values) < 10:
            return DimensionResult(
                dimension=GovernanceDimension.STABILITY,
                score=0.5,
                status="WARNING",
                reason="Insufficient data for stability analysis",
                inputs=input_data.to_dict(),
            )
        
        # Calculate stability metrics
        variance_stability = self._calculate_variance_stability(values)
        mean_stability = self._calculate_mean_stability(values)
        autocorr_stability = self._calculate_autocorrelation(values)
        
        # Aggregate stability score
        stability_score = (
            0.35 * variance_stability +
            0.35 * mean_stability +
            0.30 * autocorr_stability
        )
        
        # Determine status
        if stability_score >= 0.75:
            status = "GOOD"
            reason = f"Feature is stable (var={variance_stability:.2f}, mean={mean_stability:.2f})"
        elif stability_score >= 0.50:
            status = "WARNING"
            reason = f"Feature has moderate stability issues"
        else:
            status = "POOR"
            reason = f"Feature is unstable (var={variance_stability:.2f}, mean={mean_stability:.2f})"
        
        return DimensionResult(
            dimension=GovernanceDimension.STABILITY,
            score=stability_score,
            status=status,
            reason=reason,
            inputs={
                **input_data.to_dict(),
                "variance_stability": round(variance_stability, 4),
                "mean_stability": round(mean_stability, 4),
                "autocorr_stability": round(autocorr_stability, 4),
            },
        )
    
    def evaluate_from_scores(
        self,
        feature_name: str,
        variance_stability: float,
        mean_stability: float,
        autocorr_stability: float,
    ) -> DimensionResult:
        """
        Evaluate with pre-computed scores (for testing).
        """
        stability_score = (
            0.35 * variance_stability +
            0.35 * mean_stability +
            0.30 * autocorr_stability
        )
        
        if stability_score >= 0.75:
            status = "GOOD"
            reason = f"Feature is stable"
        elif stability_score >= 0.50:
            status = "WARNING"
            reason = f"Feature has moderate stability"
        else:
            status = "POOR"
            reason = f"Feature is unstable"
        
        return DimensionResult(
            dimension=GovernanceDimension.STABILITY,
            score=min(1.0, max(0.0, stability_score)),
            status=status,
            reason=reason,
            inputs={
                "variance_stability": variance_stability,
                "mean_stability": mean_stability,
                "autocorr_stability": autocorr_stability,
            },
        )
    
    def _calculate_variance_stability(self, values: List[float]) -> float:
        """
        Calculate variance stability.
        
        Compares rolling variance to overall variance.
        Low change = high stability.
        """
        if len(values) < 20:
            return 0.5
        
        # Overall variance
        mean = sum(values) / len(values)
        overall_var = sum((x - mean) ** 2 for x in values) / len(values)
        
        if overall_var == 0:
            return 1.0
        
        # Rolling variance (windows of 10)
        window_size = min(10, len(values) // 3)
        rolling_vars = []
        
        for i in range(len(values) - window_size + 1):
            window = values[i:i + window_size]
            w_mean = sum(window) / len(window)
            w_var = sum((x - w_mean) ** 2 for x in window) / len(window)
            rolling_vars.append(w_var)
        
        if not rolling_vars:
            return 0.5
        
        # Calculate coefficient of variation of rolling variances
        rv_mean = sum(rolling_vars) / len(rolling_vars)
        if rv_mean == 0:
            return 1.0
        
        rv_std = math.sqrt(sum((x - rv_mean) ** 2 for x in rolling_vars) / len(rolling_vars))
        cv = rv_std / rv_mean
        
        # Convert to score (lower CV = higher stability)
        stability = max(0.0, 1.0 - cv)
        return min(1.0, stability)
    
    def _calculate_mean_stability(self, values: List[float]) -> float:
        """
        Calculate mean stability.
        
        Compares rolling mean to overall mean.
        Low drift = high stability.
        """
        if len(values) < 20:
            return 0.5
        
        overall_mean = sum(values) / len(values)
        
        if overall_mean == 0:
            return 0.5
        
        # Rolling mean (windows of 10)
        window_size = min(10, len(values) // 3)
        rolling_means = []
        
        for i in range(len(values) - window_size + 1):
            window = values[i:i + window_size]
            w_mean = sum(window) / len(window)
            rolling_means.append(w_mean)
        
        if not rolling_means:
            return 0.5
        
        # Calculate max deviation from overall mean
        max_deviation = max(abs(m - overall_mean) for m in rolling_means)
        relative_deviation = max_deviation / abs(overall_mean) if overall_mean != 0 else 0
        
        # Convert to score (lower deviation = higher stability)
        stability = max(0.0, 1.0 - relative_deviation)
        return min(1.0, stability)
    
    def _calculate_autocorrelation(self, values: List[float]) -> float:
        """
        Calculate lag-1 autocorrelation.
        
        Higher autocorrelation = more predictable/stable behavior.
        """
        if len(values) < 10:
            return 0.5
        
        mean = sum(values) / len(values)
        
        # Lag-1 autocorrelation
        numerator = sum((values[i] - mean) * (values[i + 1] - mean) for i in range(len(values) - 1))
        denominator = sum((x - mean) ** 2 for x in values)
        
        if denominator == 0:
            return 0.5
        
        autocorr = numerator / denominator
        
        # Convert to score (we want positive autocorrelation for stability)
        # Negative autocorrelation indicates mean-reversion/instability
        if autocorr >= 0:
            return min(1.0, 0.5 + autocorr * 0.5)
        else:
            return max(0.0, 0.5 + autocorr * 0.5)


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FeatureStabilityEngine] = None


def get_stability_engine() -> FeatureStabilityEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FeatureStabilityEngine()
    return _engine
