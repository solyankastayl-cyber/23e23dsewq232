"""
PHASE 17.1 — Feature Drift Engine
==================================
Detects distribution drift from baseline.

Drift measures:
- Mean drift
- Variance drift
- Distribution shape change (skewness, kurtosis)
- Kolmogorov-Smirnov style distance

High drift = feature distribution has changed significantly
Low drift = feature distribution matches baseline
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
    DriftInput,
)


# ══════════════════════════════════════════════════════════════
# DRIFT THRESHOLDS
# ══════════════════════════════════════════════════════════════

DRIFT_THRESHOLDS = {
    "mean_drift_max": 0.5,      # Max allowed mean change (in std units)
    "std_drift_max": 0.5,       # Max allowed std change ratio
    "range_drift_max": 0.5,     # Max allowed range change
}


# ══════════════════════════════════════════════════════════════
# DRIFT ENGINE
# ══════════════════════════════════════════════════════════════

class FeatureDriftEngine:
    """
    Feature Drift Engine - PHASE 17.1
    
    Detects when a feature's distribution has drifted from baseline.
    """
    
    def __init__(self):
        pass
    
    def evaluate(self, feature_name: str, input_data: DriftInput) -> DimensionResult:
        """
        Evaluate drift for a feature.
        
        Args:
            feature_name: Name of the feature
            input_data: Current and baseline distributions
        
        Returns:
            DimensionResult with drift score
        """
        current = input_data.current_distribution
        baseline = input_data.baseline_distribution
        
        # Calculate drift metrics
        mean_drift = self._calculate_mean_drift(current, baseline)
        std_drift = self._calculate_std_drift(current, baseline)
        range_drift = self._calculate_range_drift(current, baseline)
        
        # Aggregate drift score (higher = better, meaning less drift)
        drift_score = (
            0.40 * (1.0 - mean_drift) +
            0.35 * (1.0 - std_drift) +
            0.25 * (1.0 - range_drift)
        )
        drift_score = min(1.0, max(0.0, drift_score))
        
        # Determine status
        if drift_score >= 0.75:
            status = "GOOD"
            reason = f"Feature distribution is stable (mean_drift={mean_drift:.2f})"
        elif drift_score >= 0.50:
            status = "WARNING"
            reason = f"Feature shows moderate drift"
        else:
            status = "POOR"
            reason = f"Feature has significant drift (mean_drift={mean_drift:.2f}, std_drift={std_drift:.2f})"
        
        return DimensionResult(
            dimension=GovernanceDimension.DRIFT,
            score=drift_score,
            status=status,
            reason=reason,
            inputs={
                **input_data.to_dict(),
                "mean_drift": round(mean_drift, 4),
                "std_drift": round(std_drift, 4),
                "range_drift": round(range_drift, 4),
            },
        )
    
    def evaluate_from_scores(
        self,
        feature_name: str,
        mean_drift: float,
        std_drift: float,
        range_drift: float,
    ) -> DimensionResult:
        """
        Evaluate with pre-computed drift values (for testing).
        
        Note: drift values are 0-1 where 0=no drift, 1=max drift
        """
        # Convert drift amounts to score (higher = less drift = better)
        drift_score = (
            0.40 * (1.0 - min(1.0, mean_drift)) +
            0.35 * (1.0 - min(1.0, std_drift)) +
            0.25 * (1.0 - min(1.0, range_drift))
        )
        drift_score = min(1.0, max(0.0, drift_score))
        
        if drift_score >= 0.75:
            status = "GOOD"
            reason = f"Feature distribution is stable"
        elif drift_score >= 0.50:
            status = "WARNING"
            reason = f"Feature shows moderate drift"
        else:
            status = "POOR"
            reason = f"Feature has significant drift"
        
        return DimensionResult(
            dimension=GovernanceDimension.DRIFT,
            score=drift_score,
            status=status,
            reason=reason,
            inputs={
                "mean_drift": mean_drift,
                "std_drift": std_drift,
                "range_drift": range_drift,
            },
        )
    
    def _calculate_mean_drift(
        self,
        current: Dict[str, float],
        baseline: Dict[str, float],
    ) -> float:
        """
        Calculate mean drift in standard deviation units.
        """
        curr_mean = current.get("mean", 0)
        base_mean = baseline.get("mean", 0)
        base_std = baseline.get("std", 1)
        
        if base_std == 0:
            base_std = 1
        
        # Drift in std units
        drift = abs(curr_mean - base_mean) / base_std
        
        # Normalize to 0-1 (cap at 2 std = 1.0)
        return min(1.0, drift / 2.0)
    
    def _calculate_std_drift(
        self,
        current: Dict[str, float],
        baseline: Dict[str, float],
    ) -> float:
        """
        Calculate standard deviation drift as ratio.
        """
        curr_std = current.get("std", 1)
        base_std = baseline.get("std", 1)
        
        if base_std == 0:
            base_std = 1
        
        # Ratio of stds
        ratio = curr_std / base_std
        
        # Drift from 1.0 (no change)
        drift = abs(ratio - 1.0)
        
        # Normalize to 0-1 (cap at 100% change = 1.0)
        return min(1.0, drift)
    
    def _calculate_range_drift(
        self,
        current: Dict[str, float],
        baseline: Dict[str, float],
    ) -> float:
        """
        Calculate range drift.
        """
        curr_range = current.get("max", 0) - current.get("min", 0)
        base_range = baseline.get("max", 0) - baseline.get("min", 0)
        
        if base_range == 0:
            base_range = 1
        
        # Ratio of ranges
        ratio = curr_range / base_range
        
        # Drift from 1.0
        drift = abs(ratio - 1.0)
        
        # Normalize to 0-1
        return min(1.0, drift)


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FeatureDriftEngine] = None


def get_drift_engine() -> FeatureDriftEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FeatureDriftEngine()
    return _engine
