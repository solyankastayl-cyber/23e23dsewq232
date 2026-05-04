"""
PHASE 17.2 — Factor Governance Engine
======================================
Main aggregation engine for alpha-factor governance.

Combines 5 dimensions:
- Performance (30%)
- Regime (20%)
- Capacity (15%)
- Crowding (15%)
- Decay (20%)

Key Difference from Feature Governance:
    - Feature Governance: creates control signals
    - Factor Governance: AFFECTS CAPITAL ALLOCATION
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

from modules.research_control.factor_governance.factor_governance_types import (
    FactorGovernanceResult,
    FactorGovernanceState,
    FactorDimension,
    FactorDimensionResult,
    FACTOR_GOVERNANCE_THRESHOLDS,
    FACTOR_GOVERNANCE_WEIGHTS,
    FACTOR_GOVERNANCE_MODIFIERS,
)
from modules.research_control.factor_governance.factor_performance_engine import get_performance_engine
from modules.research_control.factor_governance.factor_regime_engine import get_regime_engine
from modules.research_control.factor_governance.factor_capacity_engine import get_capacity_engine
from modules.research_control.factor_governance.factor_crowding_engine import get_crowding_engine
from modules.research_control.factor_governance.factor_decay_engine import get_decay_engine


# ══════════════════════════════════════════════════════════════
# KNOWN FACTORS REGISTRY
# ══════════════════════════════════════════════════════════════

KNOWN_FACTORS = {
    "trend_breakout_factor": {
        "description": "Breakout trading on strong trends",
        "category": "momentum",
        "risk_tier": "high",
    },
    "mean_reversion_factor": {
        "description": "Mean reversion in ranging markets",
        "category": "mean_reversion",
        "risk_tier": "medium",
    },
    "funding_arb_factor": {
        "description": "Funding rate arbitrage",
        "category": "exchange",
        "risk_tier": "medium",
    },
    "liquidation_cascade_factor": {
        "description": "Liquidation cascade prediction",
        "category": "exchange",
        "risk_tier": "high",
    },
    "structure_break_factor": {
        "description": "Market structure break signals",
        "category": "structure",
        "risk_tier": "medium",
    },
    "divergence_factor": {
        "description": "Price/indicator divergence signals",
        "category": "momentum",
        "risk_tier": "medium",
    },
    "flow_imbalance_factor": {
        "description": "Order flow imbalance alpha",
        "category": "exchange",
        "risk_tier": "high",
    },
    "volatility_regime_factor": {
        "description": "Volatility regime switching",
        "category": "volatility",
        "risk_tier": "medium",
    },
    "dominance_shift_factor": {
        "description": "Market dominance shift signals",
        "category": "breadth",
        "risk_tier": "low",
    },
    "cross_asset_factor": {
        "description": "Cross-asset correlation signals",
        "category": "correlation",
        "risk_tier": "medium",
    },
}


# ══════════════════════════════════════════════════════════════
# FACTOR GOVERNANCE ENGINE
# ══════════════════════════════════════════════════════════════

class FactorGovernanceEngine:
    """
    Factor Governance Engine - PHASE 17.2
    
    Second layer of Research Control Fabric.
    Evaluates alpha-factor quality across 5 dimensions.
    
    Purpose:
        Determine which factors deserve capital allocation.
        Creates CAPITAL MODIFIERS (more impactful than feature governance).
    
    Dimensions:
        1. Performance (30%) - Return stability
        2. Regime (20%) - Works across market regimes
        3. Capacity (15%) - Handles capital scaling
        4. Crowding (15%) - Not overcrowded
        5. Decay (20%) - Slow alpha decay
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Sub-engines
        self.performance_engine = get_performance_engine()
        self.regime_engine = get_regime_engine()
        self.capacity_engine = get_capacity_engine()
        self.crowding_engine = get_crowding_engine()
        self.decay_engine = get_decay_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN EVALUATION
    # ═══════════════════════════════════════════════════════════
    
    def evaluate(self, factor_name: str) -> FactorGovernanceResult:
        """
        Evaluate governance state for a factor.
        
        Args:
            factor_name: Name of the factor to evaluate
        
        Returns:
            FactorGovernanceResult with full governance assessment
        """
        now = datetime.now(timezone.utc)
        
        # Get factor data (simulated for now)
        factor_data = self._get_factor_data(factor_name)
        
        # Evaluate each dimension
        performance_result = self._evaluate_performance(factor_name, factor_data)
        regime_result = self._evaluate_regime(factor_name, factor_data)
        capacity_result = self._evaluate_capacity(factor_name, factor_data)
        crowding_result = self._evaluate_crowding(factor_name, factor_data)
        decay_result = self._evaluate_decay(factor_name, factor_data)
        
        dimension_results = [
            performance_result,
            regime_result,
            capacity_result,
            crowding_result,
            decay_result,
        ]
        
        # Calculate governance score
        governance_score = self._calculate_governance_score(
            performance_result.score,
            regime_result.score,
            capacity_result.score,
            crowding_result.score,
            decay_result.score,
        )
        
        # Determine governance state
        governance_state = self._determine_state(governance_score)
        
        # Get modifiers
        modifiers = FACTOR_GOVERNANCE_MODIFIERS[governance_state]
        capital_modifier = modifiers["capital_modifier"]
        confidence_modifier = modifiers["confidence_modifier"]
        
        # Find weakest and strongest dimensions
        weakest, strongest = self._find_extremes(dimension_results)
        
        # Build drivers
        drivers = self._build_drivers(factor_name, factor_data, dimension_results)
        
        return FactorGovernanceResult(
            factor_name=factor_name,
            timestamp=now,
            performance_score=performance_result.score,
            regime_score=regime_result.score,
            capacity_score=capacity_result.score,
            crowding_score=crowding_result.score,
            decay_score=decay_result.score,
            governance_score=governance_score,
            governance_state=governance_state,
            capital_modifier=capital_modifier,
            confidence_modifier=confidence_modifier,
            weakest_dimension=weakest,
            strongest_dimension=strongest,
            dimension_results=dimension_results,
            drivers=drivers,
        )
    
    def evaluate_from_scores(
        self,
        factor_name: str,
        performance_score: float,
        regime_score: float,
        capacity_score: float,
        crowding_score: float,
        decay_score: float,
    ) -> FactorGovernanceResult:
        """
        Evaluate with provided dimension scores (for testing).
        """
        now = datetime.now(timezone.utc)
        
        # Create dimension results
        dimension_results = [
            FactorDimensionResult(
                dimension=FactorDimension.PERFORMANCE,
                score=performance_score,
                status=self._score_to_status(performance_score),
                reason="Direct score input",
            ),
            FactorDimensionResult(
                dimension=FactorDimension.REGIME,
                score=regime_score,
                status=self._score_to_status(regime_score),
                reason="Direct score input",
            ),
            FactorDimensionResult(
                dimension=FactorDimension.CAPACITY,
                score=capacity_score,
                status=self._score_to_status(capacity_score),
                reason="Direct score input",
            ),
            FactorDimensionResult(
                dimension=FactorDimension.CROWDING,
                score=crowding_score,
                status=self._score_to_status(crowding_score),
                reason="Direct score input",
            ),
            FactorDimensionResult(
                dimension=FactorDimension.DECAY,
                score=decay_score,
                status=self._score_to_status(decay_score),
                reason="Direct score input",
            ),
        ]
        
        # Calculate governance score
        governance_score = self._calculate_governance_score(
            performance_score,
            regime_score,
            capacity_score,
            crowding_score,
            decay_score,
        )
        
        # Determine state
        governance_state = self._determine_state(governance_score)
        
        # Get modifiers
        modifiers = FACTOR_GOVERNANCE_MODIFIERS[governance_state]
        capital_modifier = modifiers["capital_modifier"]
        confidence_modifier = modifiers["confidence_modifier"]
        
        # Find extremes
        weakest, strongest = self._find_extremes(dimension_results)
        
        return FactorGovernanceResult(
            factor_name=factor_name,
            timestamp=now,
            performance_score=performance_score,
            regime_score=regime_score,
            capacity_score=capacity_score,
            crowding_score=crowding_score,
            decay_score=decay_score,
            governance_score=governance_score,
            governance_state=governance_state,
            capital_modifier=capital_modifier,
            confidence_modifier=confidence_modifier,
            weakest_dimension=weakest,
            strongest_dimension=strongest,
            dimension_results=dimension_results,
            drivers={},
        )
    
    # ═══════════════════════════════════════════════════════════
    # DIMENSION EVALUATORS
    # ═══════════════════════════════════════════════════════════
    
    def _evaluate_performance(self, factor_name: str, data: Dict) -> FactorDimensionResult:
        """Evaluate performance dimension."""
        return self.performance_engine.evaluate_from_scores(
            factor_name,
            sharpe_score=data.get("sharpe_score", 0.7),
            sortino_score=data.get("sortino_score", 0.7),
            calmar_score=data.get("calmar_score", 0.65),
            win_rate_score=data.get("win_rate_score", 0.6),
            profit_factor_score=data.get("profit_factor_score", 0.65),
        )
    
    def _evaluate_regime(self, factor_name: str, data: Dict) -> FactorDimensionResult:
        """Evaluate regime dimension."""
        return self.regime_engine.evaluate_from_scores(
            factor_name,
            bull_score=data.get("bull_score", 0.75),
            bear_score=data.get("bear_score", 0.70),
            sideways_score=data.get("sideways_score", 0.65),
            high_vol_score=data.get("high_vol_score", 0.72),
            low_vol_score=data.get("low_vol_score", 0.68),
        )
    
    def _evaluate_capacity(self, factor_name: str, data: Dict) -> FactorDimensionResult:
        """Evaluate capacity dimension."""
        return self.capacity_engine.evaluate_from_scores(
            factor_name,
            utilization_score=data.get("utilization_score", 0.70),
            slippage_score=data.get("slippage_score", 0.75),
            market_impact_score=data.get("market_impact_score", 0.70),
            scalability_score=data.get("scalability_score", 0.65),
        )
    
    def _evaluate_crowding(self, factor_name: str, data: Dict) -> FactorDimensionResult:
        """Evaluate crowding dimension."""
        return self.crowding_engine.evaluate_from_scores(
            factor_name,
            market_corr_score=data.get("market_corr_score", 0.65),
            uniqueness_score=data.get("uniqueness_score", 0.70),
            flow_corr_score=data.get("flow_corr_score", 0.60),
            crowding_score=data.get("crowding_indicator_score", 0.55),
        )
    
    def _evaluate_decay(self, factor_name: str, data: Dict) -> FactorDimensionResult:
        """Evaluate decay dimension."""
        return self.decay_engine.evaluate_from_scores(
            factor_name,
            half_life_score=data.get("half_life_score", 0.70),
            trend_score=data.get("trend_score", 0.72),
            ir_stability_score=data.get("ir_stability_score", 0.68),
        )
    
    # ═══════════════════════════════════════════════════════════
    # AGGREGATION
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_governance_score(
        self,
        performance: float,
        regime: float,
        capacity: float,
        crowding: float,
        decay: float,
    ) -> float:
        """
        Calculate aggregated governance score.
        
        Formula:
            score = 0.30 * performance
                  + 0.20 * regime
                  + 0.15 * capacity
                  + 0.15 * crowding
                  + 0.20 * decay
        """
        score = (
            FACTOR_GOVERNANCE_WEIGHTS["performance"] * performance +
            FACTOR_GOVERNANCE_WEIGHTS["regime"] * regime +
            FACTOR_GOVERNANCE_WEIGHTS["capacity"] * capacity +
            FACTOR_GOVERNANCE_WEIGHTS["crowding"] * crowding +
            FACTOR_GOVERNANCE_WEIGHTS["decay"] * decay
        )
        return min(1.0, max(0.0, score))
    
    def _determine_state(self, score: float) -> FactorGovernanceState:
        """Determine governance state from score."""
        if score > FACTOR_GOVERNANCE_THRESHOLDS["elite_min"]:
            return FactorGovernanceState.ELITE
        elif score > FACTOR_GOVERNANCE_THRESHOLDS["stable_min"]:
            return FactorGovernanceState.STABLE
        elif score > FACTOR_GOVERNANCE_THRESHOLDS["watchlist_min"]:
            return FactorGovernanceState.WATCHLIST
        elif score > FACTOR_GOVERNANCE_THRESHOLDS["degraded_min"]:
            return FactorGovernanceState.DEGRADED
        else:
            return FactorGovernanceState.RETIRE
    
    def _find_extremes(
        self, 
        dimension_results: List[FactorDimensionResult]
    ) -> tuple[FactorDimension, FactorDimension]:
        """Find weakest and strongest dimensions."""
        sorted_dims = sorted(dimension_results, key=lambda x: x.score)
        weakest = sorted_dims[0].dimension
        strongest = sorted_dims[-1].dimension
        return (weakest, strongest)
    
    def _score_to_status(self, score: float) -> str:
        """Convert score to status string."""
        if score >= 0.80:
            return "EXCELLENT"
        elif score >= 0.65:
            return "GOOD"
        elif score >= 0.50:
            return "WARNING"
        else:
            return "POOR"
    
    # ═══════════════════════════════════════════════════════════
    # DATA GATHERING
    # ═══════════════════════════════════════════════════════════
    
    def _get_factor_data(self, factor_name: str) -> Dict[str, Any]:
        """
        Get factor data for evaluation.
        
        In production, this would:
        - Fetch historical performance from database
        - Calculate regime-specific metrics
        - Get capacity utilization data
        
        For now, returns simulated realistic data.
        """
        if factor_name not in KNOWN_FACTORS:
            return self._get_default_factor_data(factor_name)
        
        factor_config = KNOWN_FACTORS[factor_name]
        category = factor_config.get("category", "unknown")
        risk_tier = factor_config.get("risk_tier", "medium")
        
        # Different categories have different characteristics
        if category == "momentum":
            return self._get_momentum_factor_data(factor_name, risk_tier)
        elif category == "mean_reversion":
            return self._get_mean_reversion_factor_data(factor_name, risk_tier)
        elif category == "exchange":
            return self._get_exchange_factor_data(factor_name, risk_tier)
        elif category == "volatility":
            return self._get_volatility_factor_data(factor_name, risk_tier)
        else:
            return self._get_default_factor_data(factor_name)
    
    def _get_momentum_factor_data(self, name: str, risk: str) -> Dict:
        """Data for momentum factors."""
        return {
            # Performance
            "sharpe_score": 0.82,
            "sortino_score": 0.78,
            "calmar_score": 0.70,
            "win_rate_score": 0.55,
            "profit_factor_score": 0.72,
            # Regime
            "bull_score": 0.85,
            "bear_score": 0.60,
            "sideways_score": 0.50,
            "high_vol_score": 0.75,
            "low_vol_score": 0.65,
            # Capacity
            "utilization_score": 0.75,
            "slippage_score": 0.70,
            "market_impact_score": 0.68,
            "scalability_score": 0.72,
            # Crowding
            "market_corr_score": 0.60,
            "uniqueness_score": 0.65,
            "flow_corr_score": 0.55,
            "crowding_indicator_score": 0.58,
            # Decay
            "half_life_score": 0.72,
            "trend_score": 0.70,
            "ir_stability_score": 0.75,
        }
    
    def _get_mean_reversion_factor_data(self, name: str, risk: str) -> Dict:
        """Data for mean reversion factors."""
        return {
            # Performance
            "sharpe_score": 0.75,
            "sortino_score": 0.80,
            "calmar_score": 0.85,
            "win_rate_score": 0.70,
            "profit_factor_score": 0.65,
            # Regime
            "bull_score": 0.60,
            "bear_score": 0.65,
            "sideways_score": 0.90,  # Excels in sideways
            "high_vol_score": 0.55,
            "low_vol_score": 0.85,
            # Capacity
            "utilization_score": 0.80,
            "slippage_score": 0.82,
            "market_impact_score": 0.78,
            "scalability_score": 0.75,
            # Crowding
            "market_corr_score": 0.70,
            "uniqueness_score": 0.60,
            "flow_corr_score": 0.65,
            "crowding_indicator_score": 0.62,
            # Decay
            "half_life_score": 0.80,
            "trend_score": 0.75,
            "ir_stability_score": 0.78,
        }
    
    def _get_exchange_factor_data(self, name: str, risk: str) -> Dict:
        """Data for exchange-based factors."""
        return {
            # Performance
            "sharpe_score": 0.88,
            "sortino_score": 0.85,
            "calmar_score": 0.75,
            "win_rate_score": 0.65,
            "profit_factor_score": 0.80,
            # Regime
            "bull_score": 0.78,
            "bear_score": 0.82,
            "sideways_score": 0.72,
            "high_vol_score": 0.88,  # Excels in volatility
            "low_vol_score": 0.55,
            # Capacity
            "utilization_score": 0.65,  # Limited capacity
            "slippage_score": 0.60,
            "market_impact_score": 0.55,
            "scalability_score": 0.50,
            # Crowding
            "market_corr_score": 0.75,
            "uniqueness_score": 0.80,
            "flow_corr_score": 0.70,
            "crowding_indicator_score": 0.65,
            # Decay
            "half_life_score": 0.65,  # Faster decay
            "trend_score": 0.68,
            "ir_stability_score": 0.62,
        }
    
    def _get_volatility_factor_data(self, name: str, risk: str) -> Dict:
        """Data for volatility factors."""
        return {
            # Performance
            "sharpe_score": 0.78,
            "sortino_score": 0.82,
            "calmar_score": 0.88,
            "win_rate_score": 0.62,
            "profit_factor_score": 0.70,
            # Regime
            "bull_score": 0.70,
            "bear_score": 0.75,
            "sideways_score": 0.68,
            "high_vol_score": 0.85,
            "low_vol_score": 0.72,
            # Capacity
            "utilization_score": 0.72,
            "slippage_score": 0.78,
            "market_impact_score": 0.75,
            "scalability_score": 0.70,
            # Crowding
            "market_corr_score": 0.72,
            "uniqueness_score": 0.75,
            "flow_corr_score": 0.68,
            "crowding_indicator_score": 0.70,
            # Decay
            "half_life_score": 0.75,
            "trend_score": 0.78,
            "ir_stability_score": 0.72,
        }
    
    def _get_default_factor_data(self, name: str) -> Dict:
        """Default data for unknown factors."""
        return {
            "sharpe_score": 0.65,
            "sortino_score": 0.65,
            "calmar_score": 0.60,
            "win_rate_score": 0.55,
            "profit_factor_score": 0.60,
            "bull_score": 0.65,
            "bear_score": 0.60,
            "sideways_score": 0.55,
            "high_vol_score": 0.60,
            "low_vol_score": 0.58,
            "utilization_score": 0.65,
            "slippage_score": 0.65,
            "market_impact_score": 0.60,
            "scalability_score": 0.60,
            "market_corr_score": 0.55,
            "uniqueness_score": 0.55,
            "flow_corr_score": 0.50,
            "crowding_indicator_score": 0.50,
            "half_life_score": 0.60,
            "trend_score": 0.58,
            "ir_stability_score": 0.55,
        }
    
    def _build_drivers(
        self,
        factor_name: str,
        factor_data: Dict,
        dimension_results: List[FactorDimensionResult],
    ) -> Dict[str, Any]:
        """Build explainability drivers."""
        factor_config = KNOWN_FACTORS.get(factor_name, {})
        
        return {
            "factor_category": factor_config.get("category", "unknown"),
            "risk_tier": factor_config.get("risk_tier", "unknown"),
            "dimension_contributions": {
                "performance": round(dimension_results[0].score * FACTOR_GOVERNANCE_WEIGHTS["performance"], 4),
                "regime": round(dimension_results[1].score * FACTOR_GOVERNANCE_WEIGHTS["regime"], 4),
                "capacity": round(dimension_results[2].score * FACTOR_GOVERNANCE_WEIGHTS["capacity"], 4),
                "crowding": round(dimension_results[3].score * FACTOR_GOVERNANCE_WEIGHTS["crowding"], 4),
                "decay": round(dimension_results[4].score * FACTOR_GOVERNANCE_WEIGHTS["decay"], 4),
            },
            "warnings": [r.reason for r in dimension_results if r.status == "WARNING"],
            "poor_dimensions": [r.dimension.value for r in dimension_results if r.status == "POOR"],
        }
    
    # ═══════════════════════════════════════════════════════════
    # BATCH EVALUATION
    # ═══════════════════════════════════════════════════════════
    
    def evaluate_batch(self, factor_names: List[str]) -> Dict[str, FactorGovernanceResult]:
        """Evaluate multiple factors at once."""
        results = {}
        for name in factor_names:
            results[name] = self.evaluate(name)
        return results
    
    def get_all_known_factors(self) -> List[str]:
        """Get list of all known factors."""
        return list(KNOWN_FACTORS.keys())
    
    # ═══════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════
    
    def get_governance_for_factor(self, factor_name: str) -> Dict[str, Any]:
        """Get governance data for downstream integration."""
        result = self.evaluate(factor_name)
        
        return {
            "factor_name": factor_name,
            "governance_score": result.governance_score,
            "governance_state": result.governance_state.value,
            "capital_modifier": result.capital_modifier,
            "confidence_modifier": result.confidence_modifier,
            "weakest_dimension": result.weakest_dimension.value,
            "strongest_dimension": result.strongest_dimension.value,
            "requires_attention": result.governance_state in [
                FactorGovernanceState.DEGRADED, 
                FactorGovernanceState.RETIRE
            ],
        }


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[FactorGovernanceEngine] = None


def get_factor_governance_engine() -> FactorGovernanceEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FactorGovernanceEngine()
    return _engine
