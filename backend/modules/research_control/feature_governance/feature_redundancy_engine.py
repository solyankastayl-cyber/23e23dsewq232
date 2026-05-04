"""
PHASE 17.1 — Feature Redundancy Engine
=======================================
Detects feature duplication and correlation.

Redundancy measures:
- Pairwise correlation with other features
- Feature clustering similarity
- Information overlap

Low redundancy = feature provides unique information
High redundancy = feature duplicates existing features
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
    RedundancyInput,
)


# ══════════════════════════════════════════════════════════════
# REDUNDANCY THRESHOLDS
# ══════════════════════════════════════════════════════════════

REDUNDANCY_THRESHOLDS = {
    "correlation_high": 0.85,    # > 0.85 correlation = highly redundant
    "correlation_medium": 0.70,  # > 0.70 correlation = moderately redundant
    "correlation_low": 0.50,     # > 0.50 correlation = somewhat redundant
}


# ══════════════════════════════════════════════════════════════
# REDUNDANCY ENGINE
# ══════════════════════════════════════════════════════════════

class FeatureRedundancyEngine:
    """
    Feature Redundancy Engine - PHASE 17.1
    
    Detects when a feature duplicates information from other features.
    """
    
    def __init__(self):
        pass
    
    def evaluate(self, feature_name: str, input_data: RedundancyInput) -> DimensionResult:
        """
        Evaluate redundancy for a feature.
        
        Args:
            feature_name: Name of the feature
            input_data: Correlation data with other features
        
        Returns:
            DimensionResult with redundancy score
        """
        max_corr = abs(input_data.max_correlation)
        most_correlated = input_data.most_correlated_feature
        
        # Score: lower correlation = higher score (less redundant = better)
        # Map: 0 correlation -> 1.0 score, 1.0 correlation -> 0.0 score
        redundancy_score = 1.0 - max_corr
        
        # Determine status
        if max_corr >= REDUNDANCY_THRESHOLDS["correlation_high"]:
            status = "POOR"
            reason = f"Highly redundant with {most_correlated} (r={max_corr:.2f})"
        elif max_corr >= REDUNDANCY_THRESHOLDS["correlation_medium"]:
            status = "WARNING"
            reason = f"Moderately redundant with {most_correlated} (r={max_corr:.2f})"
        elif max_corr >= REDUNDANCY_THRESHOLDS["correlation_low"]:
            status = "WARNING"
            reason = f"Some redundancy with {most_correlated} (r={max_corr:.2f})"
        else:
            status = "GOOD"
            reason = f"Feature provides unique information"
        
        return DimensionResult(
            dimension=GovernanceDimension.REDUNDANCY,
            score=redundancy_score,
            status=status,
            reason=reason,
            inputs={
                **input_data.to_dict(),
                "redundancy_score": round(redundancy_score, 4),
            },
        )
    
    def evaluate_from_correlation(
        self,
        feature_name: str,
        max_correlation: float,
        most_correlated_feature: Optional[str] = None,
    ) -> DimensionResult:
        """
        Evaluate with pre-computed correlation (for testing).
        """
        max_corr = abs(min(1.0, max(0.0, max_correlation)))
        redundancy_score = 1.0 - max_corr
        
        if max_corr >= REDUNDANCY_THRESHOLDS["correlation_high"]:
            status = "POOR"
            reason = f"Highly redundant"
        elif max_corr >= REDUNDANCY_THRESHOLDS["correlation_medium"]:
            status = "WARNING"
            reason = f"Moderately redundant"
        elif max_corr >= REDUNDANCY_THRESHOLDS["correlation_low"]:
            status = "WARNING"
            reason = f"Some redundancy"
        else:
            status = "GOOD"
            reason = f"Feature provides unique information"
        
        return DimensionResult(
            dimension=GovernanceDimension.REDUNDANCY,
            score=redundancy_score,
            status=status,
            reason=reason,
            inputs={
                "max_correlation": max_correlation,
                "most_correlated_feature": most_correlated_feature,
            },
        )


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FeatureRedundancyEngine] = None


def get_redundancy_engine() -> FeatureRedundancyEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FeatureRedundancyEngine()
    return _engine
