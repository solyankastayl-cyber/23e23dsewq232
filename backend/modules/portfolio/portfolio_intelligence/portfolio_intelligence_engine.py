"""
PHASE 18.1 — Portfolio Intelligence Engine
===========================================
Main aggregator for Portfolio Intelligence Layer.

Combines all sub-engines:
- portfolio_exposure_engine: Net/Gross exposure
- factor_exposure_engine: Factor concentration
- cluster_exposure_engine: Asset clusters
- portfolio_risk_engine: Risk state and actions

This layer DOES NOT break signal direction.
It influences:
- confidence
- capital allocation
- portfolio constraints
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.portfolio.portfolio_intelligence.portfolio_intelligence_types import (
    PortfolioIntelligenceState,
    Position,
    PositionDirection,
    MarketContext,
    PortfolioContext,
    PortfolioRiskState,
    RecommendedAction,
)
from modules.portfolio.portfolio_intelligence.portfolio_exposure_engine import (
    get_portfolio_exposure_engine,
)
from modules.portfolio.portfolio_intelligence.factor_exposure_engine import (
    get_factor_exposure_engine,
)
from modules.portfolio.portfolio_intelligence.cluster_exposure_engine import (
    get_cluster_exposure_engine,
)
from modules.portfolio.portfolio_intelligence.portfolio_risk_engine import (
    get_portfolio_risk_engine,
)


# ══════════════════════════════════════════════════════════════
# SIMULATED PORTFOLIO DATABASE
# ══════════════════════════════════════════════════════════════

SIMULATED_PORTFOLIOS = {
    "default": {
        "positions": [
            Position(
                symbol="BTCUSDT",
                direction=PositionDirection.SHORT,
                position_size=0.80,
                final_confidence=0.75,
                primary_factor="trend_breakout_factor",
                secondary_factor="flow_imbalance_factor",
            ),
            Position(
                symbol="ETHUSDT",
                direction=PositionDirection.SHORT,
                position_size=0.50,
                final_confidence=0.70,
                primary_factor="momentum_factor",
                secondary_factor="funding_arb_factor",
            ),
            Position(
                symbol="SOLUSDT",
                direction=PositionDirection.LONG,
                position_size=0.20,
                final_confidence=0.65,
                primary_factor="divergence_factor",
                secondary_factor="volatility_regime_factor",
            ),
        ],
        "market_context": MarketContext(
            dominance_regime="BALANCED",
            breadth_state="MIXED",
            btc_dominance=0.52,
        ),
    },
    "balanced_portfolio": {
        "positions": [
            Position(
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                position_size=0.30,
                final_confidence=0.80,
                primary_factor="trend_breakout_factor",
            ),
            Position(
                symbol="ETHUSDT",
                direction=PositionDirection.LONG,
                position_size=0.25,
                final_confidence=0.75,
                primary_factor="momentum_factor",
            ),
            Position(
                symbol="SOLUSDT",
                direction=PositionDirection.SHORT,
                position_size=0.20,
                final_confidence=0.70,
                primary_factor="mean_reversion_factor",
            ),
            Position(
                symbol="AVAXUSDT",
                direction=PositionDirection.LONG,
                position_size=0.15,
                final_confidence=0.65,
                primary_factor="divergence_factor",
            ),
        ],
        "market_context": MarketContext(
            dominance_regime="BALANCED",
            breadth_state="STRONG",
            btc_dominance=0.48,
        ),
    },
    "btc_concentrated": {
        "positions": [
            Position(
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                position_size=0.85,
                final_confidence=0.82,
                primary_factor="trend_breakout_factor",
                secondary_factor="momentum_factor",
            ),
            Position(
                symbol="ETHUSDT",
                direction=PositionDirection.LONG,
                position_size=0.10,
                final_confidence=0.60,
                primary_factor="trend_continuation_factor",
            ),
        ],
        "market_context": MarketContext(
            dominance_regime="BTC_DOM",
            breadth_state="WEAK",
            btc_dominance=0.58,
        ),
    },
    "alt_overloaded": {
        "positions": [
            Position(
                symbol="SOLUSDT",
                direction=PositionDirection.LONG,
                position_size=0.40,
                final_confidence=0.72,
                primary_factor="momentum_factor",
            ),
            Position(
                symbol="AVAXUSDT",
                direction=PositionDirection.LONG,
                position_size=0.35,
                final_confidence=0.68,
                primary_factor="momentum_factor",
            ),
            Position(
                symbol="ARBUSDT",
                direction=PositionDirection.LONG,
                position_size=0.30,
                final_confidence=0.65,
                primary_factor="divergence_factor",
            ),
            Position(
                symbol="DOGEUSDT",
                direction=PositionDirection.LONG,
                position_size=0.25,
                final_confidence=0.55,
                primary_factor="volatility_breakout_factor",
            ),
        ],
        "market_context": MarketContext(
            dominance_regime="BTC_DOM",
            breadth_state="WEAK",
            btc_dominance=0.55,
        ),
    },
    "factor_overloaded": {
        "positions": [
            Position(
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                position_size=0.50,
                final_confidence=0.78,
                primary_factor="trend_breakout_factor",
                secondary_factor="trend_continuation_factor",
            ),
            Position(
                symbol="ETHUSDT",
                direction=PositionDirection.LONG,
                position_size=0.40,
                final_confidence=0.75,
                primary_factor="trend_breakout_factor",
                secondary_factor="structure_break_factor",
            ),
            Position(
                symbol="SOLUSDT",
                direction=PositionDirection.LONG,
                position_size=0.30,
                final_confidence=0.70,
                primary_factor="trend_continuation_factor",
            ),
        ],
        "market_context": MarketContext(
            dominance_regime="BALANCED",
            breadth_state="STRONG",
            btc_dominance=0.50,
        ),
    },
    "defensive_scenario": {
        "positions": [
            Position(
                symbol="SOLUSDT",
                direction=PositionDirection.LONG,
                position_size=0.45,
                final_confidence=0.65,
                primary_factor="momentum_factor",
            ),
            Position(
                symbol="AVAXUSDT",
                direction=PositionDirection.LONG,
                position_size=0.35,
                final_confidence=0.60,
                primary_factor="divergence_factor",
            ),
            Position(
                symbol="BTCUSDT",
                direction=PositionDirection.SHORT,
                position_size=0.10,
                final_confidence=0.55,
                primary_factor="mean_reversion_factor",
            ),
        ],
        "market_context": MarketContext(
            dominance_regime="BTC_DOM",
            breadth_state="WEAK",
            btc_dominance=0.56,
        ),
    },
    "high_gross_exposure": {
        "positions": [
            Position(
                symbol="BTCUSDT",
                direction=PositionDirection.LONG,
                position_size=0.90,
                final_confidence=0.80,
                primary_factor="trend_breakout_factor",
            ),
            Position(
                symbol="ETHUSDT",
                direction=PositionDirection.LONG,
                position_size=0.80,
                final_confidence=0.78,
                primary_factor="momentum_factor",
            ),
            Position(
                symbol="SOLUSDT",
                direction=PositionDirection.SHORT,
                position_size=0.50,
                final_confidence=0.70,
                primary_factor="mean_reversion_factor",
            ),
        ],
        "market_context": MarketContext(
            dominance_regime="BALANCED",
            breadth_state="MIXED",
            btc_dominance=0.50,
        ),
    },
    "cluster_overloaded": {
        "positions": [
            Position(
                symbol="OPUSDT",
                direction=PositionDirection.LONG,
                position_size=0.40,
                final_confidence=0.72,
                primary_factor="momentum_factor",
            ),
            Position(
                symbol="ARBUSDT",
                direction=PositionDirection.LONG,
                position_size=0.35,
                final_confidence=0.68,
                primary_factor="trend_breakout_factor",
            ),
            Position(
                symbol="MATICUSDT",
                direction=PositionDirection.LONG,
                position_size=0.30,
                final_confidence=0.65,
                primary_factor="divergence_factor",
            ),
        ],
        "market_context": MarketContext(
            dominance_regime="BALANCED",
            breadth_state="MIXED",
            btc_dominance=0.50,
        ),
    },
}


# ══════════════════════════════════════════════════════════════
# PORTFOLIO INTELLIGENCE ENGINE
# ══════════════════════════════════════════════════════════════

class PortfolioIntelligenceEngine:
    """
    Portfolio Intelligence Engine - PHASE 18.1
    
    Meta Portfolio Intelligence Layer.
    
    Key principle:
    - Looks at portfolio as a single risk object
    - Does NOT break signal direction
    - Influences confidence, capital allocation, constraints
    
    Answers:
    - Net/Gross exposure
    - BTC beta / alt exposure
    - Factor concentration
    - Portfolio overcrowding
    """
    
    def __init__(self):
        # Sub-engines
        self.exposure_engine = get_portfolio_exposure_engine()
        self.factor_engine = get_factor_exposure_engine()
        self.cluster_engine = get_cluster_exposure_engine()
        self.risk_engine = get_portfolio_risk_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN ANALYSIS
    # ═══════════════════════════════════════════════════════════
    
    def analyze_portfolio(
        self,
        portfolio_id: str = "default"
    ) -> PortfolioIntelligenceState:
        """
        Full portfolio intelligence analysis.
        
        Args:
            portfolio_id: ID of portfolio to analyze
        
        Returns:
            PortfolioIntelligenceState with full analysis
        """
        # Get portfolio data
        portfolio_data = self._get_portfolio_data(portfolio_id)
        positions = portfolio_data["positions"]
        market_context = portfolio_data["market_context"]
        
        return self.analyze_from_context(
            PortfolioContext(
                positions=positions,
                market_context=market_context,
            )
        )
    
    def analyze_from_context(
        self,
        context: PortfolioContext
    ) -> PortfolioIntelligenceState:
        """
        Analyze portfolio from provided context.
        
        Args:
            context: PortfolioContext with positions and market data
        
        Returns:
            PortfolioIntelligenceState with full analysis
        """
        positions = context.positions
        market_context = context.market_context
        now = datetime.now(timezone.utc)
        
        # STEP 3-4: Calculate exposures
        exposure_result = self.exposure_engine.calculate_exposures(positions)
        asset_exposure = self.exposure_engine.calculate_asset_exposure(positions)
        
        # STEP 5: Calculate factor exposure
        factor_exposure = self.factor_engine.calculate_factor_exposure(positions)
        factor_overload = self.factor_engine.detect_factor_overload(factor_exposure)
        factor_breakdown = self.factor_engine.get_factor_breakdown(positions)
        
        # STEP 6: Calculate cluster exposure
        cluster_exposure = self.cluster_engine.calculate_cluster_exposure(positions)
        cluster_overload = self.cluster_engine.detect_cluster_overload(cluster_exposure)
        cluster_breakdown = self.cluster_engine.get_cluster_breakdown(positions)
        
        # STEP 7-11: Risk analysis
        risk_result = self.risk_engine.analyze(
            cluster_exposure=cluster_exposure,
            factor_exposure=factor_exposure,
            asset_exposure=asset_exposure,
            market_context=market_context,
            factor_overload=factor_overload,
            gross_exposure=exposure_result["gross_exposure"],
        )
        
        # Build asset breakdown
        asset_breakdown = self.exposure_engine.calculate_asset_exposure_directional(positions)
        
        return PortfolioIntelligenceState(
            # Exposure metrics
            net_exposure=exposure_result["net_exposure"],
            gross_exposure=exposure_result["gross_exposure"],
            
            # Asset exposure
            btc_exposure=asset_exposure["btc_exposure"],
            eth_exposure=asset_exposure["eth_exposure"],
            alt_exposure=asset_exposure["alt_exposure"],
            
            # Factor and cluster exposure
            factor_exposure=factor_exposure,
            cluster_exposure=cluster_exposure,
            
            # Concentration metrics
            concentration_score=risk_result["concentration_score"],
            diversification_score=risk_result["diversification_score"],
            
            # Portfolio state
            portfolio_risk_state=risk_result["portfolio_risk_state"],
            recommended_action=risk_result["recommended_action"],
            
            # Modifiers
            confidence_modifier=risk_result["confidence_modifier"],
            capital_modifier=risk_result["capital_modifier"],
            
            # Metadata
            timestamp=now,
            position_count=len(positions),
            long_count=exposure_result["long_count"],
            short_count=exposure_result["short_count"],
            
            # Breakdowns
            asset_breakdown=asset_breakdown,
            factor_breakdown=factor_breakdown,
            cluster_breakdown=cluster_breakdown,
        )
    
    # ═══════════════════════════════════════════════════════════
    # SPECIFIC ENDPOINTS
    # ═══════════════════════════════════════════════════════════
    
    def get_exposures(self, portfolio_id: str = "default") -> Dict:
        """Get exposure metrics only."""
        portfolio_data = self._get_portfolio_data(portfolio_id)
        positions = portfolio_data["positions"]
        
        return self.exposure_engine.get_full_exposures(positions).to_dict()
    
    def get_factors(self, portfolio_id: str = "default") -> Dict:
        """Get factor exposure analysis."""
        portfolio_data = self._get_portfolio_data(portfolio_id)
        positions = portfolio_data["positions"]
        
        exposure = self.factor_engine.calculate_factor_exposure(positions)
        overload = self.factor_engine.detect_factor_overload(exposure)
        breakdown = self.factor_engine.get_factor_breakdown(positions)
        
        return {
            "factor_exposure": exposure,
            "overload_detection": overload,
            "breakdown": breakdown,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def get_clusters(self, portfolio_id: str = "default") -> Dict:
        """Get cluster exposure analysis."""
        portfolio_data = self._get_portfolio_data(portfolio_id)
        positions = portfolio_data["positions"]
        
        exposure = self.cluster_engine.calculate_cluster_exposure(positions)
        overload = self.cluster_engine.detect_cluster_overload(exposure)
        breakdown = self.cluster_engine.get_cluster_breakdown(positions)
        
        return {
            "cluster_exposure": exposure,
            "overload_detection": overload,
            "breakdown": breakdown,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    # ═══════════════════════════════════════════════════════════
    # DATA ACCESS
    # ═══════════════════════════════════════════════════════════
    
    def _get_portfolio_data(self, portfolio_id: str) -> Dict:
        """Get portfolio data by ID."""
        if portfolio_id in SIMULATED_PORTFOLIOS:
            return SIMULATED_PORTFOLIOS[portfolio_id]
        
        # Return default if not found
        return SIMULATED_PORTFOLIOS["default"]
    
    def get_all_known_portfolios(self) -> List[str]:
        """Get list of all known portfolios."""
        return list(SIMULATED_PORTFOLIOS.keys())


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[PortfolioIntelligenceEngine] = None


def get_portfolio_intelligence_engine() -> PortfolioIntelligenceEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = PortfolioIntelligenceEngine()
    return _engine
