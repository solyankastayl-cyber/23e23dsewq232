"""
PHASE 21.1 — Capital Router Engine
==================================
Main orchestrator for Capital Allocation Engine v2.

Combines all sub-engines:
- Strategy Capital Engine
- Factor Capital Engine
- Asset Capital Engine
- Cluster Capital Engine

Determines dominant routing and final allocations.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from modules.capital_allocation_v2.capital_allocation_types import (
    CapitalAllocationState,
    DominantRoute,
    RoutingRegime,
    AllocationSlice,
    ALLOCATION_CONFIDENCE_THRESHOLDS,
    ALLOCATION_MODIFIERS,
    ALLOCATION_CONFIDENCE_WEIGHTS,
)
from modules.capital_allocation_v2.strategy_capital_engine import (
    get_strategy_capital_engine,
    StrategyCapitalEngine,
)
from modules.capital_allocation_v2.factor_capital_engine import (
    get_factor_capital_engine,
    FactorCapitalEngine,
)
from modules.capital_allocation_v2.asset_capital_engine import (
    get_asset_capital_engine,
    AssetCapitalEngine,
)
from modules.capital_allocation_v2.cluster_capital_engine import (
    get_cluster_capital_engine,
    ClusterCapitalEngine,
)


class CapitalRouterEngine:
    """
    Capital Router Engine - PHASE 21.1
    
    Main orchestrator for system-wide capital allocation.
    Determines how to route risk budget across:
    - Strategies
    - Factors
    - Assets
    - Clusters
    """
    
    def __init__(self):
        """Initialize engine."""
        self.strategy_engine = get_strategy_capital_engine()
        self.factor_engine = get_factor_capital_engine()
        self.asset_engine = get_asset_capital_engine()
        self.cluster_engine = get_cluster_capital_engine()
        
        # Cache for inputs
        self._market_regime: str = "RANGE"
        self._btc_dominance: float = 0.55
        self._research_loop_modifier: float = 1.0
    
    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════
    
    def compute_allocation(
        self,
        total_capital: float = 1.0,
        market_regime: Optional[str] = None,
        btc_dominance: Optional[float] = None,
        regime_confidence: float = 0.7,
        portfolio_modifier: float = 1.0,
        research_modifier: float = 1.0,
        governance_states: Optional[Dict[str, str]] = None,
        lifecycle_states: Optional[Dict[str, str]] = None,
        recommended_increases: Optional[List[str]] = None,
        recommended_decreases: Optional[List[str]] = None,
    ) -> CapitalAllocationState:
        """
        Compute full capital allocation state.
        
        Returns CapitalAllocationState with all allocations.
        """
        now = datetime.now(timezone.utc)
        
        # Use provided or cached values
        if market_regime is not None:
            self._market_regime = market_regime
        if btc_dominance is not None:
            self._btc_dominance = btc_dominance
        
        # Gather inputs from other systems
        inputs = self._gather_inputs(
            governance_states=governance_states,
            lifecycle_states=lifecycle_states,
            recommended_increases=recommended_increases,
            recommended_decreases=recommended_decreases,
        )
        
        # Compute strategy allocations
        strategy_result = self.strategy_engine.compute_allocations(
            regime_confidence=regime_confidence,
            portfolio_modifier=portfolio_modifier,
            research_modifier=research_modifier,
        )
        
        # Compute factor allocations
        factor_result = self.factor_engine.compute_allocations(
            governance_states=inputs["governance_states"],
            lifecycle_states=inputs["lifecycle_states"],
            recommended_increases=inputs["recommended_increases"],
            recommended_decreases=inputs["recommended_decreases"],
            research_modifier=research_modifier,
        )
        
        # Compute asset allocations
        asset_result = self.asset_engine.compute_allocations(
            btc_dominance=self._btc_dominance,
            market_breadth=inputs.get("market_breadth", 0.5),
            portfolio_concentration=strategy_result["concentration"],
            risk_off_mode=inputs.get("risk_off", False),
        )
        
        # Compute cluster allocations
        cluster_result = self.cluster_engine.compute_allocations(
            strategy_allocations=strategy_result["allocations"],
            asset_allocations=asset_result["allocations"],
            regime=self._map_to_routing_regime(self._market_regime).value,
        )
        
        # Determine dominant route
        dominant_route = self._determine_dominant_route(
            strategy_concentration=strategy_result["concentration"],
            factor_concentration=factor_result["concentration"],
            asset_concentration=asset_result["concentration"],
            cluster_concentration=cluster_result["concentration"],
            regime_confidence=regime_confidence,
            research_modifier=research_modifier,
        )
        
        # Determine routing regime
        routing_regime = self._map_to_routing_regime(self._market_regime)
        
        # Calculate allocation confidence
        allocation_confidence = self._calculate_allocation_confidence(
            strategy_concentration=strategy_result["concentration"],
            factor_health=self.factor_engine.get_factor_health(factor_result["allocations"]),
            portfolio_health=1.0 - strategy_result["concentration"],
            regime_confidence=regime_confidence,
        )
        
        # Calculate concentration score
        concentration_score = self._calculate_concentration_score(
            strategy_result["concentration"],
            factor_result["concentration"],
            asset_result["concentration"],
            cluster_result["concentration"],
        )
        
        # Determine modifiers
        confidence_modifier, capital_modifier = self._calculate_modifiers(
            allocation_confidence=allocation_confidence,
            concentration_score=concentration_score,
        )
        
        # Build reason
        reason = self._build_reason(
            dominant_route=dominant_route,
            routing_regime=routing_regime,
            strategy_result=strategy_result,
            factor_result=factor_result,
        )
        
        return CapitalAllocationState(
            total_capital=total_capital,
            strategy_allocations=strategy_result["allocations"],
            factor_allocations=factor_result["allocations"],
            asset_allocations=asset_result["allocations"],
            cluster_allocations=cluster_result["allocations"],
            dominant_route=dominant_route,
            routing_regime=routing_regime,
            allocation_confidence=allocation_confidence,
            concentration_score=concentration_score,
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            reason=reason,
            strategy_slices=strategy_result["slices"],
            factor_slices=factor_result["slices"],
            timestamp=now,
        )
    
    def get_strategy_allocations(self) -> Dict[str, float]:
        """Get current strategy allocations."""
        result = self.strategy_engine.compute_allocations()
        return result["allocations"]
    
    def get_factor_allocations(self) -> Dict[str, float]:
        """Get current factor allocations."""
        result = self.factor_engine.compute_allocations()
        return result["allocations"]
    
    def get_asset_allocations(self) -> Dict[str, float]:
        """Get current asset allocations."""
        result = self.asset_engine.compute_allocations(btc_dominance=self._btc_dominance)
        return result["allocations"]
    
    def get_cluster_allocations(self) -> Dict[str, float]:
        """Get current cluster allocations."""
        strategy_alloc = self.get_strategy_allocations()
        asset_alloc = self.get_asset_allocations()
        result = self.cluster_engine.compute_allocations(
            strategy_allocations=strategy_alloc,
            asset_allocations=asset_alloc,
        )
        return result["allocations"]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get allocation summary."""
        state = self.compute_allocation()
        return state.to_summary()
    
    # ═══════════════════════════════════════════════════════════
    # INTERNAL METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _gather_inputs(
        self,
        governance_states: Optional[Dict[str, str]] = None,
        lifecycle_states: Optional[Dict[str, str]] = None,
        recommended_increases: Optional[List[str]] = None,
        recommended_decreases: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Gather inputs from various sources."""
        # Try to get from Research Loop
        try:
            from modules.research_loop.aggregator import get_research_loop_engine
            loop_engine = get_research_loop_engine()
            loop_state = loop_engine.compute_state()
            
            if recommended_increases is None:
                recommended_increases = loop_state.recommended_increases
            if recommended_decreases is None:
                recommended_decreases = loop_state.recommended_decreases
            
            self._research_loop_modifier = loop_state.capital_modifier
        except:
            pass
        
        # Try to get from Adaptive Promotion
        try:
            from modules.research_loop.adaptive_promotion import get_adaptive_promotion_registry
            registry = get_adaptive_promotion_registry()
            
            if lifecycle_states is None:
                lifecycle_states = {}
                for factor_name in registry.get_factor_names():
                    state = registry.get_current_state(factor_name)
                    if state:
                        lifecycle_states[factor_name] = state.value
        except:
            pass
        
        # Default governance states
        if governance_states is None:
            governance_states = self._get_default_governance_states()
        
        if lifecycle_states is None:
            lifecycle_states = {}
        
        if recommended_increases is None:
            recommended_increases = []
        
        if recommended_decreases is None:
            recommended_decreases = []
        
        return {
            "governance_states": governance_states,
            "lifecycle_states": lifecycle_states,
            "recommended_increases": recommended_increases,
            "recommended_decreases": recommended_decreases,
            "market_breadth": 0.5,
            "risk_off": False,
        }
    
    def _get_default_governance_states(self) -> Dict[str, str]:
        """Get default governance states for factors."""
        return {
            "funding_factor": "STABLE",
            "trend_breakout_factor": "WATCHLIST",
            "mean_reversion_factor": "STABLE",
            "structure_factor": "DEGRADED",
            "flow_factor": "ELITE",
            "volatility_factor": "STABLE",
            "momentum_factor": "STABLE",
            "liquidation_factor": "WATCHLIST",
            "correlation_factor": "ELITE",
        }
    
    def _determine_dominant_route(
        self,
        strategy_concentration: float,
        factor_concentration: float,
        asset_concentration: float,
        cluster_concentration: float,
        regime_confidence: float,
        research_modifier: float,
    ) -> DominantRoute:
        """Determine the dominant routing dimension."""
        scores = {
            DominantRoute.STRATEGY: strategy_concentration + regime_confidence * 0.3,
            DominantRoute.FACTOR: factor_concentration + (1.0 - research_modifier) * 0.5,
            DominantRoute.ASSET: asset_concentration + self._btc_dominance * 0.2,
            DominantRoute.CLUSTER: cluster_concentration,
        }
        
        max_score = max(scores.values())
        
        # If no clear winner, return BALANCED
        if max_score < 0.4:
            return DominantRoute.BALANCED
        
        return max(scores, key=scores.get)
    
    def _map_to_routing_regime(self, market_regime: str) -> RoutingRegime:
        """Map market regime to routing regime."""
        regime_map = {
            "TREND_UP": RoutingRegime.TREND,
            "TREND_DOWN": RoutingRegime.TREND,
            "TREND": RoutingRegime.TREND,
            "RANGE_LOW_VOL": RoutingRegime.RANGE,
            "RANGE_HIGH_VOL": RoutingRegime.RANGE,
            "RANGE": RoutingRegime.RANGE,
            "SQUEEZE": RoutingRegime.SQUEEZE,
            "SQUEEZE_SETUP_LONG": RoutingRegime.SQUEEZE,
            "SQUEEZE_SETUP_SHORT": RoutingRegime.SQUEEZE,
            "VOL_EXPANSION": RoutingRegime.VOL,
            "VOL": RoutingRegime.VOL,
            "HIGH_VOL": RoutingRegime.VOL,
        }
        return regime_map.get(market_regime.upper(), RoutingRegime.MIXED)
    
    def _calculate_allocation_confidence(
        self,
        strategy_concentration: float,
        factor_health: float,
        portfolio_health: float,
        regime_confidence: float,
    ) -> float:
        """
        Calculate allocation confidence.
        
        allocation_confidence =
            0.35 * strategy_regime_confidence
          + 0.25 * factor_health
          + 0.20 * portfolio_health
          + 0.20 * market_regime_clarity
        """
        weights = ALLOCATION_CONFIDENCE_WEIGHTS
        
        # Strategy regime confidence (inverse of concentration)
        strategy_score = 1.0 - strategy_concentration
        
        confidence = (
            weights["strategy_regime_confidence"] * strategy_score +
            weights["factor_health"] * factor_health +
            weights["portfolio_health"] * portfolio_health +
            weights["market_regime_clarity"] * regime_confidence
        )
        
        return min(1.0, max(0.0, confidence))
    
    def _calculate_concentration_score(
        self,
        strategy_conc: float,
        factor_conc: float,
        asset_conc: float,
        cluster_conc: float,
    ) -> float:
        """Calculate overall concentration score."""
        # Max of all concentrations
        max_conc = max(strategy_conc, factor_conc, asset_conc, cluster_conc)
        
        # Weighted average
        avg_conc = (strategy_conc + factor_conc + asset_conc + cluster_conc) / 4
        
        # Blend: 60% max, 40% avg
        return 0.6 * max_conc + 0.4 * avg_conc
    
    def _calculate_modifiers(
        self,
        allocation_confidence: float,
        concentration_score: float,
    ) -> Tuple[float, float]:
        """Calculate confidence and capital modifiers."""
        # Determine category
        if allocation_confidence >= ALLOCATION_CONFIDENCE_THRESHOLDS["high"]:
            category = "high"
        elif allocation_confidence >= ALLOCATION_CONFIDENCE_THRESHOLDS["normal"]:
            category = "normal"
        else:
            category = "low"
        
        # Adjust for concentration
        modifiers = ALLOCATION_MODIFIERS[category]
        
        conf_mod = modifiers["confidence_modifier"]
        cap_mod = modifiers["capital_modifier"]
        
        # Penalize high concentration
        if concentration_score > 0.5:
            penalty = (concentration_score - 0.5) * 0.1
            conf_mod -= penalty
            cap_mod -= penalty
        
        return round(conf_mod, 4), round(cap_mod, 4)
    
    def _build_reason(
        self,
        dominant_route: DominantRoute,
        routing_regime: RoutingRegime,
        strategy_result: Dict[str, Any],
        factor_result: Dict[str, Any],
    ) -> str:
        """Build human-readable reason."""
        parts = []
        
        parts.append(f"{routing_regime.value.lower()} regime")
        
        if dominant_route == DominantRoute.STRATEGY:
            dominant_strategy = self.strategy_engine.get_dominant_strategy(
                strategy_result["allocations"]
            )
            parts.append(f"strong {dominant_strategy} strategy dominance")
        elif dominant_route == DominantRoute.FACTOR:
            parts.append("factor governance actively adjusting weights")
        elif dominant_route == DominantRoute.ASSET:
            parts.append(f"asset-driven routing with BTC dominance {self._btc_dominance:.0%}")
        elif dominant_route == DominantRoute.CLUSTER:
            parts.append("cluster-based risk distribution")
        else:
            parts.append("balanced multi-dimensional routing")
        
        # Add factor health note
        factor_health = self.factor_engine.get_factor_health(factor_result["allocations"])
        if factor_health > 0.7:
            parts.append("healthy factor distribution")
        elif factor_health < 0.4:
            parts.append("concentrated factor exposure")
        
        return " with ".join(parts)


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[CapitalRouterEngine] = None


def get_capital_router_engine() -> CapitalRouterEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = CapitalRouterEngine()
    return _engine
