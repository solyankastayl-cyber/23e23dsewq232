"""
PHASE 18.1 — Portfolio Risk Engine
===================================
Risk state determination and action recommendations.

Determines:
- Concentration score (STEP 7)
- Diversification score (STEP 8)
- Portfolio risk state (STEP 9)
- Recommended action (STEP 10)
- Modifiers (STEP 11)
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from modules.portfolio.portfolio_intelligence.portfolio_intelligence_types import (
    Position,
    MarketContext,
    PortfolioRiskState,
    RecommendedAction,
    RISK_STATE_MODIFIERS,
    CONCENTRATION_THRESHOLDS,
    GROSS_EXPOSURE_MAX,
)


# ══════════════════════════════════════════════════════════════
# PORTFOLIO RISK ENGINE
# ══════════════════════════════════════════════════════════════

class PortfolioRiskEngine:
    """
    Portfolio Risk Engine - PHASE 18.1 STEP 7-11
    
    Determines portfolio risk state and recommended actions.
    
    Risk State Rules:
    - concentration < 0.40 → BALANCED
    - 0.40 – 0.65 → CONCENTRATED
    - 0.65 – 0.80 → OVERLOADED
    - breadth weak + alt exposure high → DEFENSIVE
    """
    
    # ═══════════════════════════════════════════════════════════
    # STEP 7: CONCENTRATION SCORE
    # ═══════════════════════════════════════════════════════════
    
    def calculate_concentration_score(
        self,
        cluster_exposure: Dict[str, float],
        factor_exposure: Dict[str, float],
        asset_exposure: Dict[str, float],
    ) -> float:
        """
        Calculate concentration score.
        
        First version: max(cluster_exposure, factor_exposure, asset_exposure)
        Normalized to 0-1.
        
        Args:
            cluster_exposure: Cluster exposure dict
            factor_exposure: Factor exposure dict
            asset_exposure: Asset exposure dict (btc_exposure, eth_exposure, alt_exposure)
        
        Returns:
            Concentration score 0-1
        """
        max_values = []
        
        # Max from clusters
        if cluster_exposure:
            max_values.append(max(cluster_exposure.values()))
        
        # Max from factors
        if factor_exposure:
            max_values.append(max(factor_exposure.values()))
        
        # Max from assets
        if asset_exposure:
            asset_values = [
                asset_exposure.get("btc_exposure", 0),
                asset_exposure.get("eth_exposure", 0),
                asset_exposure.get("alt_exposure", 0),
            ]
            max_values.append(max(asset_values))
        
        if max_values:
            concentration = max(max_values)
        else:
            concentration = 0.0
        
        # Normalize to 0-1
        return min(max(concentration, 0.0), 1.0)
    
    # ═══════════════════════════════════════════════════════════
    # STEP 8: DIVERSIFICATION SCORE
    # ═══════════════════════════════════════════════════════════
    
    def calculate_diversification_score(self, concentration_score: float) -> float:
        """
        Calculate diversification score.
        
        Simple version: 1 - concentration_score
        
        Args:
            concentration_score: Concentration score 0-1
        
        Returns:
            Diversification score 0-1
        """
        return 1.0 - concentration_score
    
    # ═══════════════════════════════════════════════════════════
    # STEP 9: PORTFOLIO RISK STATE
    # ═══════════════════════════════════════════════════════════
    
    def determine_risk_state(
        self,
        concentration_score: float,
        market_context: MarketContext,
        alt_exposure: float,
    ) -> PortfolioRiskState:
        """
        Determine portfolio risk state.
        
        Rules:
        - concentration < 0.40 → BALANCED
        - 0.40 – 0.65 → CONCENTRATED
        - 0.65 – 0.80 → OVERLOADED
        - breadth weak + alt exposure high → DEFENSIVE
        
        Args:
            concentration_score: Concentration score 0-1
            market_context: Market structure context
            alt_exposure: Alt exposure level
        
        Returns:
            PortfolioRiskState
        """
        thresholds = CONCENTRATION_THRESHOLDS
        
        # Check for DEFENSIVE state first (special condition)
        if market_context.breadth_state == "WEAK" and alt_exposure > 0.50:
            return PortfolioRiskState.DEFENSIVE
        
        # Standard concentration-based classification
        if concentration_score < thresholds["balanced_max"]:
            return PortfolioRiskState.BALANCED
        elif concentration_score < thresholds["concentrated_max"]:
            return PortfolioRiskState.CONCENTRATED
        elif concentration_score < thresholds["overloaded_max"]:
            return PortfolioRiskState.OVERLOADED
        else:
            # Extreme concentration → treat as OVERLOADED
            return PortfolioRiskState.OVERLOADED
    
    # ═══════════════════════════════════════════════════════════
    # STEP 10: RECOMMENDED ACTION
    # ═══════════════════════════════════════════════════════════
    
    def determine_recommended_action(
        self,
        risk_state: PortfolioRiskState,
        market_context: MarketContext,
        factor_overload: Dict,
        alt_exposure: float,
        gross_exposure: float,
    ) -> RecommendedAction:
        """
        Determine recommended portfolio action.
        
        Rules:
        - BALANCED → HOLD
        - BTC_DOM + high alt exposure → REDUCE_ALT
        - one factor overloaded → REDUCE_FACTOR
        - gross exposure too high → DELEVER
        - mixed concentrations → REBALANCE
        
        Args:
            risk_state: Current portfolio risk state
            market_context: Market structure context
            factor_overload: Factor overload detection result
            alt_exposure: Alt exposure level
            gross_exposure: Gross portfolio exposure
        
        Returns:
            RecommendedAction
        """
        # BALANCED state → HOLD
        if risk_state == PortfolioRiskState.BALANCED:
            return RecommendedAction.HOLD
        
        # Check for specific conditions
        
        # Gross exposure too high → DELEVER
        if gross_exposure > GROSS_EXPOSURE_MAX:
            return RecommendedAction.DELEVER
        
        # BTC dominance + high alt exposure → REDUCE_ALT
        if market_context.dominance_regime == "BTC_DOM" and alt_exposure > 0.50:
            return RecommendedAction.REDUCE_ALT
        
        # Factor overloaded → REDUCE_FACTOR
        if factor_overload.get("is_overloaded", False):
            return RecommendedAction.REDUCE_FACTOR
        
        # DEFENSIVE state (from weak breadth + high alt)
        if risk_state == PortfolioRiskState.DEFENSIVE:
            return RecommendedAction.REDUCE_ALT
        
        # CONCENTRATED or OVERLOADED without specific condition → REBALANCE
        if risk_state in [PortfolioRiskState.CONCENTRATED, PortfolioRiskState.OVERLOADED]:
            return RecommendedAction.REBALANCE
        
        # Default
        return RecommendedAction.HOLD
    
    # ═══════════════════════════════════════════════════════════
    # STEP 11: MODIFIERS
    # ═══════════════════════════════════════════════════════════
    
    def get_modifiers(self, risk_state: PortfolioRiskState) -> Dict[str, float]:
        """
        Get confidence and capital modifiers for risk state.
        
        Modifiers:
        - BALANCED: 1.00 / 1.00
        - CONCENTRATED: 0.95 / 0.90
        - OVERLOADED: 0.88 / 0.80
        - DEFENSIVE: 0.85 / 0.75
        
        Args:
            risk_state: Current portfolio risk state
        
        Returns:
            Dict with confidence_modifier and capital_modifier
        """
        return RISK_STATE_MODIFIERS.get(risk_state, {
            "confidence_modifier": 1.0,
            "capital_modifier": 1.0,
        })
    
    # ═══════════════════════════════════════════════════════════
    # FULL ANALYSIS
    # ═══════════════════════════════════════════════════════════
    
    def analyze(
        self,
        cluster_exposure: Dict[str, float],
        factor_exposure: Dict[str, float],
        asset_exposure: Dict[str, float],
        market_context: MarketContext,
        factor_overload: Dict,
        gross_exposure: float,
    ) -> Dict:
        """
        Full portfolio risk analysis.
        
        Returns:
            Dict with concentration, diversification, risk state,
            recommended action, and modifiers
        """
        # Calculate concentration and diversification
        concentration_score = self.calculate_concentration_score(
            cluster_exposure, factor_exposure, asset_exposure
        )
        diversification_score = self.calculate_diversification_score(concentration_score)
        
        # Get alt exposure
        alt_exposure = asset_exposure.get("alt_exposure", 0.0)
        
        # Determine risk state
        risk_state = self.determine_risk_state(
            concentration_score, market_context, alt_exposure
        )
        
        # Determine recommended action
        recommended_action = self.determine_recommended_action(
            risk_state, market_context, factor_overload, alt_exposure, gross_exposure
        )
        
        # Get modifiers
        modifiers = self.get_modifiers(risk_state)
        
        return {
            "concentration_score": concentration_score,
            "diversification_score": diversification_score,
            "portfolio_risk_state": risk_state,
            "recommended_action": recommended_action,
            "confidence_modifier": modifiers["confidence_modifier"],
            "capital_modifier": modifiers["capital_modifier"],
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[PortfolioRiskEngine] = None


def get_portfolio_risk_engine() -> PortfolioRiskEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = PortfolioRiskEngine()
    return _engine
