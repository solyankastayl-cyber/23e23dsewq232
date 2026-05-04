"""
PHASE 17.1 — Feature Utility Engine
====================================
Evaluates predictive utility of a feature.

Utility measures:
- Information Ratio (IR)
- Signal-to-Noise Ratio (SNR)
- Information Coefficient (IC) / Predictive Power
- Risk-adjusted contribution

High utility = feature provides valuable signal
Low utility = feature is noisy or uninformative
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
    UtilityInput,
)


# ══════════════════════════════════════════════════════════════
# UTILITY THRESHOLDS
# ══════════════════════════════════════════════════════════════

UTILITY_THRESHOLDS = {
    "ir_good": 0.5,          # IR > 0.5 = strong signal
    "ir_moderate": 0.2,      # IR > 0.2 = moderate signal
    "snr_good": 1.5,         # SNR > 1.5 = good signal quality
    "snr_moderate": 1.0,     # SNR > 1.0 = moderate quality
    "ic_good": 0.05,         # IC > 0.05 = useful predictor
    "ic_moderate": 0.02,     # IC > 0.02 = marginal predictor
}


# ══════════════════════════════════════════════════════════════
# UTILITY ENGINE
# ══════════════════════════════════════════════════════════════

class FeatureUtilityEngine:
    """
    Feature Utility Engine - PHASE 17.1
    
    Evaluates how useful a feature is for prediction.
    """
    
    def __init__(self):
        pass
    
    def evaluate(self, feature_name: str, input_data: UtilityInput) -> DimensionResult:
        """
        Evaluate utility for a feature.
        
        Args:
            feature_name: Name of the feature
            input_data: Utility metrics
        
        Returns:
            DimensionResult with utility score
        """
        ir = input_data.information_ratio
        snr = input_data.signal_to_noise
        ic = input_data.predictive_power
        
        # Normalize each metric to 0-1
        ir_score = self._normalize_ir(ir)
        snr_score = self._normalize_snr(snr)
        ic_score = self._normalize_ic(ic)
        
        # Aggregate utility score
        utility_score = (
            0.35 * ir_score +
            0.30 * snr_score +
            0.35 * ic_score
        )
        utility_score = min(1.0, max(0.0, utility_score))
        
        # Determine status
        if utility_score >= 0.70:
            status = "GOOD"
            reason = f"High predictive utility (IR={ir:.2f}, IC={ic:.3f})"
        elif utility_score >= 0.45:
            status = "WARNING"
            reason = f"Moderate predictive utility"
        else:
            status = "POOR"
            reason = f"Low predictive utility (IR={ir:.2f}, IC={ic:.3f})"
        
        return DimensionResult(
            dimension=GovernanceDimension.UTILITY,
            score=utility_score,
            status=status,
            reason=reason,
            inputs={
                **input_data.to_dict(),
                "ir_score": round(ir_score, 4),
                "snr_score": round(snr_score, 4),
                "ic_score": round(ic_score, 4),
            },
        )
    
    def evaluate_from_scores(
        self,
        feature_name: str,
        ir_score: float,
        snr_score: float,
        ic_score: float,
    ) -> DimensionResult:
        """
        Evaluate with pre-computed normalized scores (for testing).
        Scores should be 0-1.
        """
        utility_score = (
            0.35 * min(1.0, max(0.0, ir_score)) +
            0.30 * min(1.0, max(0.0, snr_score)) +
            0.35 * min(1.0, max(0.0, ic_score))
        )
        utility_score = min(1.0, max(0.0, utility_score))
        
        if utility_score >= 0.70:
            status = "GOOD"
            reason = f"High predictive utility"
        elif utility_score >= 0.45:
            status = "WARNING"
            reason = f"Moderate predictive utility"
        else:
            status = "POOR"
            reason = f"Low predictive utility"
        
        return DimensionResult(
            dimension=GovernanceDimension.UTILITY,
            score=utility_score,
            status=status,
            reason=reason,
            inputs={
                "ir_score": ir_score,
                "snr_score": snr_score,
                "ic_score": ic_score,
            },
        )
    
    def _normalize_ir(self, ir: float) -> float:
        """Normalize Information Ratio to 0-1."""
        # IR typically ranges from -1 to 2+
        # Good IR > 0.5, Great IR > 1.0
        if ir <= 0:
            return max(0.0, 0.3 + ir * 0.3)  # Negative IR gets low score
        elif ir <= 0.5:
            return 0.3 + ir * 0.6  # 0 -> 0.3, 0.5 -> 0.6
        elif ir <= 1.0:
            return 0.6 + (ir - 0.5) * 0.4  # 0.5 -> 0.6, 1.0 -> 0.8
        else:
            return min(1.0, 0.8 + (ir - 1.0) * 0.2)  # 1.0+ -> 0.8-1.0
    
    def _normalize_snr(self, snr: float) -> float:
        """Normalize Signal-to-Noise Ratio to 0-1."""
        # SNR typically > 0, good if > 1.5
        if snr <= 0:
            return 0.0
        elif snr <= 1.0:
            return snr * 0.5  # 0 -> 0, 1 -> 0.5
        elif snr <= 2.0:
            return 0.5 + (snr - 1.0) * 0.3  # 1 -> 0.5, 2 -> 0.8
        else:
            return min(1.0, 0.8 + (snr - 2.0) * 0.1)  # 2+ -> 0.8-1.0
    
    def _normalize_ic(self, ic: float) -> float:
        """Normalize Information Coefficient to 0-1."""
        # IC typically ranges from -0.1 to 0.1
        # Good IC > 0.03, Great IC > 0.05
        if ic <= 0:
            return max(0.0, 0.2 + ic * 5)  # -0.04 -> 0, 0 -> 0.2
        elif ic <= 0.03:
            return 0.2 + (ic / 0.03) * 0.3  # 0 -> 0.2, 0.03 -> 0.5
        elif ic <= 0.05:
            return 0.5 + ((ic - 0.03) / 0.02) * 0.25  # 0.03 -> 0.5, 0.05 -> 0.75
        elif ic <= 0.10:
            return 0.75 + ((ic - 0.05) / 0.05) * 0.2  # 0.05 -> 0.75, 0.10 -> 0.95
        else:
            return min(1.0, 0.95 + (ic - 0.10) * 0.5)  # 0.10+ -> near 1.0


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FeatureUtilityEngine] = None


def get_utility_engine() -> FeatureUtilityEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FeatureUtilityEngine()
    return _engine
