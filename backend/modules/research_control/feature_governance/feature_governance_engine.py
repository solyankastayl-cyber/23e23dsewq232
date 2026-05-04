"""
PHASE 17.1 — Feature Governance Engine
=======================================
Main aggregation engine for feature quality governance.

Combines 5 dimensions:
- Stability (25%)
- Drift (20%)
- Coverage (15%)
- Redundancy (15%)
- Utility (25%)

Key Principle:
    Feature Governance creates CONTROL SIGNALS.
    It does NOT block the system directly.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")

from modules.research_control.feature_governance.feature_governance_types import (
    FeatureGovernanceState,
    GovernanceState,
    GovernanceDimension,
    DimensionResult,
    GOVERNANCE_THRESHOLDS,
    GOVERNANCE_WEIGHTS,
    GOVERNANCE_MODIFIERS,
)
from modules.research_control.feature_governance.feature_stability_engine import get_stability_engine
from modules.research_control.feature_governance.feature_drift_engine import get_drift_engine
from modules.research_control.feature_governance.feature_coverage_engine import get_coverage_engine
from modules.research_control.feature_governance.feature_redundancy_engine import get_redundancy_engine
from modules.research_control.feature_governance.feature_utility_engine import get_utility_engine


# ══════════════════════════════════════════════════════════════
# FEATURE REGISTRY (Known features for analysis)
# ══════════════════════════════════════════════════════════════

# These are example features that the system can evaluate
# In production, this would come from Feature Library
KNOWN_FEATURES = {
    "funding_skew": {
        "description": "Funding rate skew signal",
        "category": "exchange",
        "baseline_mean": 0.0,
        "baseline_std": 0.01,
    },
    "oi_change": {
        "description": "Open interest change rate",
        "category": "exchange",
        "baseline_mean": 0.0,
        "baseline_std": 0.05,
    },
    "flow_imbalance": {
        "description": "Order flow imbalance",
        "category": "exchange",
        "baseline_mean": 0.0,
        "baseline_std": 0.2,
    },
    "rsi_14": {
        "description": "14-period RSI",
        "category": "momentum",
        "baseline_mean": 50,
        "baseline_std": 15,
    },
    "macd_signal": {
        "description": "MACD signal line",
        "category": "momentum",
        "baseline_mean": 0.0,
        "baseline_std": 100,
    },
    "atr_normalized": {
        "description": "Normalized ATR",
        "category": "volatility",
        "baseline_mean": 0.02,
        "baseline_std": 0.01,
    },
    "trend_strength": {
        "description": "ADX-based trend strength",
        "category": "trend",
        "baseline_mean": 25,
        "baseline_std": 10,
    },
    "volume_zscore": {
        "description": "Volume z-score",
        "category": "volume",
        "baseline_mean": 0.0,
        "baseline_std": 1.0,
    },
    "liquidation_risk": {
        "description": "Liquidation cascade risk",
        "category": "exchange",
        "baseline_mean": 0.3,
        "baseline_std": 0.2,
    },
    "structure_quality": {
        "description": "Market structure quality score",
        "category": "structure",
        "baseline_mean": 0.5,
        "baseline_std": 0.2,
    },
}


# ══════════════════════════════════════════════════════════════
# FEATURE GOVERNANCE ENGINE
# ══════════════════════════════════════════════════════════════

class FeatureGovernanceEngine:
    """
    Feature Governance Engine - PHASE 17.1
    
    First layer of Research Control Fabric.
    Evaluates feature quality across 5 dimensions.
    
    Purpose:
        Determine which features are healthy, degrading, or should be retired.
        Creates control signals for downstream use.
    
    Dimensions:
        1. Stability (25%) - Feature consistency over time
        2. Drift (20%) - Distribution drift from baseline
        3. Coverage (15%) - Data availability
        4. Redundancy (15%) - Uniqueness of information
        5. Utility (25%) - Predictive value
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Sub-engines
        self.stability_engine = get_stability_engine()
        self.drift_engine = get_drift_engine()
        self.coverage_engine = get_coverage_engine()
        self.redundancy_engine = get_redundancy_engine()
        self.utility_engine = get_utility_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN EVALUATION
    # ═══════════════════════════════════════════════════════════
    
    def evaluate(self, feature_name: str) -> FeatureGovernanceState:
        """
        Evaluate governance state for a feature.
        
        Args:
            feature_name: Name of the feature to evaluate
        
        Returns:
            FeatureGovernanceState with full governance assessment
        """
        now = datetime.now(timezone.utc)
        
        # Get feature data (simulated for now)
        feature_data = self._get_feature_data(feature_name)
        
        # Evaluate each dimension
        stability_result = self._evaluate_stability(feature_name, feature_data)
        drift_result = self._evaluate_drift(feature_name, feature_data)
        coverage_result = self._evaluate_coverage(feature_name, feature_data)
        redundancy_result = self._evaluate_redundancy(feature_name, feature_data)
        utility_result = self._evaluate_utility(feature_name, feature_data)
        
        dimension_results = [
            stability_result,
            drift_result,
            coverage_result,
            redundancy_result,
            utility_result,
        ]
        
        # Calculate governance score
        governance_score = self._calculate_governance_score(
            stability_result.score,
            drift_result.score,
            coverage_result.score,
            redundancy_result.score,
            utility_result.score,
        )
        
        # Determine governance state
        governance_state = self._determine_state(governance_score)
        
        # Get modifiers
        modifiers = GOVERNANCE_MODIFIERS[governance_state]
        confidence_modifier = modifiers["confidence_modifier"]
        size_modifier = modifiers["size_modifier"]
        
        # Find weakest and strongest dimensions
        weakest, strongest = self._find_extremes(dimension_results)
        
        # Build drivers
        drivers = self._build_drivers(feature_name, feature_data, dimension_results)
        
        return FeatureGovernanceState(
            feature_name=feature_name,
            timestamp=now,
            stability_score=stability_result.score,
            drift_score=drift_result.score,
            coverage_score=coverage_result.score,
            redundancy_score=redundancy_result.score,
            utility_score=utility_result.score,
            governance_score=governance_score,
            governance_state=governance_state,
            confidence_modifier=confidence_modifier,
            size_modifier=size_modifier,
            weakest_dimension=weakest,
            strongest_dimension=strongest,
            dimension_results=dimension_results,
            drivers=drivers,
        )
    
    def evaluate_from_scores(
        self,
        feature_name: str,
        stability_score: float,
        drift_score: float,
        coverage_score: float,
        redundancy_score: float,
        utility_score: float,
    ) -> FeatureGovernanceState:
        """
        Evaluate with provided dimension scores (for testing).
        """
        now = datetime.now(timezone.utc)
        
        # Create dimension results
        dimension_results = [
            DimensionResult(
                dimension=GovernanceDimension.STABILITY,
                score=stability_score,
                status=self._score_to_status(stability_score),
                reason="Direct score input",
            ),
            DimensionResult(
                dimension=GovernanceDimension.DRIFT,
                score=drift_score,
                status=self._score_to_status(drift_score),
                reason="Direct score input",
            ),
            DimensionResult(
                dimension=GovernanceDimension.COVERAGE,
                score=coverage_score,
                status=self._score_to_status(coverage_score),
                reason="Direct score input",
            ),
            DimensionResult(
                dimension=GovernanceDimension.REDUNDANCY,
                score=redundancy_score,
                status=self._score_to_status(redundancy_score),
                reason="Direct score input",
            ),
            DimensionResult(
                dimension=GovernanceDimension.UTILITY,
                score=utility_score,
                status=self._score_to_status(utility_score),
                reason="Direct score input",
            ),
        ]
        
        # Calculate governance score
        governance_score = self._calculate_governance_score(
            stability_score,
            drift_score,
            coverage_score,
            redundancy_score,
            utility_score,
        )
        
        # Determine state
        governance_state = self._determine_state(governance_score)
        
        # Get modifiers
        modifiers = GOVERNANCE_MODIFIERS[governance_state]
        confidence_modifier = modifiers["confidence_modifier"]
        size_modifier = modifiers["size_modifier"]
        
        # Find extremes
        weakest, strongest = self._find_extremes(dimension_results)
        
        return FeatureGovernanceState(
            feature_name=feature_name,
            timestamp=now,
            stability_score=stability_score,
            drift_score=drift_score,
            coverage_score=coverage_score,
            redundancy_score=redundancy_score,
            utility_score=utility_score,
            governance_score=governance_score,
            governance_state=governance_state,
            confidence_modifier=confidence_modifier,
            size_modifier=size_modifier,
            weakest_dimension=weakest,
            strongest_dimension=strongest,
            dimension_results=dimension_results,
            drivers={},
        )
    
    # ═══════════════════════════════════════════════════════════
    # DIMENSION EVALUATORS
    # ═══════════════════════════════════════════════════════════
    
    def _evaluate_stability(self, feature_name: str, data: Dict) -> DimensionResult:
        """Evaluate stability dimension."""
        # Use pre-computed stability scores from data
        return self.stability_engine.evaluate_from_scores(
            feature_name,
            variance_stability=data.get("variance_stability", 0.7),
            mean_stability=data.get("mean_stability", 0.8),
            autocorr_stability=data.get("autocorr_stability", 0.6),
        )
    
    def _evaluate_drift(self, feature_name: str, data: Dict) -> DimensionResult:
        """Evaluate drift dimension."""
        return self.drift_engine.evaluate_from_scores(
            feature_name,
            mean_drift=data.get("mean_drift", 0.2),
            std_drift=data.get("std_drift", 0.15),
            range_drift=data.get("range_drift", 0.1),
        )
    
    def _evaluate_coverage(self, feature_name: str, data: Dict) -> DimensionResult:
        """Evaluate coverage dimension."""
        return self.coverage_engine.evaluate_from_rate(
            feature_name,
            coverage_rate=data.get("coverage_rate", 0.95),
        )
    
    def _evaluate_redundancy(self, feature_name: str, data: Dict) -> DimensionResult:
        """Evaluate redundancy dimension."""
        return self.redundancy_engine.evaluate_from_correlation(
            feature_name,
            max_correlation=data.get("max_correlation", 0.4),
            most_correlated_feature=data.get("most_correlated_feature"),
        )
    
    def _evaluate_utility(self, feature_name: str, data: Dict) -> DimensionResult:
        """Evaluate utility dimension."""
        return self.utility_engine.evaluate_from_scores(
            feature_name,
            ir_score=data.get("ir_score", 0.6),
            snr_score=data.get("snr_score", 0.7),
            ic_score=data.get("ic_score", 0.65),
        )
    
    # ═══════════════════════════════════════════════════════════
    # AGGREGATION
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_governance_score(
        self,
        stability: float,
        drift: float,
        coverage: float,
        redundancy: float,
        utility: float,
    ) -> float:
        """
        Calculate aggregated governance score.
        
        Formula:
            score = 0.25 * stability
                  + 0.20 * drift
                  + 0.15 * coverage
                  + 0.15 * redundancy
                  + 0.25 * utility
        """
        score = (
            GOVERNANCE_WEIGHTS["stability"] * stability +
            GOVERNANCE_WEIGHTS["drift"] * drift +
            GOVERNANCE_WEIGHTS["coverage"] * coverage +
            GOVERNANCE_WEIGHTS["redundancy"] * redundancy +
            GOVERNANCE_WEIGHTS["utility"] * utility
        )
        return min(1.0, max(0.0, score))
    
    def _determine_state(self, score: float) -> GovernanceState:
        """Determine governance state from score."""
        if score > GOVERNANCE_THRESHOLDS["healthy_min"]:
            return GovernanceState.HEALTHY
        elif score > GOVERNANCE_THRESHOLDS["watchlist_min"]:
            return GovernanceState.WATCHLIST
        elif score > GOVERNANCE_THRESHOLDS["degraded_min"]:
            return GovernanceState.DEGRADED
        else:
            return GovernanceState.RETIRE
    
    def _find_extremes(
        self, 
        dimension_results: List[DimensionResult]
    ) -> tuple[GovernanceDimension, GovernanceDimension]:
        """Find weakest and strongest dimensions."""
        sorted_dims = sorted(dimension_results, key=lambda x: x.score)
        weakest = sorted_dims[0].dimension
        strongest = sorted_dims[-1].dimension
        return (weakest, strongest)
    
    def _score_to_status(self, score: float) -> str:
        """Convert score to status string."""
        if score >= 0.75:
            return "GOOD"
        elif score >= 0.50:
            return "WARNING"
        else:
            return "POOR"
    
    # ═══════════════════════════════════════════════════════════
    # DATA GATHERING
    # ═══════════════════════════════════════════════════════════
    
    def _get_feature_data(self, feature_name: str) -> Dict[str, Any]:
        """
        Get feature data for evaluation.
        
        In production, this would:
        - Fetch historical values from database
        - Calculate statistics
        - Get correlation data
        
        For now, returns simulated realistic data.
        """
        # Check if feature is known
        if feature_name not in KNOWN_FEATURES:
            # Unknown feature - return moderate defaults
            return self._get_default_feature_data(feature_name)
        
        feature_config = KNOWN_FEATURES[feature_name]
        
        # Simulate realistic data based on feature type
        category = feature_config.get("category", "unknown")
        
        # Different categories have different characteristics
        if category == "exchange":
            return self._get_exchange_feature_data(feature_name, feature_config)
        elif category == "momentum":
            return self._get_momentum_feature_data(feature_name, feature_config)
        elif category == "volatility":
            return self._get_volatility_feature_data(feature_name, feature_config)
        elif category == "trend":
            return self._get_trend_feature_data(feature_name, feature_config)
        else:
            return self._get_default_feature_data(feature_name)
    
    def _get_exchange_feature_data(self, name: str, config: Dict) -> Dict:
        """Get data for exchange features (funding, OI, flow)."""
        # Exchange features typically have:
        # - High stability
        # - Moderate drift
        # - Good coverage
        # - Some redundancy with each other
        return {
            "variance_stability": 0.82,
            "mean_stability": 0.78,
            "autocorr_stability": 0.70,
            "mean_drift": 0.15,
            "std_drift": 0.12,
            "range_drift": 0.10,
            "coverage_rate": 0.95,
            "max_correlation": 0.55 if "funding" in name else 0.45,
            "most_correlated_feature": "oi_change" if "funding" in name else "flow_imbalance",
            "ir_score": 0.65,
            "snr_score": 0.70,
            "ic_score": 0.72,
        }
    
    def _get_momentum_feature_data(self, name: str, config: Dict) -> Dict:
        """Get data for momentum features (RSI, MACD)."""
        return {
            "variance_stability": 0.75,
            "mean_stability": 0.85,
            "autocorr_stability": 0.80,
            "mean_drift": 0.08,
            "std_drift": 0.10,
            "range_drift": 0.05,
            "coverage_rate": 0.99,  # Always available
            "max_correlation": 0.70,  # Momentum features correlate
            "most_correlated_feature": "macd_signal" if "rsi" in name else "rsi_14",
            "ir_score": 0.55,
            "snr_score": 0.60,
            "ic_score": 0.58,
        }
    
    def _get_volatility_feature_data(self, name: str, config: Dict) -> Dict:
        """Get data for volatility features (ATR)."""
        return {
            "variance_stability": 0.65,  # Volatility is naturally unstable
            "mean_stability": 0.70,
            "autocorr_stability": 0.85,
            "mean_drift": 0.25,  # Volatility regimes shift
            "std_drift": 0.30,
            "range_drift": 0.20,
            "coverage_rate": 0.99,
            "max_correlation": 0.35,  # Unique info
            "most_correlated_feature": "volume_zscore",
            "ir_score": 0.70,
            "snr_score": 0.65,
            "ic_score": 0.68,
        }
    
    def _get_trend_feature_data(self, name: str, config: Dict) -> Dict:
        """Get data for trend features (ADX)."""
        return {
            "variance_stability": 0.78,
            "mean_stability": 0.75,
            "autocorr_stability": 0.82,
            "mean_drift": 0.12,
            "std_drift": 0.15,
            "range_drift": 0.10,
            "coverage_rate": 0.98,
            "max_correlation": 0.45,
            "most_correlated_feature": "macd_signal",
            "ir_score": 0.72,
            "snr_score": 0.75,
            "ic_score": 0.70,
        }
    
    def _get_default_feature_data(self, name: str) -> Dict:
        """Default data for unknown features."""
        return {
            "variance_stability": 0.70,
            "mean_stability": 0.70,
            "autocorr_stability": 0.65,
            "mean_drift": 0.20,
            "std_drift": 0.20,
            "range_drift": 0.15,
            "coverage_rate": 0.90,
            "max_correlation": 0.50,
            "most_correlated_feature": None,
            "ir_score": 0.55,
            "snr_score": 0.55,
            "ic_score": 0.55,
        }
    
    def _build_drivers(
        self,
        feature_name: str,
        feature_data: Dict,
        dimension_results: List[DimensionResult],
    ) -> Dict[str, Any]:
        """Build explainability drivers."""
        return {
            "feature_category": KNOWN_FEATURES.get(feature_name, {}).get("category", "unknown"),
            "dimension_contributions": {
                "stability": round(dimension_results[0].score * GOVERNANCE_WEIGHTS["stability"], 4),
                "drift": round(dimension_results[1].score * GOVERNANCE_WEIGHTS["drift"], 4),
                "coverage": round(dimension_results[2].score * GOVERNANCE_WEIGHTS["coverage"], 4),
                "redundancy": round(dimension_results[3].score * GOVERNANCE_WEIGHTS["redundancy"], 4),
                "utility": round(dimension_results[4].score * GOVERNANCE_WEIGHTS["utility"], 4),
            },
            "most_correlated_feature": feature_data.get("most_correlated_feature"),
            "warnings": [r.reason for r in dimension_results if r.status == "WARNING"],
            "poor_dimensions": [r.dimension.value for r in dimension_results if r.status == "POOR"],
        }
    
    # ═══════════════════════════════════════════════════════════
    # BATCH EVALUATION
    # ═══════════════════════════════════════════════════════════
    
    def evaluate_batch(self, feature_names: List[str]) -> Dict[str, FeatureGovernanceState]:
        """
        Evaluate multiple features at once.
        """
        results = {}
        for name in feature_names:
            results[name] = self.evaluate(name)
        return results
    
    def get_all_known_features(self) -> List[str]:
        """Get list of all known features."""
        return list(KNOWN_FEATURES.keys())
    
    # ═══════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════
    
    def get_governance_for_feature(self, feature_name: str) -> Dict[str, Any]:
        """
        Get governance data for downstream integration.
        """
        result = self.evaluate(feature_name)
        
        return {
            "feature_name": feature_name,
            "governance_score": result.governance_score,
            "governance_state": result.governance_state.value,
            "confidence_modifier": result.confidence_modifier,
            "size_modifier": result.size_modifier,
            "weakest_dimension": result.weakest_dimension.value,
            "strongest_dimension": result.strongest_dimension.value,
            "requires_attention": result.governance_state in [GovernanceState.DEGRADED, GovernanceState.RETIRE],
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FeatureGovernanceEngine] = None


def get_feature_governance_engine() -> FeatureGovernanceEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FeatureGovernanceEngine()
    return _engine
